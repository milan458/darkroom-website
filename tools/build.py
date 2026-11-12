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

# Content sections: each page type with its own hub page (site.json "sections").
SECTIONS = SITE.get("sections", {"guide": {"hub": "/guides/", "label": "Guides"}})
CONTENT_TYPES = set(SECTIONS)
RELATED_MAX = 4


# ---------- Languages ----------
# English pages live at the root. Each other language in site.json "locales" lives under its prefix
# (/de/…) with the same slugs. A page exists in a language when i18n/<lang>.json lists it under
# "pages" (translated title, description, …) and the file <lang>/<english file> exists.

DEFAULT_LANG = "en"
# Google cuts titles and descriptions by width; CJK characters are about twice as wide.
CJK = {"ja", "ko", "zh-hans", "zh-hant"}
LOCALES = SITE.get("locales", {"en": {"hreflang": "en", "inLanguage": "en-US", "og": "en_US",
                                      "label": "English", "prefix": ""}})
I18N = {}
for _lang in LOCALES:
    if _lang != DEFAULT_LANG:
        _f = ROOT / "i18n" / f"{_lang}.json"
        I18N[_lang] = json.loads(_f.read_text(encoding="utf-8")) if _f.exists() else {}

TRANSLATED_FIELDS = ("title", "description", "headline", "summary", "crumb", "keyword", "published",
                     "updated", "draft", "image", "ogImage", "allLabel")
notes = []  # printed, but don't fail the build (e.g. a translation older than its English page)

for _p in PAGES:
    _p["_lang"], _p["_src"] = DEFAULT_LANG, _p["path"]
LPAGES = {DEFAULT_LANG: BY_PATH}  # lang -> {English path -> page in that language}
for _lang, _data in I18N.items():
    LPAGES[_lang] = {}
    for _src, _tr in _data.get("pages", {}).items():
        _base = BY_PATH.get(_src)
        if not _base:
            problems.append(f"i18n/{_lang}.json: {_src} isn't a page in site.json")
            continue
        _page = dict(_base)
        _page.update({k: v for k, v in _tr.items() if k in TRANSLATED_FIELDS})
        _page.update({"_lang": _lang, "_src": _src, "file": f"{_lang}/{_base['file']}",
                      "path": LOCALES[_lang]["prefix"] + _src, "source": _tr.get("source")})
        if not (ROOT / _page["file"]).exists():
            problems.append(f"i18n/{_lang}.json lists {_src}, but {_page['file']} doesn't exist")
            continue
        if not _tr.get("source"):
            problems.append(f"i18n/{_lang}.json {_src}: add \"source\" (the English \"updated\" date it was translated from)")
        elif _tr["source"] < _base["updated"]:
            notes.append(f"{_page['file']}: translated from the {_tr['source']} English version; English was updated {_base['updated']}")
        LPAGES[_lang][_src] = _page
ALL_PAGES = PAGES + [p for lang in I18N for p in LPAGES[lang].values()]
_missing_ui = set()


def lang_of(page):
    return page.get("_lang", DEFAULT_LANG)


def t(key, lang=DEFAULT_LANG):
    """A UI string. English keys are the English text itself; i18n/<lang>.json "ui" translates them."""
    if lang == DEFAULT_LANG:
        return key
    value = I18N.get(lang, {}).get("ui", {}).get(key)
    if value is None:
        if (lang, key) not in _missing_ui:
            _missing_ui.add((lang, key))
            problems.append(f"i18n/{lang}.json: no \"ui\" translation for \"{key}\"")
        return key
    return value


def version(src, lang):
    """The page at English path `src` in `lang`, or None if it isn't translated."""
    return LPAGES.get(lang, {}).get(src)


def best(src, lang):
    """The page in `lang` if it's translated and published, else the English page (for structural links)."""
    page = version(src, lang)
    if page and not page.get("draft"):
        return page
    return BY_PATH.get(src)


def versions(page):
    """Every published language version of a page, the page itself included, keyed by language."""
    out = {}
    for lang in LOCALES:
        v = version(page["_src"], lang)
        if v and not v.get("draft"):
            out[lang] = v
    return out


def localize_href(href, lang):
    """Point a root-relative link at the same page in `lang` when that page is translated."""
    if lang == DEFAULT_LANG or not href.startswith("/"):
        return href
    path, sep, frag = href.partition("#")
    target = version(path or "/", lang)
    if target and not target.get("draft"):
        return target["path"] + (sep + frag if sep else "")
    return href


