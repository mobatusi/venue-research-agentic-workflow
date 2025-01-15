from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime

class InputData(BaseModel):
    address: str
    radius_km: float
    event_date: Optional[str] = None
    linkedin_url: Optional[str] = None
    instagram_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    email_template: Optional[str] = None
    
class Venue(BaseModel):
    id: str
    name: str
    type: str
    address: str
    distance_km: float
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    capacity: int
    amenities: List[str]
    accessibility: float
    parking: str
    special_features: str
    audio_visual: str
    technology: str
    other: str
  
class VenueScore(BaseModel):
    name: str
    score: float
    reason: str

class ScoredVenues(BaseModel):
    id: str
    name: str
    type: str
    address: str
    distance_km: float
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    score: float
    reason: str

class VenueScoreState(BaseModel):
    input_data: InputData | None = None
    venues: List[Venue] = []
    venue_score: List[VenueScore] = []
    hydrated_venues: List[ScoredVenues] = []
    scored_venues_feedback: str = ""
    generated_emails: Dict[str, str] = {}