import logging
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from utils.retry_utils import retry_async
from utils.playwright_utils import get_browser_context, new_stealth_page

logger = logging.getLogger(__name__)

async def extract_from_soup(soup, social_media):
    """Helper to extract social links from a BeautifulSoup object."""
    platforms = {
        "linkedin.com/company/": "linkedin",
        "twitter.com/": "twitter",
        "x.com/": "twitter",
        "facebook.com/": "facebook",
        "instagram.com/": "instagram",
        "youtube.com/": "youtube"
    }
    
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        href_lower = href.lower()
        for pattern, platform in platforms.items():
            if pattern in href_lower:
                # Basic validation: ensure it's not just the homepage
                # e.g., https://linkedin.com/company/abc is > 4 parts
                parts = [p for p in urlparse(href).path.split('/') if p]
                if len(parts) >= 1 or "linkedin.com/company/" in href_lower:
                    if not social_media[platform]:
                        social_media[platform] = href
    return social_media

@retry_async()
async def find_social_media(browser, company_website_url):
    """
    Extracts social media URLs from a company's website with robust sub-page checking.
    """
    if not company_website_url or company_website_url == "N/A":
        return {k: None for k in ["linkedin", "twitter", "facebook", "instagram", "youtube"]}

    context = await get_browser_context(browser, stealth=True)
    
    social_media = {
        "linkedin": None,
        "twitter": None,
        "facebook": None,
        "instagram": None,
        "youtube": None
    }
    
    try:
        # 1. Check Homepage
        page = await new_stealth_page(context)
        logger.info(f"Finding social media for {company_website_url}")
        await page.goto(company_website_url, wait_until="networkidle", timeout=30000)
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        social_media = await extract_from_soup(soup, social_media)
        
        # 2. Check for "Contact" or "About" links if some are missing
        if not all(social_media.values()):
            potential_pages = []
            for a in soup.find_all('a', href=True):
                text = a.text.lower()
                href = a['href'].lower()
                if any(x in text for x in ['contact', 'about', 'team']):
                    link = urljoin(company_website_url, a['href'])
                    if urlparse(link).netloc == urlparse(company_website_url).netloc:
                        potential_pages.append(link)
            
            # Common patterns if not found in links
            common_suffixes = ['/contact', '/about', '/contact-us']
            for s in common_suffixes:
                potential_pages.append(urljoin(company_website_url, s))
            
            # De-duplicate and limit to top 3
            potential_pages = list(dict.fromkeys(potential_pages))[:3]
            
            for sub_url in potential_pages:
                if all(social_media.values()):
                    break
                try:
                    logger.info(f"Checking sub-page: {sub_url}")
                    await page.goto(sub_url, wait_until="domcontentloaded", timeout=15000)
                    sub_soup = BeautifulSoup(await page.content(), 'html.parser')
                    social_media = await extract_from_soup(sub_soup, social_media)
                except Exception as e:
                    logger.debug(f"Failed to check sub-page {sub_url}: {e}")

        await page.close()
        return social_media

    except Exception as e:
        logger.error(f"Error finding social media for {company_website_url}: {e}")
        return social_media
    finally:
        await context.close()
