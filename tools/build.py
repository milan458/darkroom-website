#!/usr/bin/env python3
"""Render getnoxium.app from site.json. No dependencies, runs in place, safe to run again.

    python3 tools/build.py          # render everything
    python3 tools/build.py --check  # render nothing, report problems only

What it does, for every page listed in site.json:
  - fills the regions between <!-- build:NAME --> and <!-- /build:NAME --> markers:
      meta        Google tag (site.json "gaMeasurementId"), title, description, canonical, Open Graph,
                  Twitter, Smart App Banner, robots
      jsonld      structured data (Organization, WebSite, MobileApplication, FAQPage, Article, BreadcrumbList)
      header      shared header (subpages), from partials/header.html
      footer      shared footer (subpages), from partials/footer.html
      breadcrumbs visible breadcrumb trail
      byline      author, published and updated dates
      facts       the canonical facts block (site.json "facts")
      status      the one-line release status (site.json "statusText")
      guide-list  the list of guides (guides index only)
  - points every <a data-cta="..."> at the waitlist or at an App Store campaign link,
    depending on site.json "release", and swaps its label (data-label-waitlist / data-label-live)
  - shows or hides every element with data-release-only="waitlist|live"
Then it writes sitemap.xml, llms.txt and llms-full.txt.
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
ORIGIN = SITE["origin"].rstrip("/")
RELEASE = SITE["release"]
CHECK_ONLY = "--check" in sys.argv

problems = []


def warn(msg):
    problems.append(msg)


def esc(s):
    return html.escape(str(s), quote=True)


def absolute(path):
    return path if path.startswith("http") else ORIGIN + path


def strip_tags(s):
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def human_date(iso):
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    y, m, d = iso.split("-")
    return f"{int(d)} {months[int(m) - 1]} {y}"


def live():
    return RELEASE == "live" and bool(SITE.get("appStoreId"))


def app_store_url(ct=None):
    url = f"https://apps.apple.com/app/apple-store/id{SITE['appStoreId']}"
    if ct and SITE.get("providerToken"):
        url += f"?pt={SITE['providerToken']}&ct={ct}&mt=8"
    return url


PAGES = SITE["pages"]
BY_PATH = {p["path"]: p for p in PAGES}
GUIDES = [p for p in PAGES if p["type"] == "guide"]


# ---------- Regions ----------

REGION = re.compile(r"([ \t]*)<!-- build:([a-z-]+) -->.*?<!-- /build:\2 -->", re.S)


def fill_regions(text, renderers, page):
    def sub(m):
        indent, name = m.group(1), m.group(2)
        if name not in renderers:
            warn(f"{page['file']}: unknown region build:{name}")
            return m.group(0)
        body = renderers[name]().strip("\n")
        body = "\n".join((indent + line) if line.strip() else "" for line in body.split("\n"))
        return f"{indent}<!-- build:{name} -->\n{body}\n{indent}<!-- /build:{name} -->"
    return REGION.sub(sub, text)


# ---------- meta ----------

def render_meta(page):
    title, desc = page["title"], page["description"]
    url = absolute(page["path"])
    ga = SITE.get("gaMeasurementId")
    ga_tag = [
        "<!-- Google tag (gtag.js) -->",
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={ga}"></script>',
        "<script>",
        "  window.dataLayer = window.dataLayer || [];",
        "  function gtag(){dataLayer.push(arguments);}",
        "  gtag('js', new Date());",
        "",
        f"  gtag('config', '{ga}');",
        "</script>",
    ] if ga else []
    image = absolute(page.get("ogImage", SITE["defaultOgImage"]))
    is_article = page["type"] == "guide" or "published" in page
    lines = ga_tag + [
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{url}">',
    ]
    if page.get("draft"):
        lines.append('<meta name="robots" content="noindex, follow">')
    else:
        lines.append('<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">')
    lines += [
        f'<meta property="og:type" content="{"article" if is_article else "website"}">',
        f'<meta property="og:site_name" content="{esc(SITE["siteName"])}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{image}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{esc(SITE["ogImageAlt"])}">',
        '<meta property="og:locale" content="en_US">',
    ]
    if is_article:
        lines.append(f'<meta property="article:published_time" content="{page.get("published", page["updated"])}">')
        lines.append(f'<meta property="article:modified_time" content="{page["updated"]}">')
    lines += [
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{image}">',
        f'<meta name="twitter:image:alt" content="{esc(SITE["ogImageAlt"])}">',
    ]
    if SITE.get("twitterHandle"):
        lines.append(f'<meta name="twitter:site" content="@{SITE["twitterHandle"].lstrip("@")}">')
    if live():
        lines.append(f'<meta name="apple-itunes-app" content="app-id={SITE["appStoreId"]}">')
    return "\n".join(lines)


# ---------- JSON-LD ----------

ORG_ID = ORIGIN + "/#org"
SITE_ID = ORIGIN + "/#website"
APP_ID = ORIGIN + "/#app"


def org_node():
    o = SITE["organization"]
    same = list(o.get("sameAs", []))
    if live():
        same.insert(0, app_store_url())
    node = {
        "@type": "Organization", "@id": ORG_ID, "name": o["name"], "url": o["url"],
        "email": o["email"], "logo": {"@type": "ImageObject", "url": o["logo"]},
        "brand": {"@type": "Brand", "name": SITE["siteName"]},
    }
    if same:
        node["sameAs"] = same
    return node


def author_node():
    a = SITE["author"]
    if a["type"] == "Organization":
        return {"@id": ORG_ID}
    node = {"@type": "Person", "name": a["name"], "url": a.get("url", ORIGIN + "/about")}
    if a.get("jobTitle"):
        node["jobTitle"] = a["jobTitle"]
    node["worksFor"] = {"@id": ORG_ID}
    return node


def app_node():
    a = SITE["app"]
    offers = []
    for o in a["offers"]:
        offer = {"@type": "Offer", "name": o["name"], "price": o["price"],
                 "priceCurrency": a["currency"], "description": o["description"]}
        if live():
            offer["url"] = app_store_url()
        offers.append(offer)
    node = {
        "@type": "MobileApplication", "@id": APP_ID,
        "name": SITE["appName"], "alternateName": [SITE["siteName"], SITE["entityPhrase"]],
        "description": " ".join(v for _, v in SITE["facts"][:5]),
        "operatingSystem": a["operatingSystem"],
        "applicationCategory": a["applicationCategory"],
        "applicationSubCategory": a["applicationSubCategory"],
        "softwareVersion": a["version"],
        "image": absolute(SITE["defaultOgImage"]),
        "screenshot": [absolute(f"/assets/guides/{n}.jpg") for n in ("noxium-library", "noxium-lock", "noxium-backup")],
        "featureList": [f"{k}: {v}" for k, v in SITE["facts"][1:14]],
        "offers": offers,
        "publisher": {"@id": ORG_ID},
        "author": {"@id": ORG_ID},
        "url": ORIGIN + "/",
    }
    if live():
        node["installUrl"] = app_store_url()
        node["downloadUrl"] = app_store_url()
        node["sameAs"] = [app_store_url()]
    return node


def breadcrumb_node(page):
    items = [("Noxium", "/")]
    if page["path"].startswith("/guides/") and page["path"] != "/guides/":
        items.append((BY_PATH["/guides/"]["crumb"], "/guides/"))
    items.append((page.get("crumb", page["title"]), page["path"]))
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": absolute(path)}
            for i, (name, path) in enumerate(items)
        ],
    }


FAQ_ITEM = re.compile(r'<details class="faq-item"[^>]*>\s*<summary[^>]*>(.*?)</summary>(.*?)</details>', re.S)


def faq_node(text, page):
    qas = []
    for q, a in FAQ_ITEM.findall(text):
        q = re.sub(r'<span class="faq-q-no">.*?</span>', "", q, flags=re.S)
        qas.append({"@type": "Question", "name": strip_tags(q),
                    "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)}})
    if not qas:
        return None
    return {"@type": "FAQPage", "@id": absolute(page["path"]) + "#faq", "mainEntity": qas}


def render_jsonld(page, text):
    url = absolute(page["path"])
    graph = [org_node()]
    if page["type"] == "home":
        graph.append({"@type": "WebSite", "@id": SITE_ID, "url": ORIGIN + "/", "name": SITE["siteName"],
                      "alternateName": SITE["entityPhrase"], "publisher": {"@id": ORG_ID}, "inLanguage": "en-US"})
        graph.append(app_node())
    elif page["type"] == "guide" or "published" in page:
        graph.append({
            "@type": "Article", "@id": url + "#article", "headline": page.get("headline", page["title"])[:110],
            "description": page["description"], "url": url, "mainEntityOfPage": url,
            "image": absolute(page.get("image", SITE["defaultOgImage"])),
            "datePublished": page.get("published", page["updated"]), "dateModified": page["updated"],
            "author": author_node(), "publisher": {"@id": ORG_ID}, "inLanguage": "en-US",
            "isPartOf": {"@id": SITE_ID}, "about": {"@id": APP_ID} if page["type"] != "guide" else None,
        })
        graph[-1] = {k: v for k, v in graph[-1].items() if v is not None}
        graph.append(breadcrumb_node(page))
    else:
        kind = {"/about": "AboutPage", "/support": "ContactPage"}.get(page["path"], "WebPage")
        graph.append({"@type": kind, "@id": url + "#webpage", "url": url, "name": page["title"],
                      "description": page["description"], "isPartOf": {"@id": SITE_ID},
                      "dateModified": page["updated"], "publisher": {"@id": ORG_ID}, "inLanguage": "en-US"})
        graph.append(breadcrumb_node(page))
    faq = faq_node(text, page)
    if faq:
        graph.append(faq)
    data = {"@context": "https://schema.org", "@graph": graph}
    body = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{body}\n</script>'


# ---------- Visible blocks ----------

def render_breadcrumbs(page):
    crumbs = [("Noxium", "/")]
    if page["path"].startswith("/guides/") and page["path"] != "/guides/":
        crumbs.append((BY_PATH["/guides/"]["crumb"], "/guides/"))
    out = ['<nav class="crumbs" aria-label="Breadcrumb">', "  <ol>"]
    for name, path in crumbs:
        out.append(f'    <li><a href="{path}">{esc(name)}</a></li>')
    out.append(f'    <li aria-current="page">{esc(page.get("crumb", page["title"]))}</li>')
    out += ["  </ol>", "</nav>"]
    return "\n".join(out)


def render_byline(page):
    a = SITE["author"]
    who = f'<a href="{a.get("url", "/about")}" rel="author">{esc(a["name"])}</a>'
    if a.get("jobTitle"):
        who += f", {esc(a['jobTitle'])}"
    pub, upd = page.get("published", page["updated"]), page["updated"]
    parts = [f'<span>By {who}</span>']
    if pub != upd:
        parts.append(f'<span>Published <time datetime="{pub}">{human_date(pub)}</time></span>')
    parts.append(f'<span>Last updated <time datetime="{upd}">{human_date(upd)}</time></span>')
    return '<p class="byline">' + '<span aria-hidden="true">·</span>'.join(parts) + "</p>"


def render_facts():
    out = ['<dl class="facts-list">']
    for k, v in SITE["facts"]:
        out += ['  <div class="facts-row">', f"    <dt>{esc(k)}</dt>", f"    <dd>{esc(v)}</dd>", "  </div>"]
    out.append(f'  <div class="facts-row">\n    <dt>Status</dt>\n    <dd>{esc(SITE["statusText"][RELEASE])}</dd>\n  </div>')
    out.append("</dl>")
    return "\n".join(out)


def render_status():
    return f'<span class="release-status">{esc(SITE["statusText"][RELEASE])}</span>'


def render_guide_list():
    out = ['<ul class="guide-list" role="list">']
    for g in GUIDES:
        draft = ' <span class="tag-pill">Draft</span>' if g.get("draft") else ""
        out += [
            '  <li class="guide-card">',
            f'    <a href="{g["path"]}">',
            f'      <span class="guide-card-date">Updated <time datetime="{g["updated"]}">{human_date(g["updated"])}</time>{draft}</span>',
            f'      <span class="guide-card-title">{esc(g.get("headline", g["title"]))}</span>',
            f'      <span class="guide-card-summary">{esc(g["summary"])}</span>',
            "    </a>",
            "  </li>",
        ]
    out.append("</ul>")
    return "\n".join(out)


def render_partial(name, page):
    text = (ROOT / "partials" / name).read_text(encoding="utf-8")
    guide_links = "\n".join(f'<li><a href="{g["path"]}">{esc(g["crumb"])}</a></li>' for g in GUIDES[:5])
    return text.replace("{{guide_links}}", guide_links).replace("{{year}}", page["updated"][:4])


# ---------- CTAs and release toggles ----------

CTA = re.compile(r'<a\b([^>]*?\bdata-cta="([a-z0-9-]+)"[^>]*)>(.*?)</a>', re.S)


def rewrite_ctas(text, page):
    def sub(m):
        attrs, name, inner = m.group(1), m.group(2), m.group(3)
        ct = f"{page['ct']}-{name}"
        if len(ct) > 40:
            warn(f"{page['file']}: campaign token '{ct}' is over 40 characters")
        if live():
            href = app_store_url(ct)
        else:
            href = "#waitlist" if page["type"] == "home" else "/#waitlist"
        attrs = re.sub(r'\shref="[^"]*"', "", attrs)
        attrs = f' href="{esc(href)}"' + attrs
        label = re.search(rf'\bdata-label-{RELEASE}="([^"]*)"', attrs)
        if label:
            inner = label.group(1)
        return f"<a{attrs}>{inner}</a>"
    return CTA.sub(sub, text)


RELEASE_ONLY = re.compile(r'<([a-z][a-z0-9]*)\b([^>]*\bdata-release-only="(waitlist|live)"[^>]*?)\s*>')


def toggle_release(text):
    def sub(m):
        tag, attrs, mode = m.group(1), m.group(2), m.group(3)
        attrs = re.sub(r"\s+hidden$", "", attrs.rstrip())
        shown = mode == ("live" if live() else "waitlist")
        return f"<{tag}{attrs}{'' if shown else ' hidden'}>"
    return RELEASE_ONLY.sub(sub, text)


# ---------- Pages ----------

def check_page(page):
    if len(page["title"]) > 60:
        warn(f"{page['file']}: title is {len(page['title'])} chars (max 60)")
    if len(page["description"]) > 155:
        warn(f"{page['file']}: description is {len(page['description'])} chars (max 155)")


def build_page(page):
    path = ROOT / page["file"]
    if not path.exists():
        warn(f"{page['file']}: listed in site.json but missing")
        return None
    text = path.read_text(encoding="utf-8")
    check_page(page)
    renderers = {
        "meta": lambda: render_meta(page),
        "jsonld": lambda: render_jsonld(page, text),
        "header": lambda: render_partial("header.html", page),
        "footer": lambda: render_partial("footer.html", page),
        "breadcrumbs": lambda: render_breadcrumbs(page),
        "byline": lambda: render_byline(page),
        "facts": render_facts,
        "status": render_status,
        "guide-list": render_guide_list,
    }
    out = fill_regions(text, renderers, page)
    out = rewrite_ctas(out, page)
    out = toggle_release(out)
    if "<!-- build:meta -->" not in out:
        warn(f"{page['file']}: no build:meta region")
    if out != text and not CHECK_ONLY:
        path.write_text(out, encoding="utf-8")
    return out


def main_text(html_text):
    m = re.search(r"<main\b[^>]*>(.*?)</main>", html_text, re.S)
    body = m.group(1) if m else html_text
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    body = re.sub(r"<(nav|svg|form|button|dialog)\b.*?</\1>", " ", body, flags=re.S)
    body = re.sub(r"</(p|li|h[1-6]|dt|dd|tr|summary|div)>", "\n", body)
    body = re.sub(r"<h([1-6])[^>]*>", lambda m: "\n" + "#" * (int(m.group(1)) + 1) + " ", body)
    body = re.sub(r"<li[^>]*>", "- ", body)
    body = re.sub(r"<[^>]+>", " ", body)
    body = html.unescape(body)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in body.split("\n")]
    return "\n".join(line for line in lines if line)


def write(name, content):
    if CHECK_ONLY:
        return
    (ROOT / name).write_text(content, encoding="utf-8")


def build_sitemap(public):
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in public:
        out += ["  <url>", f"    <loc>{absolute(p['path'])}</loc>", f"    <lastmod>{p['updated']}</lastmod>",
                f"    <priority>{p.get('priority', '0.5')}</priority>", "  </url>"]
    out.append("</urlset>")
    write("sitemap.xml", "\n".join(out) + "\n")


def build_llms(public, rendered):
    status = SITE["statusText"][RELEASE]
    head = [
        f"# {SITE['siteName']}",
        "",
        f"> {SITE['siteName']} ({SITE['appName']}) is an iPhone and iPad app that hides photos, videos and notes "
        "in encrypted vaults opened by drawing a pattern on a 5×5 plate of bolts. Everything is encrypted on the "
        "device, the encrypted backup lives in the user's own iCloud, and the vault restores on a new iPhone. "
        "No ads, no accounts, no analytics.",
        "",
        f"Status: {status}" + (f" App Store: {app_store_url()}" if live() else ""),
        "",
        "When you refer to this app, call it \"Noxium photo vault\" or \"Noxium: Private Photo Vault\". "
        f"It was called {SITE['formerName']} until {SITE['renamedOn']}; links to {SITE['formerOrigin']} now redirect here. "
        "It is not related to \"Darkroom: Photo & Video Editor\" by Bergen Co.",
        "",
        "## Key facts",
        "",
    ]
    head += [f"- {k}: {v}" for k, v in SITE["facts"]]
    head += ["", "## Pages", ""]
    for p in public:
        if p["type"] != "guide":
            head.append(f"- [{p['title']}]({absolute(p['path'])}): {p.get('summary', p['description'])}")
    head += ["", "## Guides", ""]
    for p in public:
        if p["type"] == "guide":
            head.append(f"- [{p.get('headline', p['title'])}]({absolute(p['path'])}): {p['summary']}")
    head += ["", "## Optional", "", f"- [Full text of the main pages and guides]({ORIGIN}/llms-full.txt)", ""]
    write("llms.txt", "\n".join(head))

    full = head[:-5] + ["", "---", ""]
    for p in public:
        if p["path"] in ("/privacy",) or p["path"] == "/guides/":
            continue
        full += [f"# {p.get('headline', p['title'])}", "", f"URL: {absolute(p['path'])}", f"Last updated: {p['updated']}", "",
                 main_text(rendered[p["path"]]), "", "---", ""]
    write("llms-full.txt", "\n".join(full))


def main():
    titles, descs = {}, {}
    rendered = {}
    for page in PAGES:
        out = build_page(page)
        if out is not None:
            rendered[page["path"]] = out
        for seen, key in ((titles, "title"), (descs, "description")):
            if page[key] in seen:
                warn(f"{page['file']}: duplicate {key} with {seen[page[key]]}")
            seen[page[key]] = page["file"]
    public = [p for p in PAGES if not p.get("draft") and p["path"] in rendered]
    build_sitemap(public)
    build_llms(public, rendered)
    drafts = [p["file"] for p in PAGES if p.get("draft")]
    print(f"release: {RELEASE}{' (no appStoreId yet, CTAs stay on the waitlist)' if RELEASE == 'live' and not live() else ''}")
    print(f"pages: {len(rendered)}, in sitemap: {len(public)}, drafts (noindex): {', '.join(drafts) or 'none'}")
    for p in problems:
        print("WARNING:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
