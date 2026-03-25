import time
from typing import Dict
import asyncio
from app.services.scraper import WebsiteScraper
from app.services.rag import PolicyStore
from app.services.llm.client import LLMClient
from app.services.signal_extractor import SignalExtractor
from app.utils.cache import cache
from app.utils.logger import logger
from app.config import settings

class WebsiteClassifier:
    def __init__(self):
        self.scraper = WebsiteScraper()
        self.policy_store = PolicyStore()
        self.llm = LLMClient()
        self.signal_extractor = SignalExtractor()
        self.provider = settings.llm_provider
    
    async def classify(self, url: str) -> Dict:
        """Main classification pipeline with provider support"""
        start_time = time.time()
        
        logger.info(f"Classification started for {url} using {self.provider}")
        
        # Check cache
        cached = await cache.get(url)
        if cached:
            cached['cache_hit'] = True
            return cached
        
        try:
            # Step 1: Scrape website
            content = await self.scraper.fetch(url)
            
            if content.get('error'):
                return self._get_error_response(url, content['error'])
            
            # Step 2: Validate content
            if len(content['main_text']) < settings.min_content_length:
                return self._get_low_content_response(url)
            
            # Step 3: Extract signals using LLM
            signals = await self.signal_extractor.extract_signals(
                content['main_text'],
                url
            )
            
            # Step 4: Retrieve policies (RAG)
            query = self._build_rag_query(content, signals)
            policy_text, retrieved_policies = self.policy_store.retrieve_relevant_policies(query)
            
            # Step 5: LLM classification
            classification = await self.llm.classify_site(
                content['main_text'],
                policy_text,
                signals
            )
            
            # Step 6: Build response
            response = {
                'url': url,
                **classification,
                'scraped_content_length': len(content['main_text']),
                'classification_time_ms': int((time.time() - start_time) * 1000),
                'rag_chunks_used': len(retrieved_policies),
                'llm_provider': self.provider,
                'cache_hit': False
            }
            
            # Step 7: Cache successful results
            if classification.get('confidence') != 'low':
                await cache.set(url, response)
            
            return response
            
        except asyncio.TimeoutError:
            return self._get_timeout_response(url)
        except Exception as e:
            logger.error(f"Classification failed for {url} with {self.provider}: {e}")
            return self._get_error_response(url, str(e))
    
    def _build_rag_query(self, content: Dict, signals: Dict) -> str:
        """Build query for RAG retrieval"""
        return f"""
        Website needs classification using {self.provider}:
        URL: {content.get('title', '')}
        Category: {signals.get('primary_category', 'unknown')}
        Keywords: {', '.join(signals.get('keywords', [])[:10])}
        Business Model: {signals.get('business_model', 'unknown')}
        Risk Indicators: {', '.join(signals.get('risk_indicators', [])[:5])}
        
        Please retrieve relevant classification policies for this site type.
        """
    
    def _get_error_response(self, url: str, error: str) -> Dict:
        """Return response for error cases"""
        return {
            'url': url,
            'is_cashback_site': False,
            'is_adult_content': False,
            'is_gambling': False,
            'is_agency_or_introductory': True,
            'is_scam_or_low_quality': True,
            'overall_score': 0,
            'summary': f"Technical error with {self.provider}: Unable to classify site. {error[:100]}",
            'confidence': 'low',
            'llm_provider': self.provider,
            'cache_hit': False
        }
    
    def _get_low_content_response(self, url: str) -> Dict:
        """Return response for low content sites"""
        return {
            'url': url,
            'is_cashback_site': False,
            'is_adult_content': False,
            'is_gambling': False,
            'is_agency_or_introductory': True,
            'is_scam_or_low_quality': True,
            'overall_score': 25,
            'summary': "Insufficient content extracted from site. Likely low-quality or misconfigured.",
            'confidence': 'low',
            'llm_provider': self.provider,
            'cache_hit': False
        }
    
    def _get_timeout_response(self, url: str) -> Dict:
        """Return response for timeout cases"""
        return {
            'url': url,
            'is_cashback_site': False,
            'is_adult_content': False,
            'is_gambling': False,
            'is_agency_or_introductory': True,
            'is_scam_or_low_quality': True,
            'overall_score': 0,
            'summary': "Site response timeout. Flagged for manual review.",
            'confidence': 'low',
            'llm_provider': self.provider,
            'cache_hit': False
        }
