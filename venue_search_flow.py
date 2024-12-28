from crewai.flow.flow import Flow, listen, start
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, WebsiteSearchTool
from typing import Dict, List
import yaml
from pydantic import BaseModel

class Venue(BaseModel):
    name: str
    address: str
    distance_from_location: float
    features: List[str]
    score: float = 0
    contact_email: str = None

class VenueSearchFlow(Flow):
    def __init__(self):
        self.search_tool = SerperDevTool()
        self.web_tool = WebsiteSearchTool()
        self.agents = self._initialize_agents()
        self.state = {"venues": []}

    def _load_config(self, path: str) -> dict:
        """Load a configuration file"""
        with open(path, 'r') as file:
            return yaml.safe_load(file)

    def _initialize_agents(self) -> Dict[str, Agent]:
        """Initialize all agents from configuration files"""
        agent_configs = {
            'location_analyst': 'config/agents/location_analysis_agents.yaml',
            'feature_extractor': 'config/agents/feature_extraction_agents.yaml',
            'scoring_agent': 'config/agents/scoring_agents.yaml',
            'email_agent': 'config/agents/email_engagements_agents.yaml',
            'reporting_agent': 'config/agents/reporting_agents.yaml'
        }

        tools_map = {
            'location_analyst': [self.search_tool, self.web_tool],
            'feature_extractor': [self.web_tool],
            'scoring_agent': [],
            'email_agent': [],
            'reporting_agent': []
        }

        agents = {}
        for name, config_path in agent_configs.items():
            config = self._load_config(config_path)
            agent_config = list(config.values())[0]  # Get first (and only) agent config
            agents[name] = Agent(
                role=agent_config['role'],
                goal=agent_config['goal'],
                backstory=agent_config['backstory'],
                verbose=agent_config['verbose'],
                allow_delegation=agent_config.get('allow_delegation', False),
                tools=tools_map.get(name, [])
            )
        return agents

    def _create_task(self, task_type: str, **kwargs) -> Task:
        """Create a task from configuration"""
        config = self._load_config(f'config/tasks/{task_type}_tasks.yaml')
        task_config = list(config.values())[0]  # Get first (and only) task config
        
        return Task(
            description=task_config['description'].format(**kwargs),
            expected_output=task_config['expected_output'],
            agent=self.agents[task_type.split('_')[0]]  # Get agent name from task type
        )

    @start()
    def analyze_location(self, address: str, radius_km: float = 5.0):
        """Start the flow by analyzing the specified location"""
        print(f"Starting venue search for location: {address}")
        
        task = self._create_task('location_analysis', address=address, radius_km=radius_km)
        crew = Crew(
            agents=[self.agents['location_analyst']],
            tasks=[task],
            verbose=True
        )
        
        venues = crew.kickoff()
        self.state["venues"] = venues
        return venues

    @listen(analyze_location)
    def extract_venue_features(self, venues):
        """Extract features for each identified venue"""
        task = self._create_task('feature_extraction')
        crew = Crew(
            agents=[self.agents['feature_extractor']],
            tasks=[task],
            verbose=True
        )
        
        venue_features = crew.kickoff()
        self.state["venue_features"] = venue_features
        return venue_features

    @listen(extract_venue_features)
    def score_venues(self, venue_features):
        """Score venues based on their features"""
        task = self._create_task('scoring')
        crew = Crew(
            agents=[self.agents['scoring_agent']],
            tasks=[task],
            verbose=True
        )
        
        scored_venues = crew.kickoff()
        self.state["scored_venues"] = scored_venues
        return scored_venues

    @listen(score_venues)
    def generate_emails(self, scored_venues):
        """Generate emails for high-scoring venues"""
        task = self._create_task('email_engagement')
        crew = Crew(
            agents=[self.agents['email_agent']],
            tasks=[task],
            verbose=True
        )
        
        emails = crew.kickoff()
        self.state["emails"] = emails
        return emails

    @listen(generate_emails)
    def generate_report(self, emails):
        """Generate final report"""
        task = self._create_task('reporting')
        crew = Crew(
            agents=[self.agents['reporting_agent']],
            tasks=[task],
            verbose=True
        )
        
        report = crew.kickoff()
        self.state["final_report"] = report
        return report 