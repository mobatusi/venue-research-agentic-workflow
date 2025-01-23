#!/usr/bin/env python
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except:
    import sqlite3
    sqlite3.connect(':memory:')


import asyncio
from typing import List, Optional, Dict
import json
import streamlit as st
import sys
import os

from crewai.flow.flow import Flow, listen, or_, router, start
from pydantic import BaseModel, ValidationError, Field

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from venue_score_flow.crews.venue_search_crew.venue_search_crew import VenueSearchCrew
from venue_score_flow.crews.venue_score_crew.venue_score_crew import VenueScoreCrew
from venue_score_flow.crews.venue_reponse_crew.venue_response_crew import VenueResponseCrew
from venue_score_flow.types import InputData, Venue, VenueScore, ScoredVenues
from venue_score_flow.utils.venueUtils import combine_venues_with_scores
from venue_score_flow.constants import EMAIL_TEMPLATE

import uuid

class VenueScoreState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    input_data: InputData | None = None
    venues: List[Venue] = Field(default_factory=list)
    venue_score: List[VenueScore] = Field(default_factory=list)
    hydrated_venues: List[ScoredVenues] = Field(default_factory=list)
    scored_venues_feedback: Optional[str] = None
    generated_emails: Dict[str, str] = Field(default_factory=dict)

class VenueScoreFlow(Flow[VenueScoreState]):
    def __init__(self, openai_key: str, serper_key: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.openai_key = openai_key
        self.serper_key = serper_key

    initial_state = VenueScoreState

    @start()
    async def initialize_state(self) -> None:
        print("1. Starting VenueScoreFlow")
        print("Input data:", self.state.input_data)
        # Set the API keys for use in the flow
        os.environ["OPENAI_API_KEY"] = self.openai_key
        os.environ["SERPER_API_KEY"] = self.serper_key

    @listen("initialize_state")
    async def search_venues(self):
        print("2. Searching for venues")
        
        # Ensure input_data is not None
        if self.state.input_data is None:
            print("Error: input_data is None")
            return

        search_inputs = {
            "address": self.state.input_data.address,
            "radius_km": self.state.input_data.radius_km
        }

        result = await (
            VenueSearchCrew()
            .crew()
            .kickoff_async(inputs=search_inputs)
        )
        
        # Debug: Print the raw result before decoding
        print("Raw result:", result.raw)
        
        if not result.raw:
            print("No data returned from venue search.")
            return
        
        try:
            # result.raw contains a list of venue dictionaries
            venues_data = result.raw if isinstance(result.raw, list) else json.loads(result.raw)
            print("venues_data:", venues_data)
        except json.JSONDecodeError as e:
            print("Error decoding JSON:", e)
            return
        
         # Check if the result is a list or a single venue
        if isinstance(venues_data, dict):
            # If it's a single venue, wrap it in a list
            venues_data = [venues_data]
        elif not isinstance(venues_data, list):
            print("Expected a list of venues, got:", type(venues_data))
            return
        
        for venue_data in venues_data:
            if isinstance(venue_data, dict):
                try:
                    venue = Venue(**venue_data)
                    self.state.venues.append(venue)
                except ValidationError as e:
                    print("Validation error for venue data:", e)
            else:
                print("Unexpected data format for venue:", venue_data)

        # Debug: Check the venues list after processing
        print("Venues after processing:", self.state.venues)

    @listen(or_(search_venues, "score_venues_feedback"))
    async def score_venues(self):
        print("3. score_venues triggered")  # Debugging line
        print(f"Number of venues to score: {len(self.state.venues)}")  # Check number of venues
        print("Scoring venues")
        tasks = []

        async def score_single_venue(venue: Venue):
            print(f"Scoring venue: {venue.name}")
            venue_data = {
                "venue_id": venue.id,
                "name": venue.name,
                "type": venue.type,
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
                "other": venue.other
            }

            if hasattr(self.state, 'scored_venues_feedback'):
                venue_data["additional_instructions"] = self.state.scored_venues_feedback

            result = await VenueScoreCrew().crew().kickoff_async(inputs=venue_data)

            if not result.pydantic:
                print(f"Warning: No score generated for venue {venue.name}")
                return None

            print(f"Generated score for {venue.name}: {result.pydantic}")
            return result.pydantic

        for venue in self.state.venues:
            task = asyncio.create_task(score_single_venue(venue))
            tasks.append(task)

        venue_scores = await asyncio.gather(*tasks)
        self.state.venue_score = [score for score in venue_scores if score is not None]
        
        print(f"Successfully scored {len(self.state.venue_score)} venues")
        print("Venue scores:", self.state.venue_score)

        return "hydrate_venues"

    # @router(score_venues)
    def human_in_the_loop(self):
        print("Finding the top 3 venues for human to review")

        # Combine venues with their scores using the helper function
        self.state.hydrated_venues = combine_venues_with_scores(
            self.state.venues, self.state.venue_score
        )

        # Debug: Print the combined venues to ensure they are correct
        print("Hydrated Venues:", self.state.hydrated_venues)

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
                f"Name: {venue.name}, Score: {venue.score}, Reason: {venue.reason}"
            )

        # Present options to the user using Streamlit
        # options = ["Quit", "Redo lead scoring with additional feedback", "Proceed with writing emails to all venues"]
        # choice = st.selectbox("Please choose an option:", options)
        # Present options to the user
        print("\nPlease choose an option:")
        print("1. Quit")
        print("2. Redo lead scoring with additional feedback")
        print("3. Proceed with writing emails to all leads")

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
            return "score_venues_feedback"
        elif choice == "3":
            print("\nProceeding to write emails to all venues.")
            return "generate_emails"
        else:
            print("\nInvalid choice. Please try again.")
            return "human_in_the_loop"
        
        # if choice == "Quit":
        #     st.write("Exiting the program.")
        #     return  # You may want to handle exiting differently in Streamlit
        # elif choice == "Redo lead scoring with additional feedback":
        #     feedback = st.text_input("Please provide additional feedback on what you're looking for in venues:")
        #     if st.button("Submit Feedback"):
        #         self.state.scored_venues_feedback = feedback
        #         print("\nRe-running venue scoring with your feedback...")
        #         return "score_venues"
        # elif choice == "Proceed with writing emails to all venues":
        #     st.write("\nProceeding to write emails to all venues.")
        #     return "generate_emails"
        # else:
        #     st.write("\nInvalid choice. Please try again.")
        #     return "human_in_the_loop"    
    
    @listen(score_venues)
    async def hydrate_venues(self):
        print("4. Hydrating venues")

        # Combine venues with their scores using the helper function
        self.state.hydrated_venues = combine_venues_with_scores(
            self.state.venues, self.state.venue_score
        )

        # Debug: Print the combined venues to ensure they are correct
        print("Hydrated Venues:", self.state.hydrated_venues)

        # Sort the scored venues by their score in descending order
        sorted_venues = sorted(
            self.state.hydrated_venues, key=lambda v: v.score, reverse=True
        )
        self.state.hydrated_venues = sorted_venues
        return "hydrate_venues"
    
    @listen("hydrate_venues")
    async def write_and_save_emails(self):
        import re
        from pathlib import Path
        # If the email template is empty, use the VenueResponseCrew to generate emails
        if self.state.input_data.email_template == "":
            print("5. Writing and saving emails for all leads.")

            tasks = []

            # Create the directory 'email_responses' if it doesn't exist
            output_dir = Path(__file__).parent / "email_responses"
            print("output_dir:", output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            async def write_email(venue):
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
                            "event_date": self.state.input_data.event_date,
                            "event_time": self.state.input_data.event_time,
                            "sender_name": self.state.input_data.sender_name,
                            "sender_email": self.state.input_data.sender_email,
                        }
                    )
                )

                # Debug: Print the result to ensure it contains the expected data
                print("Result from kickoff_async:", result)

                # Sanitize the venue's name to create a valid filename
                safe_name = re.sub(r"[^a-zA-Z0-9_\- ]", "", venue.name)
                filename = f"{safe_name}.txt"
                print("Filename:", filename)

                # Write the email content to a text file
                file_path = output_dir / filename
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(result.raw)

                # Store the email content in the state
                self.state.generated_emails[venue.name] = result.raw

                # Return a message indicating the email was saved
                return f"Email saved for {venue.name} as {filename}"

            # Create tasks for all venues
            for venue in self.state.hydrated_venues:
                print("Creating email writing task for venue:", venue)
                task = asyncio.create_task(write_email(venue))
                tasks.append(task)

            # Run all email-writing tasks concurrently and collect results
            email_results = await asyncio.gather(*tasks)

            # After all emails have been generated and saved
            if email_results:
                print("\nAll emails have been written and saved to 'email_responses' folder.")
                for message in email_results:
                    print(message)
            else:
                print("No emails were written.")
        
        return self.state
    
