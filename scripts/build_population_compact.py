"""
Rebuild data/population_compact.json from the DOSM population CSVs.

The dashboard loads population_compact.json first and only falls back to the
large CSVs if it is missing, so this file is what actually sets the population
used for rates. It holds the latest-year total (sex=both, age=overall,
ethnicity=overall) for Malaysia, each state and each district.

Run after downloading the CSVs (the Sync DOSM CSVs workflow does this):
    python scripts/build_population_compact.py

generated_at only changes when the figures do, so an unchanged DOSM release
produces no diff and no commit.
"""

import csv
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUTPUT = os.path.join(DATA, 'population_compact.json')

HEADER = '<!--\nSPDX-License-Identifier: AGPL-3.0-only\nCopyright (C) 2026 drakmal\n-->\n\n'


def to_people(value):
    """DOSM publishes thousands with one decimal (79.3 -> 79300); mirrors toPeople() in index.html."""
    raw = str(value or '').replace(',', '').strip()
    if not raw:
        return None
    n = float(raw)
    if '.' in raw or n < 10000:
        n *= 1000
    return int(round(n))


def latest_totals(filename, key_cols):
    """{key tuple: {'population', 'year'}} using each key's latest overall total."""
    best = {}
    with open(os.path.join(DATA, filename), encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            if (row['sex'], row['age'], row['ethnicity']) != ('both', 'overall', 'overall'):
                continue
            people = to_people(row['population'])
            if people is None:
                continue
            key = tuple(row[c] for c in key_cols)
            date = row['date']
            if key not in best or date > best[key][0]:
                best[key] = (date, people)
    return {k: {'population': p, 'year': d[:4]} for k, (d, p) in best.items()}


def load_existing():
    try:
        with open(OUTPUT, encoding='utf-8-sig') as f:
            text = f.read()
        return json.loads(text[text.index('{'):])
    except (OSError, ValueError):
        return None


def main():
    malaysia = latest_totals('population_malaysia.csv', [])[()]
    states = latest_totals('population_state.csv', ['state'])
    districts = latest_totals('population_district.csv', ['state', 'district'])

    district_map = {}
    for (state, district), info in sorted(districts.items()):
        district_map.setdefault(state, {})[district] = info

    payload = {
        'version': 1,
        'generated_at': None,
        'malaysia': malaysia,
        'states': {state: info for (state,), info in sorted(states.items())},
        'districts': district_map,
    }

    existing = load_existing()
    if existing and {**existing, 'generated_at': None} == payload:
        print('Population figures unchanged; leaving population_compact.json as is.')
        return

    payload['generated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    with open(OUTPUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(HEADER + json.dumps(payload, indent=2, ensure_ascii=False) + '\n')

    years = sorted({i['year'] for i in districts.values()})
    print(f"Wrote {OUTPUT}: Malaysia {malaysia['year']}, "
          f"{len(states)} states, {len(districts)} districts (years {', '.join(years)})")


if __name__ == '__main__':
    main()
