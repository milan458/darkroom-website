# Darkroom Design System — Master Specification

> **LOGIC:** Global Source of Truth for Darkroom (`darkroom-website`). Synthesized via `ui-ux-pro-max` (`dark-mode-oled` + `skeuomorphism` tactile machined hardware + `bento-box-grid` + `Real-Time / Operations Landing` pattern) and `design-system` Three-Layer Token Architecture (`Primitive → Semantic → Component`).

---

**Project:** Darkroom — Encrypted iPhone & iPad Photo Vault  
**Aesthetic Direction:** Machined Optical Instrument · Safelight OLED Dark (`#070605`) & Baryta Contact-Sheet Paper Light (`#F3EEE7`)  
**Design Dials:** Variance `8/10` (Asymmetric Contact-Sheet Bento + Hardware Instrument Panels) · Motion `5/10` (Tactile Spring + Pauseable Live Simulator) · Density `5/10` (Balanced Precision)

---

## 1. Three-Layer Token Architecture

### Layer 1: Primitive Tokens (Raw Material Palette)

| Token | Value | Material Reference |
|-------|-------|--------------------|
| `--prim-obsidian-950` | `#070605` | Deep OLED darkroom chamber |
| `--prim-obsidian-900` | `#0D0B09` | Anodized chassis base |
| `--prim-obsidian-850` | `#15120F` | Machined instrument panel |
| `--prim-obsidian-800` | `#1D1814` | Elevated bolt plate surface |
| `--prim-obsidian-700` | `#2B241E` | Hairline bezel & track divider |
| `--prim-brass-600` | `#3F362E` | Unlit bolt head fill |
| `--prim-brass-500` | `#5E5146` | Machined bolt rim stroke |
| `--prim-safelight-500` | `#E83B2E` | Spectral crimson safelight (630nm) |
| `--prim-safelight-400` | `#F55A4E` | Active safelight filament highlight |
| `--prim-safelight-700` | `#C2271B` | High-contrast ink safelight (Paper mode) |
| `--prim-amber-400` | `#F5B759` | Sodium-vapor darkroom timer amber |
| `--prim-amber-700` | `#8F5106` | Contact-sheet grease-pencil amber (Paper mode) |
| `--prim-halide-400` | `#5ED196` | Silver-halide verified GCM tag mint |
| `--prim-halide-700` | `#1C6B3F` | Archival fixer stamp green (Paper mode) |
| `--prim-paper-100` | `#F3EEE7` | Warm baryta fiber base |
| `--prim-paper-150` | `#E8E0D5` | Secondary contact-sheet tray |
| `--prim-paper-50` | `#FAF7F2` | Loupe-lit card surface |
| `--prim-paper-white` | `#FFFFFF` | High-elevation paper sheet |
| `--prim-paper-line` | `#D3C6B6` | Archival rule line |
| `--prim-ink-950` | `#15110E` | Silver-gelatin deep black ink |
| `--prim-ink-700` | `#4E4339` | Secondary archival ink (≥ 7.2:1 contrast) |

### Layer 2: Semantic Tokens (Theme-Aware Purpose Aliases)

| Semantic Token | Safelight Dark (Default) | Baryta Paper (Light) | Contrast / Role |
|----------------|--------------------------|----------------------|-----------------|
| `--bg` | `var(--prim-obsidian-950)` | `var(--prim-paper-100)` | Viewport canvas |
| `--bg-alt` | `var(--prim-obsidian-900)` | `var(--prim-paper-150)` | Alternating bench band |
| `--panel` | `var(--prim-obsidian-850)` | `var(--prim-paper-50)` | Primary card / module surface |
| `--panel-elevated` | `var(--prim-obsidian-800)` | `var(--prim-paper-white)` | Hover / raised hardware surface |
| `--line` | `var(--prim-obsidian-700)` | `var(--prim-paper-line)` | 1px structural rule |
| `--text` | `#F4EFEA` | `var(--prim-ink-950)` | Primary text (> 15:1 contrast) |
| `--secondary` | `#D7CEC4` | `#2F2721` | Emphasized body copy (> 10:1 contrast) |
| `--muted` | `#B2A79C` | `var(--prim-ink-700)` | Muted prose & captions (≥ 6.8:1 contrast) |
| `--safelight` | `var(--prim-safelight-500)` | `var(--prim-safelight-700)` | Primary brand & safelight indicator |
| `--amber` | `var(--prim-amber-400)` | `var(--prim-amber-700)` | Telemetry, eyebrows & focus ring |
| `--ok` | `var(--prim-halide-400)` | `var(--prim-halide-700)` | Cryptographic integrity & verified status |

### Layer 3: Component Tokens

- `--header-bg`: translucent blurred instrument bar (`backdrop-filter: blur(16px)`)
- `--card-highlight`: top-edge specular chamfer (`inset 0 1px 0`)
- `--radius-sm` (`10px`), `--radius-md` (`16px`), `--radius-lg` (`22px`), `--radius-pill` (`999px`)

---

## 2. Typography System

Updated 2026-10: testers found the uppercase, monospace "instrument panel" look too technical, so the site now reads like a friendly consumer app.

1. **Everything (`--font-sans`)**: `"Plus Jakarta Sans"`, `400`–`700`, normal (sentence) case, no wide letter-spacing. Used for headings, buttons, labels, chips and body text.
2. **Code only (`--font-mono`)**: `"DM Mono"`, reserved for the code listing in the Security section.
3. **Wordmark only (`--font-display`)**: `"Archivo Narrow"`, `700`, uppercase. The DARKROOM logo is the only uppercase text; in sentences the name is written "Darkroom".
4. No other `text-transform: uppercase`.

**Words:** use the app's plain vocabulary (pattern, recovery phrase, vault, decoy vault, albums, Recently Deleted, backed up, emergency erase). Encryption details (Argon2id, AES-256-GCM, key hierarchy) live only in the Security section (`#security`), the one technical section on the page.

---

## 3. Interaction, Accessibility & Layout Rules

- **No Emojis as Structural Icons**: Use crisp inline vector SVGs (`stroke-width: 1.7`) with `aria-hidden="true"` when decorative or explicit accessible names on icon controls.
- **Interactive Simulator Controls (WCAG 2.2.2 & 2.5.7)**:
  - Provide one-click/keyboard-operable **Room Mode Preset Buttons** (`Main Room`, `Decoy Room`, `Duress Wipe`) and a **Pause / Play Auto-Demo** control below the phone simulator so users never have to rely solely on pointer dragging or wait for the auto-loop.
  - Detect when a user manually draws the Main, Decoy, or Duress bolt pattern, and never accidentally trigger a Duress wipe on a generic custom pattern unless Duress mode was selected.
- **Grid & Overflow Safety**:
  - Use `minmax(0, 1fr)` on multi-column grids containing `<pre>` or tables, and set `min-width: 0` on grid children so wide code blocks scroll internally without stretching the mobile viewport.
  - Avoid nested vertical scrollbars (`max-block-size`) on data tables; let the page scroll naturally with sticky headers.
