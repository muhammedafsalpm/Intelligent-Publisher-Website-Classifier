# app/config.py - Updated for LLM-first approach
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API Settings
    api_title: str = "Publisher Website Classifier"
    api_version: str = "2.0.0"
    debug: bool = False
    
    # LLM Settings
    openai_api_key: str
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1  # Low for consistency
    llm_max_tokens: int = 800
    
    # Signal Extraction Settings
    use_llm_for_signals: bool = True  # Use LLM instead of hardcoded rules
    signal_extraction_model: str = "gpt-4o-mini"
    
    # Scraping Settings
    request_timeout: int = 15
    max_content_length: int = 10000
    min_content_length: int = 200
    
    # RAG Settings
    chunk_size: int = 800  # Larger chunks for better context
    chunk_overlap: int = 100
    top_k_policies: int = 4  # More policies for better context
    
    # Cache Settings
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 86400
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