def human_date_l(iso, lang):
    if lang == DEFAULT_LANG:
        return human_date(iso)
    fmt = I18N.get(lang, {}).get("dateFormat")
    months = I18N.get(lang, {}).get("months")
    if not fmt or not months:
        problems.append(f"i18n/{lang}.json: needs \"dateFormat\" and \"months\"")
        return iso
    y, m, d = iso.split("-")
    return fmt.format(d=int(d), month=months[int(m) - 1], m=int(m), y=y)


def facts_for(lang):
    if lang != DEFAULT_LANG and I18N.get(lang, {}).get("facts"):
        return I18N[lang]["facts"]
    return SITE["facts"]


def status_text(lang):
    return I18N.get(lang, {}).get("statusText", SITE["statusText"]).get(RELEASE, SITE["statusText"][RELEASE])


def pages_of(kind, lang=DEFAULT_LANG):
    """Pages of one type in `lang`, in site.json order."""
    out = []
    for p in PAGES:
        if p["type"] == kind:
            v = version(p["path"], lang)
            if v:
                out.append(v)
    return out


def hub_of(page):
    """The hub page a content page belongs to (e.g. /guides/ for a guide), or None.
    For a translated page, the translated hub if there is one, else the English hub."""
    section = SECTIONS.get(page["type"])
    if not section or page["_src"] == section["hub"]:
        return None
    return best(section["hub"], lang_of(page))


def crumb_trail(page):
    """Breadcrumb ancestors, home first, not including the page itself."""
    trail = [("Noxium", best("/", lang_of(page))["path"])]
    hub = hub_of(page)
    if hub:
        trail.append((hub["crumb"], hub["path"]))
    return trail


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
        alts = versions(page)
        if len(alts) > 1:  # hreflang only when the page has another language version
            for lang, v in alts.items():
                lines.append(f'<link rel="alternate" hreflang="{LOCALES[lang]["hreflang"]}" href="{absolute(v["path"])}">')
            if DEFAULT_LANG in alts:
                lines.append(f'<link rel="alternate" hreflang="x-default" href="{absolute(alts[DEFAULT_LANG]["path"])}">')
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
        f'<meta property="og:locale" content="{LOCALES[lang_of(page)]["og"]}">',
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
    same = list(a.get("sameAs", []))
    if live():
        node["installUrl"] = app_store_url()
        node["downloadUrl"] = app_store_url()
        same.insert(0, app_store_url())
    if same:
        node["sameAs"] = same
    return node


def breadcrumb_node(page):
    items = crumb_trail(page) + [(page.get("crumb", page["title"]), page["path"])]
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
    in_lang = LOCALES[lang_of(page)].get("inLanguage", LOCALES[lang_of(page)]["hreflang"])
    graph = [org_node()]
    if page["type"] == "home":
        graph.append({"@type": "WebSite", "@id": SITE_ID, "url": ORIGIN + "/", "name": SITE["siteName"],
                      "alternateName": SITE["entityPhrase"], "publisher": {"@id": ORG_ID}, "inLanguage": in_lang})
        graph.append(app_node())
    elif page.get("listType"):
        # Hub page: the list of pages in its section.
        items = [p for p in pages_of(page["listType"], lang_of(page)) if not p.get("draft")]
        graph.append({
            "@type": "CollectionPage", "@id": url + "#webpage", "url": url, "name": page["title"],
            "description": page["description"], "isPartOf": {"@id": SITE_ID},
            "dateModified": page["updated"], "publisher": {"@id": ORG_ID}, "inLanguage": in_lang,
            "mainEntity": {"@type": "ItemList", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": absolute(p["path"]), "name": p.get("headline", p["title"])}
                for i, p in enumerate(items)]},
        })
        graph.append(breadcrumb_node(page))
    elif page["type"] in CONTENT_TYPES or "published" in page:
        # Feature and comparison pages (and the standalone comparison) are about the app; guides and
        # scenarios are about the reader's problem.
        about_app = page["type"] in ("feature", "compare") or page["type"] not in CONTENT_TYPES
        article = {
            "@type": "Article", "@id": url + "#article", "headline": page.get("headline", page["title"])[:110],
            "description": page["description"], "url": url, "mainEntityOfPage": url,
            "image": absolute(page.get("image", SITE["defaultOgImage"])),
            "datePublished": page.get("published", page["updated"]), "dateModified": page["updated"],
            "author": author_node(), "publisher": {"@id": ORG_ID}, "inLanguage": in_lang,
            "isPartOf": {"@id": SITE_ID},
        }
        if about_app:
            article["about"] = {"@id": APP_ID}
        if page.get("competitor"):
            article["mentions"] = {"@type": "MobileApplication", "name": page["competitor"],
                                   "operatingSystem": "iOS", "applicationCategory": "MultimediaApplication"}
        graph.append(article)
        graph.append(breadcrumb_node(page))
    else:
        kind = {"/about": "AboutPage", "/support": "ContactPage"}.get(page["path"], "WebPage")
        graph.append({"@type": kind, "@id": url + "#webpage", "url": url, "name": page["title"],
                      "description": page["description"], "isPartOf": {"@id": SITE_ID},
                      "dateModified": page["updated"], "publisher": {"@id": ORG_ID}, "inLanguage": in_lang})
        graph.append(breadcrumb_node(page))
    faq = faq_node(text, page)
    if faq:
        graph.append(faq)
    data = {"@context": "https://schema.org", "@graph": graph}
    body = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{body}\n</script>'


