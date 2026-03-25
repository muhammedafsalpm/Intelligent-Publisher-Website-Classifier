# app/services/classifier.py
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
    """Orchestrates the classification pipeline: Scrape -> Signal Extract -> RAG -> Classify"""
    
    def __init__(self):
        self.scraper = WebsiteScraper()
        self.policy_store = PolicyStore()
        self.llm = LLMClient()
        self.signal_extractor = SignalExtractor()
        self.provider = settings.llm_provider
    
    async def classify(self, url: str) -> Dict:
        """Main classification pipeline with robust step-by-step logging"""
        start_time = time.time()
        
        logger.info(f"Classification pipeline started for {url} ({self.provider})")
        
        # Try cache
        cached = await cache.get(url)
        if cached:
            cached['cache_hit'] = True
            return cached
        
        try:
            # Step 1: Scrape website
            content = await self.scraper.fetch(url)
            
            # Step 2: Validate scrape results
            if not content or content.get('error'):
                error_msg = content.get('error', 'Unknown scraping failure')
                logger.warning(f"Aborting classification for {url}: Scrape failed - {error_msg}")
                return self._get_error_response(url, error_msg)
            
            text = content.get('main_text', '')
            logger.info(f"Scraped content retrieved: {len(text)} chars, Title: '{content.get('title', 'Unknown')[:50]}'")
            
            if len(text) < 100:
                logger.warning(f"Aborting classification for {url}: Insufficient content ({len(text)} chars)")
                return self._get_low_content_response(url)
            
            # Step 3: Extract signals (LLM Analysis)
            signals = await self.signal_extractor.extract_signals(text, url)
            logger.info(f"Primary category signal detected: {signals.get('primary_category')} (Score: {signals.get('quality_score')})")
            
            # Step 4: Retrieve policies (RAG)
            query = self._build_rag_query(content, signals)
            policy_text, retrieved_policies = self.policy_store.retrieve_relevant_policies(query)
            logger.info(f"Contextualized knowledge: {len(retrieved_policies)} policy chunks retrieved")
            
            # Step 5: Perform LLM-driven classification
            classification = await self.llm.classify_site(text, policy_text, signals)
            logger.info(f"Classification completed: overall_score={classification.get('overall_score')}, confidence={classification.get('confidence')}")
            
            # Step 6: Assemble results
            response = {
                'url': url,
                **classification,
                'scraped_content_length': len(text),
                'classification_time_ms': int((time.time() - start_time) * 1000),
                'rag_chunks_used': len(retrieved_policies),
                'llm_provider': self.provider,
                'cache_hit': False
            }
            
            # Step 7: Persist if reliable
            if classification.get('confidence') != 'low':
                await cache.set(url, response)
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Pipeline timed out for {url}")
            return self._get_timeout_response(url)
        except Exception as e:
            logger.error(f"Uncaught pipeline error for {url}: {e}", exc_info=True)
            return self._get_error_response(url, str(e))
    
    def _build_rag_query(self, content: Dict, signals: Dict) -> str:
        """Construct semantic search query for policy retrieval"""
        return f"""
        Website Classification Context:
        Title: {content.get('title', '')[:200]}
        Detected Category: {signals.get('primary_category', 'unknown')}
        Keywords: {', '.join(signals.get('keywords', [])[:10])}
        Business Model: {signals.get('business_model', 'unknown')}
        """
    
    def _get_error_response(self, url: str, error: str) -> Dict:
        """Fail-safe response for technical errors"""
        return {
            'url': url,
            'is_cashback_site': False,
            'is_adult_content': False,
            'is_gambling': False,
            'is_agency_or_introductory': True,
            'is_scam_or_low_quality': True,
            'overall_score': 0,
            'summary': f"Classification stalled due to technical error: {error[:100]}",
            'confidence': 'low',
            'scraped_content_length': 0,
            'classification_time_ms': 0,
            'rag_chunks_used': 0,
            'llm_provider': self.provider,
            'cache_hit': False
        }
    
    def _get_low_content_response(self, url: str) -> Dict:
        """Response for dead or thin sites"""
        return {
            'url': url,
            'is_cashback_site': False,
            'is_adult_content': False,
            'is_gambling': False,
            'is_agency_or_introductory': True,
            'is_scam_or_low_quality': True,
            'overall_score': 25,
            'summary': "Site contains insufficient text for reliable automated classification.",
            'confidence': 'low',
            'scraped_content_length': 0,
            'classification_time_ms': 0,
            'rag_chunks_used': 0,
            'llm_provider': self.provider,
            'cache_hit': False
        }
    
    def _get_timeout_response(self, url: str) -> Dict:
        """Response for slow sites"""
        return {
            'url': url,
            'is_cashback_site': False,
            'is_adult_content': False,
            'is_gambling': False,
            'is_agency_or_introductory': True,
            'is_scam_or_low_quality': True,
            'overall_score': 0,
            'summary': "Website failed to respond within timeout limits.",
            'confidence': 'low',
            'scraped_content_length': 0,
            'classification_time_ms': 0,
            'rag_chunks_used': 0,
            'llm_provider': self.provider,
            'cache_hit': False
        }
