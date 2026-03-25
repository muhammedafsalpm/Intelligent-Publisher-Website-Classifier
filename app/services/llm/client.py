# app/services/llm/client.py
from typing import Dict, List, Any
import json
import logging
from app.services.llm.factory import llm_factory
from app.services.signal_extractor import SignalExtractor
from app.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    """Unified LLM client that works with any provider"""
    
    def __init__(self):
        self.client = llm_factory.get_client()
    
    async def classify_site(
        self, 
        text: str, 
        policies: str,
        signals: Dict
    ) -> Dict:
        """Classify website using configured LLM provider"""
        
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
            
            # Ensure required fields exist
            result = self._ensure_required_fields(result)
            
            # Track usage (if available)
            if 'usage' in result:
                self._track_usage(result['usage'])
            
            return result
            
        except Exception as e:
            logger.error(f"LLM classification failed with {settings.llm_provider}: {e}")
            return self._get_fallback_response(signals)
    
    async def extract_signals(self, text: str, url: str) -> Dict:
        """Extract signals using configured LLM provider"""
        
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
            messages = [
                {"role": "system", "content": "You are a website analysis expert. Extract structured signals accurately."},
                {"role": "user", "content": prompt}
            ]
            
            signals = await self.client.chat_completion(
                messages=messages,
                response_format="json"
            )
            
            # Add derived scores
            signals['quality_score'] = self._calculate_quality_score(signals)
            signals['risk_score'] = self._calculate_risk_score(signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"Signal extraction failed with {settings.llm_provider}: {e}")
            return self._get_fallback_signals()
    
    def _get_system_prompt(self) -> str:
        """System prompt with no hardcoded rules"""
        return f"""You are an expert website classifier for affiliate marketing quality control.

Your role is to evaluate publisher websites against dynamic policies retrieved from our knowledge base.

CRITICAL PRINCIPLES:
1. BASE DECISIONS ON RETRIEVED POLICIES: The policies provided are your only source of truth for classification rules
2. CONSIDER ALL EVIDENCE: Use extracted signals and content together
3. BE PRECISE: Provide clear reasoning in the summary
4. CALIBRATE CONFIDENCE: High = clear evidence, Medium = mixed signals, Low = insufficient information

You have no hardcoded rules. All classification criteria come from the policies section.

Provider: {settings.llm_provider}
Model: {self.client.model}"""
    
    def _build_dynamic_prompt(self, text: str, policies: str, signals: Dict) -> str:
        """Build prompt with no hardcoded assumptions"""
        
        return f"""
## ACTIVE POLICIES (Your Only Source of Classification Rules)
{policies}

## EXTRACTED SIGNALS
{json.dumps(signals, indent=2)}

## WEBSITE CONTENT
{text[:3000]}

## YOUR TASK
Based SOLELY on the policies above and the evidence provided, classify this website.

Return a JSON object with:
- is_cashback_site: boolean (based on policy definition)
- is_adult_content: boolean (based on policy definition)
- is_gambling: boolean (based on policy definition)
- is_agency_or_introductory: boolean (based on policy definition)
- is_scam_or_low_quality: boolean (based on policy definition)
- overall_score: 0-100 (higher = better quality for our campaigns)
- summary: Brief explanation referencing specific policies and evidence
- confidence: "high", "medium", or "low"

IMPORTANT: Your classification must directly reference the policies provided. Do not invent your own rules.
"""
    
    def _ensure_required_fields(self, result: Dict) -> Dict:
        """Ensure all required fields exist with defaults"""
        required = [
            "is_cashback_site", "is_adult_content", "is_gambling",
            "is_agency_or_introductory", "is_scam_or_low_quality",
            "overall_score", "summary", "confidence"
        ]
        
        for field in required:
            if field not in result:
                if field.startswith("is_"):
                    result[field] = False
                elif field == "overall_score":
                    result[field] = 50
                elif field == "summary":
                    result[field] = "Classification based on available evidence"
                elif field == "confidence":
                    result[field] = "medium"
        
        return result
    
    def _calculate_quality_score(self, signals: Dict) -> int:
        """Calculate quality score from signals"""
        score = 100
        
        quality_map = {
            "high quality original": 0,
            "original": -10,
            "mixed": -20,
            "thin": -40,
            "spammy": -60
        }
        score += quality_map.get(signals.get('content_quality', ''), -30)
        
        trust_count = len(signals.get('trust_signals', []))
        score += trust_count * 5
        
        risk_count = len(signals.get('risk_indicators', []))
        score -= risk_count * 15
        
        return max(0, min(100, score))
    
    def _calculate_risk_score(self, signals: Dict) -> int:
        """Calculate risk score (higher = more risky)"""
        risk_score = 0
        
        risky_categories = ['gambling', 'adult', 'scam', 'agency']
        if signals.get('primary_category') in risky_categories:
            risk_score += 50
        
        risk_score += len(signals.get('risk_indicators', [])) * 10
        
        return min(100, risk_score)
    
    def _get_fallback_response(self, signals: Dict) -> Dict:
        """Return safe fallback when LLM fails"""
        risk_score = signals.get('risk_score', 70)
        
        return {
            "is_cashback_site": False,
            "is_adult_content": False,
            "is_gambling": False,
            "is_agency_or_introductory": risk_score > 50,
            "is_scam_or_low_quality": risk_score > 60,
            "overall_score": max(0, 100 - risk_score),
            "summary": f"Classification system encountered an error with {settings.llm_provider}. Site flagged for manual review.",
            "confidence": "low"
        }
    
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
    
    def _track_usage(self, usage):
        """Track token usage for cost monitoring"""
        provider = settings.llm_provider
        logger.info(f"LLM Usage ({provider}) - Input: {usage.get('prompt_tokens', usage.get('prompt_eval_count', 0))}, Output: {usage.get('completion_tokens', usage.get('eval_count', 0))}")
