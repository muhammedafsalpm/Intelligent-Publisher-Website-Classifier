# app/services/scraper.py
import httpx
from bs4 import BeautifulSoup
from typing import Dict
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class WebsiteScraper:
    """HTTP-only scraper - no JavaScript rendering for maximum stability and speed"""
    
    def __init__(self):
        self.timeout = settings.request_timeout
        self.max_content = settings.max_content_length
        # Use a more realistic browser-like user agent
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
    
    async def fetch(self, url: str) -> Dict:
        """Fetch website content using pure HTTP"""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self.headers,
                verify=False  # Avoid SSL issues
            ) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    return self._parse_html(response.text)
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")
                    return self._error_response(url, f"HTTP {response.status_code}")
                
        except httpx.TimeoutException:
            logger.error(f"Timeout for {url}")
            return self._error_response(url, "Request timeout")
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return self._error_response(url, str(e))
    
    def _parse_html(self, html: str) -> Dict:
        """Extract relevant content from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove non-content elements to reduce token noise
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "iframe", "object"]):
            tag.decompose()
        
        # Extract title
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        
        # Extract meta description
        meta_desc = soup.find("meta", {"name": "description"})
        meta_description = meta_desc.get("content", "").strip() if meta_desc else ""
        
        # Extract main text
        main_text = soup.get_text(separator=' ', strip=True)
        main_text = ' '.join(main_text.split())  # Normalize whitespace
        main_text = main_text[:self.max_content]
        
        # Extract links for category signals
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith(('http://', 'https://')):
                links.append(href)
        links = list(set(links))[:50]
        
        return {
            'title': title,
            'meta_description': meta_description,
            'main_text': main_text,
            'links': links,
            'has_js_content': False  # Pure HTTP scraper
        }
    
    def _error_response(self, url: str, error: str) -> Dict:
        """Return empty result for error states"""
        return {
            'url': url,
            'title': '',
            'meta_description': '',
            'main_text': '',
            'links': [],
            'has_js_content': False,
            'error': error
        }
