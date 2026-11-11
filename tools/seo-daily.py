#!/usr/bin/env python3
"""Daily Google Search Console report for getnoxium.app (or any Search Console property), via gum.

Runs on the Mac where gum is signed in (gum keeps the Google credentials; nothing secret is stored
here). Standard library only; works with macOS's /usr/bin/python3.

    python3 tools/seo-daily.py                 # pull today's data and write the report
    python3 tools/seo-daily.py --no-inspect    # skip the URL Inspection (indexing) check
    python3 tools/seo-daily.py --install       # run it every day at 09:07 (macOS launchd)
    python3 tools/seo-daily.py --install --hour 7 --minute 41
    python3 tools/seo-daily.py --uninstall     # stop the daily run
    python3 tools/seo-daily.py --site sc-domain:example.com --sitemap https://example.com/sitemap.xml

Output (outside the repo, because this repo is public):
    ~/seo-data/<site>/reports/YYYY-MM-DD.md   the day's report (also reports/latest.md)
    ~/seo-data/<site>/raw/YYYY-MM-DD/*.json   raw gum responses, for later comparisons
    ~/seo-data/<site>/seen-queries.json       every query seen so far, to spot new ones

What the report covers (Search Console data lags 2-3 days, so windows end 3 days ago):
    - clicks and impressions, last 7 days vs the 7 before
    - striking distance: queries at positions 4-20 in the last 28 days (the fastest wins)
    - movers: queries whose average position changed most, week over week
    - new queries never seen before
    - queries where two or more of your pages compete (pick one page, link it from the other)
    - indexing: every sitemap URL through URL Inspection, flagging any that aren't indexed
Read SEO-PLAYBOOK.md section 6 for what to do with each finding.
"""

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_SITE = "sc-domain:getnoxium.app"
DEFAULT_SITEMAP = "https://getnoxium.app/sitemap.xml"
LABEL_PREFIX = "app.getnoxium.seo-daily"

STRIKING_MIN_POS, STRIKING_MAX_POS, STRIKING_MIN_IMPR = 4, 20, 3
MOVER_MIN_IMPR = 3
CANNIBAL_MIN_IMPR = 2


class GumError(Exception):
    pass


# ---------- gum ----------

def gum(args, op, params):
    cmd = [args.gum, "read", op, "--args", json.dumps(params), "--output", "json"]
    if args.profile:
        cmd += ["--profile", args.profile]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = p.stdout.strip()
    try:
        data = json.loads(out) if out else {}
    except json.JSONDecodeError:
        data = {}
    if p.returncode != 0 or "error_code" in data:
        detail = data or (p.stderr.strip() or out)[-1500:]
        raise GumError(json.dumps(detail, indent=2) if isinstance(detail, dict) else detail)
    return data


def search_analytics(args, start, end, dimensions, row_limit=1000):
    body = {"startDate": start.isoformat(), "endDate": end.isoformat(),
            "dimensions": dimensions, "rowLimit": row_limit}
    return gum(args, "searchconsole.searchanalytics.query", {"siteUrl": args.site, "body": body})


