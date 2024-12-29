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
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

class VenueSearchState(BaseModel):
    """State management for venue search workflow"""
    address: str = ""  # Will be populated from streamlit app
    radius_km: float = 0.0  # Will be populated from streamlit app
    report: ReportDocument = None
    output_dir: str = None  # Keep as string for Pydantic serialization
    current_step: str = "initialization"
    progress: float = 0.0
    venues: List[Dict] = []
    email_templates: List[Dict] = []

class VenueSearchFlow(Flow[VenueSearchState]):
    """Flow for managing the venue search process"""

    def __init__(self, address: str = "", radius_km: float = 0.5):
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

        # Set the state after flow initialization
        self.state.address = address
        self.state.radius_km = radius_km
        self.state.output_dir = str(output_dir)
        self.state.current_step = "initialization"
        self.state.progress = 0.0
        self.state.venues = []
        self.state.email_templates = []

    def _get_output_dir(self) -> Path:
        """Helper to get output directory as Path object"""
        if not self.state.output_dir:
            raise ValueError("Output directory not set in state")
        return Path(self.state.output_dir) 

    def update_progress(self, step: str, progress: float):
        """Update progress in the state"""
        self.state.current_step = step
        self.state.progress = progress
        print(f"Progress: {step} ({progress*100:.0f}%)")

    @start()
    def initialize_search(self):
        """Initialize the search parameters"""
        if not self.state.output_dir:
            raise ValueError("Output directory not set before initialization")
            
        self.update_progress("initialization", 0.1)
        print(f"Starting venue search for location: {self.state.address} with radius {self.state.radius_km}km")
        print(f"Output directory: {self.state.output_dir}")

    @listen(initialize_search)
    def execute_search(self):
        """Execute the venue search workflow"""
        print("Executing venue search workflow")
        print(f"Flow state before crew creation: address={self.state.address}, radius={self.state.radius_km}")
        
        # Validate output directory
        if not self.state.output_dir:
            raise ValueError("Output directory not set before execution")
            
        # Create crew with current state values
        crew = VenueSearchCrew()
        crew._state = {
            "address": self.state.address,
            "radius_km": self.state.radius_km,
            "venues": [],
            "features": [],
            "scores": [],
            "emails": [],
            "report": None
        }
        print(f"Crew state after initialization: {crew._state}")
        
        # Set output directories
        output_dir = self._get_output_dir()
        crew.emails_dir = output_dir / "emails"
        crew.reports_dir = output_dir / "reports"
        
        # Ensure directories exist
        crew.emails_dir.mkdir(parents=True, exist_ok=True)
        crew.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.update_progress("location_analysis", 0.2)
        print(f"Starting crew with state: {crew._state}")
        result = crew.crew(
            address=self.state.address, 
            radius_km=self.state.radius_km
        ).kickoff()

        # Process the results from each task
        print("Search completed, processing results")
        
        # Each task returns a Pydantic model
        if hasattr(result, 'tasks_outputs') and result.tasks_outputs:
            print(f"Processing {len(result.tasks_outputs)} task outputs")
            for task_output in result.tasks_outputs:
                try:
                    # Convert task output to dict if it's a string
                    if isinstance(task_output, str):
                        try:
                            task_output = json.loads(task_output)
                        except json.JSONDecodeError:
                            print(f"Failed to parse task output as JSON: {task_output[:100]}...")
                            continue
                    
                    print(f"Processing task output: {type(task_output)}")
                    
                    # Handle VenueBasicInfo
                    if isinstance(task_output, dict) and all(k in task_output for k in ["name", "type", "address"]):
                        venue_info = VenueBasicInfo(**task_output)
                        self.state.venues.append({
                            "basic_info": venue_info.dict(),
                            "features": {},
                            "score": {}
                        })
                        print(f"Added venue: {venue_info.name}")
                        self.update_progress("location_analysis", 0.4)
                    
                    # Handle VenueFeatures
                    elif isinstance(task_output, dict) and "venue_id" in task_output and any(k in task_output for k in ["capacity", "amenities"]):
                        features = VenueFeatures(**task_output)
                        venue_id = features.venue_id
                        for venue in self.state.venues:
                            if venue["basic_info"]["name"].lower().replace(" ", "_") == venue_id:
                                venue["features"] = features.dict()
                                print(f"Added features for venue: {venue_id}")
                        self.update_progress("feature_extraction", 0.6)
                    
                    # Handle VenueScore
                    elif isinstance(task_output, dict) and "venue_id" in task_output and "total_score" in task_output:
                        score = VenueScore(**task_output)
                        venue_id = score.venue_id
                        for venue in self.state.venues:
                            if venue["basic_info"]["name"].lower().replace(" ", "_") == venue_id:
                                venue["score"] = score.dict()
                                print(f"Added score for venue: {venue_id}")
                        self.update_progress("scoring", 0.8)
                    
                    # Handle EmailTemplate
                    elif isinstance(task_output, dict) and all(k in task_output for k in ["venue_id", "recipient", "subject", "body"]):
                        template = EmailTemplate(**task_output)
                        self.state.email_templates.append(template.dict())
                        # Save email to file
                        email_path = crew.emails_dir / f"{template.venue_id}_email.txt"
                        with open(email_path, "w") as f:
                            f.write(template.body)
                        print(f"Saved email for venue: {template.venue_id}")
                    
                    # Handle ReportDocument (from agent's final answer)
                    elif isinstance(task_output, dict) and all(k in task_output for k in ["venues_found", "venues_data", "emails_data"]):
                        try:
                            report = ReportDocument(**task_output)
                            self.state.report = report
                            self.update_progress("report_generation", 0.9)
                            print("Added report document from agent's final answer")
                            # Save the raw agent output for reference
                            raw_output_path = output_dir / "reports" / "agent_output.json"
                            with open(raw_output_path, "w") as f:
                                json.dump(task_output, f, indent=2)
                        except Exception as e:
                            print(f"Failed to process agent's final answer: {str(e)}")
                
                except Exception as e:
                    print(f"Error processing task output: {str(e)}")
                    print(f"Task output type: {type(task_output)}")
                    if isinstance(task_output, dict):
                        print(f"Task output keys: {task_output.keys()}")
                    continue
            
            print(f"Processed all task outputs. Found {len(self.state.venues)} venues and {len(self.state.email_templates)} emails")

    @listen(execute_search)
    def save_report(self):
        """Save the final report"""
        self.update_progress("report_generation", 0.9)
        print("Saving venue search report")
        
        # Always generate a fresh report with actual data
        print("Generating report with actual data...")
        
        # Convert venues to JSON string, ensuring we have all data
        venues_data = []
        for venue in self.state.venues:
            venue_data = {
                "basic_info": venue["basic_info"],
                "features": venue.get("features", {}),
                "score": venue.get("score", {})
            }
            venues_data.append(venue_data)
        venues_json = json.dumps(venues_data)
        
        # Convert email templates to JSON string
        emails_json = json.dumps(self.state.email_templates)
        
        # Get email file paths
        email_paths = []
        for template in self.state.email_templates:
            email_file = f"{template['venue_id']}_email.txt"
            email_path = self._get_output_dir() / "emails" / email_file
            if email_path.exists():
                email_paths.append(email_file)
        
        # Collect all recommendations from venue scores
        all_recommendations = []
        for venue in self.state.venues:
            if "score" in venue and venue["score"].get("recommendations"):
                recs = venue["score"]["recommendations"].split(";")
                all_recommendations.extend([rec.strip() for rec in recs if rec.strip()])
        
        # Create or update report
        report = ReportDocument(
            venues_found=len(self.state.venues),
            emails_generated=len(self.state.email_templates),
            venues_data=venues_json,
            emails_data=emails_json,
            emails_saved=",".join(email_paths),
            visualizations="",  # No visualizations yet
            recommendations=";".join(all_recommendations) if all_recommendations else "No specific recommendations",
            attachments=""  # No attachments yet
        )
        
        # Save report summary
        output_dir = self._get_output_dir()
        report_path = output_dir / "reports" / "search_report.json"
        
        # Print debug information
        print(f"Found {len(self.state.venues)} venues")
        print(f"Generated {len(self.state.email_templates)} emails")
        print(f"Recommendations: {';'.join(all_recommendations) if all_recommendations else 'None'}")
        
        with open(report_path, "w") as f:
            json.dump(report.dict(), f, indent=2)
        
        print(f"Report saved to {report_path}")
        self.update_progress("completed", 1.0)
        
        # Update state with the new report
        self.state.report = report
        
        # Return as a dictionary that will be converted to a FlowOutput
        return {
            "output_dir": self.state.output_dir,
            "report_path": str(report_path),
            "current_step": self.state.current_step,
            "progress": self.state.progress
        }

def kickoff(address: str, radius_km: float = 0.5) -> dict:
    """Execute the venue search workflow"""
    # Set API keys
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY")
    
    # Initialize and run the flow
    flow = VenueSearchFlow(address=address, radius_km=radius_km)
    result = flow.kickoff()
    with open("flow_output.json", "w") as f:
        json.dump(result, f, indent=2)
    
    # Return the output paths and progress
    return {
        "output_dir": flow.state.output_dir,
        "report_path": str(Path(flow.state.output_dir) / "reports" / "search_report.json"),
        "current_step": flow.state.current_step,
        "progress": flow.state.progress
    }

def plot():
    """Generate a visualization of the flow"""
    flow = VenueSearchFlow()
    flow.plot()

if __name__ == "__main__":
    # This is just for testing the script directly
    print("This script is meant to be imported by the Streamlit app.")
    print("Please run the Streamlit app instead.")