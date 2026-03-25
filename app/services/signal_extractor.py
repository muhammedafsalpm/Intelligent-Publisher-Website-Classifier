# app/services/signal_extractor.py
from typing import Dict
import logging
import json
from app.services.llm.factory import llm_factory
from app.config import settings

logger = logging.getLogger(__name__)

class SignalExtractor:
    """Pure LLM-driven signal extractor (no hardcoded rules or keyword heuristics)"""
    
    def __init__(self):
        pass
    
    async def extract_signals(self, text: str, url: str) -> Dict:
        """Analyze text and extract classification signals using structured LLM analysis"""
        
        if not text or len(text) < 100:
            logger.warning(f"Insufficient text data for signal extraction ({url})")
            return self._default_signals()
        
        prompt = f"""
        Analyze the following technical and contextual signals for the website: {url}
        
        CONTENT BUFFER (Top 2000 chars):
        {text[:2000]}
        
        Extract the following attributes as a JSON object:
        1. primary_category: (e.g., ecommerce, blog, news, gambling, adult, cashback, agency, lifestyle, tech, health)
        2. keywords: list of the top 10 most relevant keywords/entities
        3. content_quality: One of ["high", "medium", "low", "spam"]
        4. business_model: One of ["direct_sales", "affiliate", "subscription", "lead_gen", "ad_supported", "unknown"]
        5. trust_signals: list of detected markers (e.g., ["contact_info", "about_us", "privacy_policy", "ssl", "user_reviews"])
        6. risk_indicators: list of potential red flags (e.g., ["aggressive_ads", "redirects", "plagiarized_content", "no_contact"])
        
        RETURN JSON ONLY.
        """
        
        try:
            client = llm_factory.get_client()
            
            messages = [
                {"role": "system", "content": "You are a professional web publisher analyst. You classify websites based on their content, business model, and trustworthiness."},
                {"role": "user", "content": prompt}
            ]
            
            # Use JSON mode if supported by the provider
            signals = await client.chat_completion(messages, response_format="json")
            
            # Compute intelligent scores based on extracted attributes
            signals['quality_score'] = self._compute_quality_score(signals)
            signals['risk_score'] = self._compute_risk_score(signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"LLM signal extraction failed: {e}", exc_info=True)
            return self._default_signals()
    
    def _compute_quality_score(self, signals: Dict) -> int:
        """Derive quality score from extracted trust signals and LLM quality assessment"""
        q_map = {"high": 85, "medium": 60, "low": 30, "spam": 5}
        score = q_map.get(signals.get('content_quality', 'medium'), 50)
        
        # Modifier for trust signals
        trust_count = len(signals.get('trust_signals', []))
        score += (trust_count * 4)
        
        return min(100, max(0, score))
    
    def _compute_risk_score(self, signals: Dict) -> int:
        """Derive risk score from indicators and high-risk categories"""
        risk = 0
        
        # Category risk
        if signals.get('primary_category') in ['gambling', 'adult']:
            risk += 60
        
        # Indicator risk
        risk += len(signals.get('risk_indicators', [])) * 15
        
        return min(100, risk)
    
    def _default_signals(self) -> Dict:
        return {
            "primary_category": "unknown",
            "keywords": [],
            "content_quality": "low",
            "business_model": "unknown",
            "trust_signals": [],
            "risk_indicators": ["extraction_failed"],
            "quality_score": 25,
            "risk_score": 75
        }
