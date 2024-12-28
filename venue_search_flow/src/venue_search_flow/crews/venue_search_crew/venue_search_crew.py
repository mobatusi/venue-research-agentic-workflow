from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from typing import Dict, List
import os
from venue_search_flow.models.venue_models import (
    VenueBasicInfo,
    VenueFeatures,
    VenueScore,
    EmailTemplate,
    ReportDocument
)
from pydantic import Field
from pathlib import Path
import json
from datetime import datetime

@CrewBase
class VenueSearchCrew:
    """Venue Search Crew for identifying and evaluating potential venues"""

    # Get current directory path and construct config paths
    base_path = os.path.dirname(os.path.abspath(__file__))
    agents_config = os.path.join(base_path, "config", "agents.yaml")
    tasks_config = os.path.join(base_path, "config", "tasks.yaml")

    def __init__(self):
        # Initialize state with default values
        self._state = {
            "address": "333 Adams St, Brooklyn, NY 11201, United States",
            "radius_km": 1.0,
            "venues": [],
            "features": [],
            "scores": [],
            "emails": [],
            "report": None
        }
        # Create output directories
        self.emails_dir = Path("generated_emails")
        self.reports_dir = Path("generated_reports")
        self.emails_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
        self.search_tool = SerperDevTool()
        self.web_tool = ScrapeWebsiteTool()

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
            description=f"Search for venues within {self._state['radius_km']}km of {self._state['address']}",
            agent=self.location_analyst(),
            tools=[self.search_tool],
            expected_output="List of potential venues with details"
        )

    @task
    def extract_features(self) -> Task:
        return Task(
            description="Extract features from identified venues",
            agent=self.feature_extractor(),
            tools=[self.web_tool],
            input_data={"venues": self._state.get("venues", [])},
            expected_output="Detailed venue features"
        )

    @task
    def score_venues(self) -> Task:
        """Creates the Venue Scoring Task"""
        return Task(
            config=self.tasks_config["score_venues"],
            input_data={"features": self._state.get("features", [])}
        )

    @task
    def generate_emails(self) -> Task:
        """Creates the Email Generation Task"""
        return Task(
            description="Generate outreach emails for top venues and save them",
            agent=self.email_agent(),
            tools=[],
            input_data={
                "scores": self._state.get("scores", []),
                "output_dir": str(self.emails_dir)
            },
            expected_output="List of generated email paths and metadata"
        )

    @task
    def generate_report(self) -> Task:
        """Creates the Report Generation Task"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"venue_report_{timestamp}.json"
        
        return Task(
            description="Generate comprehensive venue analysis report",
            agent=self.reporting_agent(),
            tools=[],
            input_data={
                "emails": self._state.get("emails", []),
                "output_path": str(report_path)
            },
            expected_output="Path to generated report and summary"
        )

    def _save_email(self, venue_name: str, email_content: str) -> str:
        """Save email to file and return the path"""
        safe_name = "".join(c for c in venue_name if c.isalnum() or c in (' ', '-', '_')).strip()
        file_path = self.emails_dir / f"{safe_name}_email.txt"
        file_path.write_text(email_content)
        return str(file_path)

    def _save_report(self, report_data: dict) -> str:
        """Save report to file and return the path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.reports_dir / f"venue_report_{timestamp}.json"
        file_path.write_text(json.dumps(report_data, indent=2))
        return str(file_path)

    @crew
    def crew(self, address: str, radius_km: float = 5.0) -> Crew:
        """Creates the Venue Search Crew"""
        # Set state before creating tasks
        self._state["address"] = address
        self._state["radius_km"] = radius_km

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )

    # async def run(self, address: str, radius_km: float = 5.0) -> ReportDocument:
    #     """Execute the venue search workflow"""
    #     crew_instance = self.crew(address, radius_km)
    #     result = await crew_instance.kickoff()
        
    #     # Update state with results
    #     self._state.update(result)
        
    #     return ReportDocument(**self._state["report"]) 