#!/usr/bin/env python
import asyncio
from typing import List

from crewai.flow.flow import Flow, listen, or_, router, start
from pydantic import BaseModel

from venue_score_flow.crews.venue_search_crew.venue_search_crew import VenueSearchCrew
from venue_score_flow.types import InputData, Venue, VenueScore, ScoredVenues


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
        self.state.venues.append(result.pydantic)


async def run_with_inputs(inputs: dict):
    """Run the flow with given inputs"""
    input_data = InputData(**inputs)
    initial_state = VenueScoreState(input_data=input_data)
    
    flow = VenueScoreFlow()
    result = await flow.kickoff_async(inputs=initial_state.model_dump())
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
    asyncio.run(run_with_inputs(inputs))


if __name__ == "__main__":
    run()
