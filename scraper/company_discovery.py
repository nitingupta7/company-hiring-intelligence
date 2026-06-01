
import asyncio
import logging
import re
import json
from typing import List, Dict
from urllib.parse import urljoin, urlparse, parse_qs
from utils.playwright_utils import PlaywrightBrowser
from utils.retry_utils import retry_async
from config.config import HEADLESS

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL      = "https://www.ycombinator.com"
DIRECTORY_URL = f"{BASE_URL}/companies"

class YCScraper:
    """
    Scrapes the Y Combinator company directory with robust extraction.
    """

    def __init__(self, browser):
        self.browser = browser

    def unwrap_yc_redirect(self, url: str) -> str:
        """Unwraps YC-internal redirects to find the destination URL."""
        if not url:
            return url
        if "ycombinator.com/offsite-link" in url:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            if 'url' in qs:
                return qs['url'][0]
        return url

    def _clean_website(self, url: str) -> str:
        """Filters out YC-internal links and unwraps redirects."""
        if not url:
            return None
        
        # 1. Unwrap YC redirect if present
        url = self.unwrap_yc_redirect(url)
        
        # 2. Check domain using urlparse
        try:
            domain = urlparse(url).netloc.lower()
        except Exception:
            return None
            
        internal_domains = [
            "ycombinator.com",
            "startupschool.org",
            "bookface.co"
        ]
        
        # Only filter out specific YC domains
        if any(p in domain for p in internal_domains):
            return None
            
        return url

    @retry_async()
    async def get_company_details(self, context, relative_url: str) -> Dict:
        """
        Extracts detailed company information from the YC detail page.
        """
        source_url = urljoin(BASE_URL, relative_url)
        page = await context.new_page()
        
        details = {
            "name": None,
            "industry": None,
            "total_funding": None,
            "funding_stage": None,
            "headquarters": None,
            "website": None,
            "source_url": source_url
        }

        try:
            logger.info(f"Extracting details from: {source_url}")
            await page.goto(source_url, wait_until="networkidle", timeout=30000)

            # --- Attempt 1: Extraction via data-page JSON (Most Robust) ---
            data_page_elem = await page.query_selector("div[data-page]")
            if data_page_elem:
                data_attr = await data_page_elem.get_attribute("data-page")
                try:
                    data = json.loads(data_attr)
                    comp_data = data.get("props", {}).get("company", {})
                    if comp_data:
                        details["name"] = comp_data.get("name")
                        details["industry"] = comp_data.get("industry")
                        details["website"] = self._clean_website(comp_data.get("website"))
                        details["headquarters"] = comp_data.get("location")
                        details["funding_stage"] = comp_data.get("batch_name") # e.g. "W24"
                        
                        # Sometimes industry is a list or nested
                        if not details["industry"] and comp_data.get("industries"):
                            details["industry"] = ", ".join(comp_data.get("industries"))
                except Exception as e:
                    logger.warning(f"Failed to parse data-page JSON for {source_url}: {e}")

            # --- Attempt 2: Fallback Selectors ---
            if not details["name"]:
                name_elem = await page.query_selector("h1")
                details["name"] = await name_elem.inner_text() if name_elem else None

            if not details["website"]:
                website_elem = await page.query_selector("div.text-linkColor a, a[aria-label='Company website']")
                if website_elem:
                    raw_url = await website_elem.get_attribute("href")
                    details["website"] = self._clean_website(raw_url)

            if not details["funding_stage"]:
                batch_elem = await page.query_selector("a[href*='batch=']")
                details["funding_stage"] = await batch_elem.inner_text() if batch_elem else None

            if not details["headquarters"]:
                loc_elem = await page.query_selector("a[href*='/location/']")
                details["headquarters"] = await loc_elem.inner_text() if loc_elem else None

            # --- Funding Amount Extraction (Regex remains best for this) ---
            content = await page.content()
            text_content = re.sub(r'<[^>]+>', ' ', content)
            funding_patterns = [
                r"Total Funding:?\s*\$([\d\.]+)([MBK]?)",
                r"raised\s*\$([\d\.]+)([MBK]?)",
                r"valuation\s+of\s+\$([\d\.]+)([MBK]?)",
                r"\$([\d\.]+)([MBK]?)\s+in\s+funding",
                r"total\s+raised\s+is\s+\$([\d\.]+)([MBK]?)"
            ]

            for pattern in funding_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    amount = float(match.group(1))
                    suffix = match.group(2).upper()
                    multipliers = {'M': 1_000_000, 'B': 1_000_000_000, 'K': 1_000}
                    details["total_funding"] = amount * multipliers.get(suffix, 1)
                    break
            
            # Map funding stage more explicitly if it contains typical round names
            if not details["funding_stage"] or details["funding_stage"] == "N/A":
                for round_name in ["Seed", "Series A", "Series B", "Series C"]:
                    if round_name.lower() in text_content.lower():
                        details["funding_stage"] = round_name
                        break

            return details

        except Exception as e:
            logger.error(f"Error fetching details for {source_url}: {e}")
            return details
        finally:
            await page.close()

    async def scrape_companies(self, target_count: int = 30) -> List[Dict]:
        """
        Scrapes YC directory until target_count matches are found.
        """
        context = await self.browser.new_context()
        try:
            page = await context.new_page()
            logger.info(f"Navigating to {DIRECTORY_URL}")
            await page.goto(DIRECTORY_URL, wait_until="networkidle")

            final_results = []
            seen_urls = set()
            scroll_attempts = 0
            max_scroll_attempts = 50 

            while len(final_results) < target_count and scroll_attempts < max_scroll_attempts:
                # Use robust card selector
                cards = await page.query_selector_all("a[href^='/companies/']")
                
                new_candidates = []
                for card in cards:
                    href = await card.get_attribute("href")
                    if not href or href in seen_urls or href == "/companies":
                        continue
                    
                    seen_urls.add(href)
                    # Extract basic info from card as backup/initial data
                    name_elem = await card.query_selector("span[class*='_companyName_'], .font-bold")
                    name = await name_elem.inner_text() if name_elem else "Unknown"
                    
                    tags = await card.query_selector_all("span[class*='_tag_'], .px-2")
                    tag_texts = [await t.inner_text() for t in tags]
                    industry = tag_texts[0] if len(tag_texts) > 0 else "Unknown"
                    location = tag_texts[1] if len(tag_texts) > 1 else "Unknown"

                    new_candidates.append({
                        "name": name,
                        "yc_url": href,
                        "industry": industry,
                        "location": location
                    })

                # Process new candidates found in this scroll
                for candidate in new_candidates:
                    details = await self.get_company_details(context, candidate["yc_url"])
                    
                    # Merge and ensure requested field mapping
                    result = {
                        "name": details["name"] or candidate["name"],
                        "industry": details["industry"] or candidate["industry"],
                        "total_funding": details["total_funding"] or "N/A",
                        "funding_stage": details["funding_stage"] or "N/A",
                        "headquarters": details["headquarters"] or candidate["location"],
                        "website": details["website"] or "N/A",
                        "source_url": details["source_url"]
                    }

                    # Basic validation: If it has a website and name, it's likely valid
                    if result["name"] != "Unknown" and result["website"] != "N/A":
                        final_results.append(result)
                        logger.info(f"MATCH ({len(final_results)}/{target_count}): {result['name']}")
                    
                    if len(final_results) >= target_count:
                        break

                if len(final_results) < target_count:
                    logger.info(f"Scrolling to load more... (Current results: {len(final_results)})")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                    scroll_attempts += 1
                else:
                    break

            return final_results
        finally:
            await context.close()

async def main():
    async with PlaywrightBrowser(headless=HEADLESS) as browser:
        scraper = YCScraper(browser)
        results = await scraper.scrape_companies(target_count=5) # Test with 5
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
