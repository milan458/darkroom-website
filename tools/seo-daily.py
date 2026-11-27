#!/usr/bin/env python3
"""Daily Google Search Console report for getnoxium.app (or any Search Console property), via gum.

Runs on the Mac where gum is signed in (gum keeps the Google credentials; nothing secret is stored
here). Standard library only; works with macOS's /usr/bin/python3.

    python3 tools/seo-daily.py                 # pull today's data and write the report
    python3 tools/seo-daily.py --no-inspect    # skip the URL Inspection (indexing) check
    python3 tools/seo-daily.py --install       # run it every day at 09:07 (macOS launchd)
    python3 tools/seo-daily.py --install --hour 7 --minute 41
    python3 tools/seo-daily.py --uninstall     # stop the daily run
    python3 tools/seo-daily.py --publish       # also push summary.json to the private data repo
    python3 tools/seo-daily.py --install --publish
    python3 tools/seo-daily.py --sheet-only    # only update the Google Sheet (the first run creates and backfills it)
    python3 tools/seo-daily.py --install --publish --sheet   # daily report + summary push + Google Sheet
    python3 tools/seo-daily.py --site sc-domain:example.com --sitemap https://example.com/sitemap.xml

Output (outside the repo, because this repo is public):
    ~/seo-data/<site>/reports/YYYY-MM-DD.md   the day's report (also reports/latest.md)
    ~/seo-data/<site>/raw/YYYY-MM-DD/*.json   raw gum responses, for later comparisons
    ~/seo-data/<site>/seen-queries.json       every query seen so far, to spot new ones
    ~/seo-data/<site>/summary.json            compact numbers for the cloud runs (see below)
    ~/seo-data/<site>/sheet.json              the Google Sheet's id and the last day written to each tab

--publish: if ~/seo-data is a git clone of a PRIVATE repo (e.g. milan458/noxium-seo-data), commit and
push <site>/summary.json and <site>/reports/latest.md there after each run, so the daily cloud runs can
read Search Console numbers without gum. Raw data, logs and query history stay on this Mac (.gitignore).
Never point this at the public website repo.

--sheet: also append Search Console numbers to a Google Sheet (in the Google account gum is signed in
to), so any Claude session with a Google Sheets connector can read them. The first run creates the
sheet and backfills everything Search Console still has (about 16 months); later runs append only the
days that became final since the last run. Tabs: daily (whole site per day), pages (per page per day),
queries (per query per day); columns date, page/query, clicks, impressions, ctr, position. Search
Console keeps 16 months, the sheet keeps everything. Needs the Sheets scope once:
    gum login --service searchconsole,sheets

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
import time
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

def gum(args, op, params, verb="read", flags=()):
    cmd = [args.gum, verb, op]
    if verb == "write":
        cmd.append("--allow-write")
    cmd += ["--args", json.dumps(params), "--output", "json", *flags]
    if args.profile:
        cmd += ["--profile", args.profile]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if "results_omitted_count" in p.stderr:
        raise GumError(f"gum dropped rows from {op}: {p.stderr.strip()[-500:]}")
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


def origin_of(site):
    return "https://" + site.split(":", 1)[1] if site.startswith("sc-domain:") else site.rstrip("/")


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
    origin = origin_of(args.site)

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
    pages28 = save("page-28d", search_analytics(args, start28, end, ["page"]))
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

    # Compact numbers for the cloud runs (they can't run gum): pages by impressions, top queries,
    # striking distance, indexing. Paths are site-relative ("/guides/…").
    def q_row(q, a):
        page = short(max(a["pages"], key=lambda p: a["pages"][p]["impressions"]), origin) if a["pages"] else ""
        return {"query": q, "page": page, "impressions": a["impressions"], "clicks": a["clicks"],
                "position": round(a["position"], 1)}
    summary_data = {
        "site": origin, "generated": today.isoformat(),
        "windows": {"last7": [cur_start.isoformat(), end.isoformat()], "prev7": [prev_start.isoformat(), prev_end.isoformat()],
                    "last28": [start28.isoformat(), end.isoformat()]},
        "totals": {"last7": t_cur, "prev7": t_prev},
        "pages": sorted(({"page": short(r_["keys"][0], origin), "impressions": r_["impressions"], "clicks": r_["clicks"],
                          "position": round(r_["position"], 1)} for r_ in rows(pages28)), key=lambda x: -x["impressions"]),
        "queries": [q_row(q, a) for q, a in sorted(q28.items(), key=lambda x: -x[1]["impressions"])[:200]],
        "striking": [q_row(q, a) for q, a in striking[:50]],
        "competing": [{"query": q, "pages": [{"page": short(p, origin), **v} for p, v in ps]} for q, ps in cannibal[:30]],
        "notIndexed": [{"page": short(u, origin), "verdict": v.get("verdict"), "coverage": v.get("coverageState")}
                       for u, v in not_indexed],
        "pace": re.sub(r"\*\*", "", pace_note) or None,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary_data, indent=1, ensure_ascii=False), encoding="utf-8")
    if args.publish:
        publish(out_dir, today)
    if args.sheet:
        try:
            sheet_export(args)
        except GumError as e:
            print(f"--sheet: Google Sheet update failed: {e}")
            notify("SEO daily report", "Couldn't update the Google Sheet (see launchd.log)")

    summary = (f"{origin}: {t_cur['clicks']} clicks ({pct(t_cur['clicks'], t_prev['clicks'])}), "
               f"{t_cur['impressions']} impressions ({pct(t_cur['impressions'], t_prev['impressions'])}), "
               f"{len(striking)} striking-distance queries, {len(not_indexed)} not indexed")
    print(summary)
    print(f"Report: {path}")
    notify("SEO daily report", summary)


def publish(out_dir, today):
    """Commit and push summary.json and latest.md to the private data repo that ~/seo-data is a clone of."""
    repo = out_dir.parent
    if not (repo / ".git").exists():
        print(f"--publish: {repo} isn't a git clone; skipped. See SEO-PLAYBOOK.md, 'Search Console data for the cloud runs'.")
        return
    ignore = repo / ".gitignore"
    if not ignore.exists():
        ignore.write_text("# Only summaries leave this Mac.\n*/raw/\n*/seen-queries.json\n*/launchd.log\n*/reports/20*.md\n",
                          encoding="utf-8")
    site = out_dir.name
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)
    git("add", ".gitignore", f"{site}/summary.json", f"{site}/reports/latest.md")
    if git("diff", "--cached", "--quiet").returncode == 0:
        print("--publish: nothing new to push.")
        return
    git("commit", "-q", "-m", f"{site}: Search Console summary {today.isoformat()}")
    pushed = git("push", "-q", "-u", "origin", "HEAD")
    if pushed.returncode != 0:
        print(f"--publish: push failed: {pushed.stderr.strip()[-300:]}")
        notify("SEO daily report", "Couldn't push the summary to GitHub (see launchd.log)")
    else:
        print(f"--publish: pushed {site}/summary.json")


# ---------- Google Sheet export ----------

SHEET_TABS = {
    "daily": (["date"], ["date", "clicks", "impressions", "ctr", "position"]),
    "pages": (["date", "page"], ["date", "page", "clicks", "impressions", "ctr", "position"]),
    "queries": (["date", "query"], ["date", "query", "clicks", "impressions", "ctr", "position"]),
}
SC_HISTORY_DAYS = 486   # Search Console keeps about 16 months
SC_PAGE_ROWS = 25000    # the API's maximum rowLimit
APPEND_ROWS = 1000      # rows per append, keeps gum's --args well under macOS's argument size limit


def sa_all_rows(args, start, end, dimensions):
    """Every row for the window (final data only, the API default), following startRow pages."""
    out, start_row = [], 0
    while True:
        body = {"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": dimensions,
                "rowLimit": SC_PAGE_ROWS, "startRow": start_row}
        batch = rows(gum(args, "searchconsole.searchanalytics.query", {"siteUrl": args.site, "body": body},
                         flags=["--max-items", "all"]))
        out += batch
        if len(batch) < SC_PAGE_ROWS:
            return out
        start_row += SC_PAGE_ROWS


def create_sheet(args, origin):
    # gum takes a request's body fields under the reserved "body" arg; path and query
    # fields (spreadsheetId, range, valueInputOption on append) stay at the top level.
    params = {"body": {"properties": {"title": f"Search Console: {origin.split('//', 1)[-1]}"},
                       "sheets": [{"properties": {"title": tab, "gridProperties": {"frozenRowCount": 1}}}
                                  for tab in SHEET_TABS]}}
    r = gum(args, "sheets.spreadsheets.create", params, verb="write")
    sid = find_key(r, "spreadsheetId")
    if not sid:
        raise GumError(f"Sheets didn't return a spreadsheet id: {json.dumps(r)[:500]}")
    gum(args, "sheets.spreadsheets.values.batchUpdate",
        {"spreadsheetId": sid,
         "body": {"valueInputOption": "RAW",
                  "data": [{"range": f"{tab}!A1", "values": [header]} for tab, (_, header) in SHEET_TABS.items()]}},
        verb="write")
    return sid, find_key(r, "spreadsheetUrl") or f"https://docs.google.com/spreadsheets/d/{sid}/edit"


def sheet_export(args):
    """Append the days that became final since the last run; the first run creates the sheet and backfills."""
    origin = origin_of(args.site)
    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    state_file = out_dir / "sheet.json"
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    save_state = lambda: state_file.write_text(json.dumps(state, indent=1), encoding="utf-8")
    if not state.get("spreadsheetId"):
        sid, url = create_sheet(args, origin)
        state = {"spreadsheetId": sid, "url": url, "through": {}}
        save_state()
        print(f"--sheet: created {url}")
    sid, through = state["spreadsheetId"], state.setdefault("through", {})

    today = dt.date.today()
    earliest, end = today - dt.timedelta(days=SC_HISTORY_DAYS), today - dt.timedelta(days=1)
    added = {}
    for tab, (dims, _) in SHEET_TABS.items():
        last = through.get(tab)
        start = max(earliest, dt.date.fromisoformat(last) + dt.timedelta(days=1)) if last else earliest
        if start > end:
            continue
        by_date = {}
        for r in sa_all_rows(args, start, end, dims):
            keys = r["keys"]
            label = [short(keys[1], origin)] if tab == "pages" else keys[1:]
            by_date.setdefault(keys[0], []).append(
                [keys[0], *label, r["clicks"], r["impressions"], round(r["ctr"], 4), round(r["position"], 2)])
        # Append whole days at a time and record progress after each append, so a failed run
        # never writes the same day twice.
        chunk, chunk_last, n = [], None, 0
        dates = sorted(by_date)
        for i, d in enumerate(dates):
            chunk += sorted(by_date[d], key=lambda v: (-v[-4], -v[-3]))
            chunk_last = d
            if len(chunk) >= APPEND_ROWS or i == len(dates) - 1:
                gum(args, "sheets.spreadsheets.values.append",
                    {"spreadsheetId": sid, "range": f"{tab}!A1", "valueInputOption": "RAW",
                     "insertDataOption": "INSERT_ROWS", "body": {"values": chunk}}, verb="write")
                n += len(chunk)
                through[tab] = chunk_last
                save_state()
                chunk = []
                time.sleep(1.1)  # stay under the Sheets write quota (60 a minute) during a backfill
        added[tab] = n
    print(f"--sheet: added {', '.join(f'{n} {t} rows' for t, n in added.items()) or 'nothing new'} "
          f"(final data through {max(through.values(), default='none')}). {state.get('url', '')}")


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
    if args.publish:
        prog.append("--publish")
    if args.sheet:
        prog.append("--sheet")
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
    ap.add_argument("--publish", action="store_true", help="push summary.json to the private data repo (~/seo-data)")
    ap.add_argument("--sheet", action="store_true",
                    help="also append the numbers to a Google Sheet (created and backfilled on the first run)")
    ap.add_argument("--sheet-only", action="store_true", help="only update the Google Sheet, no report")
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
        sheet_export(args) if args.sheet_only else run(args)
    except GumError as e:
        msg = str(e)
        hint = ""
        if "AUTH_REFRESH_FAILED" in msg or "SCOPE_MISSING" in msg:
            hint = ("\nThe Google sign-in expired or is missing Search Console or Sheets access. Run:\n"
                    "  gum login --service searchconsole,sheets\n"
                    "If it expires every 7 days, publish the OAuth app (Google Auth Platform > Audience > Publish app).")
        notify("SEO daily report failed", "gum sign-in needed" if hint else "See launchd.log")
        sys.exit(f"gum failed:\n{msg}{hint}")


if __name__ == "__main__":
    main()
