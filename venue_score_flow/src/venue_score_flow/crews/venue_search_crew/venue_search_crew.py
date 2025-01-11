from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from venue_score_flow.types import Venue
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

@CrewBase
class VenueSearchCrew:
    """Venue Search Crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def location_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["location_analyst"],
            tools=[SerperDevTool()],
        )
    
    @task
    def analyze_location(self) -> Task:
        return Task(
            description="""Search for venues near {address} within {radius_km} km radius.
            Return details about each venue including name, address, contact info.""",
            config=self.tasks_config["analyze_location"],
            output_pydantic=Venue
        )

    @crew
    def crew(self) -> Crew:
        """Creates the venue search crew"""
        return Crew(
            agents=[self.location_analyst()],
            tasks=[self.analyze_location()],
            process=Process.sequential,
            verbose=True,
        )
