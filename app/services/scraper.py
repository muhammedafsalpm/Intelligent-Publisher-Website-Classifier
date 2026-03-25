# app/services/scraper.py
import httpx
from typing import Dict
import logging
import re
from app.config import settings

logger = logging.getLogger(__name__)

class WebsiteScraper:
    """Universal website scraper with tiered extraction (Trafilatura -> BS4 -> Regex)"""
    
    def __init__(self):
        self.timeout = settings.request_timeout
        self.max_content = self._get_safe_max_content(settings.max_content_length)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

    def _get_safe_max_content(self, length: int) -> int:
        """Ensure max content is within reasonable limits for LLM context"""
        return min(length, 15000)
    
    async def fetch(self, url: str) -> Dict:
        """Fetch website content using a universal approach (no hardcoded sites)"""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self.headers,
                verify=False
            ) as client:
                response = await client.get(url)
                
                logger.info(f"Scraper: HTTP {response.status_code} for {url}")
                
                if response.status_code in [200, 202]:
                    if response.text and len(response.text) > 500:
                        return self._extract_text_universal(response.text, url)
                    else:
                        logger.warning(f"Response body too small for {url}")
                        return self._error_response(url, "Empty or minimal response")
                else:
                    logger.warning(f"Fetch failed with HTTP {response.status_code}")
                    return self._error_response(url, f"HTTP {response.status_code}")
                    
        except httpx.TimeoutException:
            logger.error(f"Scrape timeout for {url}")
            return self._error_response(url, "Timeout")
        except Exception as e:
            logger.error(f"Scraper error for {url}: {e}")
            return self._error_response(url, str(e))
    
    def _extract_text_universal(self, html: str, url: str) -> Dict:
        """Tiered extraction strategy for maximum reliability across all domains"""
        
        # Method 1: Trafilatura (Scientific/Article extraction)
        try:
            import trafilatura
            main_text = trafilatura.extract(html, include_comments=False, include_tables=True)
            if main_text and len(main_text) > 300:
                logger.debug("Trafilatura extraction successful")
                return {
                    'title': self._extract_title(html),
                    'meta_description': self._extract_meta_description(html),
                    'main_text': main_text[:self.max_content],
                    'links': [],
                    'has_js_content': False
                }
        except Exception:
            pass
        
        # Method 2: BeautifulSoup (Selective extraction)
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Clean noise
            for tag in soup(["script", "style", "noscript", "meta", "link", "nav", "footer", "header"]):
                tag.decompose()
            
            # Target main areas
            main_text = ""
            for selector in ['main', 'article', '#content', '.content', '#main', '.main', 'section']:
                element = soup.select_one(selector)
                if element:
                    t = element.get_text(separator=' ', strip=True)
                    if len(t) > 500:
                        main_text = t
                        break
            
            # Fallback to pure body
            if len(main_text) < 300:
                body = soup.find('body')
                main_text = body.get_text(separator=' ', strip=True) if body else soup.get_text(separator=' ', strip=True)
            
            # Clean and return
            main_text = re.sub(r'\s+', ' ', main_text).strip()
            if len(main_text) > 100:
                logger.debug("BS4 extraction successful")
                return {
                    'title': self._extract_title(html),
                    'meta_description': self._extract_meta_description(html),
                    'main_text': main_text[:self.max_content],
                    'links': [],
                    'has_js_content': False
                }
        except Exception as e:
            logger.error(f"BS4 parsing failure: {e}")
        
        # Method 3: Regex (Raw fail-safe)
        return self._extract_regex_fallback(html, url)
    
    def _extract_title(self, html: str) -> str:
        """Regex-based title extraction"""
        match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""
    
    def _extract_meta_description(self, html: str) -> str:
        """Regex-based meta extraction"""
        patterns = [
            r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
            r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""
    
    def _extract_regex_fallback(self, html: str, url: str) -> Dict:
        """Bare-metal regex extraction for malformed HTML"""
        logger.info("Using regex fallback for extraction")
        # Strip code blocks
        text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        # Strip all tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return {
            'title': self._extract_title(html),
            'meta_description': self._extract_meta_description(html),
            'main_text': text[:self.max_content],
            'links': [],
            'has_js_content': False
        }
    
    def _error_response(self, url: str, error: str) -> Dict:
        return {
            'url': url,
            'title': '',
            'meta_description': '',
            'main_text': '',
            'links': [],
            'has_js_content': False,
            'error': error
        }
