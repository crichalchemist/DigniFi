# DigniFi Frontend Visual Identity — "New Deal Civic"

**Date:** 2026-06-10
**Status:** Approved (brainstorm with founder, visual companion session)
**Branch:** `feature/frontend-aesthetics`

## Problem

The frontend works (5/5 persona E2E green, WCAG AA audited) but has no visual identity. One hand-written global stylesheet with hard-coded grays, leftover Vite starter CSS actively fighting it (`index.css` ships dark-mode colors and `#646cff` links), ~15 scattered inline styles, and no design-token layer. It looks like a default app — and round-1 mockups confirmed the generic SaaS look ("navy/teal/white, rounded cards") reads as recycled AI-built tech.

## Direction: New Deal Civic

DigniFi is not fintech or legaltech SaaS. Its lineage is public programs built _for_ people — so the identity borrows from WPA-era civic design: flat geometry, poster stripes, sturdy color, optimistic and proudly institutional without being cold. A fresh start is a legal right, not a favor; the design should look like that sentence.

**Intensity rule — "bold shell, calm core":** The frame (header, progress stripe, buttons, landing page) carries the identity at full strength. Work surfaces — where someone spends 45 minutes entering income and amounts owed — go near-white and quiet. Color appears only where it guides.

### Rejected alternatives

- **Calm Institutional / Warm Human / Modern Clarity (round 1):** all three read as recycled SaaS templates. Rejected by founder.
- **Editorial Dignity** (ProPublica-style literary serif): strong, but the civic direction resonated more. Its warmth survives in tone-of-voice guidance.
- **Paper Trail** (typewriter/form skeuomorphism): memorable but costume-y; survives only as the input "fill-in-this-line" base-line detail.
- **Condensed all-caps display type:** part of the original civic mockup; rejected as shouty. Mixed case everywhere.
- **Tailwind v4 / CSS Modules:** rejected as implementation approaches — both rewrite every component to reach the same pixels. Token-based plain CSS matches the existing semantic-className convention.

## 1 · Design tokens (`frontend/src/styles/tokens.css`)

All values become CSS custom properties on `:root`. Components consume tokens only — no raw hex in component CSS.

### Color

| Token           | Hex       | Role                                                                    |
| --------------- | --------- | ----------------------------------------------------------------------- |
| `--color-pine`  | `#2e4034` | Header band, headings, primary text, borders, links on light            |
| `--color-gold`  | `#d9a441` | Primary buttons, progress fill, accents, focus rings on dark surfaces   |
| `--color-cream` | `#f2ecd9` | Landing/marketing canvas; text on pine                                  |
| `--color-paper` | `#fdfcf8` | Work-surface background (wizard, dashboard, documents)                  |
| `--color-body`  | `#4d5345` | Secondary body text                                                     |
| `--color-muted` | `#5d6356` | Helper/caption text (floor — nothing lighter carries text)              |
| `--color-rust`  | `#9c4a2e` | Errors. Warm, not alarm-red (trauma-informed)                           |
| `--color-sage`  | `#5b7c52` | Success ("marked as filed", confirmations)                              |
| `--color-sand`  | `#e7e2d2` | Dividers, progress track, disabled, disclaimer band bg (`#f6f3e9` tint) |

**Contrast rules (verified, encode as comments in tokens.css):**

- pine on paper 10.77:1 · pine on cream 9.36:1 · body on paper 7.75:1 · muted on paper 6.04:1 — AA normal ✓
- cream on pine 9.36:1 · gold on pine 4.92:1 · pine on gold 4.92:1 · rust on paper 5.96:1 — AA normal ✓
- **Gold never carries normal-size text on light surfaces** (darkened gold tops out ~3.95:1 — large text/UI only). Links on light use pine.
- **Focus rings: pine on light surfaces, gold on pine surfaces.** Gold on paper is only 2.19:1 — below the 3:1 non-text contrast of WCAG 2.2 SC 2.4.11. Pine on paper is 10.77:1; gold on pine 4.92:1.

### Typography

- `--font-display: 'Jost', system sans fallback` — headings, buttons, logotype. Jost is a Futura revival (the actual 1930s typeface); SIL OFL.
- `--font-body: 'Public Sans', system sans fallback` — everything else. USWDS's typeface, designed for government-service legibility; SIL OFL.
- **Self-hosted via `@fontsource/jost` + `@fontsource/public-sans`** (the only new dependencies). No Google Fonts CDN — no third-party request from a bankruptcy site.
- Scale: display 2.125rem/Jost 600 · h1 1.5rem/600 · h2 1.1875rem/500 · h3 1rem/500 · body 1rem/Public Sans 400, line-height 1.6 · caption 0.875rem (floor — nothing smaller).

### Geometry & motion

