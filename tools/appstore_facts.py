#!/usr/bin/env python3
"""Pull dated competitor facts from the App Store into data/competitors.json.

Comparison pages and the monthly refresh (SEO-PLAYBOOK.md section 7) cite this file, so every
competitor claim has a source and a date. Standard library only.

    python3 tools/appstore_facts.py                  # every app in data/competitors.json, US store
    python3 tools/appstore_facts.py keepsafe privault
    python3 tools/appstore_facts.py --country de     # the German store (prices in EUR), for translations
    python3 tools/appstore_facts.py --show keepsafe  # print what's stored

For each app it records, with the date checked:
  - from Apple's lookup API: name, developer, price, rating and rating count, version, last update,
    minimum iOS, App Store URL
  - from the App Store page: the privacy label headings ("Data Used to Track You", "Data Not Collected"…)
    and the in-app purchase list with prices
Add an app by adding {"id": "<numeric Apple ID>", "name": "…"} under "apps" in data/competitors.json.
"""

import datetime as dt
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "competitors.json"
LABELS = ["Data Used to Track You", "Data Linked to You", "Data Not Linked to You", "Data Not Collected"]
UA = {"User-Agent": "getnoxium-competitor-facts/1.0"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def lookup(app_id, country):
    data = json.loads(get(f"https://itunes.apple.com/lookup?id={app_id}&country={country}"))
    if not data.get("results"):
        return None
    r = data["results"][0]
    return {
        "name": r.get("trackName"),
        "developer": r.get("sellerName"),
        "price": r.get("formattedPrice"),
        "rating": round(r["averageUserRating"], 1) if r.get("averageUserRating") else None,
        "ratingCount": r.get("userRatingCount"),
        "version": r.get("version"),
        "lastUpdate": (r.get("currentVersionReleaseDate") or "")[:10] or None,
        "minimumOs": r.get("minimumOsVersion"),
        "url": (r.get("trackViewUrl") or "").split("?")[0],
    }


def page_facts(url):
    """Privacy label headings and in-app purchases from the App Store web page (best effort)."""
    raw = get(url)
    text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", raw)))
    text = re.sub(r"\s+", " ", text)
    labels = [l for l in LABELS if l in text]
    iaps = []
    m = re.search(r"In-App Purchases (?:Yes )?(.*?)(?:Learn More|Copyright|Developer Website)", text)
    if m:
        for name, price in re.findall(r"(.+?) ([$€£¥₩]\s?[\d.,]+|[\d.,]+\s?[$€£¥₩]|R\$\s?[\d.,]+)\s*", m.group(1)):
            item = {"name": name.strip(), "price": price.strip()}
            if item not in iaps:
                iaps.append(item)
    return {"privacyLabel": labels or None, "inAppPurchases": iaps}


def main():
    args = sys.argv[1:]
    country = "us"
    if "--country" in args:
        i = args.index("--country")
        country = args[i + 1].lower()
        del args[i:i + 2]
    store = json.loads(DATA.read_text(encoding="utf-8"))
    if "--show" in args:
        args.remove("--show")
        for slug in args or store["apps"]:
            print(slug, json.dumps(store["apps"][slug], indent=2, ensure_ascii=False))
        return 0
    slugs = args or list(store["apps"])
    today = dt.date.today().isoformat()
    failed = 0
    for slug in slugs:
        app = store["apps"].get(slug)
        if not app:
            print(f"{slug}: not in {DATA.relative_to(ROOT)}")
            failed += 1
            continue
        try:
            facts = lookup(app["id"], country)
            if not facts:
                print(f"{slug}: not found in the {country.upper()} store (removed, or not sold there)")
                app.setdefault("listings", {})[country] = {"checked": today, "available": False}
                continue
            try:
                facts.update(page_facts(facts["url"]))
            except Exception as e:  # the page layout can change; keep the API facts
                facts["pageError"] = str(e)[:120]
            facts["checked"] = today
            app.setdefault("listings", {})[country] = facts
            print(f"{slug}: {facts['name']} · {facts['price']} · {facts['rating']}★ ({facts['ratingCount']}) · "
                  f"updated {facts['lastUpdate']} · {len(facts.get('inAppPurchases', []))} IAPs · "
                  f"{', '.join(facts.get('privacyLabel') or ['no label found'])}")
        except Exception as e:
            print(f"{slug}: failed: {e}")
            failed += 1
        time.sleep(1)  # be gentle with Apple's endpoints
    DATA.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
