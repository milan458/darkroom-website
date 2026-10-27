# Nocturne for the web: design system

The website copies the Noxium app's approved Nocturne look (Liquid Night × Porcelain). This file is the reference for every page on getnoxium.app. Tokens live in `styles.css` (`:root`, with Light values under `@media (prefers-color-scheme: light)`); subpage components are in `pages.css` and use only those tokens. There is no theme toggle: the site follows the device, like the app.

Notes on this build:
- The token layer, components and motion below are implemented in `styles.css`; the hero bolt pad, reveals, sticky bar and cursor light are in `app.js`.
- The App Store badge on the homepage is a placeholder until Apple's official artwork is added (live mode only).
- Homepage photos in `assets/home/` are generated colour-field placeholders until rights-cleared photos are supplied.
- Google Analytics is still on every page (site.json `gaMeasurementId`), so the privacy section uses the "The app collects nothing." copy and has no live request list.

## 2. What Nocturne for the web is (keep in mind)

Liquid Night × Porcelain, the same system as the app. A true-black canvas in Dark Mode and warm porcelain in Light Mode, chosen by the visitor's device. Photos edge to edge in a square grid with 2 px gaps. Controls float as clear Liquid Glass capsules over scrims. Titles speak in a quiet editorial serif (Instrument Serif, regular and italic, never bold); everything else is the system font (SF Pro on Apple devices). Red "safelight" is rare: the "Locked" dot, the favourite heart, the + button, errors. Primary buttons are **ink** capsules: white on black in Dark, black on porcelain in Light. Motion moves in depth: things press in, lift and settle along z. Nothing slides sideways for its own sake.

The one thing a visitor should remember: *I drew a shape, and it opened.*

---

## 3. Files you will touch

| File | Change |
|---|---|
| `styles.css` | Replace the token layer (§4) and the homepage components. Delete the machined-plate, film-strip, simulator and amber styles once unused. |
| `pages.css` | Restyle subpage components with the new tokens (§12). Class names stay. |
| `assets/fonts/` + `fonts.css` + `LICENSES.md` | Add Instrument Serif (regular, italic) and Inter Tight; remove Plus Jakarta Sans and Archivo Narrow after a repo-wide search shows no use (§5). |
| `index.html` | Rebuild the homepage markup per §9. Keep build regions, `data-cta`, `data-release-only`, FAQ structure, IDs. |
| `partials/header.html`, `partials/footer.html` | New glass capsule header and Nocturne footer (§8.1, §8.12). |
| `templates/guide.html` | Same skeleton, new classes only where needed. |
| `app.js` | Remove simulator, `#pattern-canvas` and theme toggle code. Add the bolt pad (§10), reveal fallback (§11.4), cursor light, request list (§9.8), sticky install bar (§8.10). Keep mobile nav, comparison filters, install dialog, copy buttons, waitlist. |
| `design-system/darkroom/MASTER.md` | Replace with `design-system/nocturne/MASTER.md` containing §2–§8 of this document; update the "Design" lines in `CLAUDE.md` to point to it and to the new fonts. |
| `_headers` | Add `Cache-Control: public, max-age=31536000, immutable` for `/assets/fonts/*`. |
| `assets/home/` (new) | Homepage photo wall images (§13). |

---

## 4. Tokens — replace the `:root` / `[data-theme="light"]` layers in `styles.css`

Dark values live in `:root`; light values in `@media (prefers-color-scheme: light) { :root { … } }`. Delete `[data-theme="light"]` rules (D2). Add `color-scheme: dark light;` on `:root` and two `<meta name="theme-color">` tags (`#000000` with `media="(prefers-color-scheme: dark)"`, `#FAF9F6` with `media="(prefers-color-scheme: light)"`) through the build's meta region.

### 4.1 Colour

