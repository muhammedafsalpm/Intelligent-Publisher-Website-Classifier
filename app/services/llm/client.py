# app/services/llm/client.py
from typing import Dict, List, Any
import json
import logging
from app.services.llm.factory import llm_factory
from app.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    """Unified LLM client with improved error management and fallback support"""
    
    def __init__(self):
        self.client = llm_factory.get_client()
    
    async def classify_site(
        self, 
        text: str, 
        policies: str,
        signals: Dict
    ) -> Dict:
        """Classify website using LLM with explicit error capture"""
        
        prompt = self._build_dynamic_prompt(text, policies, signals)
        
        try:
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ]
            
            result = await self.client.chat_completion(
                messages=messages,
                response_format="json"
            )
            
            # Check for structural errors from provider
            if "error" in result:
                error_msg = result['error']
                logger.error(f"LLM provider error ({settings.llm_provider}): {error_msg}")
                return self._get_fallback_classification(signals, error_msg)
            
            result = self._ensure_required_fields(result)
            return result
            
        except Exception as e:
            logger.error(f"Classification pipeline breakdown: {e}", exc_info=True)
            return self._get_fallback_classification(signals, str(e))
    
    async def extract_signals(self, text: str, url: str) -> Dict:
        """Extract signals with robustness for short/empty content"""
        
        if not text or len(text) < 100:
            logger.warning(f"Incomplete content for extraction: {url}")
            return self._get_fallback_signals()
        
        prompt = self._build_signals_prompt(text, url)
        
        try:
            messages = [
                {"role": "system", "content": "You are a website analysis expert. Extract structured signals accurately."},
                {"role": "user", "content": prompt}
            ]
            
            signals = await self.client.chat_completion(
                messages=messages,
                response_format="json"
            )
            
            if "error" in signals:
                logger.error(f"Signals extract failed ({settings.llm_provider}): {signals['error']}")
                return self._get_fallback_signals()
            
            # Enrich signals
            signals['quality_score'] = self._calculate_quality_score(signals)
            signals['risk_score'] = self._calculate_risk_score(signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"Signal extraction failure: {e}")
            return self._get_fallback_signals()
    
    def _get_system_prompt(self) -> str:
        """System prompt with clear scoring guidelines"""
        return """You are a precise website classifier for affiliate marketing quality control.

SCORING GUIDELINES (assign overall_score based on these bands):
- 90-100: Excellent quality, legitimate publisher, all trust signals present
- 70-89: Good quality, meets standards, minor gaps
- 50-69: Acceptable quality, some concerns
- 30-49: Poor quality, significant concerns, flag for review
- 0-29: Unacceptable - policy violations (gambling, adult, scam = 0)

CLASSIFICATION DIMENSIONS:
- is_cashback_site: Cashback/rewards programs sharing affiliate commissions with users
- is_adult_content: Explicit sexual content or adult services
- is_gambling: Real money betting, casino, or wagering
- is_agency_or_introductory: Thin content, primarily redirects to affiliate offers
- is_scam_or_low_quality: Deceptive practices or extremely poor quality

CRITICAL: Base your decisions on the provided policies. Return ONLY valid JSON.
Do NOT explain your reasoning outside the summary field."""

    def _build_dynamic_prompt(self, text: str, policies: str, signals: Dict) -> str:
        """Build optimized classification prompt (lean for speed)"""
        category = signals.get('primary_category', 'unknown')
        quality = signals.get('content_quality', 'medium')
        return f"""Policies:
{policies[:800]}

Site type: {category} | Quality: {quality}

Content:
{text[:2000]}

Classify. Return JSON only:
{{
    "is_cashback_site": false,
    "is_adult_content": false,
    "is_gambling": false,
    "is_agency_or_introductory": false,
    "is_scam_or_low_quality": false,
    "overall_score": 0,
    "summary": "brief explanation",
    "confidence": "high|medium|low"
}}"""

    def _build_signals_prompt(self, text: str, url: str) -> str:
        """Build lean signals extraction prompt"""
        return f"""Analyze this website. URL: {url}

Content: {text[:1500]}

Return JSON only:
{{
    "primary_category": "ecommerce|blog|news|gambling|adult|cashback|agency|other",
    "content_quality": "high|medium|low|spam",
    "business_model": "direct_sales|affiliate|subscription|ad_supported|unknown",
    "trust_signals": [],
    "risk_indicators": []
}}"""
    
    def _ensure_required_fields(self, result: Dict) -> Dict:
        """Ensure all required fields exist — trust the LLM's score, never override it"""
        required = [
            "is_cashback_site", "is_adult_content", "is_gambling",
            "is_agency_or_introductory", "is_scam_or_low_quality",
            "overall_score", "summary", "confidence"
        ]
        
        # Fill only missing fields — do not overwrite LLM-provided values
        for field in required:
            if field not in result:
                if field.startswith("is_"):
                    result[field] = False
                elif field == "overall_score":
                    result[field] = 50  # Fallback only if LLM omitted it
                elif field == "summary":
                    result[field] = "Classification based on available evidence"
                elif field == "confidence":
                    result[field] = "medium"
        
        # Only enforce valid numeric range — no hardcoded score overrides
        result['overall_score'] = max(0, min(100, result['overall_score']))
        return result
    
    def _get_fallback_classification(self, signals: Dict, error_msg: str = None) -> Dict:
        """Return safe fallback classification"""
        risk_score = signals.get('risk_score', 70) if signals else 70
        reason = f"Classification fault: {error_msg if error_msg else 'No LLM signal'}"
        
        return {
            "is_cashback_site": False,
            "is_adult_content": False,
            "is_gambling": False,
            "is_agency_or_introductory": risk_score > 50,
            "is_scam_or_low_quality": risk_score > 60,
            "overall_score": max(0, 100 - risk_score),
            "summary": f"{reason}. Flagged for manual audit.",
            "confidence": "low"
        }
    
    def _get_fallback_signals(self) -> Dict:
        """Standard fallback signals"""
        return {
            "primary_category": "unknown",
            "keywords": [],
            "content_quality": "unknown",
            "business_model": "unknown",
            "trust_signals": [],
            "risk_indicators": ["extraction_fault"],
            "language": "unknown",
            "uniqueness_score": 0.5,
            "quality_score": 30,
            "risk_score": 70
        }

    def _calculate_quality_score(self, signals: Dict) -> int:
        """Calculates derived quality score"""
        score = 100
        quality_map = {"original": 0, "mixed": -20, "thin": -40, "spammy": -60}
        score += quality_map.get(signals.get('content_quality', ''), -30)
        score += len(signals.get('trust_signals', [])) * 5
        score -= len(signals.get('risk_indicators', [])) * 15
        return max(0, min(100, score))

    def _calculate_risk_score(self, signals: Dict) -> int:
        """Calculates derived risk score"""
        score = 0
        if signals.get('primary_category') in ['gambling', 'adult', 'scam', 'agency']:
            score += 50
        score += len(signals.get('risk_indicators', [])) * 10
        return min(100, score)
