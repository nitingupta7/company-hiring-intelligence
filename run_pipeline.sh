#!/bin/bash

# ============================================
# CRON HEARTBEAT — proves cron triggered this
# ============================================
echo "=========================================="
echo "CRON TRIGGERED AT: $(date)"
echo "Running on: $(hostname)"
echo "Working dir: $(pwd)"
echo "=========================================="

echo "=========================================="
echo "   Company Data Pipeline - Auto Batch"
echo "=========================================="

/Users/nitingupta/Documents/Python_project/venv/bin/python3 - << 'PYEOF'
import os
import json
import pandas as pd
import time
import logging
from pathlib import Path
from googleapiclient.discovery import build
from dotenv import load_dotenv
from ddgs import DDGS
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from datetime import date

load_dotenv("/Users/nitingupta/Documents/Python_project/.env")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
ROOT_DIR = Path('/Users/nitingupta/Documents/Python_project')
INPUT_CSV = '/Users/nitingupta/Desktop/Python_project/input/investments_VC.csv'
OUTPUT_JSON = ROOT_DIR / 'output' / 'companies.json'
OUTPUT_XLSX = ROOT_DIR / 'output' / 'companies.xlsx'
BATCH_FILE = ROOT_DIR / 'output' / 'batch_tracker.txt'
BATCH_SIZE = 20

OUTPUT_COLUMNS = [
    "Company Name", "Industry", "Total Funding", "Funding Stage",
    "Headquarters", "Website", "Careers Page", "Hiring Status",
    "LinkedIn URL", "X/Twitter URL", "Facebook URL",
    "Instagram URL", "YouTube URL", "Source URL"
]

start = int(BATCH_FILE.read_text()) if BATCH_FILE.exists() else 0
df = pd.read_csv(INPUT_CSV, encoding='latin1')
df = df[df['name'].str.match(r'^[A-Za-z]')].reset_index(drop=True)
total = len(df)

if start >= total:
    logger.info('All companies processed! Resetting...')
    start = 0

batch = df.iloc[start:start+BATCH_SIZE]
BATCH_FILE.write_text(str(start + BATCH_SIZE))
logger.info(f'Processing companies {start+1} to {start+BATCH_SIZE} of {total}')

def ddg_search(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=1))
            if results:
                return results[0]['href']
    except Exception as e:
        logger.error(f"DDG error: {e}")
    return 'N/A'

def search_youtube(name):
    if YOUTUBE_API_KEY:
        try:
            yt = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            r = yt.search().list(q=name, part='snippet', type='channel', maxResults=1).execute()
            if r.get('items'):
                cid = r['items'][0]['snippet']['channelId']
                return f"https://www.youtube.com/channel/{cid}"
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                logger.info("YouTube quota exceeded, using DDG fallback...")
    return ddg_search(f"{name} official site:youtube.com")

new_records = []
for idx, row in batch.iterrows():
    name = str(row.get('name', 'N/A'))
    logger.info(f"[{len(new_records)+1}/{BATCH_SIZE}] Processing {name}...")
    record = {
        "Company Name":  name,
        "Industry":      str(row.get('market', 'N/A')).strip() or 'N/A',
        "Total Funding": str(row.get('funding_total_usd', 'N/A')).strip() or 'N/A',
        "Funding Stage": str(row.get('funding_rounds', 'N/A')).strip() or 'N/A',
        "Headquarters":  str(row.get('country_code', 'N/A')).strip() or 'N/A',
        "Website":       str(row.get('homepage_url', 'N/A')).strip() or 'N/A',
        "Careers Page":  'N/A',
        "Hiring Status": 'Unknown',
        "LinkedIn URL":  ddg_search(f"{name} official site:linkedin.com/company"),
        "X/Twitter URL": ddg_search(f"{name} official site:twitter.com"),
        "Facebook URL":  ddg_search(f"{name} official site:facebook.com"),
        "Instagram URL": ddg_search(f"{name} official site:instagram.com"),
        "YouTube URL":   search_youtube(name),
        "Source URL":    str(row.get('permalink', 'N/A')).strip() or 'N/A',
    }
    new_records.append(record)
    time.sleep(2)

existing = json.loads(OUTPUT_JSON.read_text()) if OUTPUT_JSON.exists() else []
existing_names = {r.get('Company Name') for r in existing}
new_only = [r for r in new_records if r.get('Company Name') not in existing_names]
all_records = existing + new_only
OUTPUT_JSON.write_text(json.dumps(all_records, indent=2, ensure_ascii=False))
logger.info(f"JSON saved: {len(all_records)} total records")

wb = Workbook()
ws = wb.active
ws.title = "Companies"
ws.append(OUTPUT_COLUMNS)
header_fill = PatternFill(fill_type="solid", fgColor="1F4E78")
header_font = Font(color="FFFFFF", bold=True)
for cell in ws[1]:
    cell.fill = header_fill
    cell.font = header_font
for record in all_records:
    ws.append([record.get(col, 'N/A') for col in OUTPUT_COLUMNS])
for i, col in enumerate(OUTPUT_COLUMNS, 1):
    ws.column_dimensions[get_column_letter(i)].width = 20
wb.save(OUTPUT_XLSX)
logger.info(f"Excel saved: {len(all_records)} total records")

import shutil
today = date.today().strftime('%Y-%m-%d')
backup_dir = ROOT_DIR / 'output' / 'daily'
backup_dir.mkdir(exist_ok=True)
shutil.copy(OUTPUT_JSON, backup_dir / f'companies_{today}.json')
shutil.copy(OUTPUT_XLSX, backup_dir / f'companies_{today}.xlsx')
logger.info(f"Daily backup saved for {today}")
logger.info(f"Pipeline complete! Total: {len(all_records)} companies")
PYEOF

# ============================================
# COMPLETION MARKER — shows cron finished
# ============================================
echo "=========================================="
echo "CRON JOB COMPLETED AT: $(date)"
echo "Output files:"
ls -lh /Users/nitingupta/Documents/Python_project/output/companies.*
echo "=========================================="
open /Users/nitingupta/Documents/Python_project/output/companies.xlsx