# ---------- Visible blocks ----------

def render_breadcrumbs(page):
    out = [f'<nav class="crumbs" aria-label="{esc(t("Breadcrumb", lang_of(page)))}">', "  <ol>"]
    for name, path in crumb_trail(page):
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
    lang = lang_of(page)
    sp = "" if lang in CJK else " "  # CJK labels end in a full-width colon
    parts = [f'<span>{esc(t("By", lang))}{sp}{who}</span>']
    if pub != upd:
        parts.append(f'<span>{esc(t("Published", lang))}{sp}<time datetime="{pub}">{human_date_l(pub, lang)}</time></span>')
    parts.append(f'<span>{esc(t("Last updated", lang))}{sp}<time datetime="{upd}">{human_date_l(upd, lang)}</time></span>')
    return '<p class="byline">' + '<span aria-hidden="true">·</span>'.join(parts) + "</p>"


def render_facts(page):
    lang = lang_of(page)
    if lang != DEFAULT_LANG and not I18N.get(lang, {}).get("facts"):
        problems.append(f"{page['file']}: uses the facts block, but i18n/{lang}.json has no \"facts\"")
    out = ['<dl class="facts-list">']
    for k, v in facts_for(lang):
        out += ['  <div class="facts-row">', f"    <dt>{esc(k)}</dt>", f"    <dd>{esc(v)}</dd>", "  </div>"]
    out.append(f'  <div class="facts-row">\n    <dt>{esc(t("Status", lang))}</dt>\n    <dd>{esc(status_text(lang))}</dd>\n  </div>')
    out.append("</dl>")
    return "\n".join(out)


def render_status(page):
    return f'<span class="release-status">{esc(status_text(lang_of(page)))}</span>'


def render_list(kind, lang=DEFAULT_LANG):
    """Cards for every page of one type (a hub's "listType"). Drafts show with a Draft pill."""
    out = ['<ul class="guide-list" role="list">']
    for g in pages_of(kind, lang):
        draft = f' <span class="tag-pill">{esc(t("Draft", lang))}</span>' if g.get("draft") else ""
        out += [
            '  <li class="guide-card">',
            f'    <a href="{g["path"]}">',
            f'      <span class="guide-card-date">{esc(t("Updated", lang))}{"" if lang in CJK else " "}<time datetime="{g["updated"]}">{human_date_l(g["updated"], lang)}</time>{draft}</span>',
            f'      <span class="guide-card-title">{esc(g.get("headline", g["title"]))}</span>',
            f'      <span class="guide-card-summary">{esc(g["summary"])}</span>',
            "    </a>",
            "  </li>",
        ]
    out.append("</ul>")
    return "\n".join(out)


