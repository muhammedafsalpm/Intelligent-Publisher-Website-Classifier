# app/services/llm/openai_client.py
import openai
from typing import Dict, List, Any
import json
import logging
from app.services.llm.base import BaseLLMClient
from app.config import settings

logger = logging.getLogger(__name__)

class OpenAIClient(BaseLLMClient):
    """OpenAI implementation of LLM client"""
    
    def __init__(self):
        super().__init__(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            max_tokens=settings.openai_max_tokens
        )
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        response_format: str = "json"
    ) -> Dict[str, Any]:
        """Send chat completion to OpenAI"""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            # Add response format for JSON mode if available
            if response_format == "json" and self.model in ["gpt-4o-mini", "gpt-4o"]:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = await self.client.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            
            # Extract JSON from response
            if response_format == "json":
                return self._extract_json(content)
            
            return {"content": content, "usage": response.usage}
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI"""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise
