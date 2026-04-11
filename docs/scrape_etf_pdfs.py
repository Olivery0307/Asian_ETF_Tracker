"""
Scrape TW and SK ETF lists from investing.com PDFs.
Outputs: tw_etfs_raw.json, sk_etfs_raw.json
"""

import json
import re
import pdfplumber

# ── Exclusion filters ─────────────────────────────────────────────────────────

BOND_KEYWORDS = [
    'bond', 'treasury', 'corporate', 'sovereign', 'debt', 'yield',
    'note ', 'notes', 'bbb', 'aaa', 'credit', 'maturity', 'coupon',
    'aggregate', 'fixed income', 'banking senior', 'telecom bond',
    'utility bond', 'healthcare bond', 'municipal', 'investment grade',
    'high grade', '債券', '公債', '公司債', '00679b', '00687b',
]

EXCLUDE_KEYWORDS = [
    'inverse', 'bear ', '-1x', '-2x', '2x inverse', 'futures inverse',
    'leveraged 2x', 'leverage 2x', 'bull 2x', 'lev 2x',
    'daily leverage', 'daily bull', 'daily bear',
    'crude oil', 'wti', 'brent',         # commodity futures
    'silver futures', 'gold futures', 'copper futures',
    'soybean', 'soybeans',
    'money market', 'ultra short term', 'under 3 mo',
    'covered call', 'premium active',     # options-overlay products
    'yen ', 'dollar er', 'usd er',        # currency futures
]

LEVERAGE_RE = re.compile(r'\b(2x|3x|-1x|-2x|leveraged? 2x|bull 2x|lev 2x)\b', re.I)


def is_bond(name: str) -> bool:
    n = name.lower()
    # Symbol ending in B is a Taiwan bond convention
    return any(k in n for k in BOND_KEYWORDS)


def is_excluded(name: str) -> bool:
    n = name.lower()
    if any(k in n for k in EXCLUDE_KEYWORDS):
        return True
    if LEVERAGE_RE.search(n):
        return True
    return False


# ── Theme classifier ──────────────────────────────────────────────────────────

def classify_theme(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ['semiconductor', 'semicon', 'chip', 'wafer', 'phlx semi',
                             'fn semi', 'semi material', 'semi top']):
        return 'semiconductor'
    if any(k in n for k in ['ai ', 'artificial intelligence', 'robot', 'robotics',
                             'humanoid', 'automation', 'nvidia', 'machine learn']):
        return 'cloud_computing_robotics_ai'
    if any(k in n for k in ['5g', 'nextgen comm', 'telecom', 'communication',
                             'internet', 'digital payment', 'fang', 'nasdaq']):
        return 'internet_communications'
    if any(k in n for k in ['tech', 'technology', 'innovation', 'software',
                             'it premier', 'system semi', 'electric power']):
        return 'technology_innovations'
    if any(k in n for k in ['battery', 'secondary battery', 'ev ', 'electric vehicle',
                             '2차전지', 'lithium', 'energy storage', 'tesla value']):
        return 'esg_clean_energy'
    if any(k in n for k in ['clean energy', 'solar', 'wind', 'renewable',
                             'esg', 'sustainable', 'carbon', 'green energy',
                             'low carbon', 'low volatility esg']):
        return 'esg_clean_energy'
    if any(k in n for k in ['biotech', 'bio ', 'healthcare', 'health care',
                             'pharma', 'medical', 'life science', 'cosmetic']):
        return 'biotech_healthcare'
    if any(k in n for k in ['defense', 'defence', 'military', 'aerospace',
                             'kdefense', 'k-defense', 'constructions', 'shipbuilding']):
        return 'military_defense'
    if any(k in n for k in ['consumer', 'brand', 'retail', 'e-commerce',
                             'lifestyle', 'liquor', 'big apple']):
        return 'consumer_e_commerce'
    if any(k in n for k in ['real estate', 'reit', 'property', '부동산',
                             'mortgage reit', 'infrastructure']):
        return 'real_estate'
    if any(k in n for k in ['gold', 'silver', 'commodity', 'material',
                             'resource', 'mining']):
        return 'gold_commodities'
    if any(k in n for k in ['financ', 'bank', 'insurance', 'securities',
                             'covered call']):
        return 'financials'
    if any(k in n for k in ['dividend', 'high div', 'income equity',
                             'value-up', 'value up']):
        return 'dividend_income'
    if any(k in n for k in ['transport', 'logistics', 'shipping', 'aviation']):
        return 'transportation'
    if any(k in n for k in ['50', '100', '150', '200', '500',
                             'kospi', 'taiex', 'twse', 'kosdaq', 'total market',
                             'broad', 'top 10', 'top10', 'blue chip',
                             'mid-cap', 'small', 'momentum', 'growth']):
        return 'broad_market'
    return 'other'


