#!/usr/bin/env python
from pydantic import BaseModel, Field
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
    address: str = Field(default="")  # Will be populated from streamlit app
    radius_km: float = Field(default=0.5)  # Will be populated from streamlit app
    email_template: str | None = Field(default=None)  # Will be populated from streamlit app
    report: ReportDocument | None = Field(default=None)
    output_dir: str | None = Field(default=None)  # Keep as string for Pydantic serialization
    current_step: str = Field(default="initialization")
    progress: float = Field(default=0.0)
    venues: List[Dict] = Field(default_factory=list)
    email_templates: List[Dict] = Field(default_factory=list)
    task_outputs: Dict = Field(default_factory=dict)

class VenueSearchFlow(Flow[VenueSearchState]):
    """Flow for managing the venue search process"""

    def __init__(self):
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
        
        # Store output directory for later use
        self._output_dir = str(output_dir)

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
        # Set output directory in state
        self.state.output_dir = self._output_dir
            
        self.update_progress("initialization", 0.1)
        self.logger.info(f"Starting venue search for location: {self.state.address} with radius {self.state.radius_km}km")
        self.logger.info(f"Output directory: {self.state.output_dir}")
        
        return {
            "address": self.state.address,
            "radius_km": self.state.radius_km,
            "email_template": self.state.email_template
        }

    @listen(initialize_search)
    def execute_search(self, search_params):
        """Execute the venue search flow"""
        self.logger.info(f"\n=== Starting Venue Search Flow ===")
        self.logger.info(f"Search Parameters: {json.dumps(search_params, indent=2)}")
        
        try:
            # Create crew instance and execute
            crew = VenueSearchCrew(logger=self.logger)
            
            # Execute crew with inputs
            result = crew.crew().kickoff(inputs=search_params)
            
            # Update flow state with crew results
            if hasattr(result, 'tasks_outputs'):
                for task_output in result.tasks_outputs:
                    if isinstance(task_output, dict):
                        if 'venues' in task_output:
                            self.state.venues.extend(task_output['venues'])
                        if 'features' in task_output:
                            self.state.features.extend(task_output['features'])
            
            self.logger.info("\n=== Venue Search Flow Complete ===")
            self.logger.info(f"Result: {json.dumps(result, indent=2) if isinstance(result, dict) else str(result)}")
            
            # Save flow output
            output_dir = self._get_output_dir()
            flow_output_path = output_dir / "flow_output.json"
            with open(flow_output_path, "w") as f:
                json.dump({
                    'state': {
                        'venues': self.state.venues,
                        'features': self.state.features,
                        'current_step': self.state.current_step,
                        'progress': self.state.progress
                    },
                    'result': result if isinstance(result, dict) else str(result)
                }, f, indent=2)
            
            return result
            
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
        if isinstance(self.state.report, ReportDocument):
            self.logger.info(f"- Venues found: {self.state.report.venues_found}")
            self.logger.info(f"- Emails generated: {self.state.report.emails_generated}")
            if self.state.report.recommendations:
                self.logger.info(f"- Recommendations: {self.state.report.recommendations}")
        else:
            self.logger.warning("Report is not a ReportDocument instance")
        
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
    
    # Initialize flow
    flow = VenueSearchFlow()
    
    # Initialize state values
    flow.state.address = address
    flow.state.radius_km = radius_km
    flow.state.email_template = email_template
    
    # Log initial state
    logger = logging.getLogger(__name__)
    logger.info(f"Initial flow state: {flow.state}")
    
    # Run the flow and get result
    result = flow.kickoff()
    
    # Log the flow execution
    logger.info(f"Flow state after execution: {flow.state}")
    logger.info(f"Flow result: {result}")
    
    # Return combined output
    return {
        "output_dir": flow.state.output_dir,
        "current_step": flow.state.current_step,
        "progress": flow.state.progress,
        "result": result
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