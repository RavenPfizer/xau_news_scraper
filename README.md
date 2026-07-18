# XAUUSD News Scraper — REX-Finance

**Economic Calendar Data → Clean JSON for AI Agent**

Bypasses Cloudflare protection on ForexFactory to extract high-impact economic news data for XAUUSD sentiment analysis.

## Installation

```bash
# 1. Clone / copy the xau_news_scraper folder to your project

# 2. Install dependencies
pip install cloudscraper beautifulsoup4 lxml

# 3. (Optional) For Playwright fallback
pip install playwright
playwright install chromium
```

## Quick Start

```python
from xau_news_scraper import XAUNewsScraper
import json

scraper = XAUNewsScraper()

# Get this week's events
events = scraper.get_this_week()

# Filter high impact only
high_impact = scraper.get_high_impact(events)

# Output JSON for AI agent
output = scraper.to_json(high_impact)
print(output)
```

## CLI Usage

```bash
# This week (default)
python example.py

# Next week
python example.py --week next

# Last week
python example.py --week last

# Specific month (July 2026)
python example.py --month 2026-07

# Filters
python example.py --high-impact-only          # Only red events
python example.py --xau-only                  # XAUUSD-relevant only
python example.py --currency USD              # By currency
python example.py --search CPI                # Search by keyword

# Save to file
python example.py --high-impact-only --save output.json

# Use Playwright (alternative engine)
python example.py --use-playwright

# Debug mode
python example.py --debug
```

## Historical Data (2007-2025)

```bash
# Download from HuggingFace
pip install datasets

# Or manual: https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar
```

Then use:

```python
from xau_news_scraper import XAUHistoricalData

hist = XAUHistoricalData(csv_path='forex_factory_calendar.csv')
events = hist.load()

# Filter: USD high impact from 2020-2024
usd_high = hist.filter(
    events=events,
    currency='USD',
    impact='High',
    date_from='2020-01-01',
    date_to='2024-12-31',
)
```

## JSON Output Format

```json
{
  "meta": {
    "source": "ForexFactory",
    "scraper": "XAUNewsScraper v1.0",
    "timestamp": "2026-07-18T11:10:42+00:00",
    "total_events": 14,
    "high_impact_count": 14,
    "xau_relevant_count": 8
  },
  "events": [
    {
      "date_display": "Tue Jul 14",
      "time": "7:30pm",
      "currency": "USD",
      "impact": "High",
      "event": "Core CPI m/m",
      "actual": "0.0%",
      "forecast": "0.2%",
      "previous": "0.2%",
      "has_data": true,
      "is_high_impact": true,
      "is_xau_relevant": true,
      "timestamp": 1784373042
    }
  ]
}
```

## Architecture

```
xau_news_scraper/
├── __init__.py          # Package init
├── scraper.py           # Primary: cloudscraper + BeautifulSoup (recommended)
├── playwright_scraper.py # Fallback: Playwright with stealth patches
├── historical.py        # Historical: HuggingFace dataset (2007-2025)
├── config.py            # Configuration & constants
├── example.py           # CLI entry point & examples
└── requirements.txt     # Dependencies
```

## Anti-Scrap Bypass Strategy

| Layer | Method | Status |
|-------|--------|--------|
| **Cloudflare JS Challenge** | `cloudscraper` (JS2Py solver) | ✅ Working |
| **Bot Detection** | Rotating User-Agent, browser fingerprint | ✅ Working |
| **Rate Limiting** | Auto-throttle (2s between requests) | ✅ Implemented |
| **Playwright Fallback** | Stealth patches, `--disable-blink-features` | ✅ Available |
| **No-Scrape Option** | HuggingFace dataset (2007-2025) | ✅ Available |

## Disclaimer

For educational and research purposes only. Respect ForexFactory's terms of service.