| Token | Dark | Light | Use |
|---|---|---|---|
| `--bg` | `#000000` | `#FAF9F6` | Page background |
| `--panel` | `#1C1C1E` | `#FFFFFF` | Cards, alternate sections (decoy, privacy), note tiles |
| `--line` | `#2C2C2E` | `#DEDBD3` | Hairlines (0.5 px), card inner borders |
| `--text` | `#FFFFFF` | `#111111` | Primary text, icons, trails |
| `--muted` | `#98989F` | `#6B6B6B` | Secondary text on plain ground (6.9:1 / 5.2:1) |
| `--text-2` | `#C7C7CC` | `#3D3D3D` | Body copy, secondary text **on glass** |
| `--safelight` | `#FF453A` | `#C8372B` | "Locked" dot, heart, + button, wrong-pattern state |
| `--safelight-text` | `#FF6961` | `#C8372B` | Error text |
| `--ok` | `#30D158` | `#2F6B4A` | "Unlocked", "Backed up", success trail |
| `--ink` | `#FFFFFF` | `#111111` | Primary button fill, App Store badge plate |
| `--on-ink` | `#000000` | `#FAF9F6` | Text on ink |
| `--fill` | `rgba(255,255,255,.07)` | `rgba(255,255,255,.55)` | Rows inside glass groups, recovery-phrase chips |
| `--tile` | `#0D0D0F` | `#F1EFE9` | Encrypted ("cipher") tiles and band |
| `--tile-text` | `#4A4A52` | `#B4AE9F` | Cipher characters (decorative, `aria-hidden`) |
| `--stage-1` / `--stage-2` / `--stage-3` | `#18181C` / `#000000` / `#000000` | `#FFFFFF` / `#FAF9F6` / `#EFECE5` | Radial gradient of the lock stage |
| `--glow` | `rgba(255,255,255,.075)` | `rgba(255,186,120,.14)` | Cursor light |
| `--scrim` | `rgba(0,0,0,.55)` | `rgba(250,249,246,.7)` | Radial scrim behind glass cards over photos |

**Lock stage background** (hero, final CTA, stage cards):
`radial-gradient(ellipse 70% 60% at 72% 48%, var(--stage-1) 0%, var(--stage-2) 62%, var(--stage-3) 100%)` — on phones centre it: `at 50% 50%`.

**Bolts:**

| Token | Dark | Light |
|---|---|---|
| `--bolt-ring` | `rgba(255,255,255,.45)` | `#A9A395` |
| `--bolt-on` | `#FFFFFF` | `#111111` |
| `--bolt-halo` | `rgba(255,255,255,.08)` | `rgba(17,17,17,.07)` |
| `--bolt-glow` | `rgba(255,255,255,.55)` | none (transparent) |

Amber is **retired** from the site. Every `--amber` use moves to `--text` (focus, eyebrows, highlights) or `--muted`. The waitlist "pulse" dots become `--ok`.

### 4.2 Liquid Glass

```css
.glass {
  background: var(--glass-bg);
  -webkit-backdrop-filter: blur(30px) saturate(180%);
  backdrop-filter: blur(30px) saturate(180%);
  box-shadow: inset 0 1px 0 var(--glass-hi), 0 0 0 .5px var(--glass-line), 0 12px 32px var(--glass-shadow);
}
```

| Token | Dark | Light |
|---|---|---|
| `--glass-bg` | `rgba(255,255,255,.12)` | `rgba(255,255,255,.5)` |
| `--glass-hi` (top highlight) | `rgba(255,255,255,.38)` | `rgba(255,255,255,.95)` |
| `--glass-line` (hairline) | `rgba(255,255,255,.22)` | `rgba(0,0,0,.10)` |
| `--glass-shadow` | `rgba(0,0,0,.40)` | `rgba(60,50,30,.12)` (and saturate 170%) |

