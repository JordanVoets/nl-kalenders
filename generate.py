#!/usr/bin/env python3
"""Generate Dutch holiday / school-vacation calendars (.ics) for subscription.

Feeds:
  vrije-feestdagen.ics      contractual days off
  overige-feestdagen-nl.ics other Dutch holidays and observances (not days off)
  schoolvakanties-zuid.ics  school vacations for one region (Rijksoverheid open data)

Holidays are computed, so the window rolls forward automatically each year.
School vacations come from the Rijksoverheid open-data API; the last good
response is cached in data/schoolvakanties.json and used when the API is down.

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------- settings
REGION = "zuid"                 # noord | midden | zuid
YEARS_BACK = 1                  # holidays: years before the current one
YEARS_AHEAD = 10                # holidays: years after the current one
API_URL = "https://opendata.rijksoverheid.nl/v1/infotypes/schoolholidays?output=json"
SITE = "jordanvoets.github.io"  # used in event UIDs; keep stable

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "data" / "schoolvakanties.json"
WEEKDAY_NL = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
MONTH_NL = ["", "januari", "februari", "maart", "april", "mei", "juni", "juli",
            "augustus", "september", "oktober", "november", "december"]


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------- date helpers
def easter(year: int) -> date:
    """Gregorian Easter Sunday (anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """n-th weekday (0=Mon .. 6=Sun) of a month; n=-1 means the last one."""
    if n > 0:
        d = date(year, month, 1)
        d += timedelta(days=(weekday - d.weekday()) % 7)
        return d + timedelta(weeks=n - 1)
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    d = nxt - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def koningsdag(year: int) -> date:
    d = date(year, 4, 27)
    return d - timedelta(days=1) if d.weekday() == 6 else d  # Sunday -> Saturday 26th


def carnaval(year: int) -> tuple[date, date]:
    e = easter(year)
    return e - timedelta(days=49), e - timedelta(days=47)  # Sunday .. Tuesday


def fmt(d: date) -> str:
    return f"{d.day} {MONTH_NL[d.month]}"


# ---------------------------------------------------------------- holidays
def vrije_feestdagen(years: range) -> list[tuple]:
    events = []
    for y in years:
        e = easter(y)
        for d, name in [
            (date(y, 1, 1), "Nieuwjaarsdag"),
            (e, "Eerste Paasdag"),
            (e + timedelta(days=1), "Tweede Paasdag"),
            (koningsdag(y), "Koningsdag"),
            (e + timedelta(days=39), "Hemelvaartsdag"),
            (e + timedelta(days=49), "Eerste Pinksterdag"),
            (e + timedelta(days=50), "Tweede Pinksterdag"),
            (date(y, 12, 25), "Eerste Kerstdag"),
            (date(y, 12, 26), "Tweede Kerstdag"),
        ]:
            desc = "Vrije dag (feestdag volgens contract)."
            if d.weekday() >= 5:
                desc = f"Valt op {WEEKDAY_NL[d.weekday()]} - geen extra vrije werkdag."
            if name == "Koningsdag" and d.day == 26:
                desc += " (27 april valt op zondag, daarom zaterdag 26 april.)"
            events.append((d, d, name, desc))
    return events


def overige_feestdagen(years: range) -> list[tuple]:
    events = []
    not_free = "Officiele feestdag, geen vrije dag volgens contract."
    for y in years:
        e = easter(y)
        c_start, c_end = carnaval(y)
        one_day = [
            (date(y, 1, 6), "Driekoningen", ""),
            (date(y, 2, 14), "Valentijnsdag", ""),
            (e - timedelta(days=46), "Aswoensdag", ""),
            (nth_weekday(y, 3, 6, -1), "Zomertijd begint", "Klok een uur vooruit (02:00 -> 03:00)."),
            (e - timedelta(days=2), "Goede Vrijdag", not_free),
            (date(y, 5, 4), "Dodenherdenking", "Twee minuten stilte om 20:00."),
            (date(y, 5, 5), "Bevrijdingsdag", not_free + (" Lustrumjaar." if y % 5 == 0 else "")),
            (nth_weekday(y, 5, 6, 2), "Moederdag", ""),
            (nth_weekday(y, 6, 6, 3), "Vaderdag", ""),
            (nth_weekday(y, 6, 5, -1), "Veteranendag", ""),
            (date(y, 7, 1), "Keti Koti", "Herdenking en viering van de afschaffing van de slavernij."),
            (nth_weekday(y, 9, 1, 3), "Prinsjesdag", ""),
            (date(y, 10, 4), "Dierendag", ""),
            (nth_weekday(y, 10, 6, -1), "Wintertijd begint", "Klok een uur terug (03:00 -> 02:00)."),
            (date(y, 10, 31), "Halloween", ""),
            (date(y, 11, 11), "Sint-Maarten", ""),
            (date(y, 12, 5), "Sinterklaasavond", "Pakjesavond."),
            (date(y, 12, 24), "Kerstavond", ""),
            (date(y, 12, 31), "Oudejaarsdag", ""),
        ]
        events += [(d, d, name, desc) for d, name, desc in one_day]
        events.append((c_start, c_end, "Carnaval", "Zondag t/m dinsdag voor Aswoensdag."))
    return events


# ---------------------------------------------------------------- school vacations
def _round_to_day(ts: str) -> date:
    """API timestamps are local-midnight-ish in UTC (e.g. 00:00Z start, 21:59Z/22:59Z end).
    Rounding to the nearest UTC midnight yields the day boundary."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    return (dt + timedelta(hours=12)).date()


def parse_api(raw: list) -> list[dict]:
    rows = []
    for item in raw:
        for content in item.get("content", []):
            schoolyear = content.get("schoolyear", "").strip()
            for vac in content.get("vacations", []):
                name = vac.get("type", "").strip()
                fixed = str(vac.get("compulsorydates", "")).strip().lower() == "true"
                for reg in vac.get("regions", []):
                    region = reg.get("region", "").strip().lower()
                    rows.append({
                        "schoolyear": schoolyear,
                        "name": name,
                        "fixed": fixed,
                        "region": region,
                        "start": _round_to_day(reg["startdate"]).isoformat(),
                        "end": (_round_to_day(reg["enddate"]) - timedelta(days=1)).isoformat(),  # inclusive
                    })
    rows.sort(key=lambda r: (r["start"], r["region"], r["name"]))
    if not rows:
        raise ValueError("API response contained no vacations")
    return rows


def fetch_api() -> list:
    req = urllib.request.Request(API_URL, headers={"User-Agent": f"nl-kalenders ({SITE})"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def load_school_rows(api_file: Path | None, offline: bool) -> tuple[list[dict], str]:
    """Return (rows, source). Updates the cache when fresh data parses correctly."""
    try:
        if offline:
            raise RuntimeError("offline mode")
        raw = json.loads(api_file.read_text()) if api_file else fetch_api()
        rows = parse_api(raw)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
        return rows, "api"
    except Exception as exc:  # noqa: BLE001 - any failure falls back to cache
        if not CACHE.exists():
            raise SystemExit(f"School data unavailable ({exc}) and no cache at {CACHE}")
        log(f"::warning::Rijksoverheid API unavailable ({exc}); using cached data")
        return json.loads(CACHE.read_text()), "cache"


def schoolvakanties(rows: list[dict], region: str) -> list[tuple]:
    events = []
    for r in rows:
        if r["region"] not in (region, "heel nederland"):
            continue
        start, end = date.fromisoformat(r["start"]), date.fromisoformat(r["end"])
        desc = "Vastgestelde data (Rijksoverheid)." if r["fixed"] else \
            "Adviesdata OCW - scholen mogen afwijken, check de schoolgids."
        if r["name"].lower() == "voorjaarsvakantie" and region == "zuid":
            c_start, c_end = carnaval(start.year)
            if not (start <= c_start and c_end <= end):
                desc += (f" Let op: carnaval valt dit jaar op {fmt(c_start)} t/m {fmt(c_end)};"
                         " scholen in Zuid kunnen daarom andere data kiezen.")
        desc += f" Schooljaar {r['schoolyear']}."
        # "Herfstvakantie" -> "Schoolvakantie: herfst (Zuid)"
        name = r["name"]
        season = name[: -len("vakantie")].lower() if name.lower().endswith("vakantie") else name
        season = {"voorjaars": "voorjaar"}.get(season, season)
        events.append((start, end, f"Schoolvakantie: {season} ({region.capitalize()})", desc))
    return events


# ---------------------------------------------------------------- iCalendar output
def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    if len(line.encode()) <= 75:
        return line
    parts, cur = [], b""
    for ch in line:
        b = ch.encode()
        if len(cur) + len(b) > (75 if not parts else 74):
            parts.append(cur.decode())
            cur = b""
        cur += b
    parts.append(cur.decode())
    return "\r\n ".join(parts)


def write_ics(path: Path, calname: str, description: str, events: list[tuple], busy: bool) -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = path.stem
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{SITE}//nl-kalenders//NL",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_esc(calname)}",
        f"X-WR-CALDESC:{_esc(description)}",
        "X-WR-TIMEZONE:Europe/Amsterdam",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]
    for start, end, summary, desc in sorted(events, key=lambda e: (e[0], e[2])):
        uid_name = "".join(c if c.isalnum() else "-" for c in summary.lower())
        lines += [
            "BEGIN:VEVENT",
            f"UID:{slug}-{start:%Y%m%d}-{uid_name}@{SITE}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{start:%Y%m%d}",
            f"DTEND;VALUE=DATE:{end + timedelta(days=1):%Y%m%d}",  # exclusive
            f"SUMMARY:{_esc(summary)}",
        ]
        if desc:
            lines.append(f"DESCRIPTION:{_esc(desc)}")
        lines += [f"TRANSP:{'OPAQUE' if busy else 'TRANSPARENT'}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    path.write_bytes(("\r\n".join(_fold(l) for l in lines) + "\r\n").encode())
    return len(events)


INDEX_HTML = """<!doctype html>
<html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NL kalenders</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:46rem;margin:3rem auto;padding:0 1rem;color:#222}}
code{{background:#f3f3f3;padding:.15rem .35rem;border-radius:4px;word-break:break-all}}li{{margin:.8rem 0}}
small{{color:#666}}</style></head><body>
<h1>NL kalenders</h1>
<p>Abonneer in je agenda-app via "kalender toevoegen via URL".</p>
<ul>{items}</ul>
<p><small>Laatst gegenereerd: {generated} &middot; schoolvakanties-bron: {source}</small></p>
</body></html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "public", help="output directory")
    ap.add_argument("--api-file", type=Path, help="read API JSON from a file instead of fetching")
    ap.add_argument("--offline", action="store_true", help="skip the API and use the cache")
    args = ap.parse_args()

    this_year = date.today().year
    years = range(this_year - YEARS_BACK, this_year + YEARS_AHEAD + 1)
    rows, source = load_school_rows(args.api_file, args.offline)
    region_title = REGION.capitalize()

    feeds = [
        ("vrije-feestdagen.ics", "Vrije feestdagen",
         "Feestdagen die volgens contract vrij zijn (als ze op een werkdag vallen).",
         vrije_feestdagen(years), True),
        ("overige-feestdagen-nl.ics", "Overige feestdagen NL",
         "Nederlandse feest- en gedenkdagen die geen vrije dag zijn.",
         overige_feestdagen(years), False),
        (f"schoolvakanties-{REGION}.ics", f"Schoolvakanties {region_title}",
         f"Schoolvakanties regio {region_title} (bron: Rijksoverheid open data).",
         schoolvakanties(rows, REGION), False),
    ]

    args.out.mkdir(parents=True, exist_ok=True)
    items = []
    for filename, name, desc, events, busy in feeds:
        n = write_ics(args.out / filename, name, desc, events, busy)
        log(f"{filename}: {n} events")
        url = f"https://{SITE}/nl-kalenders/{filename}"
        items.append(f"<li><strong>{name}</strong><br><code>{url}</code></li>")
    (args.out / "index.html").write_text(INDEX_HTML.format(
        items="".join(items),
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        source="Rijksoverheid API" if source == "api" else "cache (API niet bereikbaar)",
    ))


if __name__ == "__main__":
    main()
