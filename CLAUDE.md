# darkroom.buzz

Static marketing site for Darkroom, an encrypted iPhone/iPad photo vault (app repo: `~/dev/darkroom`). Plain HTML/CSS/JS, no framework. Deployed from GitHub as a Cloudflare Worker serving the repo folder as static assets (`wrangler.jsonc`). Everything in the folder is public unless it's listed in `.assetsignore`, so add new repo-only files there. Fonts are self-hosted in `assets/fonts/`; don't add Google Fonts. The only third-party script is the Google Analytics tag, added to every page by the build from `site.json` `gaMeasurementId` (the privacy page's website section describes it). Don't add others without updating `/privacy`.

## Ground rules
- **Never push, merge or deploy without asking Milan.** Work on a branch, commit in small logical commits.
- Read `SEO-PLAYBOOK.md` before SEO or content work. It has the weekly routine, the publish-a-guide checklist and the keyword backlog.

## How the site is built
- `site.json` is the source of truth: release mode (`waitlist` / `live`), App Store ID, campaign token, the facts block, and every page's title, description, dates and draft flag.
- After any change run `python3 tools/build.py`. It fills the `<!-- build:NAME -->…<!-- /build:NAME -->` regions (meta, jsonld, header, footer, breadcrumbs, byline, facts, status, guide-list), rewrites every `<a data-cta="…">` to the waitlist or an App Store campaign link (`ct` = page `ct` + button name), toggles `data-release-only` blocks, and writes `sitemap.xml`, `llms.txt`, `llms-full.txt`. Never hand-edit those regions or generated files.
- The build must finish with no warnings: titles ≤ 60 characters, descriptions ≤ 155, no duplicates.
- Preview: `python3 tools/serve.py` (clean URLs, like Cloudflare: `/about` → `about.html`).
- New pages: copy the skeleton of an existing subpage (or `templates/guide.html` for guides), add the page to `site.json`, build.
- URLs have no `.html` and no brand name in the slug. Links between pages are root-relative (`/guides/…`).
- After publishing: `python3 tools/indexnow.py <path>` (Bing and other IndexNow engines).

## Design
- Follow `design-system/darkroom/MASTER.md`. Tokens live in `styles.css` (`:root` and `[data-theme="light"]`). Subpage components are in `pages.css` and use only those tokens.
- Archivo Narrow (uppercase) for headings and buttons, Plus Jakarta Sans for prose, DM Mono for labels, specs and dates.
- Mobile-first: test at 375 px, no horizontal page scroll; wide tables scroll inside `.data-table-wrap`.
- Inline SVG icons with `aria-hidden="true"`, never emoji as icons. One `<h1>` per page, no skipped heading levels.

## Content and voice
- Match the App Store voice: short, plain sentences ("Photos only you can see."). Specific numbers, dates and menu paths.
- **No unverifiable claims**: no invented testimonials, ratings, user counts, audits or performance numbers. No `aggregateRating` until real App Store ratings exist.
- Facts about Darkroom come from `site.json` `facts` (also mirrored in `llms.txt` and JSON-LD). If the app changes, update `site.json` first. Check claims against the app code in `~/dev/darkroom` when unsure (e.g. the free tier is in `App/Core/AppEnvironment.swift`).
- Competitor statements must be factual, dated and sourced (their App Store listing or a cited page). Never copy competitor text or screenshots.
- Guides: direct answer in the first 1–2 sentences under every heading, a "Short answer" box, steps, FAQ, 2–3 internal links, a named author and dates (from `site.json`), and Darkroom mentioned only where it honestly fits ("which we make"). New guides start with `"draft": true` (noindex, out of the sitemap) until Milan reviews them.
- Use "Darkroom photo vault" as the entity phrase; "darkroom" alone belongs to an unrelated photo editor.

## Launch switch
Set `"release": "live"`, `"appStoreId"` and `"providerToken"` in `site.json`, then build. Details: `SEO-PLAYBOOK.md` section 1.
