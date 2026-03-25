# app/utils/guardrails.py - REMOVED or simplified to pure logging
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class ClassificationGuardrails:
    """Minimal guardrails - only logging, no rule-based overrides"""
    
    @staticmethod
    def validate_and_log(text: str, classification: Dict) -> Dict:
        """Only log classifications for monitoring, no overrides"""
        
        # Log for monitoring
        logger.info(
            "Classification result",
            extra={
                "is_cashback": classification.get('is_cashback_site'),
                "is_adult": classification.get('is_adult_content'),
                "is_gambling": classification.get('is_gambling'),
                "is_agency": classification.get('is_agency_or_introductory'),
                "is_scam": classification.get('is_scam_or_low_quality'),
                "score": classification.get('overall_score'),
                "confidence": classification.get('confidence')
            }
        )
        
        # No overrides - trust the LLM
        return classification
