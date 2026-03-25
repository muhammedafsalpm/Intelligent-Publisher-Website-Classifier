# app/services/signal_extractor.py
from typing import Dict
import logging
from app.services.llm.client import LLMClient

logger = logging.getLogger(__name__)

class SignalExtractor:
    """Extract signals using LLM - Decoupled from core classification logic"""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    async def extract_signals(self, text: str, url: str) -> Dict:
        """Extract signals using configured LLM provider"""
        return await self.llm_client.extract_signals(text, url)
