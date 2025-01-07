from typing import Optional
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
    website: str
    phone: str
    email: str

class VenueScore(BaseModel):
    id: str
    score: float
    reason: str

class ScoredVenues(BaseModel):
    id: str
    name: str
    type: str
    address: str
    distance_km: float
    website: str
    phone: str
    email: str
    score: float
    reason: str