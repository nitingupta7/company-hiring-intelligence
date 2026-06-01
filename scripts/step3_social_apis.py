import os
import pandas as pd
from googleapiclient.discovery import build
from dotenv import load_dotenv
import time
from ddgs import DDGS
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

def ddg_search(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=1))
            if results:
                return results[0]['href']
    except Exception as e:
        logger.error(f"Search error: {e}")
    return None

def search_twitter(company_name):
    result = ddg_search(f"{company_name} official site:twitter.com")
    logger.info(f"  Twitter: {result}")
    return result

def search_facebook(company_name):
    result = ddg_search(f"{company_name} official site:facebook.com")
    logger.info(f"  Facebook: {result}")
    return result

def search_linkedin(company_name):
    result = ddg_search(f"{company_name} official site:linkedin.com/company")
    logger.info(f"  LinkedIn: {result}")
    return result

def search_instagram(company_name):
    result = ddg_search(f"{company_name} official site:instagram.com")
    logger.info(f"  Instagram: {result}")
    return result

def search_youtube(company_name):
    # Try YouTube API first
    if YOUTUBE_API_KEY:
        try:
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            request = youtube.search().list(
                q=company_name,
                part="snippet",
                type="channel",
                maxResults=1
            )
            response = request.execute()
            if response.get('items'):
                channel_id = response['items'][0]['snippet']['channelId']
                result = f"https://www.youtube.com/channel/{channel_id}"
                logger.info(f"  YouTube (API): {result}")
                return result
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                logger.info("  YouTube quota exceeded, using DuckDuckGo fallback...")
            else:
                logger.error(f"  YouTube API error: {e}")

    # Fallback to DuckDuckGo
    result = ddg_search(f"{company_name} official site:youtube.com")
    logger.info(f"  YouTube (DDG): {result}")
    return result

def enrich_social_apis():
    input_file = 'output/step2_enriched.csv'
    if not os.path.exists(input_file):
        input_file = 'output/step1_base.csv'
        logger.info(f"Step 2 output not found. Falling back to {input_file}")

    if not os.path.exists(input_file):
        logger.error("Input file not found.")
        return

    logger.info(f"Loading companies from {input_file}...")
    df = pd.read_csv(input_file)

    if 'name' not in df.columns and 'Company Name' not in df.columns:
        logger.error("'name' or 'Company Name' column missing in CSV.")
        return

    if 'Company Name' in df.columns:
        df = df.rename(columns={'Company Name': 'name'})

    logger.info(f"Enriching {len(df)} companies with social links...")

    twitter_links = []
    youtube_links = []
    facebook_links = []
    linkedin_links = []
    instagram_links = []

    for idx, row in df.iterrows():
        name = row['name']
        logger.info(f"\n[{idx+1}/{len(df)}] Searching for {name}...")

        twitter_links.append(search_twitter(name))
        youtube_links.append(search_youtube(name))
        facebook_links.append(search_facebook(name))
        linkedin_links.append(search_linkedin(name))
        instagram_links.append(search_instagram(name))

        time.sleep(2)

    df['Twitter URL'] = twitter_links
    df['YouTube URL'] = youtube_links
    df['Facebook URL'] = facebook_links
    df['LinkedIn URL'] = linkedin_links
    df['Instagram URL'] = instagram_links

    os.makedirs('output', exist_ok=True)
    output_path = 'output/step3_social.csv'
    df.to_csv(output_path, index=False)
    logger.info(f"Step 3 complete. Results saved to {output_path}")
    print(df[['name','Twitter URL','YouTube URL','Facebook URL','LinkedIn URL','Instagram URL']])

if __name__ == "__main__":
    enrich_social_apis()
