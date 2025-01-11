from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class VenueResponseCrew:
    """Venue Response Crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def email_followup_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["email_followup_agent"],
            verbose=True,
            allow_delegation=False,
        )

    @task
    def send_followup_email_task(self) -> Task:
        return Task(
            config=self.tasks_config["send_followup_email"],
            verbose=True,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Venue Response Crew"""
        return Crew(
            agents=[self.email_followup_agent()],
            tasks=[self.send_followup_email_task()],
            process=Process.sequential,
            verbose=True,
        )