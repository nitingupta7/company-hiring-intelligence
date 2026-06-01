# Company Hiring Intelligence

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/Playwright-Automated-45ba4b?style=flat&logo=playwright&logoColor=white)](https://playwright.dev/python/docs/intro)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Processing-150458?style=flat&logo=pandas&logoColor=white)](https://pandas.pydata.org/docs/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://docs.streamlit.io)
[![OpenPyXL](https://img.shields.io/badge/OpenPyXL-Excel%20Export-217346?style=flat)](https://openpyxl.readthedocs.io/en/stable/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Stars](https://img.shields.io/github/stars/nitingupta7/company-hiring-intelligence?style=flat)](https://github.com/nitingupta7/company-hiring-intelligence/stargazers)

> An automated Playwright-based talent intelligence platform that discovers well-funded startups (>$4M), verifies hiring activity, and aggregates company, careers, LinkedIn, and social media data into structured Excel and JSON reports — fully automated with cron scheduling and a live Streamlit dashboard.

This repository provides **two complete approaches** for collecting company hiring intelligence:

1. **Automated Pipeline Script:** A fully automated batch scraper that runs on cron schedule, processes 48,966+ VC-funded companies from a Crunchbase dataset, and outputs clean structured Excel + JSON reports.
2. **Streamlit Live Dashboard:** An interactive real-time frontend to filter, search, visualize, and export the collected data without touching the terminal.

---

## Table of Contents

- [1. Automated Pipeline](#1-automated-pipeline)
  - [Features](#features)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Implementation](#implementation)
  - [How It Works — Step by Step](#how-it-works--step-by-step)
  - [Sample Output](#sample-output)
  - [Limitations & Challenges](#limitations--challenges)
- [2. Streamlit Live Dashboard](#2-streamlit-live-dashboard)
  - [Dashboard Features](#dashboard-features)
  - [Getting Started](#getting-started)
  - [Dashboard Sections](#dashboard-sections)
- [Data Fields Reference](#data-fields-reference)
- [Auto Scheduling with Cron](#auto-scheduling-with-cron)
- [Project Structure](#project-structure)
- [Bonus Features](#bonus-features)
- [Resources & Support](#resources--support)

---

## 1. Automated Pipeline

A Python + Playwright implementation that automatically discovers well-funded companies, finds their social media profiles, verifies hiring status, and saves everything to structured output files.

### Features

This pipeline collects publicly available data, including:

- **Company fundamentals** — name, industry, headquarters country, official website
- **Funding data** — total funding raised in USD, number of funding rounds completed
- **Hiring verification** — careers page detection, status: Hiring / Not Hiring / Unknown
- **LinkedIn profile** — company LinkedIn page URL
- **Twitter/X profile** — company Twitter/X handle URL
- **Facebook page** — company Facebook URL
- **Instagram profile** — company Instagram URL
- **YouTube channel** — company YouTube channel URL
- **Source tracking** — original Crunchbase permalink for every record
- **Batch resumption** — automatically resumes from last processed position using [batch_tracker.txt](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/output/batch_tracker.txt)
- **Deduplication** — prevents duplicate records from appearing in output files
- **Daily backups** — copies both output files to `output/daily/` with date stamp every run
- **Multi-engine fallback** — uses 7+ search engines (Google → DuckDuckGo → Brave → Yandex → Yahoo → Mojeek → Wikipedia → Grokipedia) to maximize social media coverage


### Prerequisites

- Python 3.10 or higher installed
- pip package manager
- macOS or Linux (required for cron auto-scheduling)
- YouTube Data API v3 key *(optional — automatically falls back to DuckDuckGo if not set or quota exceeded)*
- Input CSV file with VC investment data — included as [startup-investments-crunchbase.zip](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/startup-investments-crunchbase.zip)


### Installation

**Step 1 — Clone the repository:**

```bash
git clone https://github.com/nitingupta7/company-hiring-intelligence.git
cd company-hiring-intelligence
```

**Step 2 — Create and activate a virtual environment:**

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

**Step 3 — Install all Python dependencies:**

```bash
pip install -r requirements.txt
```

View the full list of dependencies: [requirements.txt](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/requirements.txt)

**Step 4 — Install Playwright browser engine:**

```bash
playwright install chromium
```

**Step 5 — Set up your environment variables:**

```bash
cp env_template .env
```

View the environment template: [env_template](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/env_template)

Open `.env` and add your YouTube API key:

```env
YOUTUBE_API_KEY=your_youtube_data_api_v3_key_here
```

**Step 6 — Extract the Crunchbase dataset:**

```bash
unzip startup-investments-crunchbase.zip -d input/
```

Dataset archive: [startup-investments-crunchbase.zip](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/startup-investments-crunchbase.zip)

> 💡 **Note:** The YouTube API key is completely optional. If missing or daily quota is exceeded (10,000 units/day), the pipeline automatically switches to DuckDuckGo search to find YouTube channel URLs — no manual action required.


### Configuration

All pipeline settings live in [config/config.py](https://github.com/nitingupta7/company-hiring-intelligence/tree/main/config):

| Parameter | Type | Default | Description |
|---|---|---|---|
| `MIN_FUNDING_USD` | `int` | `4_000_000` | Minimum funding threshold — companies below this are skipped |
| `BATCH_SIZE` | `int` | `20` | Number of companies processed per single pipeline run |
| `HEADLESS` | `bool` | `True` | Run Playwright Chromium browser in headless (invisible) mode |
| `TIMEOUT_MS` | `int` | `30000` | Maximum page load wait time in milliseconds |
| `MAX_RETRIES` | `int` | `3` | Number of retry attempts when a request fails |
| `RETRY_DELAY` | `int` | `2` | Base delay in seconds between retries (doubles each attempt) |
| `OUTPUT_EXCEL` | `str` | `output/companies.xlsx` | Path for Excel output file |
| `OUTPUT_JSON` | `str` | `output/companies.json` | Path for JSON output file |
| `LOG_FILE` | `str` | `logs/pipeline.log` | Path for pipeline log file |

**Example — change batch size and funding threshold:**

```python
# config/config.py
MIN_FUNDING_USD = 10_000_000   # Only companies with >$10M funding
BATCH_SIZE = 50                # Process 50 companies per run
HEADLESS = True                # Keep browser hidden
MAX_RETRIES = 3                # Retry 3 times on failure
```


### Implementation

**Step 1 — Access the main pipeline scripts:**

- Main entry point: [main.py](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/main.py)
- Shell runner (cron entry): [run_pipeline.sh](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/run_pipeline.sh)
- Data processor: [process_data.py](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/process_data.py)
- Full pipeline: [pipeline.py](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/pipeline.py)

**Step 2 — Verify dataset is in place:**

```bash
ls input/
# Should show: investments_VC.csv
```

**Step 3 — Run the pipeline manually:**

```bash
bash run_pipeline.sh
```

**Step 4 — Live terminal output you will see:**

```
==========================================
CRON TRIGGERED AT: Mon Jun  1 11:19:39 IST 2026
Running on: Nitins-MacBook-Air-2
Working dir: /Users/nitingupta/Documents/Python_project
==========================================
   Company Data Pipeline - Auto Batch
==========================================
2026-06-01 11:19:39 - INFO - Processing companies 221 to 240 of 48966
2026-06-01 11:19:39 - INFO - [1/20] Processing Stripe...
2026-06-01 11:19:41 - INFO - response: https://www.linkedin.com/company/stripe 200
2026-06-01 11:19:43 - INFO - [2/20] Processing Airbnb...
...
2026-06-01 11:23:44 - INFO - JSON saved: 240 total records
2026-06-01 11:23:44 - INFO - Excel saved: 240 total records
2026-06-01 11:23:44 - INFO - Daily backup saved for 2026-06-01
2026-06-01 11:23:44 - INFO - Pipeline complete! Total: 240 companies
==========================================
CRON JOB COMPLETED AT: Mon Jun  1 11:23:44 IST 2026
Output files:
-rw-r--r-- 1 nitingupta staff 113K Jun 1 11:23 companies.json
-rw-r--r-- 1 nitingupta staff  28K Jun 1 11:23 companies.xlsx
==========================================
```

**Step 5 — Check total companies collected:**

```bash
cat output/companies.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
hiring = sum(1 for c in data if c.get('Hiring Status') == 'Hiring')
not_hiring = sum(1 for c in data if c.get('Hiring Status') == 'Not Hiring')
unknown = sum(1 for c in data if c.get('Hiring Status') == 'Unknown')
print(f'Total companies : {len(data)}')
print(f'Hiring          : {hiring}')
print(f'Not Hiring      : {not_hiring}')
print(f'Unknown         : {unknown}')
"
```


### How It Works — Step by Step

```
Step 1: Read CSV dataset
        ↓
        Read investments_VC.csv (48,966 companies)
        Filter: company name must start with a letter
        Load batch_tracker.txt → resume from last saved position

Step 2: Process batch of 20 companies
        ↓
        For each company → search 7 engines per social platform
        LinkedIn → Twitter → Facebook → Instagram → YouTube
        Add 2-second delay between companies (avoids rate limiting)

Step 3: Verify hiring status
        ↓
        Visit company website
        Try paths: /careers, /jobs, /work-with-us, /join, /openings
        Page returns 200 + job content → "Hiring"
        Page 404 / no job content → "Not Hiring"
        Website unreachable → "Unknown"

Step 4: Deduplicate + validate
        ↓
        Load existing companies.json
        Skip any company already in file (match by name)
        Validate all URLs (must start with http/https)
        Fill missing fields with "N/A"

Step 5: Save outputs
        ↓
        Append new records → companies.json
        Rebuild full Excel → companies.xlsx (styled, frozen header)
        Copy both → output/daily/companies_YYYY-MM-DD.*
        Update batch_tracker.txt → next starting position
```


### Sample Output

The pipeline produces two output files:

**companies.json** — full structured JSON array:

```json
[
  {
    "Company Name": "Academia.edu",
    "Industry": "Education",
    "Total Funding": "17700000",
    "Funding Stage": "3",
    "Headquarters": "USA",
    "Website": "http://www.academia.edu",
    "Careers Page": "http://www.academia.edu/hiring",
    "Hiring Status": "Hiring",
    "LinkedIn URL": "https://www.linkedin.com/company/academia-edu/",
    "X/Twitter URL": "https://twitter.com/academia",
    "Facebook URL": "https://www.facebook.com/academia.edu",
    "Instagram URL": "N/A",
    "YouTube URL": "https://www.youtube.com/channel/UCVMuGMCKvFaP-aKSaWGajcQ",
    "Source URL": "/organization/academia-edu"
  },
  {
    "Company Name": "ACACIA Semiconductor",
    "Industry": "Semiconductors",
    "Total Funding": "31000000",
    "Funding Stage": "4",
    "Headquarters": "USA",
    "Website": "http://www.acacia-semi.com",
    "Careers Page": "N/A",
    "Hiring Status": "Unknown",
    "LinkedIn URL": "https://www.linkedin.com/company/acacia-research/",
    "X/Twitter URL": "N/A",
    "Facebook URL": "N/A",
    "Instagram URL": "N/A",
    "YouTube URL": "N/A",
    "Source URL": "/organization/acacia-semiconductor"
  }
]
```

**companies.xlsx** — professionally styled spreadsheet with frozen header row, bold blue column headers, and auto-sized column widths:

| Company Name | Industry | Total Funding | Funding Stage | Headquarters | Hiring Status | LinkedIn URL |
|---|---|---|---|---|---|---|
| Academia.edu | Education | 17700000 | 3 | USA | Hiring | linkedin.com/company/academia-edu |
| ACACIA Semiconductor | Semiconductors | 31000000 | 4 | USA | Unknown | linkedin.com/company/acacia-research |
| Stripe | Fintech | 2000000000 | 5 | USA | Hiring | linkedin.com/company/stripe |


### Limitations & Challenges

**Rate Limiting (HTTP 429):**
Google, Brave, and DuckDuckGo aggressively rate-limit automated requests. After ~30 requests they return HTTP 429 errors. The pipeline handles this by automatically rotating through 7 fallback search engines — if one is blocked the next is tried immediately without stopping the run.

**CAPTCHA Detection:**
Startpage frequently responds with a CAPTCHA challenge instead of search results. The pipeline detects `/sp/captcha` in the response URL and skips to the next available engine automatically.

**YouTube API Quota Exhaustion:**
The free YouTube Data API v3 provides 10,000 units per day. With 20 companies × 5 social platforms this quota runs out quickly. The pipeline catches the quota error and immediately falls back to DuckDuckGo `site:youtube.com` search — no manual action required.

**LinkedIn Anti-Scraping:**
LinkedIn detects Playwright's headless browser within 1–2 page loads and redirects to a login wall. Direct LinkedIn scraping is not used. Instead, LinkedIn URLs are found via `site:linkedin.com/company "[company name]"` queries on external search engines.

**Inconsistent Careers Page URLs:**
Different companies use completely different URL paths: `/jobs`, `/careers`, `/join`, `/work-with-us`, `/join-us`, `/openings`, `/positions`. The pipeline tries multiple common paths and falls back to `Unknown` when none match.

**Dynamic JavaScript Rendering:**
Many company websites are React, Next.js, or Vue.js SPAs. Content is rendered client-side. Playwright's `wait_until="networkidle"` parameter waits until all JavaScript finishes executing before attempting extraction.

**DuckDuckGo Timeout Errors:**
DuckDuckGo occasionally times out completely (`ConnectTimeout`). These are caught by the retry decorator in [utils/retry_utils.py](https://github.com/nitingupta7/company-hiring-intelligence/tree/main/utils), which retries up to 3 times with exponential backoff (2s → 4s → 8s).

---

## 2. Streamlit Live Dashboard

The Streamlit Dashboard in [pipeline.py](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/pipeline.py) provides a fully interactive, real-time frontend to explore all collected data without the terminal. It reads directly from `companies.json` and auto-refreshes every 30 seconds.

### Dashboard Features

- **Live auto-refresh** — reads `companies.json` and updates automatically every 30 seconds
- **Company search** — instant name-based search across all records in real time
- **Multi-filter sidebar** — filter simultaneously by hiring status, industry, and headquarters
- **Summary metric cards** — total companies, hiring, not hiring, unknown, LinkedIn coverage %
- **Hiring rate progress bar** — visual percentage bar of companies currently hiring
- **Top industries bar chart** — which sectors have the most companies in the dataset
- **Social media coverage chart** — coverage percentage for each platform
- **Headquarters distribution chart** — top countries by company count
- **Interactive data table** — all 14 fields with clickable link icons for every social profile
- **CSV export** — download currently filtered view as a `.csv` file
- **JSON export** — download currently filtered view as a `.json` file
- **Live log viewer** — last 50 lines of `pipeline.log` displayed in the browser
- **Pipeline status panel** — last successful run timestamp and total companies processed
- **Refresh button** — manually force data reload without restarting the app


### Getting Started

**Step 1 — Install Streamlit:**

```bash
pip install streamlit
```

**Step 2 — Run the pipeline first to generate data:**

```bash
bash run_pipeline.sh
```

**Step 3 — Launch the dashboard:**

```bash
streamlit run pipeline.py
```

See the full dashboard script: [pipeline.py](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/pipeline.py)

**Step 4 — Open in your browser:**

```
http://localhost:8501
```

> 💡 **Note:** The dashboard requires `output/companies.json` to exist. Run the pipeline at least once before launching. If no data exists, a warning banner is shown with instructions.


### Dashboard Sections

| Section | Location | Description |
|---|---|---|
| Header | Top of page | Title, subtitle, live status badge |
| Summary cards | Row 1 | Total, Hiring, Not Hiring, Unknown, LinkedIn coverage |
| Hiring progress bar | Below cards | Visual percentage of companies actively hiring |
| Sidebar search | Left panel | Real-time company name search |
| Sidebar filters | Left panel | Hiring status, industry, headquarters dropdowns |
| Pipeline status | Sidebar bottom | Last run time, companies processed, batch progress |
| Export buttons | Sidebar bottom | Download CSV and JSON of current filtered view |
| Company data table | Main area | Full sortable table with clickable link icons |
| Analytics charts | Below table | Industries, social media coverage, HQ locations |
| Live log viewer | Bottom | Last 50 log lines from `logs/` folder |

---

## Data Fields Reference

Complete reference for all 14 fields collected per company:

| Field | Type | Description | Example Value |
|---|---|---|---|
| `Company Name` | `string` | Official company name from dataset | `Stripe` |
| `Industry` | `string` | Business sector/market category | `Fintech` |
| `Total Funding` | `string` | Total funding raised in USD | `2000000000` |
| `Funding Stage` | `string` | Number of completed funding rounds | `5` |
| `Headquarters` | `string` | ISO country code of headquarters | `USA` |
| `Website` | `string` | Official company website URL | `https://stripe.com` |
| `Careers Page` | `string` | Direct URL to careers/jobs page | `https://stripe.com/jobs` |
| `Hiring Status` | `string` | Current hiring activity status | `Hiring` / `Not Hiring` / `Unknown` |
| `LinkedIn URL` | `string` | Company LinkedIn profile page | `https://linkedin.com/company/stripe` |
| `X/Twitter URL` | `string` | Company Twitter/X profile | `https://twitter.com/stripe` |
| `Facebook URL` | `string` | Company Facebook page | `https://facebook.com/stripehq` |
| `Instagram URL` | `string` | Company Instagram profile | `https://instagram.com/stripe` |
| `YouTube URL` | `string` | Company YouTube channel | `https://youtube.com/channel/...` |
| `Source URL` | `string` | Original Crunchbase organization permalink | `/organization/stripe` |

> All missing or unverifiable values are stored as `"N/A"` rather than `null` to ensure clean Excel rendering.

---

## Auto Scheduling with Cron

The pipeline is fully designed for unattended automated operation using macOS/Linux cron.

**Step 1 — Grant Full Disk Access to cron on macOS (required):**

```
Apple Menu → System Settings → Privacy & Security
→ Full Disk Access → Click + button
→ Press Cmd+Shift+G → type /usr/sbin/cron → Open
→ Toggle ON → restart cron:
```

```bash
sudo launchctl stop com.vix.cron && sudo launchctl start com.vix.cron
```

**Step 2 — Open crontab editor:**

```bash
crontab -e
```

**Step 3 — Add this line (update path to match your system):**

```
*/5 * * * * /bin/bash /Users/nitingupta/Documents/Python_project/run_pipeline.sh >> /Users/nitingupta/Documents/Python_project/logs/pipeline.log 2>&1
```

**Step 4 — Verify cron is saved:**

```bash
crontab -l
```

**Step 5 — Monitor logs to confirm cron is running:**

```bash
tail -f logs/pipeline.log
```

Every 5 minutes a new `CRON TRIGGERED AT:` line will appear.

**Common cron schedule options:**

| Description | Cron Expression |
|---|---|
| Every 5 minutes | `*/5 * * * *` |
| Every 30 minutes | `*/30 * * * *` |
| Once daily at 9:00 AM | `0 9 * * *` |
| Twice daily (9AM + 6PM) | `0 9,18 * * *` |
| Every Monday at 9AM | `0 9 * * 1` |

> 💡 Use [crontab.guru](https://crontab.guru) to visually build and test any cron schedule expression.

---

## Project Structure

```
company-hiring-intelligence/
│
├── scraper/                          # Core scraping modules
│   ├── company_discovery.py          # Playwright YC + Wellfound scraper
│   ├── hiring_checker.py             # Careers page detection
│   └── social_media_finder.py        # Multi-engine social URL discovery
│
├── output/                           # All generated output files
│   ├── companies.xlsx                # Final styled Excel (all records)
│   ├── companies.json                # Final JSON (all records)
│   ├── batch_tracker.txt             # Current batch position (integer)
│   └── daily/                        # Auto-dated daily backups
│
├── logs/                             # Run logs
│   └── pipeline.log                  # Full timestamped pipeline logs
│
├── config/                           # Configuration
│   └── config.py                     # All constants and settings
│
├── utils/                            # Shared utilities
│   ├── playwright_utils.py           # Browser launch helpers
│   └── retry_utils.py                # Retry decorator with backoff
│
├── input/                            # Source data
│   └── investments_VC.csv            # Crunchbase dataset (48,966 companies)
│
├── scripts/                          # Helper scripts
│   └── step3_social_apis.py          # Social media API helpers
│
├── pipeline.py                       # Streamlit dashboard frontend
├── run_pipeline.sh                   # Shell script — cron entry point
├── main.py                           # Playwright async entry point
├── process_data.py                   # Data cleaning utilities
├── requirements.txt                  # Python dependencies
├── env_template                      # Environment variables template
├── startup-investments-crunchbase.zip # Source dataset archive
├── .gitignore                        # Excludes venv, .env, __pycache__
└── README.md                         # This file
```

---

## Bonus Features

| Feature | Status | Description |
|---|---|---|
| ✅ Streamlit dashboard | Implemented | Full interactive frontend with charts, filters, exports |
| ✅ Daily auto-backups | Implemented | Dated copies of both output files created every run |
| ✅ Multi-engine fallback | Implemented | 7+ search engines tried per social platform |
| ✅ Cron heartbeat logging | Implemented | Each cron trigger logs hostname, timestamp, working directory |
| ✅ Batch resumption | Implemented | `batch_tracker.txt` persists position across all runs |
| ✅ Deduplication | Implemented | Name-based matching prevents duplicate records |
| ✅ YouTube API + DDG fallback | Implemented | Handles quota exhaustion automatically |
| ✅ Retry with backoff | Implemented | [utils/retry_utils.py](https://github.com/nitingupta7/company-hiring-intelligence/tree/main/utils) — 3 retries, doubles delay |
| 🔜 Job count per company | Planned | Count of open positions per company |
| 🔜 Hiring role titles | Planned | Extract specific role titles (Engineer, PM, Designer) |
| 🔜 Funding date | Planned | Latest funding round date extraction |
| 🔜 Company description | Planned | Short description from About page / meta tags |
| 🔜 Email notifications | Planned | Alert when new funded companies start hiring |

---

## Resources & Support

**Core Libraries Used:**

| Library | Purpose | Documentation |
|---|---|---|
| Playwright Python | Browser automation & scraping | [playwright.dev/python/docs/intro](https://playwright.dev/python/docs/intro) |
| Pandas | Data processing & manipulation | [pandas.pydata.org/docs](https://pandas.pydata.org/docs/) |
| Streamlit | Interactive dashboard frontend | [docs.streamlit.io](https://docs.streamlit.io) |
| OpenPyXL | Excel file creation & styling | [openpyxl.readthedocs.io](https://openpyxl.readthedocs.io/en/stable/) |
| duckduckgo-search | Social media URL discovery | [pypi.org/project/duckduckgo-search](https://pypi.org/project/duckduckgo-search/) |
| python-dotenv | Environment variable management | [pypi.org/project/python-dotenv](https://pypi.org/project/python-dotenv/) |

**APIs Used:**

| API | Purpose | Documentation |
|---|---|---|
| YouTube Data API v3 | YouTube channel URL lookup | [developers.google.com/youtube/v3](https://developers.google.com/youtube/v3) |
| Google Custom Search | Fallback search for social URLs | [developers.google.com/custom-search](https://developers.google.com/custom-search/v1/overview) |

**Dataset:**
- Crunchbase Startup Investments (48,966 companies): [startup-investments-crunchbase.zip](https://github.com/nitingupta7/company-hiring-intelligence/blob/main/startup-investments-crunchbase.zip)

**Useful Tools:**
- Cron schedule builder: [crontab.guru](https://crontab.guru)
- Playwright anti-detection guide: [scrapingant.com/blog/playwright-stealth](https://scrapingant.com/blog/playwright-stealth)
- Playwright async API reference: [playwright.dev/python/docs/api/class-playwright](https://playwright.dev/python/docs/api/class-playwright)

**Repository Links:**

| Page | Link |
|---|---|
| Main repository | [github.com/nitingupta7/company-hiring-intelligence](https://github.com/nitingupta7/company-hiring-intelligence) |
| All source files | [github.com/nitingupta7/company-hiring-intelligence/tree/main](https://github.com/nitingupta7/company-hiring-intelligence/tree/main) |
| Scraper modules | [/scraper](https://github.com/nitingupta7/company-hiring-intelligence/tree/main/scraper) |
| Utility modules | [/utils](https://github.com/nitingupta7/company-hiring-intelligence/tree/main/utils) |
| Config | [/config](https://github.com/nitingupta7/company-hiring-intelligence/tree/main/config) |
| Output folder | [/output](https://github.com/nitingupta7/company-hiring-intelligence/tree/main/output) |
| Open an issue | [github.com/.../issues](https://github.com/nitingupta7/company-hiring-intelligence/issues) |
