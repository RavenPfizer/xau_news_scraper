#!/usr/bin/env python3
"""
XAUUSD News Scraper — CLI & Example Usage
=========================================
Outputs clean JSON for AI agent consumption.

Quick start:
    python example.py                          # This week's events (JSON)
    python example.py --week next              # Next week
    python example.py --month 2026-08          # Specific month
    python example.py --high-impact-only       # Only red events
    python example.py --xau-only               # Only XAUUSD-relevant
    python example.py --save output.json       # Save to file
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path if running directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xau_news_scraper import XAUNewsScraper, XAUHistoricalData


def setup_logging(debug: bool = False):
    import logging
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(name)-25s | %(levelname)-5s | %(message)s',
        datefmt='%H:%M:%S',
    )
    return logging.getLogger('xau_cli')


def print_banner():
    print()
    print('='*66)
    print('  [REX-FINANCE] XAUUSD NEWS SCRAPER')
    print('  Economic Calendar Data -> Clean JSON for AI Agent')
    print('='*66)
    print()


def fetch_current_week(cli, args):
    """Fetch current week's events."""
    print('📅 Fetching this week...')
    events = cli.get_this_week()
    return events


def fetch_next_week(cli, args):
    """Fetch next week's events."""
    print('📅 Fetching next week...')
    events = cli.get_next_week()
    return events


def fetch_last_week(cli, args):
    """Fetch last week's events."""
    print('📅 Fetching last week...')
    events = cli.get_last_week()
    return events


def fetch_week_by_date(cli, args):
    """Fetch week containing specific date."""
    print(f'📅 Fetching week of {args.date}...')
    events = cli.get_week_by_date(args.date)
    return events


def fetch_month(cli, args):
    """Fetch specific month."""
    print(f'📅 Fetching month {args.month}...')
    # Convert "2026-08" to "2026-08-01"
    date_str = f'{args.month}-01'
    events = cli.get_month(date_str)
    return events


