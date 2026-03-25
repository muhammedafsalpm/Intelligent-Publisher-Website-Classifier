import httpx
import asyncio
from playwright.async_api import async_playwright
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
import logging
from app.config import settings
from app.utils.retry import retry_async

logger = logging.getLogger(__name__)

class WebsiteScraper:
    def __init__(self):
        self.timeout = settings.request_timeout
        self.max_content = settings.max_content_length
        self.headers = {'User-Agent': settings.user_agent}
    
    async def fetch(self, url: str) -> Dict:
        """Fetch website content with graceful degradation"""
        try:
            # Try simple HTTP first
            content, used_js = await self._fetch_with_retry(url)
            
            if content and not used_js and len(content['main_text']) < settings.min_content_length:
                # Content too short, try JS rendering
                content, used_js = await self._fetch_with_playwright(url)
                content['has_js_content'] = True
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return {
                'url': url,
                'title': '',
                'meta_description': '',
                'main_text': '',
                'links': [],
                'has_js_content': False,
                'error': str(e)
            }
    
    async def _fetch_with_retry(self, url: str) -> Tuple[Dict, bool]:
        """Fetch with retry logic"""
        async def fetch_http():
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self.headers
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return self._parse_html(response.text), False
        
        try:
            return await retry_async(
                fetch_http,
                max_retries=2,
                exceptions=(httpx.TimeoutException, httpx.NetworkError)
            )
        except Exception:
            return await self._fetch_with_playwright(url)
    
    async def _fetch_with_playwright(self, url: str) -> Tuple[Dict, bool]:
        """Fetch using Playwright for JS-heavy sites"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.headers['User-Agent'],
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                
                try:
                    await page.goto(url, timeout=self.timeout * 1000)
                    await page.wait_for_load_state('networkidle')
                    
                    # Scroll to load lazy content
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(1)
                    
                    content = await page.content()
                    return self._parse_html(content), True
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Playwright fetch failed for {url}: {e}")
            raise
    
    def _parse_html(self, html: str) -> Dict:
        """Extract relevant content from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove non-content elements
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
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
        
        # Extract links
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith(('http://', 'https://')):
                links.append(href)
        links = list(set(links))[:50]  # Deduplicate and limit
        
        return {
            'title': title,
            'meta_description': meta_description,
            'main_text': main_text,
            'links': links
        }
