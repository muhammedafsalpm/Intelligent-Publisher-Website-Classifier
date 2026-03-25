import openai
from typing import Dict, List
import json
import logging
from app.config import settings
from app.utils.logger import logger

class LLMClient:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model
    
    async def classify_site(
        self, 
        text: str, 
        policies: str,
        signals: Dict
    ) -> Dict:
        """Classify website using LLM with retrieved policies - NO HARDCODED RULES"""
        
        prompt = self._build_dynamic_prompt(text, policies, signals)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # No hardcoded validation - LLM is trusted
            # Just ensure required fields exist
            result = self._ensure_required_fields(result)
            
            # Track usage
            self._track_usage(response.usage)
            
            return result
            
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return self._get_fallback_response(signals)
    
    def _get_system_prompt(self) -> str:
        """System prompt with no hardcoded rules"""
        return """You are an expert website classifier for affiliate marketing quality control.

Your role is to evaluate publisher websites against dynamic policies retrieved from our knowledge base.

CRITICAL PRINCIPLES:
1. BASE DECISIONS ON RETRIEVED POLICIES: The policies provided are your only source of truth for classification rules
2. CONSIDER ALL EVIDENCE: Use extracted signals and content together
3. BE PRECISE: Provide clear reasoning in the summary
4. CALIBRATE CONFIDENCE: High = clear evidence, Medium = mixed signals, Low = insufficient information

You have no hardcoded rules. All classification criteria come from the policies section."""
    
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
    
    def _get_fallback_response(self, signals: Dict) -> Dict:
        """Return safe fallback when LLM fails"""
        # Use signals to make best guess
        risk_score = signals.get('risk_score', 70)
        
        return {
            "is_cashback_site": False,
            "is_adult_content": False,
            "is_gambling": False,
            "is_agency_or_introductory": risk_score > 50,
            "is_scam_or_low_quality": risk_score > 60,
            "overall_score": max(0, 100 - risk_score),
            "summary": "Classification system encountered an error. Site flagged for manual review.",
            "confidence": "low"
        }
    
    def _track_usage(self, usage):
        """Track token usage for cost monitoring"""
        logger.info(f"LLM Usage - Input: {usage.prompt_tokens}, Output: {usage.completion_tokens}")
