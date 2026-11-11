#!/usr/bin/env python3
"""Quality gate for getnoxium.app content pages. Run it after tools/build.py, before opening a PR.

    python3 tools/check_content.py                      # every guide, feature, comparison and scenario
    python3 tools/check_content.py guides/new-guide.html compare/keepsafe.html
    python3 tools/check_content.py --plan               # also check content-plan.json

Errors (exit 1) block publishing; warnings are worth a look. The rules come from CLAUDE.md and
SEO-PLAYBOOK.md: a short answer, an FAQ, internal links, enough substance, no banned marketing words,
Noxium facts that match site.json, dated sources on comparisons, and the safety protocol on sensitive
scenarios. Standard library only.
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
SECTIONS = SITE.get("sections", {"guide": {"hub": "/guides/"}})
HUBS = {s["hub"] for s in SECTIONS.values()}

MIN_WORDS = {"guide": 900, "feature": 700, "compare": 1200, "scenario": 700}
MIN_FAQ = 3
MIN_INTERNAL_LINKS = 2

BANNED = ["military-grade", "military grade", "bank-level", "bank level", "best-in-class", "revolutionary",
          "unhackable", "100% secure", "completely secure", "totally secure", "guaranteed", "game-changer",
          "cutting-edge", "state-of-the-art", "world-class", "ultimate"]
PLACEHOLDERS = re.compile(
    r"\b(TODO|TBD|FIXME|PLACEHOLDER|COMPETITOR|ORGANIZATION|HEADLINE|QUESTION-STYLE|CTA HEADLINE|ONE-PARAGRAPH|"
    r"DIRECT ANSWER|THE DIRECT ANSWER|ANSWER FIRST|STEP\.|idNNN|noxium-IMAGE|IMAGE\.jpg|RELATED-\d|DATE)\b")
SAFETY_ORGS = ["support.apple.com", "apple.com/legal", "techsafety.org", "nnedv.org", "stopstalkerware.org",
               "stopncii.org", "takeitdown.ncmec.org", "missingkids.org", "ssd.eff.org", "eff.org", "aclu.org",
               "thehotline.org", "rainn.org", "cybercivilrights.org", "ncmec.org", "fbi.gov", "ic3.gov",
               "consumer.ftc.gov", "ftc.gov", "cpj.org", "freedom.press", "accessnow.org", "hhs.gov",
               "plannedparenthood.org", "uscis.gov", "hud.gov", "nlrb.gov", "eeoc.gov", "988lifeline.org"]
MONTHS = r"(January|February|March|April|May|June|July|August|September|October|November|December)"


def strip(s):
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def facts_text():
    return " ".join(v for _, v in SITE["facts"])


def check_noxium_claims(text, errors):
    """Prices and free-plan limits in any sentence that names Noxium must match site.json facts."""
    facts = facts_text()
    fact_prices = set(re.findall(r"\$\d+(?:\.\d\d)?", facts))
    fact_counts = set(re.findall(r"(\d+) (?:photos|videos)", facts))
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if "Noxium" not in sentence:
            continue
        # Other apps' prices often share the sentence ("Noxium is $19.99 a year; X is $23.99"):
        # only flag a price when no other app name sits between it and "Noxium".
        for price in re.findall(r"\$\d+(?:\.\d\d)?", sentence):
            if price not in fact_prices and re.search(r"Noxium[^;:]{0,60}" + re.escape(price), sentence):
                errors.append(f"Noxium price {price} isn't in site.json facts: \"{sentence[:140]}\"")
        for n in re.findall(r"Noxium[^.;]{0,60}?\b(\d+) (?:photos|videos)\b", sentence):
            if n not in fact_counts:
                errors.append(f"Noxium limit \"{n} photos/videos\" isn't in site.json facts: \"{sentence[:140]}\"")


def check_page(page, errors, warnings):
    path = ROOT / page["file"]
    if not path.exists():
        errors.append("file missing")
        return
    raw = path.read_text(encoding="utf-8")
    src = re.sub(r"<!--.*?-->", " ", raw, flags=re.S)
    kind = page["type"]
    m = re.search(r'<article class="prose">(.*?)</article>', src, re.S)
    article = m.group(1) if m else ""
    main = re.search(r"<main\b.*?</main>", src, re.S)
    main = main.group(0) if main else src
    text = strip(article)

    if not article:
        errors.append('no <article class="prose">')
    if len(re.findall(r"<h1\b", src)) != 1:
        errors.append("needs exactly one <h1>")
    if 'class="answer"' not in main:
        errors.append('no "Short answer" box (<div class="answer">)')
    words = len(text.split())
    if words < MIN_WORDS.get(kind, 0):
        errors.append(f"{words} words in the article; {kind} pages need at least {MIN_WORDS[kind]}")
    faqs = len(re.findall(r'<details class="faq-item"', article))
    if faqs < MIN_FAQ:
        errors.append(f"{faqs} FAQ items; need at least {MIN_FAQ}")
    internal = {h for h in re.findall(r'href="(/[^"#]*)"', article) if h not in ("/",) and not h.startswith("/#")}
    if len(internal) < MIN_INTERNAL_LINKS:
        errors.append(f"{len(internal)} internal links in the article text; need at least {MIN_INTERNAL_LINKS}")
    for p in sorted(internal):
        target = p.rstrip("/") or "/"
        known = {x["path"].rstrip("/") or "/" for x in SITE["pages"]}
        if target not in known and not p.startswith("/assets/"):
            errors.append(f"internal link {p} isn't a page in site.json")
    hits = PLACEHOLDERS.findall(strip(main))
    if hits or re.search(r"<td>…</td>", main):
        errors.append(f"template placeholders left: {', '.join(sorted(set(hits))) or '…'}")
    lower = text.lower()
    # Quoting a phrase to debunk it ("military-grade" alone tells you nothing) is fine, and so is a
    # question about what it means.
    claims = re.sub(r'["“][^"”]{0,60}["”]', " ", lower)
    claims = " ".join(s for s in re.split(r"(?<=[.!?])\s+", claims) if not (s.endswith("?") and "mean" in s))
    for b in BANNED:
        if b in claims:
            errors.append(f'banned phrase "{b}" (SEO-PLAYBOOK.md section 11)')
    for img in re.findall(r"<img\b[^>]*>", main):
        if "alt=" not in img:
            errors.append(f"image without alt: {img[:80]}")
        if "width=" not in img or "height=" not in img:
            errors.append(f"image without width/height: {img[:80]}")
    check_noxium_claims(text, errors)

    kw = page.get("keyword", "")
    if kw:
        words_kw = [w for w in re.findall(r"[a-z0-9]+", kw.lower()) if len(w) > 2]
        title = page["title"].lower()
        if words_kw and not any(w in title for w in words_kw):
            warnings.append(f'title doesn\'t contain any word of the keyword "{kw}"')

    if kind == "compare":
        if not page.get("competitor"):
            errors.append('site.json needs "competitor" (the app\'s exact App Store name)')
        src_m = re.search(r'id="sources".*?</ol>', article, re.S)
        if not src_m or not re.search(r'href="https?://', src_m.group(0)):
            errors.append("comparison needs a Sources list (id=\"sources\") with at least one external link")
        if not re.search(MONTHS + r" \d{4}|\d{4}-\d\d-\d\d", text):
            errors.append("comparison has no date for when competitor facts were checked")

    if kind == "scenario" and page.get("sensitive"):
        first_h2 = article.find("<h2")
        safety = article.find('id="safety"')
        if safety == -1 or (first_h2 != -1 and safety > first_h2):
            errors.append('sensitive scenario: the "If you\'re in danger" callout (id="safety") must come before the first heading')
        if 'data-cta="body"' in article or 'class="cta-card"' in article:
            errors.append("sensitive scenario: remove the CTA card")
        links = re.findall(r'href="(https?://[^"]+)"', article)
        orgs = {l for l in links if any(o in l for o in SAFETY_ORGS)}
        if len(orgs) < 2:
            errors.append(f"sensitive scenario: link at least 2 established organizations (found {len(orgs)})")
        if "not legal advice" not in lower:
            errors.append('sensitive scenario: say it is "not legal advice"')
    if kind == "scenario" and not page.get("sensitive") and 'id="safety"' in article:
        warnings.append('safety callout on a page not marked "sensitive": true (intended?)')


def check_plan(errors):
    plan_file = ROOT / "content-plan.json"
    if not plan_file.exists():
        errors.append("content-plan.json missing")
        return 0
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    site_paths = {p["path"] for p in SITE["pages"]}
    site_kw = {p.get("keyword", "").lower(): p["path"] for p in SITE["pages"] if p.get("keyword")}
    seen_paths, seen_kw = {}, {}
    for t in plan["topics"]:
        tag = t.get("path", "?")
        for key in ("order", "path", "type", "keyword", "cluster", "status"):
            if key not in t:
                errors.append(f"plan {tag}: missing \"{key}\"")
        if t.get("type") not in SECTIONS and t.get("type") != "expand":
            errors.append(f"plan {tag}: unknown type {t.get('type')}")
        if "noxium" in tag.lower():
            errors.append(f"plan {tag}: no brand name in slugs (CLAUDE.md)")
        if t.get("type") != "expand":
            if tag in seen_paths:
                errors.append(f"plan {tag}: path listed twice")
            if tag in site_paths and t.get("status") == "todo":
                errors.append(f"plan {tag}: already a page in site.json but still \"todo\"")
            kw = t.get("keyword", "").lower()
            if kw in seen_kw:
                errors.append(f"plan {tag}: keyword \"{kw}\" also targeted by {seen_kw[kw]}")
            if kw in site_kw and site_kw[kw] != tag:
                errors.append(f"plan {tag}: keyword \"{kw}\" already targeted by {site_kw[kw]}")
            seen_paths[tag], seen_kw[kw] = True, tag
        elif tag not in site_paths:
            errors.append(f"plan {tag}: \"expand\" topic must be an existing page")
    return len(plan["topics"])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    by_file = {p["file"]: p for p in SITE["pages"]}
    if args:
        pages = []
        for a in args:
            rel = str(Path(a).resolve().relative_to(ROOT)) if Path(a).exists() else a
            if rel not in by_file:
                print(f"{a}: not listed in site.json pages")
                return 1
            pages.append(by_file[rel])
    else:
        pages = [p for p in SITE["pages"] if p["type"] in SECTIONS and p["path"] not in HUBS]
    failed = 0
    for page in pages:
        errors, warnings = [], []
        check_page(page, errors, warnings)
        status = "FAIL" if errors else "ok  "
        if errors or warnings:
            print(f"{status} {page['file']}")
            for e in errors:
                print(f"       error: {e}")
            for w in warnings:
                print(f"       warning: {w}")
        failed += bool(errors)
    print(f"{len(pages) - failed} of {len(pages)} pages pass.")
    if "--plan" in sys.argv:
        errors = []
        n = check_plan(errors)
        for e in errors:
            print("plan error:", e)
        print(f"content-plan.json: {n} topics, {len(errors)} problems.")
        failed += bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
