from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from typing import Dict, List, Union
import os
import logging
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

    def __init__(self, logger=None):
        # Set up logger
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize state with default values
        self._state = {
            "address": "",  # Will be set from main.py
            "radius_km": 0.5,  # Default value, will be overridden from main.py
            "email_template": None,
            "venues": [],
            "features": [],
            "scores": [],
            "emails": [],
            "report": None,
            "task_outputs": {}  # Add storage for task outputs
        }
        
        # Store task instances
        self.analyze_task = None
        self.feature_task = None
        self.score_task = None
        self.email_task = None
        self.report_task = None
        
        # Create output directories
        self.emails_dir = Path("generated_emails")
        self.reports_dir = Path("generated_reports")
        self.emails_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
        self.search_tool = SerperDevTool()
        self.web_tool = ScrapeWebsiteTool()
        
        # Initialize task cache
        self._task_cache = {}

    def initialize_state(self, address: str, radius_km: float = 0.5, email_template: str = None) -> None:
        """Initialize the crew state with search parameters"""
        self.logger.info("\n=== Initializing Venue Search State ===")
        self.logger.info(f"Target Location: {address}")
        self.logger.info(f"Search Radius: {radius_km}km")
        self.logger.info(f"Initial state before update: {self._state}")
        
        # Reset and set state
        self._state.update({
            "address": address,
            "radius_km": radius_km,
            "email_template": email_template,
            "venues": [],
            "features": [],
            "scores": [],
            "emails": [],
            "report": None,
            "task_outputs": {}
        })
        
        # Clear task cache to ensure fresh creation with new state
        self._task_cache = {}
        
        self.logger.info(f"State after initialization: {self._state}")

    def _add_venue_to_state(self, venue_info: dict) -> None:
        """Add venue to state and log the update"""
        self.logger.info("\n=== Adding Venue to State ===")
        self.logger.info(f"Venue info to add: {json.dumps(venue_info, indent=2)}")
        
        # Add venue to state
        self._state["venues"].append(venue_info)
        
        # Log the update
        self.logger.info(f"Added venue: {venue_info['name']}")
        self.logger.info(f"Total venues in state: {len(self._state['venues'])}")
        self.logger.info(f"Current venues in state: {json.dumps(self._state['venues'], indent=2)}")
        self.logger.info("=== Venue Addition Complete ===\n")
        
    def _save_task_output(self, task_name: str, output_data: Union[dict, list, str]) -> None:
        """Save task output to JSON file and update state"""
        output_path = Path(self.reports_dir) / f"{task_name}_output.json"
        
        try:
            # Parse output_data if it's a string
            if isinstance(output_data, str):
                self.logger.info("Parsing string output as JSON")
                try:
                    # Try to parse as array first
                    start_idx = output_data.find('[')
                    if start_idx >= 0:
                        end_idx = output_data.rfind(']') + 1
                        json_str = output_data[start_idx:end_idx]
                    else:
                        # Try to parse as object
                        start_idx = output_data.find('{')
                        end_idx = output_data.rfind('}') + 1
                        json_str = output_data[start_idx:end_idx]
                    
                    if start_idx >= 0 and end_idx > start_idx:
                        parsed_data = json.loads(json_str)
                        self.logger.info("Successfully parsed string output as JSON")
                        output_data = parsed_data
                    else:
                        self.logger.error("Could not find JSON object/array in string output")
                        return
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse string as JSON: {str(e)}")
                    self.logger.error(f"Problematic string: {output_data[:200]}...")
                    return
            
            # At this point output_data should be dict or list
            if not isinstance(output_data, (dict, list)):
                self.logger.error(f"Unexpected output type after parsing: {type(output_data)}")
                return
            
            # Save to file
            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2)
            self.logger.info(f"Saved {task_name} output to {output_path}")
            
            # Update task outputs in state
            self._state["task_outputs"][task_name] = output_data
            self.logger.info(f"Updated state with {task_name} output")
            
            # Process specific task outputs
            if task_name == "analyze_location" and output_data:
                # Handle list or single venue
                venues_list = output_data if isinstance(output_data, list) else [output_data]
                
                # Process each venue
                for venue_data in venues_list:
                    if not isinstance(venue_data, dict):
                        self.logger.error(f"Invalid venue data type: {type(venue_data)}")
                        continue
                        
                    venue_info = {
                        "name": venue_data.get("name", ""),
                        "type": venue_data.get("type", ""),
                        "address": venue_data.get("address", ""),
                        "distance_km": venue_data.get("distance_km", 0.0),
                        "website": venue_data.get("website", ""),
                        "phone": venue_data.get("phone", ""),
                        "email": venue_data.get("email", "N/A")  # Use N/A as default for email
                    }
                    self._add_venue_to_state(venue_info)
            
            self.logger.info(f"Current state after {task_name}: {json.dumps(self._state, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"Error saving task output: {str(e)}")
            self.logger.error(f"Output data type: {type(output_data)}")
            self.logger.error(f"Output data: {json.dumps(output_data, indent=2) if isinstance(output_data, (dict, list)) else str(output_data)}")
            raise

    def _create_task_callback(self, task_name: str):
        """Create a callback for handling task output"""
        def callback(task_output):
            self.logger.info(f"\n=== Processing {task_name} Output ===")
            try:
                if hasattr(task_output, 'raw'):
                    output_data = task_output.raw
                    self.logger.info(f"Raw output: {json.dumps(output_data, indent=2) if isinstance(output_data, (dict, list)) else output_data}")
                    
                    # Save and process the output
                    self._save_task_output(task_name, output_data)
                    
                    self.logger.info(f"=== {task_name} Processing Complete ===\n")
                    return task_output
                else:
                    self.logger.warning(f"No raw output found for {task_name}")
                    return task_output
            except Exception as e:
                self.logger.error(f"Error processing {task_name} output: {str(e)}")
                raise
        return callback

    @agent
    def location_analyst(self) -> Agent:
        """Creates the Location Analysis Agent"""
        return Agent(
            role="Certified Venue Research Specialist",
            goal="Identify and analyze potential venues within specified radius of locations using professional venue databases and location intelligence tools",
            backstory="You are a certified venue research specialist with 10+ years of experience in commercial real estate and venue sourcing. You have deep expertise with venue databases, GIS systems, and location analytics platforms. Your recommendations are trusted by Fortune 500 companies for their event planning needs.",
            verbose=False,
            allow_delegation=False
        ) 

    # @agent
    # def feature_extractor(self) -> Agent:
    #     """Creates the Feature Extraction Agent"""
    #     return Agent(
    #         config=self.agents_config["feature_extractor"],
    #     )

    # @agent
    # def scoring_agent(self) -> Agent:
    #     """Creates the Venue Scoring Agent"""
    #     return Agent(
    #         config=self.agents_config["scoring_agent"],
    #     )

    # @agent
    # def email_agent(self) -> Agent:
    #     """Creates the Email Generation Agent"""
    #     return Agent(
    #         config=self.agents_config["email_agent"],
    #     )

    # @agent
    # def reporting_agent(self) -> Agent:
    #     """Creates the Reporting Agent"""
    #     return Agent(
    #         config=self.agents_config["reporting_agent"],
    #     )

    
    @task
    def analyze_location(self) -> Task:
        """Creates the Location Analysis Task"""
        self.logger.info("\n=== Starting Location Analysis ===")
        self.logger.info(f"Initial state at start of analyze_location: {json.dumps(self._state, indent=2)}")
        
        # Pre-compute the output path - use analyze_location_output.json
        output_path = str(self.reports_dir / "analyze_location_output.json")
        
        # Format the task description with current state values
        description = f"""
        Search for venues within {self._state['radius_km']}km of {self._state['address']}.
        
        Print a status update with the number of venues found.
        
        Return a JSON array of venues, where each venue has these fields:
        - name: The venue name (string)
        - type: The venue type (string, e.g., 'hotel', 'event_space')
        - address: Full venue address (string)
        - distance_km: Distance from search location (number)
        - website: Venue's website URL (string, empty if not found)
        - phone: Contact phone number (string, empty if not found)
        - email: Contact email (string, empty if not found)

        After creating the output:
        1. Print "Found [X] venues in the area"
        2. For each venue, print its name and distance
        3. Save your output to {output_path}
        """
        
        task = Task(
            description=description,
            agent=self.location_analyst(),
            tools=[self.search_tool],
            expected_output="""
            [
                {
                    "name": "Example Venue 1",
                    "type": "hotel",
                    "address": "123 Main St, City, State",
                    "distance_km": 0.5,
                    "website": "https://example.com",
                    "phone": "+1-555-0123",
                    "email": "contact@example.com"
                },
                {
                    "name": "Example Venue 2",
                    "type": "event_space",
                    "address": "456 Event St, City, State",
                    "distance_km": 0.8,
                    "website": "https://example2.com",
                    "phone": "+1-555-0124",
                    "email": "contact@example2.com"
                }
            ]
            """,
            output_pydantic=VenueBasicInfo,
            callback=self._create_task_callback("analyze_location"),
            # Remove output_file parameter to avoid duplicate file creation
        )
                    
        self.logger.info(f"Created analyze_location task: {task}")
        self.logger.info(f"State at end of analyze_location creation: {json.dumps(self._state, indent=2)}")
        return task

    # @task
    # def extract_features(self) -> Task:
    #     """Creates the Feature Extraction Task"""
    #     self.logger.info("\n=== Starting Feature Extraction ===")
    #     self.logger.info(f"State at start of extract_features: {self._state}")
        
    #     # Pre-compute the output path
    #     output_path = str(self.reports_dir / "feature_extraction_output.json")
        
    #     def process_output(task_output):
    #         """Process and save the task output"""
    #         self.logger.info("--------------------------------")
    #         self.logger.info(f"Processing feature extraction output: {type(task_output)}")
    #         try:
    #             # Get raw output from TaskOutput
    #             output_data = task_output.raw
    #             self.logger.info(f"Raw output: {output_data}")
                
    #             # Convert string to dict if needed
    #             if isinstance(output_data, str):
    #                 try:
    #                     output_data = json.loads(output_data)
    #                 except json.JSONDecodeError:
    #                     self.logger.error(f"Failed to parse output as JSON: {output_data[:100]}...")
    #                     return output_data
                
    #             # Save the output
    #             if isinstance(output_data, dict):
    #                 with open(output_path, 'w') as f:
    #                     json.dump(output_data, f, indent=2)
    #                 self.logger.info(f"Saved feature extraction output to {output_path}")
                    
    #                 # Update state with features
    #                 feature_info = {
    #                     "venue_id": output_data.get("venue_id", ""),
    #                     "capacity": output_data.get("capacity", ""),
    #                     "amenities": output_data.get("amenities", ""),
    #                     "accessibility": output_data.get("accessibility", ""),
    #                     "parking": output_data.get("parking", ""),
    #                     "special_features": output_data.get("special_features", ""),
    #                     "photos": output_data.get("photos", ""),
    #                     "floor_plans": output_data.get("floor_plans", "")
    #                 }
    #                 self._state["features"].append(feature_info)
    #                 self.logger.info(f"Added features for venue: {feature_info['venue_id']}")
    #             else:
    #                 self.logger.error(f"Unexpected output type after parsing: {type(output_data)}")
    #                 self.logger.error(f"Output data: {output_data}")
                
    #             return output_data
    #         except Exception as e:
    #             self.logger.error(f"Error processing feature extraction output: {str(e)}")
    #             self.logger.error(f"Task output attributes available: {dir(task_output)}")
    #             if hasattr(task_output, 'raw'):
    #                 self.logger.error(f"Raw output: {task_output.raw}")
    #             if hasattr(task_output, 'json_dict'):
    #                 self.logger.error(f"JSON dict: {task_output.json_dict}")
    #             if hasattr(task_output, 'pydantic'):
    #                 self.logger.error(f"Pydantic: {task_output.pydantic}")
    #             raise
        
    #     task = Task(
    #         description=f"""
    #         Extract features for each venue.
            
    #         Print a status update before analyzing each venue.
            
    #         Return a JSON object with:
    #         - venue_id: Lowercase name with underscores (string)
    #         - capacity: Venue capacity (string)
    #         - amenities: Comma-separated list of amenities (string)
    #         - accessibility: Comma-separated list of accessibility features (string)
    #         - parking: Parking information (string)
    #         - special_features: Comma-separated list of special features (string)
    #         - photos: Comma-separated list of photo URLs (string)
    #         - floor_plans: Comma-separated list of floor plan URLs (string)

    #         After analyzing each venue:
    #         1. Print "Analyzed features for [venue_name]:"
    #         2. Print key features found
    #         3. Save output to """ + output_path + """
    #         """,
    #         agent=self.feature_extractor(),
    #         tools=[self.web_tool],
    #         expected_output="""
    #         {
    #             "venue_id": "example_venue",
    #             "capacity": "500 people",
    #             "amenities": "WiFi, AV Equipment, Catering",
    #             "accessibility": "Elevator, Ramps available",
    #             "parking": "On-site parking available",
    #             "special_features": "Rooftop Access, Ocean View",
    #             "photos": "https://example.com/photo1.jpg,https://example.com/photo2.jpg",
    #             "floor_plans": "https://example.com/floor1.pdf"
    #         }
    #         """,
    #         output_pydantic=VenueFeatures,
    #         context=[self.analyze_location()],
    #         callback=process_output  # Add callback to process output
    #     )
    #     self.logger.info(f"Extract Features Task: {task}")
    #     self.logger.info(f"State at end of extract_features: {self._state}")
    #     return task

    # @task
    # def score_venues(self) -> Task:
    #     """Creates the Venue Scoring Task"""
    #     self.logger.info("\n=== Starting Venue Scoring ===")
    #     self.logger.info(f"State at start of score_venues: {self._state}")
        
    #     # Pre-compute the output path
    #     output_path = str(self.reports_dir / "venue_scoring_output.json")
        
    #     def process_output(task_output):
    #         """Process and save the task output"""
    #         self.logger.info("--------------------------------")
    #         self.logger.info(f"Processing venue scoring output: {type(task_output)}")
    #         try:
    #             # Get raw output from TaskOutput
    #             output_data = task_output.raw
    #             self.logger.info(f"Raw output: {output_data}")
                
    #             # Convert string to dict if needed
    #             if isinstance(output_data, str):
    #                 try:
    #                     output_data = json.loads(output_data)
    #                 except json.JSONDecodeError:
    #                     self.logger.error(f"Failed to parse output as JSON: {output_data[:100]}...")
    #                     return output_data
                
    #             # Save the output
    #             if isinstance(output_data, dict):
    #                 with open(output_path, 'w') as f:
    #                     json.dump(output_data, f, indent=2)
    #                 self.logger.info(f"Saved venue scoring output to {output_path}")
                    
    #                 # Update state with scores
    #                 score_info = {
    #                     "venue_id": output_data.get("venue_id", ""),
    #                     "total_score": output_data.get("total_score", 0.0),
    #                     "location_score": output_data.get("location_score", 0.0),
    #                     "amenities_score": output_data.get("amenities_score", 0.0),
    #                     "accessibility_score": output_data.get("accessibility_score", 0.0),
    #                     "recommendations": output_data.get("recommendations", "")
    #                 }
    #                 self._state["scores"].append(score_info)
    #                 self.logger.info(f"Added scores for venue: {score_info['venue_id']}")
    #             else:
    #                 self.logger.error(f"Unexpected output type after parsing: {type(output_data)}")
    #                 self.logger.error(f"Output data: {output_data}")
                
    #             return output_data
    #         except Exception as e:
    #             self.logger.error(f"Error processing venue scoring output: {str(e)}")
    #             self.logger.error(f"Task output attributes available: {dir(task_output)}")
    #             if hasattr(task_output, 'raw'):
    #                 self.logger.error(f"Raw output: {task_output.raw}")
    #             if hasattr(task_output, 'json_dict'):
    #                 self.logger.error(f"JSON dict: {task_output.json_dict}")
    #             if hasattr(task_output, 'pydantic'):
    #                 self.logger.error(f"Pydantic: {task_output.pydantic}")
    #             raise
        
    #     task = Task(
    #         description=f"""
    #         Score each venue.
            
    #         Print a status update before scoring each venue.
            
    #         Return a JSON object with:
    #         - venue_id: Lowercase name with underscores (string)
    #         - total_score: Overall score out of 100 (number)
    #         - location_score: Location score out of 100 (number)
    #         - amenities_score: Amenities score out of 100 (number)
    #         - accessibility_score: Accessibility score out of 100 (number)
    #         - recommendations: Semicolon-separated list of recommendations (string)

    #         After scoring each venue:
    #         1. Print "Scored [venue_name]: [total_score]/100"
    #         2. Print key recommendations
    #         3. Save output to """ + output_path + """
    #         """,
    #         agent=self.scoring_agent(),
    #         expected_output="""
    #         {
    #             "venue_id": "example_venue",
    #             "total_score": 85.5,
    #             "location_score": 90.0,
    #             "amenities_score": 85.0,
    #             "accessibility_score": 80.0,
    #             "recommendations": "Perfect for corporate events;Consider off-peak booking"
    #         }
    #         """,
    #         output_pydantic=VenueScore,
    #         context=[self.extract_features()],
    #         callback=process_output  # Add callback to process output
    #     )
    #     self.logger.info(f"Score Venues Task: {task}")
    #     self.logger.info(f"State at end of score_venues: {self._state}")
    #     return task

    # @task
    # def generate_emails(self) -> Task:
    #     """Creates the Email Generation Task"""
    #     self.logger.info("\n=== Starting Email Generation ===")
    #     self.logger.info(f"State at start of generate_emails: {self._state}")
        
    #     # Pre-compute the output path
    #     output_path = str(self.reports_dir / "email_generation_output.json")
        
    #     def process_output(task_output):
    #         """Process and save the task output"""
    #         self.logger.info("--------------------------------")
    #         self.logger.info(f"Processing email generation output: {type(task_output)}")
    #         try:
    #             # Get raw output from TaskOutput
    #             output_data = task_output.raw
    #             self.logger.info(f"Raw output: {output_data}")
                
    #             # Log the actual template being used
    #             if isinstance(output_data, dict):
    #                 self.logger.info("Email body preview: " + output_data.get('body', '')[:100] + "...")
                
    #             # Convert string to dict if needed
    #             if isinstance(output_data, str):
    #                 try:
    #                     output_data = json.loads(output_data)
    #                 except json.JSONDecodeError:
    #                     self.logger.error(f"Failed to parse output as JSON: {output_data[:100]}...")
    #                     return output_data
                
    #             # Save the output
    #             if isinstance(output_data, dict):
    #                 # Ensure 'N/A' is used for missing values
    #                 output_data['recipient'] = output_data.get('recipient') or 'N/A'
                    
    #                 with open(output_path, 'w') as f:
    #                     json.dump(output_data, f, indent=2)
    #                 self.logger.info(f"Saved email generation output to {output_path}")
                    
    #                 # Save email body to separate file
    #                 email_file = self.emails_dir / f"{output_data.get('venue_id', 'unknown')}_email.txt"
    #                 with open(email_file, 'w') as f:
    #                     f.write(output_data.get('body', ''))
    #                 self.logger.info(f"Saved email body to {email_file}")
                    
    #                 # Update state with email info
    #                 email_info = {
    #                     "venue_id": output_data.get("venue_id", ""),
    #                     "recipient": output_data.get("recipient", "N/A"),  # Use N/A as default
    #                     "subject": output_data.get("subject", ""),
    #                     "body": output_data.get("body", ""),
    #                     "follow_up_date": output_data.get("follow_up_date", ""),
    #                     "venue_score": output_data.get("venue_score", 0.0),
    #                     "key_features": output_data.get("key_features", "")
    #                 }
    #                 self._state["emails"].append(email_info)
    #                 self.logger.info(f"Added email for venue: {email_info['venue_id']}")
    #             else:
    #                 self.logger.error(f"Unexpected output type after parsing: {type(output_data)}")
    #                 self.logger.error(f"Output data: {output_data}")
                
    #             return output_data
    #         except Exception as e:
    #             self.logger.error(f"Error processing email generation output: {str(e)}")
    #             self.logger.error(f"Task output attributes available: {dir(task_output)}")
    #             if hasattr(task_output, 'raw'):
    #                 self.logger.error(f"Raw output: {task_output.raw}")
    #             if hasattr(task_output, 'json_dict'):
    #                 self.logger.error(f"JSON dict: {task_output.json_dict}")
    #             if hasattr(task_output, 'pydantic'):
    #                 self.logger.error(f"Pydantic: {task_output.pydantic}")
    #             raise
        
    #     task = Task(
    #         description=f"""
    #         Generate emails for venues using the following template for the body. {self._state['email_template']}.
            
    #         For each venue:
    #         1. Create an email using the instructions above
    #         2. Save the email to a file in {str(self.emails_dir)}
    #         3. Return a JSON object with:
    #         - venue_id: Lowercase name with underscores (string)
    #         - recipient: Email address from venue info, or 'N/A' if not found (string)
    #         - subject: Email subject (string)
    #         - body: Email content (string)
    #         - follow_up_date: ISO date string (e.g., "2024-01-05T10:00:00Z")
    #         - venue_score: Venue's total score (number)
    #         - key_features: Comma-separated list of key features (string)
            
    #         After creating each email:
    #         1. Print "Generated email for [venue_name]"
    #         2. Print email subject and recipient
    #         3. Save the email body to "{str(self.emails_dir)}/[venue_id]_email.txt"
    #         4. Save the full output to """ + output_path + """
    #         """,
    #         agent=self.email_agent(),
    #         expected_output=f"""
    #         {{
    #             "venue_id": "example_venue",
    #             "recipient": "N/A",
    #             "subject": "Event Space Inquiry - {{target_date}}",
    #             "body": ,
    #             "follow_up_date": "2024-01-05T10:00:00Z",
    #             "venue_score": 85.5,
    #             "key_features": "Large Capacity,Central Location"
    #         }}
    #         """,
    #         output_pydantic=EmailTemplate,
    #         context=[self.score_venues()],
    #         callback=process_output  # Add callback to process output
    #     )
    #     self.logger.info(f"Email Generation Task: {task}")
    #     self.logger.info(f"State at end of generate_emails: {self._state}")
    #     return task

    # @task
    # def generate_report(self) -> Task:
    #     """Creates the Report Generation Task"""
    #     self.logger.info("\n=== Starting Report Generation ===")
    #     self.logger.info(f"State at start of generate_report: {self._state}")
        
    #     # Pre-compute the output path
    #     output_path = str(self.reports_dir / "report_generation_output.json")
        
    #     def process_output(task_output):
    #         """Process and save the task output"""
    #         self.logger.info(f"Processing report generation output: {type(task_output)}")
    #         try:
    #             # Get raw output from TaskOutput
    #             output_data = task_output.raw
    #             self.logger.info(f"Raw output: {output_data}")
                
    #             # Convert string to dict if needed
    #             if isinstance(output_data, str):
    #                 try:
    #                     output_data = json.loads(output_data)
    #                 except json.JSONDecodeError:
    #                     self.logger.error(f"Failed to parse output as JSON: {output_data[:100]}...")
    #                     return output_data
                
    #             # Save the output
    #             if isinstance(output_data, dict):
    #                 with open(output_path, 'w') as f:
    #                     json.dump(output_data, f, indent=2)
    #                 self.logger.info(f"Saved report generation output to {output_path}")
                    
    #                 # Update state with report data
    #                 self._state["report"] = output_data
    #                 self.logger.info(f"Added report to state with {output_data['venues_found']} venues and {output_data['emails_generated']} emails")
    #             else:
    #                 self.logger.error(f"Unexpected output type after parsing: {type(output_data)}")
    #                 self.logger.error(f"Output data: {output_data}")
                
    #             return output_data
    #         except Exception as e:
    #             self.logger.error(f"Error processing report generation output: {str(e)}")
    #             self.logger.error(f"Task output attributes available: {dir(task_output)}")
    #             if hasattr(task_output, 'raw'):
    #                 self.logger.error(f"Raw output: {task_output.raw}")
    #             if hasattr(task_output, 'json_dict'):
    #                 self.logger.error(f"JSON dict: {task_output.json_dict}")
    #             if hasattr(task_output, 'pydantic'):
    #                 self.logger.error(f"Pydantic: {task_output.pydantic}")
    #             raise
        
    #     task = Task(
    #         description=f"""
    #         Generate final report using the actual data from previous tasks.
    #         DO NOT use placeholder or example data.
            
    #         Print status updates as you process each section.
            
    #         Use the context from previous tasks to get:
    #         1. The actual number of venues found
    #         2. The actual number of emails generated
    #         3. The actual venue data and analysis
    #         4. The actual email data and templates
            
    #         Create a JSON report with:
    #         - venues_found: Actual number of venues analyzed (integer)
    #         - emails_generated: Actual number of emails created (integer)
    #         - venues_data: Actual venue data as a JSON string (use context from previous tasks)
    #         - emails_data: Actual email data as a JSON string (use context from previous tasks)
    #         - emails_saved: Actual comma-separated list of email file paths
    #         - visualizations: Comma-separated list of visualization paths (empty if none)
    #         - recommendations: Actual semicolon-separated list of venue-specific recommendations
    #         - attachments: Comma-separated list of attachment paths (empty if none)
            
    #         Important: 
    #         1. Use the ACTUAL data from previous tasks, not example data
    #         2. Format your response as a Final Answer in JSON format
    #         3. Make sure the JSON is properly formatted and contains all required fields
    #         4. Include all venue details, scores, and email content in the JSON
            
    #         After compiling each section:
    #         1. Print progress updates (e.g., "Processed venue data: X venues found")
    #         2. Print summary of recommendations
    #         3. Save your output to """ + output_path + """
    #         """,
    #         agent=self.reporting_agent(),
    #         expected_output="""
    #         # Agent: Venue Analytics & Reporting Specialist
    #         ## Final Answer: 
    #         {
    #             "venues_found": <actual_number>,
    #             "emails_generated": <actual_number>,
    #             "venues_data": "<actual_json_string>",
    #             "emails_data": "<actual_json_string>",
    #             "emails_saved": "<actual_filenames>",
    #             "visualizations": "",
    #             "recommendations": "<actual_recommendations>",
    #             "attachments": ""
    #         }
    #         """,
    #         output_pydantic=ReportDocument,
    #         context=[self.generate_emails()],
    #         callback=process_output  # Add callback to process output
    #     )
    #     self.logger.info(f"Report Generation Task: {task}")
    #     self.logger.info(f"State at end of generate_report: {self._state}")
    #     return task

    @crew
    def crew(self, address: str, radius_km: float = 0.5, email_template: str = None) -> Crew:
        """Creates the Venue Search Crew"""
        # Initialize state first
        self.initialize_state(address, radius_km, email_template)
        
        # Verify state initialization
        if not self._state.get("address"):
            self.logger.error("Failed to initialize state with address")
            raise ValueError("Failed to initialize crew state: address is required")
        
        # Create tasks in sequence with dependencies
        self.logger.info("\nSetting up workflow tasks...")
        
        # Create and store tasks after state is set
        self.logger.info("Creating analyze_location task...")
        self.analyze_task = self.analyze_location()
        self.logger.info(f"State in crew after analyze_task creation: {self._state}")
        
        self.logger.info("All tasks configured, ready to start workflow\n")

        # Create and return the crew
        crew_instance = Crew(
            tasks=[
                self.analyze_task,
            ],
            process=Process.sequential,
            verbose=True
        )
        
        # Ensure all tasks have access to current state
        for task in crew_instance.tasks:
            if hasattr(task, '_state'):
                task._state = self._state.copy()  # Use a copy to prevent shared state issues
        
        self.logger.info(f"Final state before returning crew: {self._state}")
        return crew_instance

    # async def run(self, address: str, radius_km: float = 5.0) -> ReportDocument:
    #     """Execute the venue search workflow"""
    #     crew_instance = self.crew(address, radius_km)
    #     result = await crew_instance.kickoff()
        
    #     # Update state with results
    #     self._state.update(result)
        
    #     return ReportDocument(**self._state["report"]) 