- Fallbacks: `@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)))` and `@media (prefers-reduced-transparency: reduce)` → `background: var(--panel); box-shadow: 0 0 0 1px var(--line);`.
- Do **not** add SVG displacement/refraction filters: Safari ignores them and most installers are on Safari. The blur version above is the design.
- No more than four glass elements visible at once. Glass is chrome only (nav, buttons, cards over photos, the sticky bar). Never put body copy on glass without a scrim behind it.
- Glass over photos always sits on a scrim: top `linear-gradient(180deg, var(--bg) 38%, transparent)`, bottom `linear-gradient(0deg, var(--bg) 8%, transparent)`, centre `radial-gradient(ellipse 46% 40% at 50% 54%, var(--scrim), transparent 72%)`.

### 4.3 Radii, sizes, shadows

| Token | Value |
|---|---|
| `--r-capsule` | `999px` (nav, buttons, chips, sticky bar, search/email fields) |
| `--r-card` | `28px` (content cards, pricing, comparison wrapper, band) |
| `--r-group` | `22px` (glass groups of rows, privacy request list) |
| `--r-sheet` | `34px` (vault card, install dialog) |
| `--r-chip` | `12px` (recovery-phrase chips, small icon tiles) |
| Photo grids | `0` (edge-to-edge tiles, 2 px gaps); a grid inside a card gets `14px` on its wrapper only |
| Button heights | primary/secondary `50px`; nav button `40px`; hero demo button `44px`; sticky "Get" `46px`; App Store badge `54px` desktop, `46px` phone |
| Phone frame (decoy section) | `280 × 560`, radius `46px`; phone width ≤ 760 px: `240 × 500` |
| Phone ring | Dark `0 0 0 8px #161618, 0 0 0 9px #3A3A3C, 0 34px 80px rgba(0,0,0,.7)`; Light `0 0 0 8px #FFF, 0 0 0 9px #DEDBD3, 0 34px 80px rgba(60,50,30,.18)` |
| Card | `background: var(--panel); border-radius: 28px; box-shadow: inset 0 0 0 .5px var(--line); padding: 28px` (pricing `36px`) |
| Focus ring | `outline: 2px solid var(--text); outline-offset: 3px;` on `:focus-visible` only, every interactive element |
| Selection | `::selection { background: color-mix(in srgb, var(--safelight) 35%, transparent); }` |

### 4.4 Spacing and layout

- Container: `max-width: 1240px; margin-inline: auto; padding-inline: 32px` (≤ 760 px: `20px`).
- Section padding: `168px` top / `150px` bottom on desktop; ≤ 760 px: `96px` / `88px`.
- Section head → content: `64px` (≤ 760 px: `40px`). Eyebrow → title: `18px`.
- Two-column rows use `display:flex; flex-wrap:wrap; gap: 28px 64px` with `flex: 1 1 560px` / `flex: 0 1 400px` so they stack on phones with no media query.
- Card grids: `repeat(auto-fit, minmax(min(<min>px, 100%), 1fr))`.
- Breakpoints (only these): `999px` (bento drops to one column), `760px` (phone layout: nav links hide, QR hides, sticky bar appears, phones shrink).

---

## 5. Type

### 5.1 Fonts (self-hosted)

- **Instrument Serif** Regular and Italic (SIL OFL), from `github.com/google/fonts`, path `ofl/instrumentserif/` (`InstrumentSerif-Regular.ttf`, `InstrumentSerif-Italic.ttf`, `OFL.txt`). Subset to latin and latin-ext WOFF2 with `pyftsubset` (`pip install fonttools brotli`), named like the existing files: `instrument-serif-latin-400-normal.woff2`, `instrument-serif-latin-400-italic.woff2`, plus `-latin-ext-` versions with the matching `unicode-range`. `font-display: swap`. Preload only `instrument-serif-latin-400-normal.woff2`.
- **Inter Tight** (SIL OFL), `ofl/intertight/`, variable weight 400–600, latin + latin-ext. It is only the fallback for non-Apple devices (the mockups use it as a stand-in for SF Pro on Windows/Android). Apple devices never download it.
- **DM Mono** (already hosted): recovery-phrase words, the request list, cipher text, the FAQ numbers, technical details. Nothing else.
- Remove Plus Jakarta Sans and Archivo Narrow files, `@font-face` rules and licence entries **only after** `grep -rn "Jakarta\|Archivo" --include=*.html --include=*.css --include=*.js .` returns nothing outside `.agents/`.
- Add Instrument Serif and Inter Tight to `assets/fonts/LICENSES.md` with the OFL text.
- Never set `font-weight` other than 400 or `font-style: oblique` on Instrument Serif. **It has no bold.**
- Metric fallback to stop layout shift: define `@font-face { font-family: "Instrument Serif Fallback"; src: local("Georgia"); size-adjust: …; ascent-override: …; descent-override: …; }` with values computed from the font files (`fontTools`: `size-adjust = (IS xHeight / IS unitsPerEm) / (Georgia xHeight / Georgia unitsPerEm)`; ascent/descent from `hhea`). Put it after Instrument Serif in the stack.

