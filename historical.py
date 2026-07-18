"""
XAUUSD News Scraper — Historical Data via HuggingFace Dataset
2007-2025 macroeconomic calendar data, no scraping needed.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Union
from pathlib import Path

from . import config

logger = logging.getLogger('xau_news_scraper.historical')


class XAUHistoricalData:
    """
    Access historical ForexFactory calendar data from HuggingFace dataset.

    Dataset: Ehsanrs2/Forex_Factory_Calendar (2007-01-01 to 2025-04-07)
    Source: https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar

    Two modes:
    1. Auto-download: Load via HuggingFace datasets library
    2. Manual CSV: Load from downloaded CSV file
    """

    DATASET_ID = 'Ehsanrs2/Forex_Factory_Calendar'
    HF_URL = 'https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar'

    def __init__(self, csv_path: Optional[Path] = None):
        self.csv_path = csv_path
        self._data = None

    def _load_from_hf(self) -> Optional[List[Dict]]:
        """Load dataset from HuggingFace."""
        try:
            from datasets import load_dataset

            logger.info(f'Loading dataset from HuggingFace: {self.DATASET_ID}')
            dataset = load_dataset(self.DATASET_ID, split='train')
            df = dataset.to_pandas()

            events = []
            for _, row in df.iterrows():
                event = {
                    'datetime': str(row.get('DateTime', '')),
                    'currency': str(row.get('Currency', '')),
                    'impact': str(row.get('Impact', '')),
                    'event': str(row.get('Event', '')),
                    'actual': str(row.get('Actual', '')),
                    'forecast': str(row.get('Forecast', '')),
                    'previous': str(row.get('Previous', '')),
                    'detail': str(row.get('Detail', '')),
                }
                events.append(event)

            logger.info(f'Loaded {len(events)} historical events')
            return events

        except ImportError:
            logger.error(
                'HuggingFace datasets library not installed. '
                'Run: pip install datasets'
            )
            return None
        except Exception as e:
            logger.error(f'Failed to load HF dataset: {e}')
            return None

    def _load_from_csv(self) -> Optional[List[Dict]]:
        """Load dataset from local CSV file."""
        if not self.csv_path or not self.csv_path.exists():
            logger.error(f'CSV file not found: {self.csv_path}')
            return None

        try:
            import pandas as pd

            logger.info(f'Loading historical data from CSV: {self.csv_path}')
            df = pd.read_csv(self.csv_path)

            events = []
            for _, row in df.iterrows():
                event = {
                    'datetime': str(row.get('DateTime', row.get('date', ''))),
                    'currency': str(row.get('Currency', row.get('currency', ''))),
                    'impact': str(row.get('Impact', row.get('impact', ''))),
                    'event': str(row.get('Event', row.get('event', ''))),
                    'actual': str(row.get('Actual', row.get('actual', ''))),
                    'forecast': str(row.get('Forecast', row.get('forecast', ''))),
                    'previous': str(row.get('Previous', row.get('previous', ''))),
                    'detail': str(row.get('Detail', row.get('detail', ''))),
                }
                events.append(event)

            logger.info(f'Loaded {len(events)} historical events from CSV')
            return events

        except Exception as e:
            logger.error(f'Failed to load CSV: {e}')
            return None

    def load(self) -> List[Dict]:
        """Load historical data from best available source."""
        if self._data is not None:
            return self._data

        if self.csv_path:
            data = self._load_from_csv()
            if data:
                self._data = data
                return data

        data = self._load_from_hf()
        if data:
            self._data = data
            return data

        logger.error('No historical data loaded. Provide CSV path or install datasets library.')
        return []

    def filter(
        self,
        events: Optional[List[Dict]] = None,
        currency: Optional[str] = None,
        impact: Optional[str] = None,
        event_keyword: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict]:
        """
        Filter historical events by multiple criteria.

        Args:
            events: Event list to filter. If None, uses loaded data.
            currency: Filter by currency code (e.g., 'USD')
            impact: Filter by impact level (e.g., 'High')
            event_keyword: Search in event name
            date_from: Start date 'YYYY-MM-DD'
            date_to: End date 'YYYY-MM-DD'
        """
        source = events if events is not None else self.load()
        if not source:
            return []

        result = source

        if currency:
            result = [e for e in result if e['currency'].upper() == currency.upper()]

        if impact:
            result = [e for e in result if impact.lower() in e['impact'].lower()]

        if event_keyword:
            kw = event_keyword.lower()
            result = [e for e in result if kw in e['event'].lower()]

        if date_from:
            result = [e for e in result if e['datetime'][:10] >= date_from]

        if date_to:
            result = [e for e in result if e['datetime'][:10] <= date_to]

        return result

    def get_xau_events(
        self,
        events: Optional[List[Dict]] = None,
        min_impact: str = 'High',
    ) -> List[Dict]:
        """Get XAUUSD-relevant events (USD, key economic indicators)."""
        source = events if events is not None else self.load()

        usd_events = [e for e in source if e['currency'] == 'USD']

        impact_levels = {'High': 3, 'Medium': 2, 'Low': 1}
        min_level = impact_levels.get(min_impact, 1)

        result = []
        for e in usd_events:
            e_impact = 0
            for level_name, level_val in impact_levels.items():
                if level_name.lower() in e['impact'].lower():
                    e_impact = level_val
                    break

            if e_impact >= min_level:
                result.append(e)

        return result

    def to_json(self, events: List[Dict], indent: int = 2) -> str:
        """Convert events to formatted JSON."""
        return json.dumps(
            {
                'meta': {
                    'source': 'HuggingFace Dataset: Ehsanrs2/Forex_Factory_Calendar',
                    'url': self.HF_URL,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'total_events': len(events),
                },
                'events': events,
            },
            indent=indent,
            ensure_ascii=False,
        )

    def save_json(self, events: List[Dict], filepath: Union[str, Path]):
        """Save filtered events to JSON file."""
        filepath = Path(filepath)
        filepath.write_text(self.to_json(events), encoding='utf-8')
        logger.info(f'Saved {len(events)} historical events to {filepath}')

    @staticmethod
    def download_instructions() -> str:
        """Print instructions for downloading the dataset."""
        return f"""
{'='*65}
  DOWNLOAD HISTORICAL DATA (2007-2025)
{'='*65}

  Option 1: HuggingFace (auto)
    pip install datasets
    Then use XAUHistoricalData()

  Option 2: Manual CSV Download
    1. Go to: {XAUHistoricalData.HF_URL}
    2. Click "Download" button
    3. Save CSV file and load with:
       XAUHistoricalData(csv_path='forex_factory_calendar.csv')
{'='*65}
"""
