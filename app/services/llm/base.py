# app/services/llm/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import json

class BaseLLMClient(ABC):
    """Abstract base class for all LLM providers"""
    
    def __init__(self, model: str, temperature: float, max_tokens: int):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        response_format: str = "json"
    ) -> Dict[ Any, Any]:
        """Send chat completion request to LLM"""
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        pass
    
    def _extract_json(self, response: str) -> Dict:
        """Extract JSON from response"""
        try:
            # Try direct parsing
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON in response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return {}
