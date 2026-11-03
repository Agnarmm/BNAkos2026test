"""Turn civicAPI's live 2026 midterm results into flat CSVs for Datawrapper.

Writes:
  data/senate.csv  - one row per state (all 50; states with no race say "No race")
  data/house.csv   - one row per district (e.g. AZ-01)

Data: civicAPI (https://civicapi.org) - free, no key. Attribution required:
put "Source: civicAPI / AP-style unofficial results" in your Datawrapper notes.

Usage:
  python scripts/build_csv.py           # real data
  python scripts/build_csv.py --test    # also accept civicAPI's test data
  python scripts/build_csv.py --demo    # fake data, no internet (for building the map now)
"""

import csv
import json
import random
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data"
BASE = "https://civicapi.org/api/v2"
# civicAPI's national documents for 3 Nov 2026 (one document, with a result per state/district).
DOCS = {"senate": 87528, "house": 87524}
ELECTION_DATE = "2026-11-03"
ALLOW_TEST = "--test" in sys.argv
DEMO = "--demo" in sys.argv

STATES = {
    "al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas", "ca": "California",
    "co": "Colorado", "ct": "Connecticut", "de": "Delaware", "fl": "Florida", "ga": "Georgia",
    "hi": "Hawaii", "id": "Idaho", "il": "Illinois", "in": "Indiana", "ia": "Iowa",
    "ks": "Kansas", "ky": "Kentucky", "la": "Louisiana", "me": "Maine", "md": "Maryland",
    "ma": "Massachusetts", "mi": "Michigan", "mn": "Minnesota", "ms": "Mississippi",
    "mo": "Missouri", "mt": "Montana", "ne": "Nebraska", "nv": "Nevada", "nh": "New Hampshire",
    "nj": "New Jersey", "nm": "New Mexico", "ny": "New York", "nc": "North Carolina",
    "nd": "North Dakota", "oh": "Ohio", "ok": "Oklahoma", "or": "Oregon", "pa": "Pennsylvania",
    "ri": "Rhode Island", "sc": "South Carolina", "sd": "South Dakota", "tn": "Tennessee",
    "tx": "Texas", "ut": "Utah", "vt": "Vermont", "va": "Virginia", "wa": "Washington",
    "wv": "West Virginia", "wi": "Wisconsin", "wy": "Wyoming",
}

FIELDS = [
    "id", "state", "postal", "status", "leader", "leader_party", "leader_pct",
    "runner_up", "runner_up_party", "runner_up_pct", "margin_pts", "pct_reporting",
    "called", "updated_utc",
]


def get(path):
    req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": "election-csv/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print(f"  {path}: {e} (try {attempt + 1}/3)")
            time.sleep(5 * (attempt + 1))
    return None


def usable(doc, name):
    if not doc:
        print(f"{name}: no document returned")
        return False
    if doc.get("test_data") and not ALLOW_TEST:
        print(f"{name}: civicAPI is still serving TEST data; ignoring (use --test to accept)")
        return False
    if not (doc.get("election_date") or ELECTION_DATE).startswith(ELECTION_DATE):
        print(f"{name}: document is for {doc.get('election_date')}, not {ELECTION_DATE}")
        return False
    return True


def party(c):
    """Map whatever civicAPI calls the party to D / R / I / Other."""
    raw = str(c.get("party") or c.get("party_name") or c.get("party_abbreviation") or "").strip().lower()
    if raw.startswith("d"):
        return "D"
    if raw.startswith("r") or raw.startswith("gop"):
        return "R"
    if raw.startswith("i") or raw.startswith("ind"):
        return "I"
    return "Other" if raw else ""


def summarise(region, now):
    """One results row from civicAPI's per-region block."""
    cands = sorted(region.get("candidates", []), key=lambda c: c.get("votes") or 0, reverse=True)
    total = sum(c.get("votes") or 0 for c in cands)
    reporting = region.get("percent_reporting") or 0
    pct = lambda c: round(100 * (c.get("votes") or 0) / total, 1) if total else ""
    lead = cands[0] if cands else {}
    second = cands[1] if len(cands) > 1 else {}
    winner = next((c for c in cands if c.get("winner")), None)

    if winner:
        lead = winner
        second = next((c for c in cands if c is not winner), {})
        status = {"D": "Dem win", "R": "Rep win", "I": "Ind win"}.get(party(winner), "Other win")
    elif total == 0:
        status = "Too early"
    else:
        status = {"D": "Dem lead", "R": "Rep lead", "I": "Ind lead"}.get(party(lead), "Other lead")

    margin = round(pct(lead) - pct(second), 1) if total and second else ""
    return {
        "status": status,
        "leader": lead.get("name", ""),
        "leader_party": party(lead) if lead else "",
        "leader_pct": pct(lead) if lead else "",
        "runner_up": second.get("name", ""),
        "runner_up_party": party(second) if second else "",
        "runner_up_pct": pct(second) if second else "",
        "margin_pts": margin,
        "pct_reporting": reporting,
        "called": "yes" if winner else "no",
        "updated_utc": now,
    }


def empty_row(status, now):
    row = {k: "" for k in FIELDS}
    row.update(status=status, called="no", updated_utc=now)
    return row


def demo_region():
    """Fake results so the map can be styled before real numbers arrive."""
    reporting = random.choice([0, 0, 12, 45, 78, 100])
    d, r = random.randint(40_000, 900_000), random.randint(40_000, 900_000)
    cands = [{"name": "Demo Democrat", "party": "Democratic", "votes": d if reporting else 0},
             {"name": "Demo Republican", "party": "Republican", "votes": r if reporting else 0}]
    if reporting == 100:
        max(cands, key=lambda c: c["votes"])["winner"] = True
    return {"percent_reporting": reporting, "candidates": cands}


def build(kind, doc, now):
    regions = (doc or {}).get("region_results", {}) if (DEMO or usable(doc, kind)) else {}
    rows = []
    if kind == "senate":
        for code, name in STATES.items():
            region = regions.get(code)
            if DEMO and random.random() < 0.7:
                region = demo_region()
            row = summarise(region, now) if region else empty_row(
                "Too early" if regions and code in regions else "No race", now)
            row.update(id=code.upper(), state=name, postal=code.upper())
            rows.append(row)
        # Before results exist we can't tell which states vote, so keep everything "Too early"
        # rather than calling every state "No race".
        if not regions and not DEMO:
            for row in rows:
                row["status"] = "Too early"
    else:
        keys = sorted(regions) if regions else []
        if DEMO:
            keys = [f"{s}-{n:02d}" for s in ("az", "ca", "pa", "tx") for n in range(1, 6)]
        for key in keys:
            region = demo_region() if DEMO else regions[key]
            code, _, dist = key.partition("-")
            row = summarise(region, now)
            dist_label = "AL" if dist in ("", "00", "al") else dist.zfill(2)
            row.update(id=f"{code.upper()}-{dist_label}", state=STATES.get(code, code.upper()),
                       postal=code.upper())
            rows.append(row)
    return rows


def write(name, rows):
    path = OUT / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"wrote {path.relative_to(ROOT)}: {len(rows)} rows {counts}")


def main():
    OUT.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    for kind, race_id in DOCS.items():
        doc = None if DEMO else get(f"race/{race_id}")
        rows = build(kind, doc, now)
        if rows or kind == "senate" or not (OUT / f"{kind}.csv").exists():
            write(kind, rows)
        else:
            print(f"{kind}: no results yet; keeping the previous file")


if __name__ == "__main__":
    main()
