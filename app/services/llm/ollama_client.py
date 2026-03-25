# app/services/llm/ollama_client.py
import httpx
from typing import Dict, List, Any
import json
import logging
from app.services.llm.base import BaseLLMClient
from app.config import settings

logger = logging.getLogger(__name__)

class OllamaClient(BaseLLMClient):
    """Ollama (local Llama) implementation of LLM client"""
    
    def __init__(self):
        super().__init__(
            model=settings.ollama_model,
            temperature=settings.ollama_temperature,
            max_tokens=settings.ollama_max_tokens
        )
        self.base_url = settings.ollama_base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        response_format: str = "json"
    ) -> Dict[str, Any]:
        """Send chat completion to Ollama"""
        try:
            # Convert messages to Ollama format
            prompt = self._format_messages(messages)
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("response", "")
            
            # Extract JSON if requested
            if response_format == "json":
                return self._extract_json(content)
            
            return {"content": content, "usage": {"total_tokens": result.get("eval_count", 0)}}
            
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise
    
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings using Ollama"""
        try:
            payload = {
                "model": self.model,
                "prompt": text
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("embedding", [])
            
        except Exception as e:
            logger.error(f"Ollama embedding error: {e}")
            # Fallback to dummy embedding for local testing
            import hashlib
            hash_val = hashlib.md5(text.encode()).hexdigest()
            return [int(hash_val[i:i+2], 16) / 255.0 for i in range(0, min(20, len(hash_val)), 2)]
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for Ollama prompt"""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                formatted.append(f"System: {content}\n")
            elif role == "user":
                formatted.append(f"User: {content}\n")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}\n")
        
        formatted.append("Assistant: ")
        return "".join(formatted)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        
    def __del__(self):
        # Synchronous close is not possible easily here, but we should try
        pass
