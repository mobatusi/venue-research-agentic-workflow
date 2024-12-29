from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

class VenueBasicInfo(BaseModel):
    """Basic information about a venue"""
    name: str = Field(..., description="Name of the venue")
    type: str = Field(..., description="Type of venue (e.g., hotel, event_space)")
    address: str = Field(..., description="Full address of the venue")
    distance_km: float = Field(..., description="Distance from search location in kilometers")
    website: str = Field(default="", description="Venue's website URL")
    phone: str = Field(default="", description="Contact phone number")
    email: str = Field(default="", description="Contact email")

class VenueFeatures(BaseModel):
    """Detailed features of a venue"""
    venue_id: str = Field(..., description="Unique identifier for the venue (lowercase name with underscores)")
    capacity: str = Field(default="", description="Venue capacity")
    amenities: str = Field(default="", description="List of amenities as comma-separated string")
    accessibility: str = Field(default="", description="List of accessibility features as comma-separated string")
    parking: str = Field(default="", description="Parking information")
    special_features: str = Field(default="", description="Special features as comma-separated string")
    photos: str = Field(default="", description="Photo URLs as comma-separated string")
    floor_plans: str = Field(default="", description="Floor plan URLs as comma-separated string")

class VenueScore(BaseModel):
    """Scoring information for a venue"""
    venue_id: str = Field(..., description="Unique identifier for the venue")
    total_score: float = Field(..., description="Overall venue score out of 100")
    location_score: float = Field(default=0.0, description="Location score out of 100")
    amenities_score: float = Field(default=0.0, description="Amenities score out of 100")
    accessibility_score: float = Field(default=0.0, description="Accessibility score out of 100")
    recommendations: str = Field(default="", description="Recommendations as semicolon-separated string")

class EmailTemplate(BaseModel):
    """Email template for venue outreach"""
    venue_id: str = Field(..., description="Unique identifier for the venue")
    recipient: str = Field(..., description="Email recipient address")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body text")
    follow_up_date: str = Field(..., description="Follow-up date in ISO format")
    venue_score: float = Field(..., description="Venue's total score")
    key_features: str = Field(default="", description="Key features as comma-separated string")

class ReportDocument(BaseModel):
    """Complete venue search report"""
    venues_found: int = Field(..., description="Number of venues found")
    emails_generated: int = Field(..., description="Number of emails generated")
    venues_data: str = Field(..., description="JSON string containing venue data")
    emails_data: str = Field(..., description="JSON string containing email data")
    emails_saved: str = Field(default="", description="Email file paths as comma-separated string")
    visualizations: str = Field(default="", description="Visualization file paths as comma-separated string")
    recommendations: str = Field(default="", description="Recommendations as semicolon-separated string")
    attachments: str = Field(default="", description="Attachment file paths as comma-separated string") 