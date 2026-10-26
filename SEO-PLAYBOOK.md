# Darkroom SEO + AI visibility playbook

The operating manual for darkroom.buzz. Goal: rank in Google and Bing for the questions people ask about hiding and moving private photos, get cited by AI answer engines (ChatGPT search, Perplexity, Google AI Overviews, Claude, Copilot), and turn that traffic into App Store installs.

Written 22 October 2026. Update the dates and the backlog table as you go.

---

## 0. How the site works (read once)

- **`site.json` is the source of truth.** Release mode, App Store ID, campaign token, the facts block, and every page's title, description and dates.
- **`python3 tools/build.py`** renders everything from it: meta tags, Open Graph/Twitter, JSON-LD, the shared header/footer, breadcrumbs, bylines, the facts block, the guide list, App Store links, `sitemap.xml`, `llms.txt` and `llms-full.txt`. Run it after any change. It warns about titles over 60 characters, descriptions over 155, and duplicates.
- **Never hand-edit** anything between `<!-- build:… -->` and `<!-- /build:… -->`, or `sitemap.xml` / `llms*.txt`. The build overwrites them.
- **Preview locally:** `python3 tools/serve.py` → http://localhost:4321 (clean URLs like on Cloudflare).
- **Positioning:** "Your photos never get lost, even on a new phone." The bare word "darkroom" belongs to Bergen Co.'s photo editor (29k ratings), so we rank on problems and questions, not the brand. Use the entity phrase **"Darkroom photo vault"**. Keep the brand out of URLs and slugs until the trademark check is done.

---

## 1. Launch day: flip the site from waitlist to App Store

When Apple approves Darkroom and you release it:

1. In `site.json` set:
   - `"release": "live"`
   - `"appStoreId": "<numeric Apple ID>"` (App Store Connect → App Information → Apple ID)
   - `"providerToken": "<pt>"` (App Store Connect → Analytics → Campaigns → "Generate campaign link"; the `pt=` number)
2. Run `python3 tools/build.py`.
3. Check locally: every "Join the Early Tester List" button now says "Download on the App Store" and links to `apps.apple.com/app/apple-store/id…?pt=…&ct=<page>-<button>&mt=8`; the waitlist card is hidden; the Smart App Banner meta is present.
4. Add the App Store URL to `organization.sameAs` in `site.json` if you want it listed twice (the build already adds it once when live). Rebuild.
5. Commit, push, deploy. Then `python3 tools/indexnow.py`.
6. When real ratings exist (aim for 10+), consider adding `aggregateRating` to the MobileApplication JSON-LD in `tools/build.py`. Never invent or estimate it.

To go back to waitlist mode: set `"release": "waitlist"` and rebuild. It round-trips cleanly.

Every CTA has its own campaign token (`ct`), e.g. `home-hero`, `g-hide-photos-body`, `compare-nav`. App Store Connect → Analytics → Sources → Campaigns then shows which pages and buttons drive installs.

---

## 2. One-time setup (dashboards)

### Google Search Console
1. https://search.google.com/search-console → Add property → **Domain** → `darkroom.buzz`.
2. Verify with the DNS TXT record in Cloudflare (DNS → Records → Add TXT on `@`).
3. Sitemaps → submit `https://darkroom.buzz/sitemap.xml`.
4. URL Inspection → request indexing for `/`, `/best-photo-vault-apps-iphone`, `/guides/`, `/about`.

### Bing Webmaster Tools (ChatGPT search leans on Bing)
1. https://www.bing.com/webmasters → **Import from Google Search Console** (fastest), or add the site and verify by DNS.
2. Sitemaps → submit `https://darkroom.buzz/sitemap.xml`.
3. IndexNow is already wired: the key file `/7d2d95383a4c423d99b6b0cb4c75ca88.txt` deploys with the site, and `python3 tools/indexnow.py` pings Bing, Yandex, Seznam, Naver and Yep. Run it after every publish. Bing → IndexNow shows the submissions.

### Cloudflare bot settings (important: these can silently block AI crawlers)
In the Cloudflare dashboard for darkroom.buzz:
1. **AI Crawl Control** (or Security → Bots → "Block AI bots"): set to **allow** / do not block. If it's on, GPTBot, ClaudeBot, PerplexityBot and others get blocked no matter what robots.txt says.
2. **Managed robots.txt**: turn it **off**, so Cloudflare serves our `robots.txt` instead of its content-signals-only file. Then check https://darkroom.buzz/robots.txt shows our file, with the `Sitemap:` line.
3. **Bot Fight Mode / Super Bot Fight Mode**: if on, make sure **verified bots are allowed**. Bot Fight Mode can challenge crawlers; turn it off if Search Console or Bing report crawl errors.
4. **Analytics**: the site uses Google Analytics (`gaMeasurementId` in `site.json`, added to every page by the build). If you add or remove an analytics tool, update the "This website" section of `/privacy` in the same change.
5. After deploy, check that repo-only files aren't served (they're listed in `.assetsignore`): `curl -I https://darkroom.buzz/site.json` should return 404. New repo-only files must be added to `.assetsignore`, because the Worker serves the whole folder.

