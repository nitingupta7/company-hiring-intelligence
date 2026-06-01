import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils.retry_utils import retry_async
from utils.playwright_utils import get_browser_context

logger = logging.getLogger(__name__)

@retry_async()
async def check_hiring(browser, company_website_url):
    """
    Checks if a company is hiring by visiting their website and looking for a careers page.
    """
    context = await get_browser_context(browser)
    page = await context.new_page()
    
    result = {
        "hiring_status": "Not Hiring",
        "jobs_count": 0,
        "careers_url": None
    }
    
    try:
        logger.info(f"Checking hiring status for {company_website_url}")
        await page.goto(company_website_url, wait_until="networkidle", timeout=30000)
        
        soup = BeautifulSoup(await page.content(), 'html.parser')
        
        # Keywords to look for in links
        career_keywords = ["careers", "jobs", "work with us", "join us", "opportunities", "openings"]
        
        career_link = None
        for a in soup.find_all('a', href=True):
            text = a.get_text().lower()
            href = a['href'].lower()
            
            if any(keyword in text for keyword in career_keywords) or \
               any(keyword in href for keyword in ["/careers", "/jobs", "career-", "job-"]):
                career_link = urljoin(company_website_url, a['href'])
                break
        
        if career_link:
            result["careers_url"] = career_link
            logger.info(f"Found careers page: {career_link}")
            
            # Visit the careers page
            await page.goto(career_link, wait_until="networkidle", timeout=30000)
            career_soup = BeautifulSoup(await page.content(), 'html.parser')
            
            # Detect active job listings
            # Look for job-related keywords and structures
            career_text = career_soup.get_text().lower()
            
            hiring_indicators = ["open positions", "current openings", "apply now", "search jobs", "view jobs", "available roles"]
            is_hiring = any(indicator in career_text for indicator in hiring_indicators)
            
            # Heuristic for job count: look for elements that might represent job postings
            # Common patterns: elements with "job", "listing", "position" in their class or ID
            job_elements = career_soup.find_all(lambda tag: tag.name in ['div', 'li', 'tr'] and 
                                             any(attr in str(tag.get('class', [])) or attr in str(tag.get('id', ''))
                                                 for attr in ['job', 'listing', 'position', 'opening', 'vacancy']))
            
            # Filter out very small elements or those that are clearly not job cards
            job_elements = [el for el in job_elements if len(el.get_text()) > 20]
            
            # Fallback if no specific elements found but text indicates hiring
            if is_hiring and not job_elements:
                # Count list items in specific sections or just assume 1 if text is strong
                result["hiring_status"] = "Hiring"
                result["jobs_count"] = 1 # Minimal estimate
            elif job_elements:
                result["hiring_status"] = "Hiring"
                result["jobs_count"] = len(job_elements)
            elif is_hiring:
                result["hiring_status"] = "Hiring"
                result["jobs_count"] = 1
                
        return result

    except Exception as e:
        logger.error(f"Error checking hiring for {company_website_url}: {e}")
        return {
            "hiring_status": "Error",
            "jobs_count": 0,
            "careers_url": None
        }
    finally:
        await page.close()
        await context.close()