# ── PDF text parser ───────────────────────────────────────────────────────────

# investing.com row pattern (single-space separated):
#   NAME [truncated with …]  SYMBOL  LAST  CHG%  VOL  TIME
# Symbol is the first all-uppercase/digit token after the name
# Anchor: line ends with  VOL  DATE pattern like "09/04" or "02:29:59"
ROW_RE = re.compile(
    r'^(.+?)\s+([A-Z0-9]{4,8})\s+[\d,\.]+\s+[+\-]?\d+[\.,]\d+%\s+[\d\.KMB]+\s+[\d:/]+\s*$'
)


def extract_etfs_from_text(text: str, market: str) -> list[dict]:
    etfs = []
    seen = set()
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Skip header / navigation lines
        if any(s in line for s in ['Investing.com', 'issuer_filter', 'What patterns',
                                    'Name Symbol', 'Try Chart', 'Worldwide',
                                    'Americas', 'Europe', 'Asia', 'Middle East',
                                    'Africa', 'Search', 'Find ETF', 'Country',
                                    'Asset Class', 'Issuer']):
            continue

        m = ROW_RE.match(line)
        if not m:
            continue

        name   = m.group(1).strip().rstrip('…').strip()
        symbol = m.group(2).strip()

        if not name or len(name) < 4:
            continue
        if symbol in seen:
            continue
        # Taiwan bond symbols end with B
        if symbol.endswith('B') and len(symbol) >= 6:
            continue
        # Inverse/leveraged symbols ending in L or R
        if symbol.endswith(('L', 'R')) and len(symbol) >= 6:
            continue
        if is_bond(name):
            continue
        if is_excluded(name):
            continue

        seen.add(symbol)
        theme = classify_theme(name)
        etfs.append({
            'symbol': symbol,
            'name':   name,
            'theme':  theme,
            'market': market,
        })
    return etfs


def process(pdf_path: str, market: str) -> list[dict]:
    print(f"\n{'='*60}")
    print(f"  {market}: {pdf_path}")
    print(f"{'='*60}")

    all_text = ''
    with pdfplumber.open(pdf_path) as pdf:
        print(f"  Pages: {len(pdf.pages)}")
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                all_text += t + '\n'

    etfs = extract_etfs_from_text(all_text, market)
    print(f"  ETFs extracted: {len(etfs)}")

    from collections import Counter
    counts = Counter(e['theme'] for e in etfs)
    for theme, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"    {theme:35s} {n:3d}")

    return etfs


if __name__ == '__main__':
    base = '/Users/oliveryang/Desktop/rays/project/docs'

    tw = process(f'{base}/tw_etf_list.pdf', 'Taiwan')
    sk = process(f'{base}/sk_etf_list.pdf', 'South Korea')

    with open(f'{base}/tw_etfs_raw.json', 'w', encoding='utf-8') as f:
        json.dump(tw, f, ensure_ascii=False, indent=2)
    with open(f'{base}/sk_etfs_raw.json', 'w', encoding='utf-8') as f:
        json.dump(sk, f, ensure_ascii=False, indent=2)

    print(f"\n✓ tw_etfs_raw.json  → {len(tw)} ETFs")
    print(f"✓ sk_etfs_raw.json  → {len(sk)} ETFs")