### App Store Connect URLs (after this branch is deployed)
- **Support URL:** `https://darkroom.buzz/support`
- **Marketing URL:** `https://darkroom.buzz/`
- **Privacy Policy URL:** `https://darkroom.buzz/privacy` (App Privacy section, and in the description's last lines)
- Then merge the `move-to-darkroom-buzz` branch in `~/dev/darkroom-site` and push it, so old GitHub Pages links redirect.

---

## 3. Off-site entity consistency

AI engines build their picture of Darkroom from every place it's mentioned. Use the **same name and the same sentence** everywhere:

> **Darkroom photo vault** — an iPhone and iPad app that hides photos, videos and notes behind a pattern only you know. Encrypted on your device, backed up to your own iCloud. No ads, no accounts.

| Where | What to do | Status |
|---|---|---|
| App Store | Name "Darkroom: Private Photo Vault"; marketing URL darkroom.buzz | ☐ |
| X profile | Name "Darkroom photo vault", bio = the sentence above, link darkroom.buzz | ☐ |
| GitHub | Profile/org README with the sentence and link; link from darkroom.buzz/about once public | ☐ |
| AlternativeTo | Add Darkroom as an alternative to Private Photo Vault, Keepsafe, Hidden album; same sentence | ☐ |
| Product Hunt | Launch page with the sentence; schedule after App Store launch | ☐ |
| Reddit | Profile bio says you're the developer of Darkroom photo vault | ☐ |
| Privacy Guides forum | Account bio, same | ☐ |

When something changes (pricing, features), change `site.json` facts first, rebuild, then update these.

---

## 4. Daily (15 minutes)

Answer **one** real question about hiding, locking, backing up or moving private photos.

- Where: r/iphone, r/ios, r/privacy, r/apple, Apple Support Community, Quora. Search "hidden album", "photo vault", "new iPhone photos missing", "keepsafe".
- How: answer the question fully in the reply itself. Most answers shouldn't mention Darkroom at all.
- **Always disclose** when you mention Darkroom: "I'm the developer of Darkroom, a photo vault app, so I'm biased, but…".
- Link only when the link genuinely answers more than the reply can (usually a guide, not the homepage). Follow each subreddit's self-promotion rules.
- Note the exact question wording in the backlog (section 10). Real questions are the best guide topics.

---

## 5. Weekly (about 4–5 hours)

| Day | Task | Time |
|---|---|---|
| **Monday** | Pick the next keyword from the backlog. Google it in a private window: note People Also Ask questions, what the top 5 results cover, and what they miss. Check Search Console for related queries. | 30 min |
| **Tuesday–Wednesday** | Write and publish one guide with `templates/guide.html` (checklist in section 9). | 2–3 h |
| **Thursday** | Improve one older page using Search Console (section 6). | 45 min |
| **Friday** | One action to earn a link (list below). | 45 min |

Friday link actions, rotate through:
- Submit/update AlternativeTo and Product Hunt listings.
- Show HN once the app is live: "Show HN: Darkroom – encrypted photo vault for iPhone with a 5×5 bolt pattern lock". Be ready to answer crypto questions.
- Post in the Privacy Guides forum's community software section; be open about being the developer.
- Find "best photo vault apps" and "Keepsafe alternatives" articles (Google: `best photo vault app iphone 2026`, `keepsafe alternatives`). Email the writer a short, specific pitch: what's different (encrypted backup that restores, recovery phrase, Data Not Collected), a link to the comparison page, and an offer of a Pro code for testing.
- Answer a journalist request (Qwoted, Featured) about phone privacy.

---

## 6. Thursday: improve an older page with Search Console

1. Search Console → Performance → Pages. Pick a page with impressions but few clicks.
2. Click it → Queries. Look for queries at **positions 8–20**: Google already thinks the page is relevant.
3. Do one or more:
   - Rewrite the title (≤60) and description (≤155) in `site.json` to match the main query's wording.
   - Add a section or FAQ item that directly answers a query you don't cover yet. Answer in the first sentence.
   - Add an internal link to it from a related guide.
4. Update `"updated"` in `site.json`, rebuild, deploy, run `python3 tools/indexnow.py <path>`, and request indexing in URL Inspection.
5. Log the change (date, page, what changed) at the bottom of this file, so you can see what worked a month later.

---

## 7. Monthly (first Monday, about 1 hour)

1. **Search Console review:** queries and pages, last 28 days vs previous. Note the top 10 queries, any page at positions 8–20 (Thursday candidates), and pages that dropped.
2. **Refresh the comparison page** (`/best-photo-vault-apps-iphone`): re-run the App Store data pull (ratings, last update, privacy labels, prices) and update the table, the "Short answer" counts and `"updated"` in `site.json`. Also update the homepage summary table. Claude can do this: "Refresh the comparison data on darkroom.buzz following SEO-PLAYBOOK.md section 7."
3. **AI visibility check:** in a private/logged-out window, ask ChatGPT (search on), Perplexity, Google (AI Overview), Claude and Copilot the questions below. For each, note whether darkroom.buzz is cited, whether Darkroom is mentioned, and which sites are cited instead. Log it in section 12.
   - How do I hide photos on my iPhone?
   - Is the iPhone Hidden album private?
   - How do I move a photo vault app to a new iPhone without losing photos?
   - What's the best photo vault app for iPhone?
   - What are good Keepsafe alternatives without an account?
   - What is a decoy vault?
   - Photo vault app without ads or subscription?
4. **Check `llms.txt`** still reads correctly: https://darkroom.buzz/llms.txt.
5. **Update the backlog** statuses (section 10).

---

## 8. KPIs

| When | Measure | Target | Where |
|---|---|---|---|
| Week 4 | Pages indexed | All public pages in the sitemap | Search Console → Pages; Bing → Site Explorer |
| Week 4 | Impressions | Growing week over week; first guide queries appear | Search Console → Performance |
| Month 3 | Clicks on guides | 300+/month across guides | Search Console, filter page contains `/guides/` |
| Month 3 | AI citations | darkroom.buzz cited for at least 2 of the 7 monthly questions | Section 12 log |
| Month 6 | Rankings | Top 10 for several guide keywords | Search Console → average position per query |
| Month 6 | Installs from the site | Steady campaign-link installs; know which pages drive them | App Store Connect → Analytics → Sources → Campaigns |

These are starting targets, not forecasts. Adjust them after month 1 with real data.

---

## 9. Checklist: publish a new guide

1. **Keyword:** pick it from the backlog (section 10). Write down the exact question and 3–5 People Also Ask questions.
2. **Copy the template:** `cp templates/guide.html guides/<slug>.html`. The slug describes the question, no brand name: `how-to-hide-videos-on-iphone`.
3. **Add it to `site.json` `pages`:** `type: "guide"`, `path: "/guides/<slug>"`, `ct` (short, e.g. `g-hide-videos`), `crumb`, `title` (≤60, the main query near the start), `headline`, `description` (≤155, answers the question), `summary`, `published`, `updated`, `image`, and `"draft": true`.
4. **Write it** (1,200–2,000 words):
   - Short answer box: 2–3 sentences that stand alone. This is what gets quoted.
   - Every H2 is a question or a task; the answer is the first 1–2 sentences under it.
   - Exact menu paths in `<span class="path">`, numbered steps in `<ol class="steps">`.
   - Tables with explicit numbers and dates where things compare.
   - Facts about Apple features: link the support.apple.com source.
   - Mention Darkroom only where it honestly fits, and say "which we make".
   - 2–3 internal links (other guides, the comparison page).
   - FAQ: 4–6 real People Also Ask questions. FAQPage JSON-LD is generated from it.
5. **Screenshots:** iOS screenshots from a real device on the current iOS, cropped to the relevant part, saved as JPEG ~560 px wide in `/assets/guides/`, with real alt text and `width`/`height` set.
6. **Build:** `python3 tools/build.py`. Fix any warnings. Preview with `python3 tools/serve.py`.
7. **Review:** check every step on a real iPhone. Then set `"draft": false` and rebuild (adds it to the sitemap, llms.txt and the guides index, removes noindex).
8. **Internal links in:** link to the new guide from at least 2 existing pages (related lists, a sentence in a relevant guide).
9. **Deploy**, then `python3 tools/indexnow.py /guides/<slug>`.
10. **Google:** Search Console → URL Inspection → paste the URL → Request indexing.
11. **Update the backlog** status and add the guide to the Reddit/Quora answer bank.

---

## 10. Keyword backlog

Sources for new rows: Search Console queries, Google autocomplete and People Also Ask, competitor 1★ review themes (subscription/paywall 67 mentions, lost photos 47, video 40, backup/new phone 31, locked out 27, crashes 22, ads 17), and the questions you answer daily.

| # | Keyword / question | Intent | URL | Status |
|---|---|---|---|---|
| 1 | How to hide photos on iPhone (all methods, Hidden album limits) | How-to | /guides/how-to-hide-photos-on-iphone | Live 22 Oct 2026, check menu paths on a device |
| 2 | Is the iPhone Hidden album actually private? | Question | /guides/is-iphone-hidden-album-private | Live 22 Oct 2026, check menu paths on a device |
| 3 | How to move a private photo vault to a new iPhone without losing photos | How-to | /guides/move-photo-vault-to-new-iphone | Live 22 Oct 2026, check menu paths on a device |
| 4 | Private Photo Vault lost my photos: what to do | Problem | /guides/photo-vault-lost-photos | Live 22 Oct 2026, check menu paths on a device |
| 5 | Best photo vault apps for iPhone 2026 | Comparison | /best-photo-vault-apps-iphone | Live (refresh monthly) |
| 6 | Keepsafe alternatives with no account | Comparison | /guides/keepsafe-alternatives | Live 22 Oct 2026, check menu paths on a device |
| 7 | How to lock photos on iPhone with Face ID or a pattern | How-to | /guides/lock-photos-iphone-face-id | Live 22 Oct 2026, check menu paths on a device |
| 8 | What is a decoy vault | Definition | /guides/what-is-a-decoy-vault | Live 22 Oct 2026, check menu paths on a device |
| 9 | How to hide videos on iPhone | How-to | /guides/how-to-hide-videos-on-iphone | Live 22 Oct 2026, check menu paths on a device |
| 10 | Photo vault apps without subscriptions or ads | Comparison | /guides/photo-vault-no-subscription-no-ads | Live 22 Oct 2026, check menu paths on a device |
| 11 | Forgot photo vault password: what now | Problem | /guides/forgot-photo-vault-password | Live 22 Oct 2026, check menu paths on a device |
| 12 | How encrypted photo vaults work (Argon2id/AES-GCM in plain English) | Explainer | /guides/how-encrypted-photo-vaults-work | Live 22 Oct 2026, check menu paths on a device |
| 13 | Are photo vault apps safe? | Question | /guides/are-photo-vault-apps-safe | Live 22 Oct 2026, check menu paths on a device |
| 14 | How to hide photos on iPad | How-to | /guides/how-to-hide-photos-on-ipad | To do |
| 15 | Calculator vault apps: do they actually hide anything? | Question | /guides/calculator-vault-apps | To do |
| 16 | How to hide apps on iPhone (iOS 18+) | How-to | /guides/how-to-hide-apps-on-iphone | To do |
| 17 | Vaultaire vs Keepsafe (Search Console: 13 impressions, position 9.5, Oct 2026) | Comparison | /guides/vaultaire-vs-keepsafe | Live 26 Oct 2026 |

Statuses: To do → Drafting → Draft, needs review → Live → Refreshed (date).

---

## 11. Writing rules (match the App Store voice)

- Short, plain sentences. "Photos only you can see." "Backed up. Still private."
- Specific and checkable: numbers, dates, menu paths, sources. No "military-grade", "bank-level", "best-in-class", "revolutionary".
- No fake social proof, no invented ratings or testimonials, no claims about competitors that aren't in their own listing or a dated source.
- Never copy competitor text or screenshots.
- Say what each option doesn't protect, including Darkroom (see the honest threat model on the homepage).
- If a fact about Darkroom changes, change it in `site.json` first.

---

## 12. Logs

### AI visibility (monthly)

| Date | Engine | Question | darkroom.buzz cited? | Darkroom mentioned? | Sites cited instead |
|---|---|---|---|---|---|
| | | | | | |

### Page changes (Thursday)

| Date | Page | Change | Result after 4 weeks |
|---|---|---|---|
| | | | |

---

## 13. Screenshots needed for the guides

The App Store screenshots in `~/dev/darkroom/AppStore/screenshots/iphone/` are reused for Darkroom shots (`/assets/guides/darkroom-*.jpg`). These iOS screenshots still need to be taken on a real iPhone running iOS 26 (they're marked `SCREENSHOT TODO` in the HTML):

| File | Shows | Guide |
|---|---|---|
| `ios-photos-hide-menu.jpg` | Photos: touch-and-hold menu on a photo, "Hide" visible | How to hide photos |
| `ios-settings-photos.jpg` | Settings › Apps › Photos: "Use Face ID" and "Show Hidden Album" | How to hide photos |
| `ios-hidden-album-locked.jpg` | Collections › Utilities with the Hidden album locked | Hidden album private? |
| `darkroom-restore.jpg` | Darkroom "Restore your vault" screen on a new iPhone | Move to a new iPhone |
| (optional) `ios-require-face-id.jpg` | Touch-and-hold on the Photos icon showing "Require Face ID" | How to hide photos |
| (optional) `ios-notes-lock.jpg` | A note with a photo and the Lock option | How to hide photos |

Use sample photos only. Crop out the status bar if it shows personal info.
