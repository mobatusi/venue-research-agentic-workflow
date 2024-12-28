#!/usr/bin/env python
from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start
from venue_search_flow.crews.venue_search_crew.venue_search_crew import VenueSearchCrew
from venue_search_flow.models.venue_models import ReportDocument
import os

class VenueSearchState(BaseModel):
    """State management for venue search workflow"""
    address: str = "333 Adams St, Brooklyn, NY 11201, United States"
    radius_km: float = 1.0
    report: ReportDocument = None

class VenueSearchFlow(Flow[VenueSearchState]):
    """Flow for managing the venue search process"""

    def __init__(self, address: str = "", radius_km: float = 1.0):
        self._state = VenueSearchState(
            address=address,
            radius_km=radius_km
        )
        super().__init__()

    @start()
    def initialize_search(self):
        """Initialize the search parameters"""
        print(f"Starting venue search for location: {self.state.address} with radius {self.state.radius_km}km")
        # Could add validation or preprocessing here

    @listen(initialize_search)
    def execute_search(self):
        """Execute the venue search workflow"""
        print("Executing venue search workflow")
        result = (
            VenueSearchCrew()
            .crew(address=self.state.address, radius_km=self.state.radius_km)
            .kickoff()
        )

        print("Search completed, processing results")
        self.state.report = ReportDocument(**result["report"])

    @listen(execute_search)
    def save_report(self):
        """Save the final report"""
        print("Saving venue search report")
        # Save report to file
        report_path = "venue_search_report.json"
        self.state.report.json(path=report_path)
        print(f"Report saved to {report_path}")

def kickoff(address: str, radius_km: float = 5.0):
    """Execute the venue search workflow"""
    # Set API keys
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY")
    
    # Initialize and run the flow
    flow = VenueSearchFlow(address=address, radius_km=radius_km)
    flow.kickoff()

def plot():
    """Generate a visualization of the flow"""
    flow = VenueSearchFlow()
    flow.plot()

if __name__ == "__main__":
    # Example usage
    kickoff(
        address="333 Adams St, Brooklyn, NY 11201, United States",
        radius_km=1.0
    )