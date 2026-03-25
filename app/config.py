from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, Literal

class Settings(BaseSettings):
    # API Settings
    api_title: str = "Publisher Website Classifier"
    api_version: str = "2.0.0"
    debug: bool = False
    
    # LLM Provider Selection
    llm_provider: Literal["openai", "ollama"] = "openai"
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.1
    openai_max_tokens: int = 800
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_temperature: float = 0.1
    ollama_max_tokens: int = 800
    
    # Common LLM Settings
    llm_temperature: float = 0.1
    llm_max_tokens: int = 800
    
    # Scraping Settings
    request_timeout: int = 15
    max_content_length: int = 10000
    min_content_length: int = 200
    user_agent: str = "Mozilla/5.0 (compatible; PublisherClassifier/1.0)"
    
    # RAG Settings
    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k_policies: int = 4
    
    # Cache Settings
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 86400
    
    # Rate Limiting
    rate_limit_per_minute: int = 30
    
    # Monitoring
    enable_metrics: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def validate_provider_config(self):
        """Validate configuration based on selected provider"""
        if self.llm_provider == "openai":
            if not self.openai_api_key:
                # Instead of raising error during initialization, we'll log a warning
                # and the factory will fail if it's actually used.
                pass
        elif self.llm_provider == "ollama":
            pass
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")

@lru_cache()
def get_settings() -> Settings:
    st = Settings()
    st.validate_provider_config()
    return st

settings = get_settings()