def main():
    parser = argparse.ArgumentParser(
        description='XAUUSD News Scraper — Economic Calendar Data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python example.py                          # This week
  python example.py --week next              # Next week
  python example.py --month 2026-07          # July 2026
  python example.py --high-impact-only       # High impact only
  python example.py --xau-only               # XAUUSD-relevant only
  python example.py --save news.json         # Save to file
  python example.py --debug                  # Debug logging
        """
    )
    
    # Time range
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('--week', choices=['this', 'next', 'last'], 
                            default='this', help='Week to fetch')
    time_group.add_argument('--date', type=str, 
                            help='Fetch week containing date (YYYY-MM-DD)')
    time_group.add_argument('--month', type=str,
                            help='Fetch specific month (YYYY-MM)')
    
    # Filters
    parser.add_argument('--high-impact-only', action='store_true',
                        help='Only include High impact events')
    parser.add_argument('--xau-only', action='store_true',
                        help='Only include XAUUSD-relevant events (USD, key indicators)')
    parser.add_argument('--currency', type=str,
                        help='Filter by currency code (e.g., USD)')
    parser.add_argument('--search', type=str,
                        help='Search events by keyword (e.g., CPI, NFP)')
    
    # Output
    parser.add_argument('--save', type=str,
                        help='Save output to JSON file')
    parser.add_argument('--pretty', action='store_true', default=True,
                        help='Pretty-print JSON (default: True)')
    parser.add_argument('--minify', action='store_true',
                        help='Minify JSON output (no indent)')
    
    # Historical
    parser.add_argument('--historical', type=str, nargs='?', const='hf',
                        help='Use historical data from HuggingFace or CSV path')
    parser.add_argument('--from-date', type=str,
                        help='Historical: start date (YYYY-MM-DD)')
    parser.add_argument('--to-date', type=str,
                        help='Historical: end date (YYYY-MM-DD)')
    
    # Misc
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--use-playwright', action='store_true',
                        help='Use Playwright instead of cloudscraper')
    
    args = parser.parse_args()
    log = setup_logging(args.debug)
    
    print_banner()
    
    # ─── Choose data source ───
    if args.historical:
        # Historical mode
        csv_path = Path(args.historical) if args.historical != 'hf' else None
        hist = XAUHistoricalData(csv_path=csv_path)
        
        if csv_path:
            print(f'📂 Loading historical data from CSV: {csv_path}')
        else:
            print('🤗 Loading historical data from HuggingFace...')
            print('   (Requires: pip install datasets)')
        
        events = hist.load()
        
        if not events:
            print('❌ Failed to load historical data!')
            print(XAUHistoricalData.download_instructions())
            sys.exit(1)
        
        # Apply filters
        events = hist.filter(
            events=events,
            currency=args.currency,
            impact='High' if args.high_impact_only else None,
            event_keyword=args.search,
            date_from=args.from_date,
            date_to=args.to_date,
        )
        
        if args.xau_only:
            events = hist.get_xau_events(events)
        
        output = hist.to_json(events)
        
    else:
        # Live mode
        if args.use_playwright:
            log.info('Using Playwright scraper')
            from xau_news_scraper import XAUNewsScraperPlaywright
            cli = XAUNewsScraperPlaywright(headless=True)
        else:
            log.info('Using cloudscraper (recommended)')
            cli = XAUNewsScraper()
        
        # Fetch
        if args.week == 'next':
            events = fetch_next_week(cli, args)
        elif args.week == 'last':
            events = fetch_last_week(cli, args)
        elif args.date:
            events = fetch_week_by_date(cli, args)
        elif args.month:
            events = fetch_month(cli, args)
        else:
            events = fetch_current_week(cli, args)
        
        if not events:
            print('❌ No events fetched!')
            print('   - Check internet connection')
            print('   - ForexFactory may be blocking')
            print('   - Try --use-playwright flag')
            print('   - Or use --historical mode')
            sys.exit(1)
        
        # Apply filters
        if args.high_impact_only:
            events = cli.get_high_impact(events)
            print('🔴 Filtered: High impact only')
        
        if args.xau_only:
            events = cli.get_xau_relevant(events)
            print('🥇 Filtered: XAUUSD-relevant only')
        
        if args.currency:
            events = cli.get_by_currency(args.currency, events)
            print(f'💱 Filtered: {args.currency} only')
        
        if args.search:
            events = cli.search_events(args.search, events)
            print(f'🔍 Filtered: "{args.search}" matches')
        
        # Build output
        output = cli.to_json(events)
    
    # ─── Display Stats ───
    data = json.loads(output)
    meta = data['meta']
    evts = data['events']
    
    print(f'\n📊 RESULTS')
    print(f'   Total events:    {meta["total_events"]}')
    if 'high_impact_count' in meta:
        print(f'   High impact:     {meta["high_impact_count"]}')
    if 'xau_relevant_count' in meta:
        print(f'   XAUUSD relevant: {meta["xau_relevant_count"]}')
    
    # Show sample
    high_impact = [e for e in evts if e.get('impact') == 'High']
    if high_impact:
        print(f'\n🔴 HIGH IMPACT HIGHLIGHTS ({len(high_impact)} total):')
        for e in high_impact[:10]:
            print(f'   {e.get("date_display", e.get("datetime","")):12s} | '
                  f'{e.get("time",""):8s} | '
                  f'{e.get("currency","?"):4s} | '
                  f'{e.get("event","?"):55s} | '
                  f'A={e.get("actual","-"):8s} F={e.get("forecast","-"):8s} P={e.get("previous","-"):8s}')
    
    # ─── Output JSON ───
    indent = None if args.minify else 2
    json_output = json.dumps(data, indent=indent, ensure_ascii=False)
    
    if args.save:
        Path(args.save).write_text(json_output, encoding='utf-8')
        print(f'\n💾 Saved to: {args.save}')
    else:
        print(f'\n{"─"*70}')
        print('📋 JSON OUTPUT (for AI Agent):')
        print(f'{"─"*70}')
        print(json_output[:5000])  # Preview
        if len(json_output) > 5000:
            print(f'\n   ... ({len(json_output)} total chars — use --save for full output)')
    
    print(f'\n✅ Done. REX-Finance out. 🎯')


if __name__ == '__main__':
    main()
