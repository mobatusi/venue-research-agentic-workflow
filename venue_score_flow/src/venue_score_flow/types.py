from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
class InputData(BaseModel):
    address: str
    radius_km: float
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    linkedin_url: Optional[str] = None
    instagram_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    email_template: Optional[str] = None
    
class Venue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    type: Optional[str] = None
    address: Optional[str] = None
    distance_km: Optional[float] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    capacity: Optional[int] = None
    amenities: Optional[List[str]] = None
    accessibility: Optional[float] = None
    parking: Optional[str] = None
    special_features: Optional[str] = None
    audio_visual: Optional[str] = None
    technology: Optional[str] = None
    other: Optional[str] = None
  
class VenueScore(BaseModel):
    name: Optional[str] = None
    score: Optional[float] = None
    reason: Optional[str] = None

class ScoredVenues(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    address: Optional[str] = None
    distance_km: Optional[float] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    score: Optional[float] = None
    reason: Optional[str] = None
