import os
from dotenv import load_dotenv

load_dotenv()

MIN_FUNDING_USD = int(os.getenv("MIN_FUNDING_USD", 4000000))
SOURCES = ["wellfound"]  # Switched from YC to Wellfound
OUTPUT_EXCEL = "output/companies.xlsx"
OUTPUT_JSON = "output/companies.json"
LOG_FILE = "logs/scraper.log"
HEADLESS = True
TIMEOUT_MS = 30000
MAX_RETRIES = 3
DAILY_LIMIT = 20