def find_key(obj, key):
    """First value for `key` anywhere in a nested JSON object."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        obj = list(obj.values())
    if isinstance(obj, list):
        for v in obj:
            found = find_key(v, key)
            if found is not None:
                return found
    return None


def sitemap_urls(url):
    p = subprocess.run(["curl", "-fsSL", "-m", "30", url], capture_output=True, text=True)
    if p.returncode != 0:
        raise GumError(f"could not fetch {url}: {p.stderr.strip()}")
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", p.stdout)


# ---------- analysis ----------

def rows(data):
    return data.get("rows", []) if isinstance(data, dict) else []


def by_query(data):
    """{query: {clicks, impressions, position}} from rows with keys [query] or [query, page]."""
    out = {}
    for r in rows(data):
        q = r["keys"][0]
        a = out.setdefault(q, {"clicks": 0, "impressions": 0, "pos_x_impr": 0.0, "pages": {}})
        a["clicks"] += r["clicks"]
        a["impressions"] += r["impressions"]
        a["pos_x_impr"] += r["position"] * r["impressions"]
        if len(r["keys"]) > 1:
            a["pages"][r["keys"][1]] = {"impressions": r["impressions"], "position": r["position"]}
    for a in out.values():
        a["position"] = a["pos_x_impr"] / a["impressions"] if a["impressions"] else 0.0
    return out


def totals(daily, start, end):
    t = {"clicks": 0, "impressions": 0}
    for r in rows(daily):
        d = dt.date.fromisoformat(r["keys"][0])
        if start <= d <= end:
            t["clicks"] += r["clicks"]
            t["impressions"] += r["impressions"]
    return t


def short(url, origin):
    return url.replace(origin, "") or "/"


def pct(cur, prev):
    if not prev:
        return "new" if cur else "–"
    return f"{(cur - prev) / prev * 100:+.0f}%"


def table(header, body):
    if not body:
        return "_None._\n"
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |" for row in body]
    return "\n".join(lines) + "\n"


def pace_check(results, origin, today):
    """SEO-PLAYBOOK.md pace rule: if more than 25% of pages published 14+ days ago aren't indexed,
    drop to 2 pages a day. Uses "published" dates from site.json when this script runs from the repo."""
    site_file = Path(__file__).resolve().parent.parent / "site.json"
    if not site_file.exists():
        return ""
    site = json.loads(site_file.read_text(encoding="utf-8"))
    if site.get("origin", "").rstrip("/") != origin:
        return ""
    cutoff = today - dt.timedelta(days=14)
    old = [origin + p["path"] for p in site["pages"]
           if not p.get("draft") and p.get("published") and dt.date.fromisoformat(p["published"]) <= cutoff]
    checked = [u for u in old if u in results]
    if not checked:
        return "**Pace rule:** no pages published 14+ days ago to check yet."
    missing = [u for u in checked if results[u].get("verdict") != "PASS"]
    share = len(missing) / len(checked)
    verdict = ("**over 25%: drop to 2 pages a day** and improve the weakest pages (SEO-PLAYBOOK.md, Pace rule)"
               if share > 0.25 else "under 25%: keep 4 pages a day")
    return (f"**Pace rule:** {len(missing)} of {len(checked)} pages published 14+ days ago aren't indexed "
            f"({share:.0%}), {verdict}.")


# ---------- report ----------

def run(args):
    today = dt.date.today()
    end = today - dt.timedelta(days=3)
    cur_start, prev_end = end - dt.timedelta(days=6), end - dt.timedelta(days=7)
    prev_start, start28 = end - dt.timedelta(days=13), end - dt.timedelta(days=27)
    origin = "https://" + args.site.split(":", 1)[1] if args.site.startswith("sc-domain:") else args.site.rstrip("/")

    out_dir = Path(args.out).expanduser()
    raw_dir = out_dir / "raw" / today.isoformat()
    rep_dir = out_dir / "reports"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rep_dir.mkdir(parents=True, exist_ok=True)

    def save(name, data):
        (raw_dir / f"{name}.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
        return data

    daily = save("daily-28d", search_analytics(args, start28, end, ["date"]))
    qp28 = save("query-page-28d", search_analytics(args, start28, end, ["query", "page"]))
    cur7 = save("query-7d", search_analytics(args, cur_start, end, ["query"]))
    prev7 = save("query-prev-7d", search_analytics(args, prev_start, prev_end, ["query"]))

    t_cur, t_prev = totals(daily, cur_start, end), totals(daily, prev_start, prev_end)
    q28, qc, qp = by_query(qp28), by_query(cur7), by_query(prev7)

    striking = sorted(
        ((q, a) for q, a in q28.items()
         if STRIKING_MIN_POS <= a["position"] <= STRIKING_MAX_POS and a["impressions"] >= STRIKING_MIN_IMPR),
        key=lambda x: -x[1]["impressions"])

    movers = []
    for q in set(qc) & set(qp):
        if max(qc[q]["impressions"], qp[q]["impressions"]) >= MOVER_MIN_IMPR:
            movers.append((q, qp[q]["position"], qc[q]["position"], qc[q]["impressions"]))
    improved = sorted((m for m in movers if m[2] < m[1]), key=lambda m: m[2] - m[1])[:10]
    dropped = sorted((m for m in movers if m[2] > m[1]), key=lambda m: m[1] - m[2])[:10]

    seen_file = out_dir / "seen-queries.json"
    first_run = not seen_file.exists()
    seen = set(json.loads(seen_file.read_text())) if not first_run else set()
    new = sorted(((q, a) for q, a in q28.items() if q not in seen), key=lambda x: -x[1]["impressions"])
    seen_file.write_text(json.dumps(sorted(seen | set(q28) | set(qc)), indent=0), encoding="utf-8")

    cannibal = sorted(
        ((q, [(p, v) for p, v in a["pages"].items() if v["impressions"] >= CANNIBAL_MIN_IMPR])
         for q, a in q28.items()),
        key=lambda x: -sum(v["impressions"] for _, v in x[1]))
    cannibal = [(q, ps) for q, ps in cannibal if len(ps) >= 2]

    not_indexed, inspect_note, pace_note = [], "", ""
    if args.inspect:
        try:
            urls = sitemap_urls(args.sitemap)
            results = {}
            for u in urls:
                try:
                    r = gum(args, "searchconsole.urlInspection.index.inspect",
                            {"body": {"inspectionUrl": u, "siteUrl": args.site}})
                    results[u] = {"verdict": find_key(r, "verdict"), "coverageState": find_key(r, "coverageState"),
                                  "lastCrawlTime": find_key(r, "lastCrawlTime")}
                except GumError as e:
                    results[u] = {"verdict": "ERROR", "coverageState": str(e)[:200]}
            save("url-inspection", results)
            not_indexed = [(u, v) for u, v in results.items() if v.get("verdict") != "PASS"]
            inspect_note = f"{len(urls) - len(not_indexed)} of {len(urls)} sitemap URLs indexed."
            pace_note = pace_check(results, origin, today)
        except GumError as e:
            inspect_note = f"Indexing check failed: {e}"
    else:
        inspect_note = "Skipped (--no-inspect)."

    # ---- write the report ----
    d = lambda x: x.strftime("%-d %b")
    md = [f"# Search Console report: {origin}", "",
          f"Generated {today.isoformat()}. Last 7 days = {d(cur_start)}–{d(end)}; previous = {d(prev_start)}–{d(prev_end)}; "
          f"28-day window from {d(start28)}. Search Console data lags 2–3 days.", "",
          "## Totals, week over week", "",
          table(["", "Last 7 days", "Previous 7", "Change"], [
              ["Clicks", t_cur["clicks"], t_prev["clicks"], pct(t_cur["clicks"], t_prev["clicks"])],
              ["Impressions", t_cur["impressions"], t_prev["impressions"], pct(t_cur["impressions"], t_prev["impressions"])]]),
          f"## Striking distance (positions {STRIKING_MIN_POS}–{STRIKING_MAX_POS}, 28 days)", "",
          "Google already finds these pages relevant. Improve the page that ranks: match the query in the title, "
          "answer it in the first sentence, and link to it from related guides.", "",
          table(["Query", "Impressions", "Clicks", "Avg position", "Page"],
                [[q, a["impressions"], a["clicks"], f"{a['position']:.1f}",
                  short(max(a["pages"], key=lambda p: a["pages"][p]["impressions"]), origin) if a["pages"] else ""]
                 for q, a in striking[:25]]),
          "## Biggest movers (average position, week over week)", "",
          "### Improved", "",
          table(["Query", "Was", "Now", "Impressions (7d)"], [[q, f"{a:.1f}", f"{b:.1f}", i] for q, a, b, i in improved]),
          "### Dropped", "",
          table(["Query", "Was", "Now", "Impressions (7d)"], [[q, f"{a:.1f}", f"{b:.1f}", i] for q, a, b, i in dropped]),
          "## New queries", "",
          ("_First run: every query is new, so this list starts tomorrow._\n" if first_run else
           table(["Query", "Impressions", "Avg position", "Page"],
                 [[q, a["impressions"], f"{a['position']:.1f}",
                   short(max(a["pages"], key=lambda p: a["pages"][p]["impressions"]), origin) if a["pages"] else ""]
                  for q, a in new[:25]])),
          "## Pages competing for the same query", "",
          "Two of your pages split the same query. Decide which page should rank, and link to it from the other with the query's wording.", "",
          table(["Query", "Pages (impressions, position)"],
                [[q, "; ".join(f"{short(p, origin)} ({v['impressions']}, {v['position']:.1f})" for p, v in ps)]
                 for q, ps in cannibal[:15]]),
          "## Indexing", "", inspect_note, "", pace_note, "",
          table(["URL", "Verdict", "Coverage"], [[short(u, origin), v.get("verdict"), v.get("coverageState")] for u, v in not_indexed])
          if not_indexed else ""]
    report = "\n".join(md)
    path = rep_dir / f"{today.isoformat()}.md"
    path.write_text(report, encoding="utf-8")
    (rep_dir / "latest.md").write_text(report, encoding="utf-8")

    summary = (f"{origin}: {t_cur['clicks']} clicks ({pct(t_cur['clicks'], t_prev['clicks'])}), "
               f"{t_cur['impressions']} impressions ({pct(t_cur['impressions'], t_prev['impressions'])}), "
               f"{len(striking)} striking-distance queries, {len(not_indexed)} not indexed")
    print(summary)
    print(f"Report: {path}")
    notify("SEO daily report", summary)


# ---------- macOS helpers ----------

def notify(title, text):
    if sys.platform == "darwin" and shutil.which("osascript"):
        script = f'display notification {json.dumps(text)} with title {json.dumps(title)}'
        subprocess.run(["osascript", "-e", script], capture_output=True)


def slug(site):
    return re.sub(r"[^a-z0-9]+", "-", site.split(":", 1)[-1].lower()).strip("-")


def launchd_paths(args):
    label = f"{LABEL_PREFIX}.{slug(args.site)}"
    return label, Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"


def install(args):
    if sys.platform != "darwin":
        sys.exit("--install uses macOS launchd. On Linux, add a cron line instead, e.g.\n"
                 f"  7 9 * * * {sys.executable} {Path(__file__).resolve()} --site {args.site}")
    gum_path = shutil.which(args.gum) or args.gum
    if not Path(gum_path).exists():
        sys.exit(f"gum not found ({args.gum}). Install it first, or pass --gum /absolute/path/to/gum.")
    label, plist = launchd_paths(args)
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    prog = [sys.executable, str(Path(__file__).resolve()), "--site", args.site, "--sitemap", args.sitemap,
            "--gum", gum_path, "--out", str(out)]
    if args.profile:
        prog += ["--profile", args.profile]
    if not args.inspect:
        prog.append("--no-inspect")
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key>
  <array>
{chr(10).join(f"    <string>{esc(a)}</string>" for a in prog)}
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>{esc(str(Path(gum_path).parent))}:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>{args.hour}</integer><key>Minute</key><integer>{args.minute}</integer></dict>
  <key>StandardOutPath</key><string>{esc(str(out / "launchd.log"))}</string>
  <key>StandardErrorPath</key><string>{esc(str(out / "launchd.log"))}</string>
</dict>
</plist>
""", encoding="utf-8")
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(plist)], capture_output=True)
    r = subprocess.run(["launchctl", "bootstrap", domain, str(plist)], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"launchctl bootstrap failed: {r.stderr.strip()}\nPlist written to {plist}")
    print(f"Installed {label}: runs every day at {args.hour:02d}:{args.minute:02d} "
          "(if the Mac is asleep then, it runs when it wakes).")
    print(f"Reports: {out / 'reports'}   Log: {out / 'launchd.log'}")
    print(f"Run it now to test: launchctl kickstart {domain}/{label}")


