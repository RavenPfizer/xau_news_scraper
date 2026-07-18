"""
XAUUSD News Scraper — Core Engine
Cloudscraper-based (bypasses Cloudflare) with BeautifulSoup parsing.
"""

import cloudscraper
from bs4 import BeautifulSoup
import re
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Union, List, Dict
from pathlib import Path

from . import config

logger = logging.getLogger('xau_news_scraper')


class XAUNewsScraper:
    """
    Scraper for ForexFactory economic calendar.
    
    Uses cloudscraper to bypass Cloudflare, then parses the calendar table
    HTML directly. No Selenium/Playwright needed for normal operation.
    
    Features:
    - Fetch current/next/previous week
    - Fetch by specific month
    - Filter by currency, impact, event keywords
    - Clean JSON output
    - Historical data via HuggingFace dataset (recommended for >1yr)
    """
    
    def __init__(
        self,
        timeout: int = config.REQUEST_TIMEOUT,
        max_retries: int = config.MAX_RETRIES,
        auto_throttle: bool = True,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.auto_throttle = auto_throttle
        self._last_request_time = 0.0
        self._scraper = self._create_scraper()
    
    def _create_scraper(self) -> cloudscraper.CloudScraper:
        """Create a cloudscraper instance with browser-like fingerprint."""
        return cloudscraper.create_scraper(
            interpreter='js2py',  # JS challenge solver
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False,
                'desktop': True,
            },
        )
    
    def _throttle(self):
        """Respect rate limits — min 2s between requests."""
        if not self.auto_throttle:
            return
        elapsed = time.time() - self._last_request_time
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)
        self._last_request_time = time.time()
    
    def _fetch(self, url: str) -> Optional[str]:
        """Fetch URL with retry logic."""
        for attempt in range(self.max_retries):
            try:
                self._throttle()
                resp = self._scraper.get(url, timeout=self.timeout)
                
                if resp.status_code == 200:
                    # Verify it's not a Cloudflare challenge page
                    if len(resp.text) > 20000 and 'calendar__table' in resp.text:
                        return resp.text
                    elif 'Just a moment' in resp.text or 'security verification' in resp.text:
                        logger.warning(f'Cloudflare challenge page (attempt {attempt+1})')
                    else:
                        logger.debug(f'Page loaded ({len(resp.text)} bytes) but calendar table not found')
                        return resp.text  # Return anyway, caller will validate
                elif resp.status_code == 403:
                    logger.warning(f'403 Forbidden (attempt {attempt+1})')
                elif resp.status_code == 429:
                    wait = config.RETRY_BACKOFF * (attempt + 1)
                    logger.warning(f'429 Rate limited, waiting {wait}s')
                    time.sleep(wait)
                else:
                    logger.warning(f'HTTP {resp.status_code} (attempt {attempt+1})')
            
            except Exception as e:
                logger.error(f'Request error: {e} (attempt {attempt+1})')
            
            if attempt < self.max_retries - 1:
                time.sleep(config.RETRY_BACKOFF * (attempt + 1))
        
        logger.error(f'All {self.max_retries} attempts failed for {url}')
        return None
    
    # ─── URL BUILDERS ───────────────────────────────────────────
    
    def _week_ref_from_date(self, date_str: str) -> str:
        """Convert 'YYYY-MM-DD' to ForexFactory week ref like 'jul12.2026'."""
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%b%d.%Y').lower()
    
    def _month_ref_from_date(self, date_str: str) -> str:
        """Convert 'YYYY-MM-DD' to ForexFactory month ref like 'july.2026'."""
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%B.%Y').lower()
    
    # ─── PARSER ─────────────────────────────────────────────────
    
    def _parse_calendar_html(self, html: str) -> List[Dict]:
        """
        Parse ForexFactory calendar HTML table into structured event list.
        
        Handles:
        - Day-breaker rows (date separators)
        - Multi-day rowspans
        - Impact icons (red=High, orange=Medium, yellow=Low, grey=None)
        - Revision indicators
        - All Day events (no time)
        """
        soup = BeautifulSoup(html, 'lxml')
        table = soup.find('table', class_='calendar__table')
        if not table:
            logger.error('Calendar table not found in HTML')
            return []
        
        rows = table.find_all('tr')
        events = []
        current_date = ''
        current_date_ts = 0
        
        for row in rows:
            classes = row.get('class', [])
            
            # Skip header and border rows
            if 'subhead' in classes or 'borderfix' in classes:
                continue
            
            # ── Day breaker row ──
            if 'calendar__row--day-breaker' in classes:
                cell = row.find('td', class_='calendar__cell')
                if cell:
                    raw_date = cell.get_text(strip=True)
                    # Parse the date text like "Sun Jul 12" -> structured
                    current_date = self._clean_date_text(raw_date)
                continue
            
            # ── No-event row ──
            if 'calendar__row--no-event' in classes:
                continue
            
            # ── Event row ──
            if 'calendar__row' in classes:
                event = self._parse_event_row(
                    row=row,
                    current_date=current_date,
                )
                if event:
                    # Update current date if row has a date cell
                    date_cell = row.find('td', class_='calendar__date')
                    if date_cell:
                        span = date_cell.find('span', class_='date')
                        if span:
                            current_date = self._clean_date_text(span.get_text(strip=True))
                    
                    events.append(event)
        
        logger.debug(f'Parsed {len(events)} events from calendar HTML')
        return events
    
    def _clean_date_text(self, raw: str) -> str:
        """Clean date text like 'Mon Jul 12' or 'Sun  Jul 12' -> 'Mon, Jul 12'."""
        # Remove extra whitespace and HTML
        cleaned = re.sub(r'<[^>]+>', '', raw)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        # Ensure there's a space between day abbreviation and month
        # e.g., 'TueJul' -> 'Tue Jul'
        cleaned = re.sub(r'([A-Za-z]{3})([A-Z][a-z]{2,}\s*\d)', r'\1 \2', cleaned)
        return cleaned
    
    def _parse_event_row(self, row, current_date: str) -> Optional[Dict]:
        """Parse a single event row from the calendar table."""
        cells = row.find_all('td', class_='calendar__cell')
        if not cells:
            return None
        
        event_cell = row.find('td', class_='calendar__event')
        if not event_cell:
            return None
        
        # Check if there's actually an event title
        event_title = event_cell.find('span', class_='calendar__event-title')
        if not event_title:
            return None
        
        event_name = event_title.get_text(strip=True)
        if not event_name:
            return None
        
        # ── Time ──
        time_cell = row.find('td', class_='calendar__time')
        time_text = time_cell.get_text(strip=True) if time_cell else ''
        
        # ── Currency ──
        currency_cell = row.find('td', class_='calendar__currency')
        currency = currency_cell.get_text(strip=True) if currency_cell else ''
        
        # ── Impact (from icon class) ──
        impact = self._parse_impact(row)
        
        # ── Actual / Forecast / Previous ──
        actual_cell = row.find('td', class_='calendar__actual')
        forecast_cell = row.find('td', class_='calendar__forecast')
        previous_cell = row.find('td', class_='calendar__previous')
        
        actual = self._clean_value(actual_cell) if actual_cell else ''
        forecast = self._clean_value(forecast_cell) if forecast_cell else ''
        previous = self._clean_value(previous_cell) if previous_cell else ''
        
        # ── Is this event in the past? ──
        has_data = bool(actual) or bool(forecast) or bool(previous)
        
        # ── Build event dict ──
        event = {
            'date_display': current_date,
            'time': time_text,
            'currency': currency,
            'impact': impact,
            'event': event_name,
            'actual': actual,
            'forecast': forecast,
            'previous': previous,
            'has_data': has_data,
            'is_high_impact': impact == 'High',
            'is_xau_relevant': self._is_xau_relevant(currency, event_name),
            'timestamp': int(time.time()),
        }
        
        return event
    
    def _parse_impact(self, row) -> str:
        """Parse impact level from the icon class."""
        impact_cell = row.find('td', class_='calendar__impact')
        if not impact_cell:
            return 'None'
        
        icon = impact_cell.find('span', class_=re.compile(r'icon--ff-impact'))
        if not icon:
            return 'None'
        
        icon_class = ' '.join(icon.get('class', []))
        
        if 'red' in icon_class:
            return 'High'
        elif 'ora' in icon_class:
            return 'Medium'
        elif 'yel' in icon_class:
            return 'Low'
        elif 'gray' in icon_class or 'grey' in icon_class:
            return 'Non-Economic'
        else:
            return 'Unknown'
    
    def _clean_value(self, cell) -> str:
        """Clean actual/forecast/previous value."""
        # Get text, but exclude revision images
        text = cell.get_text(strip=True)
        # Remove revision indicator artifacts
        text = re.sub(r'\s*\[\s*\]\s*', '', text)
        text = text.strip()
        return text
    
    def _is_xau_relevant(self, currency: str, event_name: str) -> bool:
        """Check if event is relevant for XAUUSD analysis."""
        # USD events are most relevant for XAUUSD
        if currency == 'USD':
            # Check if it's a key event
            for keyword in config.XAUUSD_KEY_EVENTS:
                if keyword.lower() in event_name.lower():
                    return True
            return True  # All USD events are somewhat relevant
        return False
    
    # ─── PUBLIC API ────────────────────────────────────────────
    
    def get_this_week(self) -> List[Dict]:
        """Get this week's calendar events."""
        html = self._fetch(config.CALENDAR_URL)
        if not html:
            return []
        return self._parse_calendar_html(html)
    
    def get_next_week(self) -> List[Dict]:
        """Get next week's calendar events."""
        html = self._fetch(config.CALENDAR_WEEK_URL.format(week_ref='next'))
        if not html:
            return []
        return self._parse_calendar_html(html)
    
    def get_last_week(self) -> List[Dict]:
        """Get last week's calendar events."""
        html = self._fetch(config.CALENDAR_WEEK_URL.format(week_ref='last'))
        if not html:
            return []
        return self._parse_calendar_html(html)
    
    def get_week_by_date(self, date_str: str) -> List[Dict]:
        """
        Get events for the week containing a specific date.
        
        Args:
            date_str: 'YYYY-MM-DD' format
        """
        week_ref = self._week_ref_from_date(date_str)
        url = config.CALENDAR_WEEK_URL.format(week_ref=week_ref)
        html = self._fetch(url)
        if not html:
            return []
        return self._parse_calendar_html(html)
    
    def get_month(self, date_str: str) -> List[Dict]:
        """
        Get events for a specific month.
        
        Args:
            date_str: Any date in 'YYYY-MM-DD' format (month is extracted)
        """
        month_ref = self._month_ref_from_date(date_str)
        url = config.CALENDAR_MONTH_URL.format(month_ref=month_ref)
        html = self._fetch(url)
        if not html:
            return []
        return self._parse_calendar_html(html)
    
    def get_high_impact(self, events: Optional[List[Dict]] = None) -> List[Dict]:
        """Filter events by High impact only."""
        source = events if events is not None else self.get_this_week()
        return [e for e in source if e['impact'] == 'High']
    
    def get_by_currency(self, currency: str, events: Optional[List[Dict]] = None) -> List[Dict]:
        """Filter events by currency (e.g., 'USD')."""
        source = events if events is not None else self.get_this_week()
        return [e for e in source if e['currency'] == currency.upper()]
    
    def get_xau_relevant(self, events: Optional[List[Dict]] = None) -> List[Dict]:
        """Filter events relevant to XAUUSD."""
        source = events if events is not None else self.get_this_week()
        return [e for e in source if e['is_xau_relevant']]
    
    def search_events(self, keyword: str, events: Optional[List[Dict]] = None) -> List[Dict]:
        """Search events by keyword (case-insensitive)."""
        source = events if events is not None else self.get_this_week()
        kw = keyword.lower()
        return [e for e in source if kw in e['event'].lower()]
    
    # ─── OUTPUT ────────────────────────────────────────────────
    
    def to_json(self, events: List[Dict], indent: int = 2) -> str:
        """Convert events list to formatted JSON string."""
        return json.dumps(
            {
                'meta': {
                    'source': 'ForexFactory',
                    'scraper': 'XAUNewsScraper v1.0',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'total_events': len(events),
                    'high_impact_count': len([e for e in events if e['impact'] == 'High']),
                    'xau_relevant_count': len([e for e in events if e['is_xau_relevant']]),
                },
                'events': events,
            },
            indent=indent,
            ensure_ascii=False,
        )
    
    def save_json(self, events: List[Dict], filepath: Union[str, Path]):
        """Save events to JSON file."""
        filepath = Path(filepath)
        filepath.write_text(self.to_json(events), encoding='utf-8')
        logger.info(f'Saved {len(events)} events to {filepath}')