async def run_with_inputs(inputs: dict):
    """Run the flow with given inputs"""
    print("inputs:", inputs)
    # Ensure that all required fields are present in the inputs
    required_fields = ['address', 'radius_km', 'event_date', 'event_time', 'sender_name', 'sender_email']
    if not all(key in inputs for key in required_fields):
        print("Error: Missing required input fields.")
        return None

    # Create InputData instance
    input_data = InputData(**inputs)  
    # print("input_data:", input_data)  # Debugging output

    # Ensure to provide a unique id for the state
    initial_state = VenueScoreState(input_data=input_data)  # The id will be generated automatically
    print("initial_state:", initial_state)
    print("initial_state.model_dump():", initial_state.model_dump())
    
    flow = VenueScoreFlow(openai_key=inputs['openai_key'], serper_key=inputs['serper_key'])
    flow._state = initial_state
    print("flow.state:", flow.state)
    result = await flow.kickoff_async()
    
    # Debug: Check the result type and content
    print("Result type:", type(result))
    print("Result content:", result)
    
    # Check if result is a Pydantic model or JSON string
    if isinstance(result, VenueScoreState):
        return result
    elif isinstance(result, str):
        try:
            result_data = json.loads(result)
            return VenueScoreState(**result_data)
        except json.JSONDecodeError as e:
            print("Error decoding JSON:", e)
            return None
    else:
        print("Unexpected result type:", type(result))
        return None


def run():
    """Run the flow with default inputs"""
    # Default inputs when running from command line
    inputs = {
        "address": "1333 Adams St, Brooklyn, NY 11201, United States",
        "radius_km": 0.5,
        "event_date": "2024-06-01",
        "event_time": "10:00 AM",
        "linkedin_url": "https://linkedin.com/company/mycompany",
        "instagram_url": "https://instagram.com/mycompany",
        "tiktok_url": "https://tiktok.com/@mycompany",
        "sender_name": "John Doe",
        "sender_email": "john.doe@example.com",
        "email_template": EMAIL_TEMPLATE
    }
    result = asyncio.run(run_with_inputs(inputs))

    # Ensure result is not None before writing
    if result:
        # Write results to JSON file
        with open('venue_search_results.json', 'w', encoding='utf-8') as f:
            f.write(result.model_dump_json(indent=2))
    else:
        print("No results to write to JSON.")
    


if __name__ == "__main__":
    run()
