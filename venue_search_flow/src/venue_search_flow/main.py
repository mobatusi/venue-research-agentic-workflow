#!/usr/bin/env python
from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start
from venue_search_flow.crews.venue_search_crew.venue_search_crew import VenueSearchCrew
from venue_search_flow.models.venue_models import (
    ReportDocument,
    VenueBasicInfo,
    VenueFeatures,
    VenueScore,
    EmailTemplate
)
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

class VenueSearchState(BaseModel):
    """State management for venue search workflow"""
    address: str = ""  # Will be populated from streamlit app
    radius_km: float = 0.0  # Will be populated from streamlit app
    email_template: str = None  # Will be populated from streamlit app
    report: ReportDocument = None
    output_dir: str = None  # Keep as string for Pydantic serialization
    current_step: str = "initialization"
    progress: float = 0.0
    venues: List[Dict] = []
    email_templates: List[Dict] = []

class VenueSearchFlow(Flow[VenueSearchState]):
    """Flow for managing the venue search process"""

    def __init__(self, address: str = "", radius_km: float = 0.5, email_template: str = None):
        # Initialize the flow first
        super().__init__()
        
        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = Path("outputs")
        output_dir = base_dir / f"search_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (output_dir / "reports").mkdir(exist_ok=True)
        (output_dir / "emails").mkdir(exist_ok=True)
        
        # Set up logging
        log_dir = output_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "venue_search.log"
        
        # Configure logging with a new logger instance
        self.logger = logging.getLogger(f"venue_search_{timestamp}")
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"Starting new venue search session at {timestamp}")

        # Set the state after flow initialization
        self.state.address = address
        self.state.radius_km = radius_km
        self.state.email_template = email_template
        self.state.output_dir = str(output_dir)
        self.state.current_step = "initialization"
        self.state.progress = 0.0
        self.state.venues = []
        self.state.email_templates = []
        
        self.logger.info(f"Initialized flow with address: {address} and radius: {radius_km}km")

    def _get_output_dir(self) -> Path:
        """Helper to get output directory as Path object"""
        if not self.state.output_dir:
            self.logger.error("Output directory not set in state")
            raise ValueError("Output directory not set in state")
        return Path(self.state.output_dir) 

    def update_progress(self, step: str, progress: float):
        """Update progress in the state"""
        self.state.current_step = step
        self.state.progress = progress
        self.logger.info(f"Progress: {step} ({progress*100:.0f}%)")

    @start()
    def initialize_search(self):
        """Initialize the search parameters"""
        if not self.state.output_dir:
            self.logger.error("Output directory not set before initialization")
            raise ValueError("Output directory not set before initialization")
            
        self.update_progress("initialization", 0.1)
        self.logger.info(f"Starting venue search for location: {self.state.address} with radius {self.state.radius_km}km")
        self.logger.info(f"Output directory: {self.state.output_dir}")

    @listen(initialize_search)
    def execute_search(self):
        """Execute the venue search workflow"""
        self.logger.info("Executing venue search workflow")
        self.logger.info(f"Flow state before crew creation: address={self.state.address}, radius={self.state.radius_km}")
        
        # Validate output directory
        if not self.state.output_dir:
            self.logger.error("Output directory not set before execution")
            raise ValueError("Output directory not set before execution")
            
        # Create crew with current state values and pass logger
        crew = VenueSearchCrew(logger=self.logger)
        crew._state = {
            "address": self.state.address,
            "radius_km": self.state.radius_km,
            "email_template": self.state.email_template,
            "venues": [],
            "features": [],
            "scores": [],
            "emails": [],
            "report": None
        }
        self.logger.info(f"Crew state after initialization: {crew._state}")
        
        # Set output directories
        output_dir = self._get_output_dir()
        crew.emails_dir = output_dir / "emails"
        crew.reports_dir = output_dir / "reports"
        
        # Ensure directories exist
        crew.emails_dir.mkdir(parents=True, exist_ok=True)
        crew.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.update_progress("location_analysis", 0.2)
        self.logger.info(f"Starting crew with state: {crew._state}")
        
        try:
            # Execute the crew
            crew_instance = crew.crew(
                address=self.state.address, 
                radius_km=self.state.radius_km,
                email_template=self.state.email_template
            )
            if not crew_instance:
                self.logger.error("Failed to create crew instance")
                return
                
            result = crew_instance.kickoff()
            if not result:
                self.logger.error("Crew execution failed - no result returned")
                return
                
            self.logger.info("Crew execution completed successfully")
            
            # Process the results from each task
            self.logger.info("Processing results")
            
            if not hasattr(result, 'tasks_outputs'):
                self.logger.error("No task outputs in result")
                return
                
            self.logger.info(f"Processing {len(result.tasks_outputs)} task outputs")
            
            # Track if we've processed a report
            report_processed = False
            
            for task_output in result.tasks_outputs:
                try:
                    # Convert task output to dict if it's a string
                    if isinstance(task_output, str):
                        try:
                            task_output = json.loads(task_output)
                        except json.JSONDecodeError:
                            self.logger.error(f"Failed to parse task output as JSON: {task_output[:100]}...")
                            continue
                    
                    self.logger.info(f"Processing task output: {type(task_output)}")
                    
                    # Handle VenueBasicInfo
                    if isinstance(task_output, dict) and all(k in task_output for k in ["name", "type", "address"]):
                        venue_info = VenueBasicInfo(**task_output)
                        self.state.venues.append({
                            "basic_info": venue_info.dict(),
                            "features": {},
                            "score": {}
                        })
                        self.logger.info(f"Added venue: {venue_info.name}")
                        self.update_progress("location_analysis", 0.4)
                    
                    # Handle VenueFeatures
                    elif isinstance(task_output, dict) and "venue_id" in task_output and any(k in task_output for k in ["capacity", "amenities"]):
                        features = VenueFeatures(**task_output)
                        venue_id = features.venue_id
                        for venue in self.state.venues:
                            if venue["basic_info"]["name"].lower().replace(" ", "_") == venue_id:
                                venue["features"] = features.dict()
                                self.logger.info(f"Added features for venue: {venue_id}")
                        self.update_progress("feature_extraction", 0.6)
                    
                    # Handle VenueScore
                    elif isinstance(task_output, dict) and "venue_id" in task_output and "total_score" in task_output:
                        score = VenueScore(**task_output)
                        venue_id = score.venue_id
                        for venue in self.state.venues:
                            if venue["basic_info"]["name"].lower().replace(" ", "_") == venue_id:
                                venue["score"] = score.dict()
                                self.logger.info(f"Added score for venue: {venue_id}")
                        self.update_progress("scoring", 0.8)
                    
                    # Handle EmailTemplate
                    elif isinstance(task_output, dict) and all(k in task_output for k in ["venue_id", "recipient", "subject", "body"]):
                        template = EmailTemplate(**task_output)
                        self.state.email_templates.append(template.model_dump())
                        self.logger.info(f"Added email for venue: {template.venue_id}")
                    
                    # Handle ReportDocument (from agent's final answer)
                    elif isinstance(task_output, dict) and all(k in task_output for k in ["venues_found", "venues_data", "emails_data"]):
                        try:
                            report = ReportDocument(**task_output)
                            self.state.report = report
                            report_processed = True
                            self.update_progress("report_generation", 0.9)
                            self.logger.info("Added report document from agent's final answer")
                        except Exception as e:
                            self.logger.error(f"Failed to process agent's final answer: {str(e)}")
                
                except Exception as e:
                    self.logger.error(f"Error processing task output: {str(e)}")
                    self.logger.error(f"Task output type: {type(task_output)}")
                    if isinstance(task_output, dict):
                        self.logger.error(f"Task output keys: {task_output.keys()}")
                    continue
            
            self.logger.info(f"Processed all task outputs. Found {len(self.state.venues)} venues and {len(self.state.email_templates)} emails")
            
            # If we haven't processed a report yet, try to get it from the crew's state
            if not report_processed and hasattr(crew, '_state'):
                crew_report = crew._state.get('report')
                if isinstance(crew_report, dict):
                    try:
                        self.state.report = ReportDocument(**crew_report)
                        self.logger.info("Retrieved report from crew state")
                        report_processed = True
                    except Exception as e:
                        self.logger.error(f"Failed to get report from crew state: {str(e)}")
                else:
                    self.logger.error(f"Crew state report has invalid type: {type(crew_report)}")
            
            # If we still don't have a report, try to read it from the file
            if not report_processed:
                try:
                    report_path = output_dir / "reports" / "report_generation_output.json"
                    if report_path.exists():
                        with open(report_path) as f:
                            report_data = json.load(f)
                            self.state.report = ReportDocument(**report_data)
                            self.logger.info("Retrieved report from file")
                            report_processed = True
                except Exception as e:
                    self.logger.error(f"Failed to read report from file: {str(e)}")
            
            if not report_processed:
                self.logger.error("Failed to process or find report data")
                
        except Exception as e:
            self.logger.error(f"Error during crew execution: {str(e)}")
            raise

    @listen(execute_search)
    def save_report(self):
        """Save the final report"""
        self.update_progress("report_generation", 0.9)
        self.logger.info("Saving venue search report")
        
        # The report data should already be in self.state.report from the crew's output
        if not self.state.report:
            self.logger.error("No report data found in state")
            return {
                "output_dir": self.state.output_dir,
                "current_step": "error",
                "progress": 0.0
            }
        
        # Log report summary
        self.logger.info(f"Report summary:")
        self.logger.info(f"- Venues found: {self.state.report.venues_found}")
        self.logger.info(f"- Emails generated: {self.state.report.emails_generated}")
        if self.state.report.recommendations:
            self.logger.info(f"- Recommendations: {self.state.report.recommendations}")
        
        self.update_progress("completed", 1.0)
        
        # Return as a dictionary that will be converted to a FlowOutput
        return {
            "output_dir": self.state.output_dir,
            "current_step": self.state.current_step,
            "progress": self.state.progress
        }

def kickoff(address: str, radius_km: float = 0.5, email_template: str = None) -> dict:
    """Execute the venue search workflow"""
    # Set API keys
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY")
    
    # Initialize and run the flow
    flow = VenueSearchFlow(address=address, radius_km=radius_km, email_template=email_template)
    result = flow.kickoff()
    
    # Save flow output
    output_dir = Path(flow.state.output_dir)
    flow_output_path = output_dir / "flow_output.json"
    with open(flow_output_path, "w") as f:
        json.dump(result, f, indent=2)
    
    # Return the output paths and progress
    return {
        "output_dir": flow.state.output_dir,
        "current_step": flow.state.current_step,
        "progress": flow.state.progress
    }

def plot():
    """Generate a visualization of the flow"""
    flow = VenueSearchFlow()
    flow.plot()

if __name__ == "__main__":
    # This is just for testing the script directly
    logger = logging.getLogger(__name__)
    logger.info("This script is meant to be imported by the Streamlit app.")
    logger.info("Please run the Streamlit app instead.")