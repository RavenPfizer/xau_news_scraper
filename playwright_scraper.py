"""
XAUUSD News Scraper — Playwright Engine
Fallback/alternative scraper using Playwright with stealth patches.
"""

import re
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
from pathlib import Path

from . import config

logger = logging.getLogger('xau_news_scraper.playwright')


class XAUNewsScraperPlaywright:
    """
    Playwright-based scraper for ForexFactory.
    
    Uses browser automation to bypass Cloudflare's JS challenge.
    Includes stealth patches to avoid bot detection.
    
    Requirements: playwright (pip install playwright && playwright install chromium)
    
    Note: cloudscraper-based XAUNewsScraper is preferred for reliability.
    This Playwright version is a fallback when cloudscraper fails.
    """
    
    def __init__(
        self,
        headless: bool = True,
        timeout: int = 60000,
        stealth: bool = True,
    ):
        self.headless = headless
        self.timeout = timeout
        self.stealth = stealth
        self._browser = None
        self._context = None
    
    def _get_stealth_script(self) -> str:
        """JavaScript to patch browser fingerprints."""
        return '''
        // ─── Remove Automation Traces ───
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        
        // ─── Fake Chrome Runtime ───
        window.chrome = {
            runtime: { 
                onConnect: { addListener: () => {} },
                onMessage: { addListener: () => {} },
                sendMessage: () => {},
                connect: () => {},
            },
            loadTimes: () => {},
            csi: () => {},
            app: { isInstalled: false, InstallState: {}, RunningState: {} },
        };
        
        // ─── Permissions ───
        const originalQuery = window.navigator.permissions.query.bind(window.navigator.permissions);
        window.navigator.permissions.query = (params) => {
            if (params.name === 'notifications') {
                return Promise.resolve({ state: 'denied' });
            }
            return originalQuery(params);
        };
        
        // ─── Plugins ───
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                { name: 'Native Client', filename: 'internal-nacl-plugin' },
            ],
        });
        
        // ─── Languages ───
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        // ─── Platform ───
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32',
        });
        
        // ─── Hardware Concurrency ───
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
        });
        
        // ─── Device Memory ───
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
        });
        
        // ─── WebGL Vendor (hide headless) ───
        const getParameterProxy = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(params) {
            if (params === 37445) return 'Intel Inc.';
            if (params === 37446) return 'Intel Iris OpenGL Engine';
            return getParameterProxy.call(this, params);
        };
        '''
    
    def _launch(self):
        """Launch browser with stealth configuration."""
        from playwright.sync_api import sync_playwright
        
        self._playwright = sync_playwright().start()
        
        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-infobars',
            '--window-size=1920,1080',
        ]
        
        if self.headless:
            launch_args.append('--headless=new')
        
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
        )
        
        self._context = self._browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.006},
            permissions=['geolocation'],
            java_script_enabled=True,
            bypass_csp=True,
            ignore_https_errors=True,
        )
        
        # Apply stealth patches
        if self.stealth:
            self._context.add_init_script(self._get_stealth_script())
    
    def _close(self):
        """Close browser."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if hasattr(self, '_playwright') and self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.debug(f'Browser close error: {e}')
    
    def _fetch_with_browser(self, url: str) -> Optional[str]:
        """Fetch URL using Playwright browser."""
        self._launch()
        page = self._context.new_page()
        page.set_default_timeout(self.timeout)
        
        try:
            # Navigate with wait strategy
            page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
            
            # Wait for Cloudflare challenge to resolve (if any)
            max_wait = 30
            for i in range(max_wait):
                content = page.content()
                if 'calendar__table' in content:
                    logger.debug('Calendar loaded successfully')
                    return content
                if 'Just a moment' not in content and 'security' not in content.lower():
                    if i > 5:  # Give it some time
                        logger.debug(f'Page loaded but calendar table not found (wait {i}s)')
                        return content
                time.sleep(1)
            
            logger.warning('Timed out waiting for calendar to load')
            return page.content()
            
        except Exception as e:
            logger.error(f'Playwright navigation error: {e}')
            return None
        finally:
            page.close()
            self._close()
    
    # ─── PUBLIC API ────────────────────────────────────────────
    
    def get_calendar(self, url: Optional[str] = None) -> List[Dict]:
        """
        Fetch calendar events using Playwright.
        
        Args:
            url: ForexFactory calendar URL. Defaults to current week.
        """
        from .scraper import XAUNewsScraper
        
        target_url = url or config.CALENDAR_URL
        html = self._fetch_with_browser(target_url)
        
        if not html:
            logger.error('Failed to fetch calendar with Playwright')
            return []
        
        # Reuse the same parser from cloudscraper version
        parser = XAUNewsScraper()
        return parser._parse_calendar_html(html)
    
    def get_this_week(self) -> List[Dict]:
        """Get this week's events."""
        return self.get_calendar(config.CALENDAR_URL)
    
    def get_next_week(self) -> List[Dict]:
        """Get next week's events."""
        return self.get_calendar(config.CALENDAR_WEEK_URL.format(week_ref='next'))
    
    def get_week_by_date(self, date_str: str) -> List[Dict]:
        """Get events for week containing date_str (YYYY-MM-DD)."""
        from .scraper import XAUNewsScraper
        parser = XAUNewsScraper()
        week_ref = parser._week_ref_from_date(date_str)
        url = config.CALENDAR_WEEK_URL.format(week_ref=week_ref)
        return self.get_calendar(url)
