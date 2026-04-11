"""
Curate TW and SK ETF lists:
- Drop commodity futures ETNs (TW: symbol ends in U; SK: symbol starts with Q)
- Drop leveraged/inverse (L/R suffix for TW)
- Fix misclassified themes
- Limit SK to top 8 per theme (order in PDF = roughly by volume)
- Add yfinance suffixes (.TW / .KS)
- Output tw_etfs_curated.json, sk_etfs_curated.json
"""

import json
import re

BASE = '/Users/oliveryang/Desktop/rays/project/docs'

THEMATIC = {
    'semiconductor',
    'cloud_computing_robotics_ai',
    'technology_innovations',
    'esg_clean_energy',
    'biotech_healthcare',
    'military_defense',
    'consumer_e_commerce',
    'real_estate',
    'internet_communications',
    'transportation',
    'gold_commodities',
}

# ── Manual theme overrides ────────────────────────────────────────────────────
TW_OVERRIDES = {
    '00893': 'esg_clean_energy',       # Cathay Global Autonomous and Electric Vehicles
    '00899': 'esg_clean_energy',       # Franklin Templeton SinoAm Global Clean Energy
    '00892': 'semiconductor',          # Fubon Taiwan Core Semi
    '00851': 'cloud_computing_robotics_ai',  # Taishin Global AI
    '006201': 'broad_market',          # Yuanta/P-shares Taiwan GreTai 50 (misclassified)
    '00735': 'semiconductor',          # Cathay Korea/Taiwan IT Premier
}

SK_OVERRIDES = {
    '203780': 'biotech_healthcare',    # MiraeAsset TIGER NASDAQ BIO
    '261070': 'biotech_healthcare',    # Mirae Asset TIGER KOSDAQ150 Biotech
    '371470': 'biotech_healthcare',    # MiraeAsset TIGER China Biotech Solactive
    '483030': 'biotech_healthcare',    # Kiwoom KOSEF US Blockbuster Biotech Drug
    '185680': 'biotech_healthcare',    # Samsung KODEX Synth-US Biotech
    '394670': 'esg_clean_energy',      # TIGER Global Lithium & Battery Tech
    '475070': 'esg_clean_energy',      # SamsungActive KoAct Global Climate Tech
    '140710': 'transportation',        # Samsung KODEX Transportation
}

# SK themes to exclude from curated output (too broad/not thematic enough)
SK_EXCLUDE_THEMES = {'financials', 'broad_market', 'dividend_income', 'other', 'gold_commodities'}
TW_EXCLUDE_THEMES = {'broad_market', 'dividend_income', 'other', 'gold_commodities'}

MAX_PER_THEME = 8  # SK cap


def clean_tw(raw: list) -> list:
    out = []
    seen = set()
    for e in raw:
        sym = e['symbol']
        name = e['name']

        # Drop commodity futures ETNs
        if sym.endswith('U') and len(sym) >= 6:
            continue
        # Drop leveraged (L) and inverse (R)
        if sym.endswith(('L', 'R')) and len(sym) >= 6:
            continue
        # Drop K-suffix (currency-hedged duplicates with tiny volume)
        if sym.endswith('K') and len(sym) >= 6:
            continue
        # Drop bond symbols
        if sym.endswith('B') and len(sym) >= 6:
            continue

        # Apply overrides
        theme = TW_OVERRIDES.get(sym, e['theme'])

        # Exclude non-thematic
        if theme in TW_EXCLUDE_THEMES:
            continue

        if sym in seen:
            continue
        seen.add(sym)

        out.append({
            'symbol':  sym + '.TW',
            'code':    sym,
            'name':    name,
            'theme':   theme,
            'market':  'Taiwan',
            'currency': 'TWD',
        })
    return out


def clean_sk(raw: list) -> list:
    # Apply overrides first, then filter, then cap per theme
    by_theme: dict[str, list] = {}
    seen = set()

    for e in raw:
        sym = e['symbol']
        name = e['name']

        # Drop ETNs (Q prefix)
        if sym.startswith('Q'):
            continue
        # Drop leveraged/inverse by name keywords
        n = name.lower()
        if any(k in n for k in ['inverse', 'leverage', '2x', '-2x', 'bear', 'futures inverse',
                                  'covered call', 'money market', 'ultra short']):
            continue
        # Drop bond/fixed income
        if any(k in n for k in ['bond', 'treasury', 'note', 'maturity', 'cd plus',
                                  'frn', 'preferred securit']):
            continue

        theme = SK_OVERRIDES.get(sym, e['theme'])

        if theme in SK_EXCLUDE_THEMES:
            continue

        if sym in seen:
            continue
        seen.add(sym)

        by_theme.setdefault(theme, []).append({
            'symbol':   sym + '.KS',
            'code':     sym,
            'name':     name,
            'theme':    theme,
            'market':   'South Korea',
            'currency': 'KRW',
        })

    # Cap per theme (PDF order ≈ volume order)
    out = []
    for theme, etfs in sorted(by_theme.items()):
        selected = etfs[:MAX_PER_THEME]
        out.extend(selected)
        print(f"  SK {theme:35s}: kept {len(selected):2d} / {len(etfs)}")

    return out


if __name__ == '__main__':
    tw_raw = json.load(open(f'{BASE}/tw_etfs_raw.json'))
    sk_raw = json.load(open(f'{BASE}/sk_etfs_raw.json'))

    print('=== Taiwan ===')
    tw = clean_tw(tw_raw)
    by_theme_tw: dict[str, list] = {}
    for e in tw:
        by_theme_tw.setdefault(e['theme'], []).append(e)
    for theme, etfs in sorted(by_theme_tw.items()):
        print(f"  TW {theme:35s}: {len(etfs)}")

    print('\n=== South Korea ===')
    sk = clean_sk(sk_raw)

    with open(f'{BASE}/tw_etfs_curated.json', 'w', encoding='utf-8') as f:
        json.dump(tw, f, ensure_ascii=False, indent=2)
    with open(f'{BASE}/sk_etfs_curated.json', 'w', encoding='utf-8') as f:
        json.dump(sk, f, ensure_ascii=False, indent=2)

    print(f'\n✓ tw_etfs_curated.json → {len(tw)} ETFs')
    print(f'✓ sk_etfs_curated.json → {len(sk)} ETFs')

    # Print final lists for review
    print('\n=== FINAL TW LIST ===')
    for e in tw:
        print(f"  [{e['theme']:35s}] {e['symbol']:12s} {e['name']}")

    print('\n=== FINAL SK LIST (thematic, top 8/theme) ===')
    for e in sk:
        print(f"  [{e['theme']:35s}] {e['symbol']:14s} {e['name']}")