```css
--font-serif: "Instrument Serif", "Instrument Serif Fallback", Georgia, serif;
--font-sans: -apple-system, BlinkMacSystemFont, "Inter Tight", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
--font-mono: "DM Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
```

Never upload or reference SF Pro font files (Apple's licence forbids it); `-apple-system` gets it from the OS.

### 5.2 Scale

| Role | Font | Size | Line height | Notes |
|---|---|---|---|---|
| Hero h1 | Serif | `clamp(50px, 6.4vw + 12px, 104px)` | `.94` | Line 1 regular, line 2 *italic*; letter-spacing `-.005em` |
| Section h2 | Serif | `clamp(44px, 5.6vw + 8px, 88px)` | `.95` | Ends on an *italic* phrase (see copy deck) |
| Privacy h2 | Serif | `clamp(48px, 6.6vw + 8px, 104px)` | `.94` | Second sentence italic in `--muted` |
| Final CTA h2 | Serif | `clamp(60px, 8.6vw + 12px, 136px)` | `.9` | |
| Vault card title | Serif | `clamp(44px, 5vw, 64px)` | `1` | |
| Card / step title (h3) | Serif | `30–32px` (phone `26px`) | `1.05` | |
| Step numerals | Serif *italic* | `80px` | `.8` | `--muted` |
| Wordmark | Serif | `24px` nav, `34px` footer | `1` | "Noxium" + italic full stop in `--muted` |
| Lede | Sans 400 | `19px` hero / `18px` sections (phone `16–17px`) | `1.5–1.55` | `--text-2`, `max-width: 36–46ch` |
| Body | Sans 400 | `15–16px` | `1.6` | |
| Eyebrow | Sans 600, UPPERCASE | `11px` | — | `letter-spacing: .16em`, `--muted` (on glass `--text-2`) |
| Status line | Sans 600, UPPERCASE | `11px` | — | 6 px dot + 8 px gap |
| Nav links | Sans 600 | `14px` | — | `--text-2` |
| Buttons | Sans 600 | `15–16px` | — | |
| Captions | Sans 400 | `12–13px` | `1.45` | `--muted` |
| FAQ question | Sans 600 | `19px` (phone `17px`) | `1.3` | |
| Mono | DM Mono 400 | `13px` lists, `14px` chips, `11px` cipher tiles | `1.55` | |

Rules:
- Serif for page/section/card titles, the wordmark and the hero prompt only. Never for body, buttons or labels.
- Uppercase only for eyebrows and status lines. **Never put "iPhone" in an uppercase element** (Apple's rule: never "IPHONE"). Write "Encrypted on device", not "ENCRYPTED ON YOUR iPhone".
- `text-wrap: balance` on h1/h2, `text-wrap: pretty` on paragraphs.

---

## 6. Icons

Inline SVG, `viewBox="0 0 24 24"`, `fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round`, `aria-hidden="true"`. Sizes 16–20 px (`+` button 24 px at stroke 2.2). Paths used in the mockups:

- Lock: `<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>`
- Search: `<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>`
- Plus: `<path d="M12 5v14M5 12h14"/>`
- Check: `<path d="M5 12.5l4.5 4.5L19 7.5"/>`
- Share/import: `<path d="M12 3v12M7 8l5-5 5 5"/><path d="M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/>`
- No ads: `<circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/>`
- No analytics: `<path d="M4 20h16M7 16v-4M12 16V8M17 16v-6M3 3l18 18"/>`
- Face ID: `<path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2M9 9v1M15 9v1M12 9v4h-1M9 16c1.5 1 4.5 1 6 0"/>`
- Menu: `<path d="M5 9h14M5 15h14"/>`
- Play (filled, 10–12 px): `<path d="M7 4l13 8-13 8z" fill="currentColor" stroke="none"/>`
- Heart (filled, `--safelight`): `<path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"/>`

No emoji anywhere.

---

## 7. Apple marketing rules that shape the design

- **App Store badge:** Apple's official artwork only (download from Apple's Marketing Resources), black badge on Light, white badge on Dark, never recoloured, tilted, animated or 3D. At least 40 px tall; clear space ≥ ¼ of its height. **One badge per layout**: hero and final CTA only. Every other install button is an ink capsule with text.
- **Devices:** no rendered iPhone, no Dynamic Island, no fake status bar, no tilt, no 3D. The decoy section's phones are plain rounded rectangles with a neutral ring (§4.3) and nothing Apple-specific.
- **Naming:** "Noxium for iPhone and iPad". Never "IPHONE". Requirements ("iOS 17 or later") only in small print and the FAQ, never in a headline.
- **Credit line** in the footer: "Apple, the Apple logo, iPhone, iPad and Face ID are trademarks of Apple Inc., registered in the U.S. and other countries. App Store is a service mark of Apple Inc."
- **Screen content:** fictional and rights-cleared imagery only (§13). No real people's faces.

---

## 8. Components

### 8.1 Header (`partials/header.html` and the homepage header)
- Wrapper: `position: sticky; top: 0; height: 0; z-index: 50` (takes no space, so the hero runs under it). Inside, centred, `padding: 18px 16px 0`.
- `nav.glass`: capsule, height `56px`, padding `0 8px 0 22px`, gap `28px`. Contents: wordmark link → `/`; links (§D7) `14px/600 --text-2`, gap `22px`; ink button "Get Noxium" (`data-cta="nav"`, `data-label-waitlist="Join the beta"`, `data-label-live="Get Noxium"`), height `40px`, padding `0 18px`, `14px`.
- ≤ 760 px: links hide; a 44 × 38 menu button (`aria-label="Menu"`, `aria-expanded`) opens the existing mobile drawer, restyled as a glass sheet (`--r-sheet`, 16 px from the edges, links `17px/600`, 52 px rows, hairline separators). When the sticky install bar (§8.10) is showing, the nav hides its ink button so there is only one install button on screen.
- Subpages: same header; the current page's link gets `aria-current="page"` and `--text` colour with a 1.5 px underline 4 px below.

### 8.2 Buttons
| Kind | Spec |
|---|---|
| Ink (primary) | `height 50px; padding 0 24px; radius 999; background var(--ink); color var(--on-ink); 16px/600`. One per view. Hover `opacity: .88`; active `transform: scale(.97)` (100 ms). |
| Glass (secondary) | `.glass` + `height 50px; padding 0 22px; radius 999; 15px/600 --text`. Same press scale. |
| Small glass | Demo button: `height 44px; 14px`, leading 12 px play glyph. |
| Text link | `--text`, underline on hover, `text-underline-offset: 3px`. |
| Disabled | `opacity: .45`, no pointer events. |

### 8.3 App Store badge and QR (live mode only)
- Row: `display:flex; flex-wrap:wrap; align-items:center; gap:22px`. Badge (§7), `54px` tall, `data-cta="hero-badge"` (no `data-label-*` so the build leaves the image alone).
- QR block (hidden ≤ 760 px): white tile `64 × 64`, radius `12px`, padding `5px`, QR as inline SVG (`shape-rendering: crispEdges`) generated from the real App Store campaign URL for `ct=home-qr` once `appStoreId` exists (add a tiny step to `build.py` or commit a generated SVG; no runtime library). Beside it: "Scan with your iPhone camera" `14px/600`, then "Opens Noxium on the App Store" `13px --muted`. `role="img"` + `aria-label` on the SVG.

### 8.4 Waitlist form (waitlist mode)
- Row: email field + ink submit, `gap: 8px`, wraps on phones (button full width).
- Field: `.glass` capsule, height `54px`, `padding: 0 20px 0 46px`, mail icon at left 18 px, `16px` text (16 px stops iOS zoom), placeholder `--muted`, `<label>` visually hidden ("Email address").
- Submit: ink capsule `54px` "Get the beta".
- Hint below: `13px --muted` "Opens in Apple TestFlight · No spam, ever · Privacy policy".
- Error: `14px/600 --safelight-text`, `aria-live="polite"`.
- Success (`#waitlist-success`): glass card radius `22px`, padding `24px`: status line with `--ok` dot "You're on the list"; serif `30px` "Thanks! You're in."; body `15px`; ink "Join the beta on TestFlight"; perk rows (DM Mono labels `12px --muted`, values `15px`); text button "Use a different email". Enters with the chrome-settle motion (§11.1 M6).

### 8.5 Eyebrow and status line
- Eyebrow: §5.2. Optional leading 6 px dot.
- Status line (hero): 6 px dot (`--safelight` = Locked, `--text` = Unlocking, `--ok` = Unlocked), 8 px gap, `11px/600/.16em` uppercase `--text-2`.

### 8.6 PRO badge
Outline capsule: `font: 700 10px/1 var(--font-sans); letter-spacing: .1em; padding: 2px 8px; border: 1px solid var(--text); border-radius: 999px; opacity: .85`. Text "PRO", `aria-label="Pro feature"` when it is the only signal.

### 8.7 Glass group with rows (settings style)
- Container `.glass` with `background: var(--fill)`, radius `22px`.
- Row: `display:flex; justify-content:space-between; align-items:center; gap:16px; padding:14px 18px; 15px`. Title `500`, detail `13px --muted` 3 px below. Separator: `height:.5px; background: var(--glass-line); margin-left:18px`.

### 8.8 Photo tile, note tile, badges
- Tile: `aspect-ratio: 1; overflow: hidden; background: var(--panel)`; image `object-fit: cover`.
- Video badge "▶ 0:42" and "LIVE": `12px/600 #FFF`, `text-shadow: 0 1px 3px rgba(0,0,0,.8)`, bottom-right inset `7px / 6px`, play glyph 10 px.
- Favourite: filled heart `16px` `--safelight`, top-left inset `8px`.
- Note tile: `--panel` + `inset 0 0 0 .5px var(--line)`, padding `14px`; title serif `24px/1.05` (in phones `14–20px`), then "Note" `12px --muted` 6 px below.

### 8.9 Mini bolt pad (decoy section, features card, final CTA)
- Square box (`132px` decoy, `84px` card, `200px` final), 5 × 5 CSS grid of centred cells.
- Idle bolt: ring `9px` (`inset 0 0 0 1px var(--bolt-ring)`). Lit: `12px` filled `--bolt-on`, halo `0 0 0 4px var(--bolt-halo)`, glow `0 0 10px var(--bolt-glow)`. Final CTA: idle `12px`, lit `16px`, halo `5px`, glow `16px`.
- Trail: SVG `viewBox="0 0 100 100"` over the grid; cell centres at `10 + 20·col`, `10 + 20·row`; `polyline` with `stroke: var(--bolt-on); stroke-width: 2; vector-effect: non-scaling-stroke; stroke-linecap/linejoin: round; fill: none`; `pathLength="1"` + `stroke-dasharray: 1` so it can draw in (§11.2 S4).
- `aria-hidden="true"` (decorative; the surrounding text says what it shows).

### 8.10 Sticky install bar (≤ 760 px only)
- `position: fixed; left: 14px; right: 14px; bottom: calc(14px + env(safe-area-inset-bottom)); height: 66px`, `.glass`, radius 999, `display:flex; align-items:center; gap:12px; padding: 0 9px 0 10px`, `z-index: 40`.
- Left: the real app icon (`/assets/noxium-icon-180.png`, `46 × 46`, radius `12px`, `alt=""`). Middle: "Noxium" `15px/600`, below "Free · No ads · No analytics" `12px --muted`. Right: ink capsule `46px` (`data-cta="sticky"`, `data-label-waitlist="Get the beta"`, `data-label-live="Get"`).
- A `140px` bottom scrim (`linear-gradient(0deg, color-mix(in srgb, var(--bg) 95%, transparent) 30%, transparent)`) sits behind it, `pointer-events: none`.
- Shows when the hero's CTA row has scrolled out of view; hides while `#waitlist`, `.final-cta` or the footer is in view (IntersectionObserver). Motion: §11.1 M9. Add `padding-bottom: 96px` to `body` on phones so the footer isn't covered.

### 8.11 FAQ item
- `details.faq-item` with `border-bottom: .5px solid var(--line)`; list has `border-top` too.
- `summary`: `display:flex; justify-content:space-between; gap:24px; padding:24px 0; min-height:44px; 19px/600; list-style:none` (`::-webkit-details-marker{display:none}`). Keep `.faq-q-no` (DM Mono `12px --muted`, 14 px before the question; the build strips it from JSON-LD).
- Plus icon at right (`20px`), rotates 45° on `[open]` (`transform .3s var(--ease-settle)`).
- `.faq-body`: `padding: 0 48px 24px 0; 16px/1.6 --text-2`; on open, `animation: fade-up .35s var(--ease-out) both`. (Optional, Chromium only: `::details-content` height transition; never required.)

### 8.12 Footer (`partials/footer.html` and homepage)
- `border-top: .5px solid var(--line)`, container padding `56px` top/bottom, `gap: 40px`.
- Row 1: wordmark (34 px) + "A private vault for photos, videos and notes." `14px --muted`; footer links (existing groups kept: Product, Guides, Company; About and Support live here) `14px/500 --text-2`, gap `8px 26px`.
- Row 2 (hairline above, `padding-top: 22px`, `12px/1.6 --muted`): "Made by Inertia Projects, an independent developer." and the Apple credit line (§7). Keep `build:status` here.

### 8.13 Install dialog (`<dialog id="install-dialog">`, live mode, desktop)
- `::backdrop { background: rgba(0,0,0,.5); backdrop-filter: blur(8px); }`.
- Sheet: `.glass` but with `background: var(--panel)` (opaque: it carries a QR), radius `34px`, width `min(440px, calc(100% - 32px))`, padding `32px`.
- Eyebrow "For iPhone and iPad", serif `40px` "Install Noxium", body `15px --text-2`, QR tile `160px` white radius `16px`, "Data Not Collected" note with `--ok` dot, ink "Open in the App Store" (`data-cta="dialog"`), glass "Copy link". Close button: glass circle `40px`, `aria-label="Close"`.
- Opens with the chrome-settle motion; closing fades `150ms`.

### 8.14 Tables (comparison and subpages)
- Wrapper `.data-table-wrap`: card radius `28px`, `overflow-x: auto`, `inset 0 0 0 .5px var(--line)`.
- Header cells: eyebrow style. Body cells `15px`, padding `14px 18px`, rows separated by `.5px var(--line)`.
- First column sticky (`position: sticky; left: 0; background: var(--panel)`).
- The Noxium column: `background: var(--fill)` and a `1px var(--text)` top border on its header cell. Check/cross glyphs as icons with text alternatives, not colour alone.
