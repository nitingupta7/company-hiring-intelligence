import asyncio
import logging
from typing import List, Dict

from config import config
from utils.playwright_utils import PlaywrightBrowser
from scraper.wellfound_discovery import WellfoundScraper
from scraper.hiring_checker import check_hiring
from scraper.social_media_finder import find_social_media
from scraper.data_validator import normalize_name, clean_social_media_url, validate_url
from scraper.output_writer import save_results

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def process_company(browser, company: Dict) -> Dict:
    """
    Processes a single company: checks hiring, finds social media, and validates data.
    """
    name = company.get("name", "Unknown")
    website = company.get("website")
    
    logger.info(f"--- Processing: {name} ---")
    
    # Ensure we have a website URL
    if not website:
        logger.warning(f"No website found for {name}. Skipping deeper analysis.")
        return company

    try:
        # 1. Check Hiring Status
        # Use Wellfound data as primary, fallback to site checker
        wellfound_hiring = company.get("hiring_status")
        
        if wellfound_hiring == "Hiring":
            logger.info(f"{name} is marked as Hiring on Wellfound. Enriching with careers URL...")
            hiring_data = await check_hiring(browser, website)
            if hiring_data.get("careers_url"):
                company["careers_url"] = hiring_data["careers_url"]
            # Preserve Wellfound's status
        else:
            logger.info(f"Hiring status unknown for {name} from Wellfound. Using website checker...")
            hiring_data = await check_hiring(browser, website)
            company.update(hiring_data)
        
        # 2. Find Social Media Profiles
        social_data = await find_social_media(browser, website)
        company.update(social_data)
        
        # 3. Data Normalization & Validation
        company["name"] = normalize_name(company["name"])
        
        # Clean social media URLs
        for platform in ["linkedin", "twitter", "facebook", "instagram", "youtube"]:
            if company.get(platform):
                company[platform] = clean_social_media_url(company[platform])
        
        if company.get("careers_url"):
            company["careers_url"] = clean_social_media_url(company["careers_url"])

        logger.info(f"Completed processing for {name}. Hiring: {company.get('hiring_status')}")
        
    except Exception as e:
        logger.error(f"Failed to process company {name}: {e}")
    
    return company

async def main():
    logger.info("Starting Talent Intelligence Agent...")
    
    async with PlaywrightBrowser(headless=config.HEADLESS) as browser:
        scraper = WellfoundScraper(browser)
        
        # 1. Discover Candidates
        # We fetch up to DAILY_LIMIT for the full analysis
        logger.info(f"Discovering companies with >${config.MIN_FUNDING_USD/1e6:.1f}M funding...")
        candidates = await scraper.scrape_companies(target_count=config.DAILY_LIMIT)
        
        if not candidates:
            logger.warning("No companies found matching the criteria.")
            return

        logger.info(f"Found {len(candidates)} candidates. Starting enrichment...")
        
        # 2. Process Companies
        enriched_results = []
        hiring_count = 0
        
        for i, company in enumerate(candidates):
            logger.info(f"Progress: {i+1}/{len(candidates)}")
            processed_company = await process_company(browser, company)
            enriched_results.append(processed_company)
            
            if processed_company.get("hiring_status") == "Hiring":
                hiring_count += 1

        # 3. Save Results
        logger.info("Exporting results...")
        
        # Map internal keys to Pretty Labels before saving
        mapping = {
            "name": "Company Name",
            "industry": "Industry",
            "total_funding": "Total Funding",
            "funding_stage": "Funding Stage",
            "headquarters": "Headquarters",
            "website": "Website",
            "careers_url": "Careers Page",
            "hiring_status": "Hiring Status",
            "jobs_count": "Active Jobs Count",
            "linkedin": "LinkedIn URL",
            "twitter": "X/Twitter URL",
            "facebook": "Facebook URL",
            "instagram": "Instagram URL",
            "youtube": "YouTube URL",
            "source_url": "Source URL"
        }
        
        mapped_results = []
        for res in enriched_results:
            mapped_res = {mapping.get(k, k): v for k, v in res.items()}
            mapped_results.append(mapped_res)
            
        save_results(mapped_results)
        
        # 4. Final Stats
        logger.info("==========================================")
        logger.info(f"Task Completed Successfully!")
        logger.info(f"Total companies processed: {len(enriched_results)}")
        logger.info(f"Hiring companies found: {hiring_count}")
        logger.info(f"Results saved to: {config.OUTPUT_EXCEL} and {config.OUTPUT_JSON}")
        logger.info("==========================================")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
    except Exception as e:
        logger.critical(f"Agent failed with critical error: {e}")
