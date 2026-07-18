"""
XAUUSD News Scraper — Config
All tuning parameters in one place.
"""

# ─── TARGET CURRENCIES ──────────────────────────────────────────
# XAUUSD mostly reacts to USD, but also EUR, GBP, JPY, CHF
TARGET_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD']

# ─── IMPACT LEVELS ──────────────────────────────────────────────
# High = red, Medium = orange, Low = yellow, Non-Economic = grey
IMPACT_LEVELS = ['High', 'Medium', 'Low', 'Non-Economic']
MIN_IMPACT = 'High'  # Minimum impact to include

# ─── HIGH-IMPACT EVENTS FOR XAUUSD ──────────────────────────────
# Keywords that typically move gold
XAUUSD_KEY_EVENTS = [
    'NFP', 'Non Farm Payrolls', 'Nonfarm Payrolls',
    'CPI', 'Consumer Price Index',
    'PPI', 'Producer Price Index',
    'FOMC', 'Federal Funds Rate', 'Interest Rate Decision',
    'GDP', 'Gross Domestic Product',
    'Unemployment Rate', 'Jobless Claims',
    'Retail Sales',
    'ISM Manufacturing', 'ISM Services',
    'Michigan Consumer Sentiment',
    'Fed Chair', 'Federal Reserve',
    'Treasury', '10-Year Note Auction',
    'ADP', 'Employment Change',
    'Core CPI', 'Core PPI',
    'PCE', 'Core PCE',
    'Industrial Production',
    'Capacity Utilization',
    'Building Permits', 'Housing Starts',
    'Existing Home Sales', 'New Home Sales',
    'Durable Goods Orders',
    'Factory Orders',
    'Business Inventories',
    'Trade Balance',
    'Current Account',
    'Philadelphia Fed', 'Empire State',
    'Consumer Confidence',
    'JOLTS',
    'Average Hourly Earnings',
    'Labor Force Participation Rate',
    'U-6 Unemployment Rate',
    'TIC Long-Term Purchases',
]

# ─── REQUEST CONFIG ─────────────────────────────────────────────
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  # seconds

# ─── USER AGENTS ────────────────────────────────────────────────
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# ─── FOREXFACTORY URLS ─────────────────────────────────────────
BASE_URL = 'https://www.forexfactory.com'
CALENDAR_URL = 'https://www.forexfactory.com/calendar'
CALENDAR_WEEK_URL = 'https://www.forexfactory.com/calendar?week={week_ref}'
CALENDAR_MONTH_URL = 'https://www.forexfactory.com/calendar?month={month_ref}'

# ─── OUTPUT FORMAT ─────────────────────────────────────────────
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
DATETIME_DISPLAY = '%Y-%m-%d %H:%M %Z'
