#!/usr/bin/env python
import asyncio
from typing import List
import json

from crewai.flow.flow import Flow, listen, or_, router, start
from pydantic import BaseModel, ValidationError

from venue_score_flow.crews.venue_search_crew.venue_search_crew import VenueSearchCrew
from venue_score_flow.crews.venue_score_crew.venue_score_crew import VenueScoreCrew
from venue_score_flow.crews.venue_reponse_crew.venue_response_crew import VenueResponseCrew
from venue_score_flow.types import InputData, Venue, VenueScore, ScoredVenues, VenueScoreState
from venue_score_flow.utils.venuUtils import combine_venues_with_scores

class VenueScoreState(BaseModel):
    input_data: InputData | None = None
    venues: List[Venue] = []
    venue_score: List[VenueScore] = []
    hydrated_venues: List[ScoredVenues] = []
    scored_venues_feedback: str = ""


class VenueScoreFlow(Flow[VenueScoreState]):
    initial_state = VenueScoreState

    @start()
    async def initialize_state(self) -> None:
        print("Initializing state")
        print("Input data:", self.state.input_data)

    @listen(initialize_state)
    async def search_venues(self):
        print("Searching for venues")
        # Unpack only the needed fields for venue search
        search_inputs = {
            "address": self.state.input_data.address,
            "radius_km": self.state.input_data.radius_km
        }
        
        result = await (
            VenueSearchCrew()
            .crew()
            .kickoff_async(inputs=search_inputs)
        )
        
        # Debug: Print the raw result to inspect the JSON
        print("Raw JSON result:", result.raw)
        
        try:
            # Attempt to parse the JSON string
            venues_data = json.loads(result.raw)
        except json.JSONDecodeError as e:
            # Handle JSON decoding errors
            print("Error decoding JSON:", e)
            return
        
        # Ensure venues_data is a list
        if not isinstance(venues_data, list):
            print("Expected a list of venues, got:", type(venues_data))
            return
        
        for venue_data in venues_data:
            try:
                venue = Venue(**venue_data)  # Convert each item to a Pydantic model
                self.state.venues.append(venue)
            except ValidationError as e:
                print("Validation error for venue data:", e)
        
        # Return the state after processing
        # return self.state
    
    @listen(or_(search_venues, "score_venues_feedback"))
    async def score_venues(self):
        print("Scoring venues")
        tasks = []

        async def score_single_venue(venue: Venue):
            result = await (
                VenueScoreCrew()
                .crew()
                .kickoff_async(
                    inputs={
                        "venue_id": venue.id,
                        "name": venue.name,
                        "type": venue.type,
                        "address": venue.address,
                        "distance_km": venue.distance_km,
                        "website": venue.website,
                        "phone": venue.phone,
                        "email": venue.email,
                        "capacity": venue.capacity,
                        "amenities": venue.amenities,
                        "accessibility": venue.accessibility,
                        "parking": venue.parking,
                        "special_features": venue.special_features,
                        "audio_visual": venue.audio_visual,
                        "technology": venue.technology,
                        "other": venue.other,
                        "additional_instructions": self.state.scored_venues_feedback,
                    }
                )
            )

            self.state.venue_score.append(result.pydantic)

        for venue in self.state.venues:
            print("Scoring venue:", venue.name)
            task = asyncio.create_task(score_single_venue(venue))
            tasks.append(task)

        venue_scores = await asyncio.gather(*tasks)
        print("Finished scoring leads: ", len(venue_scores))

    @router(score_venues)
    def human_in_the_loop(self):
        print("Finding the top 3 venues for human to review")

        # Combine venues with their scores using the helper function
        self.state.hydrated_venues = combine_venues_with_scores(
            self.state.venues, self.state.venue_score
        )

        # Sort the scored venues by their score in descending order
        sorted_venues = sorted(
            self.state.hydrated_venues, key=lambda v: v.score, reverse=True
        )
        self.state.hydrated_venues = sorted_venues

        # Select the top 3 venues
        top_venues = sorted_venues[:3]

        print("Here are the top 3 venues:")
        for venue in top_venues:
            print(
                f"ID: {venue.id}, Name: {venue.name}, Score: {venue.score}, Reason: {venue.reason}"
            )

        # Present options to the user
        print("\nPlease choose an option:")
        print("1. Quit")
        print("2. Redo lead scoring with additional feedback")
        print("3. Proceed with writing emails to all venues")

        choice = input("Enter the number of your choice: ")

        if choice == "1":
            print("Exiting the program.")
            exit()
        elif choice == "2":
            feedback = input(
                "\nPlease provide additional feedback on what you're looking for in venues:\n"
            )
            self.state.scored_venues_feedback = feedback
            print("\nRe-running venue scoring with your feedback...")
            return "score_venues"
        elif choice == "3":
            print("\nProceeding to write emails to all venues.")
            return "generate_emails"
        else:
            print("\nInvalid choice. Please try again.")
            return "human_in_the_loop"    
    
    @listen("generate_emails")
    async def write_and_save_emails(self):
        import re
        from pathlib import Path

        print("Writing and saving emails for all leads.")

        # Determine the top 3 venues to proceed with
        top_venue_ids = {
            venue.id for venue in self.state.hydrated_venues[:3]
        }

        tasks = []

        # Create the directory 'email_responses' if it doesn't exist
        output_dir = Path(__file__).parent / "email_responses"
        print("output_dir:", output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        async def write_email(venue):
            # Check if the venue is among the top 3
            proceed_with_venue = venue.id in top_venue_ids

            # Kick off the VenueResponseCrew for each venue
            result = await (
                VenueResponseCrew()
                .crew()
                .kickoff_async(
                    inputs={
                        "venue_id": venue.id,
                        "name": venue.name,
                        "type": venue.type,
                        "address": venue.address,
                        "distance_km": venue.distance_km,
                        "website": venue.website,
                        "phone": venue.phone,
                        "email": venue.email,
                        "capacity": venue.capacity,
                        "amenities": venue.amenities,
                        "accessibility": venue.accessibility,
                        "parking": venue.parking,
                        "audio_visual": venue.audio_visual,
                        "technology": venue.technology,
                        "other": venue.other,
                        "email_template": self.state.email_template,
                        "proceed_with_venue": proceed_with_venue,
                    }
                )
            )

            # Sanitize the venue's name to create a valid filename
            safe_name = re.sub(r"[^a-zA-Z0-9_\- ]", "", venue.name)
            filename = f"{safe_name}.txt"
            print("Filename:", filename)

            # Write the email content to a text file
            file_path = output_dir / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(result.raw)

            # Return a message indicating the email was saved
            return f"Email saved for {venue.name} as {filename}"

        # Create tasks for all venues
        for venue in self.state.hydrated_venues:
            task = asyncio.create_task(write_email(venue))
            tasks.append(task)

        # Run all email-writing tasks concurrently and collect results
        email_results = await asyncio.gather(*tasks)

        # After all emails have been generated and saved
        print("\nAll emails have been written and saved to 'email_responses' folder.")
        for message in email_results:
            print(message)
        
        return self.state
async def run_with_inputs(inputs: dict):
    """Run the flow with given inputs"""
    input_data = InputData(**inputs)
    initial_state = VenueScoreState(input_data=input_data)
    
    flow = VenueScoreFlow()
    result = await flow.kickoff_async(inputs=initial_state.model_dump())
    
    # Check if result is empty or None
    if not result:
        print("No result returned from kickoff_async.")
        return None
    
    # If result is a JSON string, parse it
    try:
        result_data = json.loads(result)
        result = VenueScoreState(**result_data)
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        return None
    
    return result


def run():
    """Run the flow with default inputs"""
    # Default inputs when running from command line
    inputs = {
        "address": "1333 Adams St, Brooklyn, NY 11201, United States",
        "radius_km": 0.5,
        "event_date": "2024-06-01",
        "linkedin_url": "https://linkedin.com/company/mycompany",
        "instagram_url": "https://instagram.com/mycompany",
        "tiktok_url": "https://tiktok.com/@mycompany",
        "sender_name": "John Doe",
        "sender_email": "john.doe@example.com",
        "email_template": "Default template"
    }
    result = asyncio.run(run_with_inputs(inputs))

    # Write results to JSON file
    with open('venue_search_results.json', 'w', encoding='utf-8') as f:
        f.write(result.model_dump_json(indent=2))
    


if __name__ == "__main__":
    run()
