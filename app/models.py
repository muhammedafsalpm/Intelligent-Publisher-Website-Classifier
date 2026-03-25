from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, Literal
from enum import Enum

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ClassificationRequest(BaseModel):
    url: HttpUrl
    
    @validator('url')
    def normalize_url(cls, v):
        url_str = str(v)
        if not url_str.startswith(('http://', 'https://')):
            url_str = 'https://' + url_str
        return url_str

class ClassificationResponse(BaseModel):
    url: str
    is_cashback_site: bool
    is_adult_content: bool
    is_gambling: bool
    is_agency_or_introductory: bool
    is_scam_or_low_quality: bool
    overall_score: int = Field(ge=0, le=100)
    summary: str
    confidence: ConfidenceLevel
    scraped_content_length: Optional[int] = None
    classification_time_ms: Optional[int] = None
    rag_chunks_used: Optional[int] = None
    cache_hit: bool = False

class HealthResponse(BaseModel):
    status: str
    model: str
    policies_loaded: int
    redis_connected: bool