def uninstall(args):
    label, plist = launchd_paths(args)
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(plist)], capture_output=True)
    if plist.exists():
        plist.unlink()
    print(f"Removed {label}. Reports in {Path(args.out).expanduser()} are kept.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--site", default=DEFAULT_SITE, help="Search Console property (default: %(default)s)")
    ap.add_argument("--sitemap", default=DEFAULT_SITEMAP, help="sitemap for the indexing check")
    ap.add_argument("--gum", default=os.environ.get("GUM_BIN", "gum"), help="path to the gum binary")
    ap.add_argument("--profile", default="", help="gum profile (default: gum's own default)")
    ap.add_argument("--out", default="", help="output folder (default: ~/seo-data/<site>)")
    ap.add_argument("--no-inspect", dest="inspect", action="store_false", help="skip URL Inspection")
    ap.add_argument("--install", action="store_true", help="run daily via macOS launchd")
    ap.add_argument("--uninstall", action="store_true", help="remove the daily run")
    ap.add_argument("--hour", type=int, default=9)
    ap.add_argument("--minute", type=int, default=7)
    args = ap.parse_args()
    args.out = args.out or f"~/seo-data/{slug(args.site)}"
    if args.install:
        return install(args)
    if args.uninstall:
        return uninstall(args)
    try:
        run(args)
    except GumError as e:
        msg = str(e)
        hint = ""
        if "AUTH_REFRESH_FAILED" in msg or "SCOPE_MISSING" in msg:
            hint = ("\nThe Google sign-in expired or is missing Search Console access. Run:\n"
                    "  gum auth login --scope https://www.googleapis.com/auth/webmasters.readonly\n"
                    "If it expires every 7 days, publish the OAuth app (Google Auth Platform > Audience > Publish app).")
        notify("SEO daily report failed", "gum sign-in needed" if hint else "See launchd.log")
        sys.exit(f"gum failed:\n{msg}{hint}")


if __name__ == "__main__":
    main()
