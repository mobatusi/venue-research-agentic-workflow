from typing import Dict, List
from datetime import datetime
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