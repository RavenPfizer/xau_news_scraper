"""
XAUUSD News Scraper — Economic Calendar Data Extraction
=======================================================

Tools for extracting high-impact economic news data for XAUUSD analysis.
Bypasses Cloudflare protection on ForexFactory using cloudscraper.

Modules:
    scraper             Primary cloudscraper-based scraper (recommended)
    playwright_scraper  Playwright-based fallback
    historical          Historical data from HuggingFace dataset (2007-2025)
    config              Configuration & constants
"""

from .scraper import XAUNewsScraper
from .playwright_scraper import XAUNewsScraperPlaywright
from .historical import XAUHistoricalData
from . import config

__version__ = '1.0.0'
__author__ = 'REX-Finance'
