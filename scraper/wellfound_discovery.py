
import asyncio
import logging
import json
import re
from typing import List, Dict
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from utils.playwright_utils import PlaywrightBrowser, get_browser_context, new_stealth_page
from utils.retry_utils import retry_async
from config.config import HEADLESS, MIN_FUNDING_USD

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://wellfound.com"

class WellfoundScraper:
    def __init__(self, browser):
        self.browser = browser

    @retry_async()
    async def get_company_details(self, context, profile_url: str) -> Dict:
        """Visits the profile page to extract detailed info including social links."""
        page = await new_stealth_page(context)
        details = {
            "name": None,
            "industry": None,
            "total_funding": None,
            "funding_stage": None,
            "headquarters": None,
            "website": None,
            "linkedin": None,
            "twitter": None,
            "hiring_status": "Unknown",
            "source_url": profile_url
        }
        
        try:
            logger.info(f"Visiting Wellfound profile: {profile_url}")
            await asyncio.sleep(2)
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            script_tag = await page.query_selector("script#__NEXT_DATA__")
            if script_tag:
                content = await script_tag.inner_text()
                try:
                    data = json.loads(content)
                    apollo_state = data.get("props", {}).get("pageProps", {}).get("apolloState", {})
                    
                    for key in apollo_state.keys():
                        if key.startswith("Startup:"):
                            comp_data = apollo_state[key]
                            details["name"] = comp_data.get("name")
                            details["website"] = comp_data.get("companyUrl")
                            details["total_funding"] = comp_data.get("totalRaisedAmount")
                            details["linkedin"] = comp_data.get("linkedInUrl")
                            details["twitter"] = comp_data.get("twitterUrl")
                            
                            # Extract hiring status
                            if comp_data.get("isHiring"):
                                details["hiring_status"] = "Hiring"
                            elif comp_data.get("highlightedJobCount", 0) > 0:
                                details["hiring_status"] = "Hiring"
                            
                            if "tags" in comp_data:
                                tags = []
                                for tag_ref in comp_data["tags"]:
                                    tag_key = tag_ref.get("__ref")
                                    if tag_key and tag_key in apollo_state:
                                        tags.append(apollo_state[tag_key].get("displayName"))
                                details["industry"] = ", ".join(filter(None, tags))
                            
                            if "locations" in comp_data:
                                locs = []
                                for loc_ref in comp_data["locations"]:
                                    loc_key = loc_ref.get("__ref")
                                    if loc_key and loc_key in apollo_state:
                                        locs.append(apollo_state[loc_key].get("displayName"))
                                details["headquarters"] = ", ".join(filter(None, locs))
                            
                            if "latestFundingRound" in comp_data:
                                round_ref = comp_data["latestFundingRound"].get("__ref")
                                if round_ref and round_ref in apollo_state:
                                    details["funding_stage"] = apollo_state[round_ref].get("roundName")
                            break
                except Exception as e:
                    logger.warning(f"Error parsing Apollo state for {profile_url}: {e}")

            if not details["name"]:
                details["name"] = await page.inner_text("h1") if await page.query_selector("h1") else None
            
            if not details["website"]:
                website_elem = await page.query_selector("a[data-test='startup-website-link']")
                details["website"] = await website_elem.get_attribute("href") if website_elem else None

            if not details["linkedin"]:
                li_elem = await page.query_selector("a[href*='linkedin.com/company']")
                details["linkedin"] = await li_elem.get_attribute("href") if li_elem else None
            
            if not details["twitter"]:
                tw_elem = await page.query_selector("a[href*='twitter.com/'], a[href*='x.com/']")
                details["twitter"] = await tw_elem.get_attribute("href") if tw_elem else None

            return details

        except Exception as e:
            logger.error(f"Error getting details for {profile_url}: {e}")
            return details
        finally:
            await page.close()

    async def scrape_companies(self, target_count: int = 10) -> List[Dict]:
        """Scrapes Wellfound directory for companies matching criteria."""
        context = await get_browser_context(self.browser, stealth=True)
        try:
            page = await new_stealth_page(context)
            industries = ["ai", "fintech", "saas", "enterprise-software", "e-commerce"]
            results = []
            seen_urls = set()
            
            for industry in industries:
                if len(results) >= target_count:
                    break
                
                url = f"{BASE_URL}/startups/industry/{industry}"
                logger.info(f"Navigating to Wellfound industry page: {url}")
                
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(5)
                    
                    profile_links = []
                    script_tag = await page.query_selector("script#__NEXT_DATA__")
                    if script_tag:
                        content = await script_tag.inner_text()
                        try:
                            data = json.loads(content)
                            apollo_state = data.get("props", {}).get("pageProps", {}).get("apolloState", {})
                            for key, value in apollo_state.items():
                                if key.startswith("Startup:") and "slug" in value:
                                    slug = value["slug"]
                                    full_url = f"{BASE_URL}/company/{slug}"
                                    if full_url not in seen_urls:
                                        seen_urls.add(full_url)
                                        profile_links.append(full_url)
                        except Exception as e:
                            logger.warning(f"Failed to parse __NEXT_DATA__ on industry page: {e}")
                    
                    if not profile_links:
                        cards = await page.query_selector_all("a[href*='/company/']")
                        for card in cards:
                            href = await card.get_attribute("href")
                            if href:
                                full_url = urljoin(BASE_URL, href)
                                base_url = full_url.split('?')[0].rstrip('/')
                                if "/company/" in base_url and base_url not in seen_urls:
                                    parts = base_url.split('/company/')
                                    if len(parts) == 2 and '/' not in parts[1]:
                                        seen_urls.add(base_url)
                                        profile_links.append(base_url)
                    
                    logger.info(f"Found {len(profile_links)} candidates on {industry} page.")
                    for link in profile_links:
                        details = await self.get_company_details(context, link)
                        funding = details.get("total_funding")
                        if funding and isinstance(funding, (int, float)) and funding < MIN_FUNDING_USD:
                            continue
                        
                        if details["name"] and details["website"]:
                            results.append(details)
                            logger.info(f"Added: {details['name']} | Funding: {details['total_funding']}")
                        
                        if len(results) >= target_count:
                            break
                            
                except Exception as e:
                    logger.error(f"Error scraping industry {industry}: {e}")
            
            return results
        finally:
            await context.close()

async def main():
    async with PlaywrightBrowser(headless=HEADLESS) as browser:
        scraper = WellfoundScraper(browser)
        results = await scraper.scrape_companies(target_count=2)
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
