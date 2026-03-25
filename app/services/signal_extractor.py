# app/services/signal_extractor.py
from typing import Dict, List
import json
import openai
from app.config import settings
from app.utils.logger import logger

class SignalExtractor:
    """Extract signals using LLM - no hardcoded keywords"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model
    
    async def extract_signals(self, text: str, url: str) -> Dict:
        """Extract comprehensive signals using LLM"""
        
        prompt = f"""
        Analyze this website content and extract structured signals.
        
        WEBSITE URL: {url}
        
        CONTENT PREVIEW:
        {text[:3000]}
        
        Extract the following signals:
        1. Primary category (ecommerce, blog, news, gambling, adult, cashback, agency, etc.)
        2. Top 10 keywords (meaningful, not stopwords)
        3. Content quality indicators (original, spammy, thin, etc.)
        4. Business model (affiliate, direct sales, lead gen, etc.)
        5. Trust signals present (contact info, privacy policy, about page, etc.)
        6. Risk indicators (scam patterns, aggressive CTAs, popups, etc.)
        7. Language detected
        8. Estimated content uniqueness (unique vs generic)
        
        Return ONLY valid JSON with this exact structure:
        {{
            "primary_category": "string",
            "keywords": ["string"],
            "content_quality": "string",
            "business_model": "string",
            "trust_signals": ["string"],
            "risk_indicators": ["string"],
            "language": "string",
            "uniqueness_score": 0.0-1.0
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a website analysis expert. Extract structured signals accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            signals = json.loads(response.choices[0].message.content)
            
            # Add derived scores
            signals['quality_score'] = self._calculate_quality_score(signals)
            signals['risk_score'] = self._calculate_risk_score(signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"Signal extraction failed: {e}")
            return self._get_fallback_signals()
    
    def _calculate_quality_score(self, signals: Dict) -> int:
        """Calculate quality score from signals"""
        score = 100
        
        # Based on content quality
        quality_map = {
            "high quality original": 0,
            "original": -10,
            "mixed": -20,
            "thin": -40,
            "spammy": -60
        }
        score += quality_map.get(signals.get('content_quality', ''), -30)
        
        # Based on trust signals
        trust_count = len(signals.get('trust_signals', []))
        score += trust_count * 5
        
        # Based on risk indicators
        risk_count = len(signals.get('risk_indicators', []))
        score -= risk_count * 15
        
        return max(0, min(100, score))
    
    def _calculate_risk_score(self, signals: Dict) -> int:
        """Calculate risk score (higher = more risky)"""
        risk_score = 0
        
        # Risk based on category
        risky_categories = ['gambling', 'adult', 'scam', 'agency']
        if signals.get('primary_category') in risky_categories:
            risk_score += 50
        
        # Risk based on risk indicators
        risk_score += len(signals.get('risk_indicators', [])) * 10
        
        return min(100, risk_score)
    
    def _get_fallback_signals(self) -> Dict:
        """Return safe fallback signals"""
        return {
            "primary_category": "unknown",
            "keywords": [],
            "content_quality": "unknown",
            "business_model": "unknown",
            "trust_signals": [],
            "risk_indicators": ["signal_extraction_failed"],
            "language": "unknown",
            "uniqueness_score": 0.5,
            "quality_score": 30,
            "risk_score": 70
        }
