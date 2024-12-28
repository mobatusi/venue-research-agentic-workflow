from crewai import Agent, Task, Crew, Process
from crewai.tools import SerperDevTool, WebsiteSearchTool
from typing import Dict, List, Optional
from datetime import datetime
import yaml
from pydantic import BaseModel

class VenueBasicInfo(BaseModel):
    name: str
    type: str
    address: str
    distance_km: float
    contact_info: Dict[str, str]

class VenueFeatures(BaseModel):
    venue_id: str
    features: Dict[str, Dict]
    photos: List[str]
    floor_plans: List[str]

class VenueScore(BaseModel):
    venue_id: str
    total_score: float
    category_scores: Dict[str, float]
    recommendations: List[str]

class EmailTemplate(BaseModel):
    venue_id: str
    recipient: str
    subject: str
    body: str
    custom_elements: Dict
    follow_up_date: datetime

class ReportDocument(BaseModel):
    summary: Dict
    analysis: Dict
    outreach_status: Dict
    visualizations: List[str]
    recommendations: List[str]
    attachments: List[str]

class VenueSearchFlow:
    def __init__(self):
        self.search_tool = SerperDevTool()
        self.web_tool = WebsiteSearchTool()
        self.agents = self._initialize_agents()
        self.state = {
            "venues": [],
            "features": [],
            "scores": [],
            "emails": [],
            "report": None
        }

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
            'scoring_agent': ['VenueScoringAlgorithm', 'PricingAnalyzer'],
            'email_agent': ['EmailTemplateTool', 'ContactEnrichmentAPI'],
            'reporting_agent': ['ReportGenerator', 'DataVisualization', 'PDFCreator']
        }

        agents = {}
        for name, config_path in agent_configs.items():
            config = self._load_config(config_path)
            agent_config = list(config.values())[0]
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
        """Create a task from configuration with enhanced parameters"""
        config = self._load_config(f'config/tasks/{task_type}_tasks.yaml')
        task_config = list(config.values())[0]
        
        task = Task(
            description=task_config['description'].format(**kwargs),
            expected_output=task_config['expected_output'],
            agent=self.agents[task_type.split('_')[0]],
            context=task_config.get('context', ''),
            tools=task_config.get('tools', []),
            async_execution=task_config.get('async', False),
            output_format=task_config.get('output_format', None),
            human_intervention=task_config.get('human_intervention', None)
        )
        
        # Add task-specific output file if specified
        if 'save_to_file' in task_config:
            task.output_file = task_config['save_to_file']
            
        return task

    async def analyze_location(self, address: str, radius_km: float = 5.0) -> List[VenueBasicInfo]:
        """Start the flow by analyzing the specified location"""
        print(f"Starting venue search for location: {address}")
        
        task = self._create_task('location_analysis', address=address, radius_km=radius_km)
        crew = Crew(
            agents=[self.agents['location_analyst']],
            tasks=[task],
            verbose=True
        )
        
        venues = await crew.kickoff()
        self.state["venues"] = [VenueBasicInfo(**venue) for venue in venues["venues"]]
        return self.state["venues"]

    async def extract_venue_features(self, venues: List[VenueBasicInfo]) -> List[VenueFeatures]:
        """Extract features for each identified venue"""
        task = self._create_task('feature_extraction')
        crew = Crew(
            agents=[self.agents['feature_extractor']],
            tasks=[task],
            verbose=True
        )
        
        features = await crew.kickoff()
        self.state["features"] = [VenueFeatures(**feature) for feature in features]
        return self.state["features"]

    async def score_venues(self, features: List[VenueFeatures]) -> List[VenueScore]:
        """Score venues based on their features"""
        task = self._create_task('scoring')
        crew = Crew(
            agents=[self.agents['scoring_agent']],
            tasks=[task],
            verbose=True
        )
        
        scores = await crew.kickoff()
        self.state["scores"] = [VenueScore(**score) for score in scores]
        return self.state["scores"]

    async def generate_emails(self, scores: List[VenueScore]) -> List[EmailTemplate]:
        """Generate emails for high-scoring venues"""
        task = self._create_task('email_engagement')
        crew = Crew(
            agents=[self.agents['email_agent']],
            tasks=[task],
            verbose=True
        )
        
        emails = await crew.kickoff()
        self.state["emails"] = [EmailTemplate(**email) for email in emails]
        return self.state["emails"]

    async def generate_report(self) -> ReportDocument:
        """Generate final report"""
        task = self._create_task('reporting')
        crew = Crew(
            agents=[self.agents['reporting_agent']],
            tasks=[task],
            verbose=True
        )
        
        report = await crew.kickoff()
        self.state["report"] = ReportDocument(**report)
        return self.state["report"]

    async def run_workflow(self, address: str, radius_km: float = 5.0) -> ReportDocument:
        """Execute the complete venue search workflow"""
        venues = await self.analyze_location(address, radius_km)
        features = await self.extract_venue_features(venues)
        scores = await self.score_venues(features)
        emails = await self.generate_emails(scores)
        report = await self.generate_report()
        
        return report 