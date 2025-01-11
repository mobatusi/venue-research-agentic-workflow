from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from venue_score_flow.types import VenueScore

@CrewBase
class VenueScoreCrew:
    """Venue Score Crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def scoring_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["scoring_agent"],
            verbose=True,
        )

    @task
    def score_venues_task(self) -> Task:
        return Task(
            config=self.tasks_config["score_venues"],
            output_pydantic=VenueScore,
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the Venue Score Crew"""
        return Crew(
            agents=[self.scoring_agent()],
            tasks=[self.score_venues_task()],
            process=Process.sequential,
            verbose=True,
        )
