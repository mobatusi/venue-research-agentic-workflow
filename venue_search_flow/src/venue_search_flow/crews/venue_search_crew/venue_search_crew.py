from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from langchain.tools import Tool
from langchain_community.utilities import SerpAPIWrapper
from typing import Dict, List
import os
from venue_search_flow.models.venue_models import (
    VenueBasicInfo,
    VenueFeatures,
    VenueScore,
    EmailTemplate,
    ReportDocument
)

@CrewBase
class VenueSearchCrew:
    """Venue Search Crew for identifying and evaluating potential venues"""

    # Get current directory path and construct config paths
    base_path = os.path.dirname(os.path.abspath(__file__))
    agents_config = os.path.join(base_path, "config", "agents.yaml")
    tasks_config = os.path.join(base_path, "config", "tasks.yaml")

    def __init__(self):
        # Initialize SerpAPI search
        search = SerpAPIWrapper(
            serpapi_api_key=os.getenv("SERPER_API_KEY"),
            params={
                "engine": "google",
                "google_domain": "google.com",
                "gl": "us",
                "hl": "en"
            }
        )
        
        # Create search tools
        self.search_tool = Tool(
            name="Search",
            func=search.run,
            description="Search for venue information online"
        )
        
        self.web_tool = Tool(
            name="Detailed Search",
            func=search.run,
            description="Search for detailed venue features and specifications"
        )
        
        self.state = {
            "venues": [],
            "features": [],
            "scores": [],
            "emails": [],
            "report": None
        }

    @agent
    def location_analyst(self) -> Agent:
        """Creates the Location Analysis Agent"""
        return Agent(
            config=self.agents_config["location_analyst"],
        )

    @agent
    def feature_extractor(self) -> Agent:
        """Creates the Feature Extraction Agent"""
        return Agent(
            config=self.agents_config["feature_extractor"],
        )

    @agent
    def scoring_agent(self) -> Agent:
        """Creates the Venue Scoring Agent"""
        return Agent(
            config=self.agents_config["scoring_agent"],
        )

    @agent
    def email_agent(self) -> Agent:
        """Creates the Email Generation Agent"""
        return Agent(
            config=self.agents_config["email_agent"],
        )

    @agent
    def reporting_agent(self) -> Agent:
        """Creates the Reporting Agent"""
        return Agent(
            config=self.agents_config["reporting_agent"],
        )

    @task
    def analyze_location(self) -> Task:
        """Creates the Location Analysis Task"""
        return Task(
            config=self.tasks_config["analyze_location"],
            input_data={"address": self.state.get("address"), "radius_km": self.state.get("radius_km")}
        )

    @task
    def extract_features(self) -> Task:
        return Task(
            config=self.tasks_config["extract_features"],
        )

    @task
    def score_venues(self) -> Task:
        """Creates the Venue Scoring Task"""
        return Task(
            config=self.tasks_config["score_venues"],
        )

    @task
    def generate_emails(self) -> Task:
        """Creates the Email Generation Task"""
        return Task(
            config=self.tasks_config["generate_emails"],
        )

    @task
    def generate_report(self) -> Task:
        """Creates the Report Generation Task"""
        return Task(
            config=self.tasks_config["generate_report"],
        )

    @crew
    def crew(self, address: str, radius_km: float = 5.0) -> Crew:
        """Creates the Venue Search Crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,    # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            input_data={
                "address": address,
                "radius_km": radius_km
            }
        )

    # async def run(self, address: str, radius_km: float = 5.0) -> ReportDocument:
    #     """Execute the venue search workflow"""
    #     crew_instance = self.crew(address, radius_km)
    #     result = await crew_instance.kickoff()
        
    #     # Update state with results
    #     self.state.update(result)
        
    #     return ReportDocument(**self.state["report"]) 