- **Square corners everywhere (`--radius: 0`), no box-shadows.** Flat poster geometry _is_ the identity. Depth via borders: 1px sand for quiet edges, 2px pine for emphasis.
- Spacing on a 4px scale: `--space-1` 0.25rem → `--space-8` 3rem.
- Motion minimal: 150ms ease on hover/focus color transitions only. Respect `prefers-reduced-motion`.

## 2 · App shell

- **Header:** full-width pine band; "DigniFi" logotype in Jost 600 cream; right side step indicator ("Step 2 of 6") in Public Sans gold.
- **Progress stripe:** directly under header — segmented bar, one segment per wizard step, gold fill on sand track, 5–6px tall. This is the WPA poster stripe doing real work.
- **Disclaimer band:** sand-tinted (`#f6f3e9`) strip with ★ glyph: "This is legal information, not legal advice." Present at every decision point. Styled as quiet reassurance — never a red warning (UPL-required, trauma-informed delivery).

## 3 · Core components

- **Buttons (Jost 500–600, square):**
  - Primary: gold bg, pine text · hover adds pine border · focus 2px pine ring offset 2px
  - Secondary: transparent, 1.5px pine border, pine text
  - Tertiary ("Back"): pine text with 1.5px pine underline
- **Inputs:** white bg, 1px `#b8b2a0` frame, **2px solid pine bottom border** (the "fill in this line" nod — the only Paper Trail survivor). Focus: 2px pine outer ring. Error: bottom border goes rust + rust message below; never red fills.
- **Form cards (dashboard):** white, 1px sand border, **4px left spine encodes status** — gold = generated, sage = filed, sand = pending. Title Jost, meta Public Sans muted.
- **UPL modal:** paper surface, 2px pine border, pine Jost heading, disclaimer band inside, primary gold confirm.
- **Status/feedback:** success sage, error rust, info pine. No toasts that auto-dismiss critical info.

## 4 · Page treatments

| Page                           | Treatment                                                                                                                                                                                   |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Landing**                    | Full poster: cream canvas, oversized Jost display ("A fresh start is a legal right"), flat gold/pine geometric blocks, six-step process drawn as a poster stripe. The one page that shouts. |
| **Auth (login/register)**      | Split: pine panel with mission statement in cream; paper panel with the quiet form.                                                                                                         |
| **Wizard (6 steps)**           | Calm core: pine header + gold progress stripe, paper surface, single centered column (~640px), generous spacing, one h1 per step phrased as plain language.                                 |
| **Form dashboard**             | Calm core: spine-status cards in a grid, gold primary "Generate All".                                                                                                                       |
| **Documents/upload**           | Calm core; drop-zone gets a 2px dashed pine border (gold fails WCAG 1.4.11 non-text contrast on light surfaces).                                                                            |
| **Fee waiver / survey / misc** | Calm core defaults.                                                                                                                                                                         |

## 5 · Implementation approach & cleanup

**Approach: design tokens + plain CSS** (matches existing semantic-className convention; zero build changes).

1. New `frontend/src/styles/tokens.css` with everything in §1; `@fontsource` imports in `main.tsx`.
2. Rewrite `frontend/src/styles/global.css` against tokens (reset, base type, shell, shared components).
3. **Delete Vite scaffold:** `index.css` starter block (dark `color-scheme`, `#646cff` links, centered flex body, 3.2em h1) and `App.css` remnants (`.logo`, `.card`, `.read-the-docs`). Remove their imports.
4. Migrate ~15 inline `style={{}}` usages to classes: `App.tsx` (2), `FileDropZone` (2), `UploadQueue` (2), `DebtsStep` (1), `DocumentUploadPage` (6), `FormDashboard` (1), `LandingPage` (1).
5. Restyle component CSS (`PostTaskSurvey.css`, classNames in Button, FormField, ProgressIndicator, UPL components) against tokens.

**Guardrails:**

- WCAG 2.1 AA maintained — vitest-axe suites must stay green; contrast rules live as comments next to the tokens they constrain.
- All 171 frontend tests + 5-persona E2E remain green (styling must not change DOM semantics/ARIA).
- Reading level, trauma-informed copy, and UPL language untouched — this is a visual change; any copy edits go through UPL review separately.
- Desktop-first 1024px+; existing responsive degradation preserved.

## Out of scope

- Dark mode (light-only, like the paper forms themselves)
- Copy rewrites, new pages, component behavior changes
- Mobile-first redesign
- Logo/brandmark design (logotype = styled text for now)

## Verification

1. `npm test` — 171 tests green, vitest-axe a11y suites pass.
2. `npm run e2e` — 5/5 persona journeys green.
3. Manual sweep at 1024px and 1440px: landing, auth, all 6 wizard steps, dashboard, UPL modal, documents, fee waiver, survey.
4. Grep gate: no raw hex in component CSS (tokens only), zero `style={{` outside documented exceptions, `index.css`/`App.css` scaffold gone.
