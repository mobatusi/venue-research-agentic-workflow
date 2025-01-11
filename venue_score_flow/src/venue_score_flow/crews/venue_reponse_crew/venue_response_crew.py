from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class VenueResponseCrew:
    """Venue Response Crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def email_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["email_followup"],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def write_email_task(self) -> Task:
        return Task(
            config=self.tasks_config["send_followup_email"],
            verbose=True,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Lead Response Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
