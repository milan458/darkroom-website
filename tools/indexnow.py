#!/usr/bin/env python3
"""Tell Bing (and the other IndexNow engines: Yandex, Seznam, Naver, Yep) that pages changed.
ChatGPT search draws on Bing's index, so this is the fastest way to get new pages seen there.
Google does not use IndexNow; use Search Console's URL Inspection for Google.

    python3 tools/indexnow.py                         # every public page in site.json
    python3 tools/indexnow.py /guides/some-new-guide  # just these paths (or full URLs)

Run it after the change is live on darkroom.buzz, not before.
"""

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
ORIGIN = SITE["origin"].rstrip("/")
KEY = SITE["indexNowKey"]


def main():
    args = sys.argv[1:]
    if args:
        urls = [a if a.startswith("http") else ORIGIN + a for a in args]
    else:
        urls = [ORIGIN + p["path"] for p in SITE["pages"] if not p.get("draft")]
    body = json.dumps({
        "host": ORIGIN.split("://", 1)[1],
        "key": KEY,
        "keyLocation": f"{ORIGIN}/{KEY}.txt",
        "urlList": urls,
    }).encode()
    request = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                     headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            print(f"IndexNow: HTTP {response.status} for {len(urls)} URL(s)")
    except urllib.error.HTTPError as error:
        # 200/202 = accepted. 403 = key file not reachable yet. 422 = URLs don't match the host.
        print(f"IndexNow: HTTP {error.code} {error.reason}")
        sys.exit(1)
    for url in urls:
        print("  ", url)


if __name__ == "__main__":
    main()