def render_partial(name, page):
    lang = lang_of(page)
    text = (ROOT / "partials" / name).read_text(encoding="utf-8")
    # Guides marked "footer": true in site.json, in site.json order (the first 5 guides if none are).
    # A translated page lists the ones translated into its language, or the English ones if none are yet.
    footer_guides = [g for g in GUIDES if g.get("footer") and not g.get("draft")] or GUIDES[:5]
    if lang != DEFAULT_LANG:
        translated = [v for v in (version(g["path"], lang) for g in footer_guides) if v and not v.get("draft")]
        footer_guides = translated or footer_guides
    guide_links = "\n".join(f'<li><a href="{g["path"]}">{esc(g["crumb"])}</a></li>' for g in footer_guides)
    # Hubs other than /guides/ appear once they're published (not drafts).
    hubs = [best(s["hub"], lang) for k, s in SECTIONS.items() if k != "guide"]
    hub_links = "\n".join(f'<li><a href="{h["path"]}">{esc(h["crumb"])}</a></li>'
                          for h in hubs if h and not h.get("draft"))
    if not hub_links:
        text = re.sub(r"[ \t]*\{\{hub_links\}\}\n", "", text)
    languages = render_languages(page)
    if not languages:
        text = re.sub(r"[ \t]*\{\{languages\}\}\n", "", text)
    text = re.sub(r"\{\{t:(.+?)\}\}", lambda m: esc(t(m.group(1), lang)) if lang != DEFAULT_LANG else m.group(1), text)
    text = re.sub(r'href="(/[^"]*)"', lambda m: f'href="{localize_href(m.group(1), lang)}"', text)
    return (text.replace("{{guide_links}}", guide_links).replace("{{hub_links}}", hub_links)
            .replace("{{languages}}", languages).replace("{{year}}", page["updated"][:4]))


def render_languages(page):
    """Links to this page in its other languages (footer). Empty while the page has only one."""
    alts = versions(page)
    if len(alts) < 2:
        return ""
    lang = lang_of(page)
    links = []
    for code, v in alts.items():
        loc = LOCALES[code]
        current = ' aria-current="true"' if code == lang else ""
        links.append(f'<a href="{v["path"]}" hreflang="{loc["hreflang"]}" lang="{loc["hreflang"]}"{current}>{esc(loc["label"])}</a>')
    return f'<nav class="lang-list" aria-label="{esc(t("Language", lang))}">' + "".join(links) + "</nav>"


def render_related(page):
    """The aside's Related box: the page's own "related" paths first, then pages from the same
    "cluster", then a link to the section hub. Public pages never link to drafts."""
    lang = lang_of(page)
    picked = []
    for path in page.get("related", []):
        if path not in BY_PATH:
            warn(f"{page['file']}: related path {path} isn't in site.json")
            continue
        target = version(path, lang)  # a translated page only links to pages in its language
        if target and path != page["_src"] and (page.get("draft") or not target.get("draft")):
            picked.append(target)
    limit = max(RELATED_MAX, len(picked))
    if page.get("cluster"):
        for src in PAGES:
            if len(picked) >= limit:
                break
            p = version(src["path"], lang)
            if (p and p.get("cluster") == page["cluster"] and p["_src"] != page["_src"] and p not in picked
                    and p["type"] in CONTENT_TYPES and not p.get("draft")):
                picked.append(p)
    hub = hub_of(page)
    items = [(p["path"], p.get("crumb", p["title"])) for p in picked]
    if hub and not hub.get("draft"):
        # A hub can name its own "All …" link ("allLabel"), for languages where the words agree in gender.
        name = hub["crumb"] if lang in {"de"} | CJK else hub["crumb"].lower()
        items.append((hub["path"], hub.get("allLabel") or t("All {name}", lang).replace("{name}", name)))
    if not items:
        warn(f"{page['file']}: Related box is empty (add \"related\" or \"cluster\" in site.json)")
    out = ['<div class="related">', f'  <p class="toc-title">{esc(t("Related", lang))}</p>', '  <ul role="list">']
    out += [f'    <li><a href="{path}">{esc(label)}</a></li>' for path, label in items]
    out += ["  </ul>", "</div>"]
    return "\n".join(out)


# ---------- CTAs and release toggles ----------

CTA = re.compile(r'<a\b([^>]*?\bdata-cta="([a-z0-9-]+)"[^>]*)>(.*?)</a>', re.S)


