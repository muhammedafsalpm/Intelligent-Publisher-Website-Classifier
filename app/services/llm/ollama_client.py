# app/services/llm/ollama_client.py
import httpx
from typing import Dict, List, Any
import json
import logging
from app.services.llm.base_client import BaseLLMClient
from app.config import settings

logger = logging.getLogger(__name__)

class OllamaClient(BaseLLMClient):
    """Ollama implementation with proper error handling and health checks"""
    
    def __init__(self):
        super().__init__(
            model=settings.ollama_model,
            temperature=settings.ollama_temperature,
            max_tokens=settings.ollama_max_tokens
        )
        self.base_url = settings.ollama_base_url
        self.client = httpx.AsyncClient(timeout=60.0)  # Increased timeout for classification
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        response_format: str = "json"
    ) -> Dict[str, Any]:
        """Send chat completion to Ollama with connection and response validation"""
        try:
            # Check if Ollama is running
            if not await self._check_health():
                logger.error("Ollama service not reachable")
                return {"error": "Ollama service unavailable"}
            
            # Format messages for Ollama prompt
            prompt = self._format_messages(messages)
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "stop": ["\n\n"]  # Avoid rambling
                }
            }
            
            logger.info(f"Ollama request: model={self.model}, base_url={self.base_url}")
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama returned HTTP {response.status_code}: {response.text}")
                return {"error": f"Ollama HTTP {response.status_code}"}
            
            result = response.json()
            content = result.get("response", "")
            
            if not content:
                logger.error("Ollama returned empty response")
                return {"error": "Empty response from Ollama"}
            
            # Extract and parse JSON if requested
            if response_format == "json":
                try:
                    return self._extract_json(content)
                except Exception as e:
                    logger.error(f"Ollama JSON parse failure: {e}")
                    return {"error": "Invalid JSON response from model", "raw": content}
            
            return {"content": content, "usage": {"total_tokens": result.get("eval_count", 0)}}
            
        except httpx.ConnectError:
            logger.error(f"Connection failed to Ollama at {self.base_url}")
            return {"error": "Ollama connection failed"}
        except httpx.TimeoutException:
            logger.error("Ollama request timed out after 60s")
            return {"error": "Ollama timeout"}
        except Exception as e:
            logger.error(f"Ollama unexpected error: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _check_health(self) -> bool:
        """Verify Ollama is running"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags", timeout=2.0)
            return response.status_code == 200
        except:
            return False
    
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for Ollama template"""
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
        """Clean up HTTP connections"""
        await self.client.aclose()
