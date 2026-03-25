# app/services/llm/factory.py
from typing import Dict, Any, Optional
import logging
from app.config import settings
from app.services.llm.base_client import BaseLLMClient
from app.services.llm.openai_client import OpenAIClient
from app.services.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

class LLMFactory:
    """Factory for creating LLM client instances"""
    
    _instance = None
    _client: Optional[BaseLLMClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_client(cls) -> BaseLLMClient:
        """Get LLM client based on configuration"""
        if cls._client is None:
            provider = settings.llm_provider.lower()
            
            if provider == "openai":
                logger.info("Initializing OpenAI client")
                cls._client = OpenAIClient()
            elif provider == "ollama":
                logger.info(f"Initializing Ollama client with model: {settings.ollama_model}")
                cls._client = OllamaClient()
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        
        return cls._client
    
    @classmethod
    async def close(cls):
        """Close client connections"""
        if cls._client and hasattr(cls._client, 'close'):
            await cls._client.close()
        cls._client = None

# Global factory instance
llm_factory = LLMFactory()