def rewrite_ctas(text, page):
    def sub(m):
        attrs, name, inner = m.group(1), m.group(2), m.group(3)
        ct = f"{page['ct']}-{name}" + ("" if lang_of(page) == DEFAULT_LANG else f"-{lang_of(page)}")
        if len(ct) > 40:
            warn(f"{page['file']}: campaign token '{ct}' is over 40 characters")
        if live():
            href = app_store_url(ct)
        else:
            href = "#waitlist" if page["type"] == "home" else best("/", lang_of(page))["path"] + "#waitlist"
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
    wide = lang_of(page) in CJK
    max_title, max_desc = (32, 80) if wide else (60, 155)
    if page["type"] in CONTENT_TYPES and page["_src"] != SECTIONS[page["type"]]["hub"]:
        for key in ("keyword", "cluster"):
            if not page.get(key):
                warn(f"{page['file']}: no \"{key}\" in site.json (needed for related links and the keyword check)")
    if len(page["title"]) > max_title:
        warn(f"{page['file']}: title is {len(page['title'])} chars (max {max_title})")
    if len(page["description"]) > max_desc:
        warn(f"{page['file']}: description is {len(page['description'])} chars (max {max_desc})")


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
        "facts": lambda: render_facts(page),
        "status": lambda: render_status(page),
        "guide-list": lambda: render_list("guide", lang_of(page)),
        "list": lambda: render_list(page.get("listType", "guide"), lang_of(page)),
        "languages": lambda: render_languages(page),
        "related": lambda: render_related(page),
    }
    out = fill_regions(text, renderers, page)
    if lang_of(page) != DEFAULT_LANG:
        # Links in a translated page's body go to the translated page when there is one.
        out = re.sub(r"<main\b.*?</main>", lambda m: re.sub(
            r'href="(/[^"]*)"', lambda h: f'href="{localize_href(h.group(1), lang_of(page))}"', m.group(0)), out, flags=re.S)
    html_lang = LOCALES[lang_of(page)]["hreflang"]
    out = re.sub(r'<html lang="[^"]*"', f'<html lang="{html_lang}"', out, count=1)
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
    alternates = {p["path"]: versions(p) for p in public}
    multilingual = any(len(a) > 1 for a in alternates.values())
    xhtml = ' xmlns:xhtml="http://www.w3.org/1999/xhtml"' if multilingual else ""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"{xhtml}>']
    for p in public:
        out += ["  <url>", f"    <loc>{absolute(p['path'])}</loc>", f"    <lastmod>{p['updated']}</lastmod>",
                f"    <priority>{p.get('priority', '0.5')}</priority>"]
        alts = alternates[p["path"]]
        if len(alts) > 1:
            for lang, v in alts.items():
                out.append(f'    <xhtml:link rel="alternate" hreflang="{LOCALES[lang]["hreflang"]}" href="{absolute(v["path"])}"/>')
            if DEFAULT_LANG in alts:
                out.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{absolute(alts[DEFAULT_LANG]["path"])}"/>')
        out.append("  </url>")
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
        if p["type"] not in CONTENT_TYPES:
            head.append(f"- [{p['title']}]({absolute(p['path'])}): {p.get('summary', p['description'])}")
    for kind, section in SECTIONS.items():
        listed = [p for p in public if p["type"] == kind]
        if not listed:
            continue
        head += ["", f"## {section['label']}", ""]
        for p in listed:
            head.append(f"- [{p.get('headline', p['title'])}]({absolute(p['path'])}): {p.get('summary', p['description'])}")
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
    rendered = {}
    seen = {}  # (lang, field, value) -> file
    for page in ALL_PAGES:
        out = build_page(page)
        if out is not None:
            rendered[page["path"]] = out
        lang = lang_of(page)
        for key in ("title", "description"):
            k = (lang, key, page[key])
            if k in seen:
                warn(f"{page['file']}: duplicate {key} with {seen[k]}")
            seen[k] = page["file"]
        # Two pages chasing the same query split Google's attention (Search Console showed this for
        # "vaultaire vs keepsafe" and "photo vault recovery"). One target keyword per page, per language.
        kw = page.get("keyword", "").strip().lower()
        if kw:
            k = (lang, "keyword", kw)
            if k in seen:
                warn(f"{page['file']}: keyword \"{kw}\" is already the target of {seen[k]}")
            seen[k] = page["file"]
    public = [p for p in ALL_PAGES if not p.get("draft") and p["path"] in rendered]
    build_sitemap(public)
    build_llms([p for p in public if lang_of(p) == DEFAULT_LANG], rendered)
    drafts = [p["file"] for p in ALL_PAGES if p.get("draft")]
    print(f"release: {RELEASE}{' (no appStoreId yet, CTAs stay on the waitlist)' if RELEASE == 'live' and not live() else ''}")
    print(f"pages: {len(rendered)}, in sitemap: {len(public)}, drafts (noindex): {', '.join(drafts) or 'none'}")
    if I18N:
        print("translated: " + ", ".join(f"{lang} {len(LPAGES[lang])}" for lang in I18N))
    for n in notes:
        print("note:", n)
    for p in problems:
        print("WARNING:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
