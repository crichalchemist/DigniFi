# New Deal Civic Visual Identity — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved "New Deal Civic" visual identity (spec: `docs/superpowers/specs/2026-06-10-frontend-aesthetics-design.md`) across the entire DigniFi frontend via design tokens + plain CSS.

**Architecture:** A new `tokens.css` defines all color/type/space values as CSS custom properties. The existing 897-line `styles/global.css` (organized in banner-comment sections, consumed via semantic classNames) is rewritten section-by-section against the tokens. Dead Vite scaffold CSS is deleted. Three component groups that currently have **no CSS at all** (form dashboard, form cards, UPL modal) get new sections. ~15 inline styles migrate to classes. Fonts are self-hosted via `@fontsource`.

**Tech Stack:** React 19 + Vite 7 + TypeScript, plain CSS (no Tailwind/modules), vitest + vitest-axe, Playwright E2E. New deps: `@fontsource/jost`, `@fontsource/public-sans` (font files only).

---

## Hard constraints (apply to every task)

1. **No copy changes.** All user-facing text stays byte-identical except the two additions explicitly specified (auth aside statement, Task 10). E2E asserts on text.
2. **No ARIA/role/heading-level changes.** vitest-axe and Playwright page objects depend on them. Styling must not alter DOM semantics.
3. **Tokens only.** After Task 1, no raw hex in any CSS except `tokens.css`. No `style={{}}` except the documented dynamic-width exception (`FormDashboard.tsx` progress fill).
4. **Square corners, no box-shadows.** `--radius: 0` everywhere; depth via borders only.
5. **Working directory:** all `npm` commands run from `/Volumes/Containers/DigniFi/frontend/`.
6. **Test commands:** full suite `npm test` (vitest, runs once). Targeted: `npx vitest run <path>`. E2E (final task only): `docker compose up -d` from repo root, then `npm run e2e`.
7. **Pre-commit gotcha:** if prettier reformats staged files the commit fails and restores changes — re-`git add` and commit again.

### Mapping-table convention

For sections where the existing layout works and only the look changes, tasks give a **property table** instead of full CSS: keep every existing structural declaration (display, position, flex, margins, widths) and set/replace only the listed properties. Anything not listed stays as-is. Where a task gives a full CSS block, it replaces the entire section between its banner comment and the next banner.

---

### Task 1: Self-hosted fonts + design tokens

**Files:**

- Create: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/package.json` (via npm install)

- [ ] **Step 1: Install font packages**

```bash
cd /Volumes/Containers/DigniFi/frontend
npm install @fontsource/jost @fontsource/public-sans
```

Expected: both packages added to `dependencies`.

- [ ] **Step 2: Create `frontend/src/styles/tokens.css`** (complete file):

```css
/* ============================================================================
   DigniFi Design Tokens — "New Deal Civic"
   Spec: docs/superpowers/specs/2026-06-10-frontend-aesthetics-design.md
   ============================================================================ */

:root {
  /* --------------------------------------------------------------------------
     Color — WCAG 2.1 AA verified 2026-06-10:
       pine on paper 10.77:1 · pine on cream 9.36:1 · body on paper 7.75:1
       muted on paper 6.04:1 · cream on pine 9.36:1 · gold on pine 4.92:1
       pine on gold 4.92:1 · rust on paper 5.96:1
     RULE: gold NEVER carries normal-size text on light surfaces (≤3.95:1).
           Links on light backgrounds use pine.
     -------------------------------------------------------------------------- */
  --color-pine: #2e4034; /* header band, headings, primary text, borders */
  --color-gold: #d9a441; /* primary buttons, progress fill, focus rings */
  --color-cream: #f2ecd9; /* landing canvas; text on pine */
  --color-paper: #fdfcf8; /* work-surface background */
  --color-body: #4d5345; /* secondary body text */
  --color-muted: #5d6356; /* helper text — the lightest text color allowed */
  --color-rust: #9c4a2e; /* errors (warm, not alarm-red) */
  --color-sage: #5b7c52; /* success */
  --color-sand: #e7e2d2; /* dividers, tracks, disabled */
  --color-sand-tint: #f6f3e9; /* disclaimer band background */
  --color-line: #b8b2a0; /* quiet input frame */
  --color-white: #ffffff;
  --color-scrim: rgba(46, 64, 52, 0.55); /* modal overlay (pine @ 55%) */

  /* Typography */
  --font-display: 'Jost', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-body: 'Public Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --text-display: 2.125rem;
  --text-h1: 1.5rem;
  --text-h2: 1.1875rem;
  --text-h3: 1rem;
  --text-caption: 0.875rem; /* floor — nothing smaller carries text */

  /* Spacing (4px scale) */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.5rem;
  --space-6: 2rem;
  --space-7: 2.5rem;
  --space-8: 3rem;

  /* Geometry — flat poster identity: square corners, no shadows */
  --radius: 0;

  /* Motion */
  --transition-fast: 150ms ease;
}
```

- [ ] **Step 3: Wire imports in `frontend/src/main.tsx`** — replace the single line `import './styles/global.css'` with:

```ts
import '@fontsource/jost/400.css';
import '@fontsource/jost/500.css';
import '@fontsource/jost/600.css';
import '@fontsource/public-sans/400.css';
import '@fontsource/public-sans/500.css';
import '@fontsource/public-sans/600.css';
import './styles/tokens.css';
import './styles/global.css';
```

- [ ] **Step 4: Verify suite still green**

Run: `npm test`
Expected: 171 tests pass (CSS imports are stubbed by vitest; this catches typos in import paths).

- [ ] **Step 5: Commit**

```bash
git add src/styles/tokens.css src/main.tsx package.json package-lock.json
git commit -m "feat(frontend): design tokens + self-hosted Jost/Public Sans"
```

---

### Task 2: Delete Vite scaffold CSS

**Files:**

- Delete: `frontend/src/index.css` (imported nowhere — verified)
- Delete: `frontend/src/App.css`
- Modify: `frontend/src/App.tsx` (remove one import)

- [ ] **Step 1: Confirm scaffold classes are unused**

```bash
cd /Volumes/Containers/DigniFi/frontend
grep -rn "index.css" src/ index.html
grep -rn 'className="logo\|className="card"\|read-the-docs\|animated-logo' src/
```

Expected: no matches for either command. (`.landing-card` / `.form-card` are different classes and don't match `className="card"`.)

- [ ] **Step 2: Delete files and the import**

```bash
rm src/index.css src/App.css
```

In `frontend/src/App.tsx`, delete the line: `import './App.css';`

`App.css` also carried `#root { max-width: 1280px; margin: 0 auto; padding: 2rem; text-align: center }` — its removal changes page framing. The new framing is intentional (full-bleed shell); page-level containers handle their own width from Task 5 on.

- [ ] **Step 3: Verify**

Run: `npm test`
Expected: 171 pass.

- [ ] **Step 4: Commit**

```bash
git add -A src/
git commit -m "chore(frontend): remove Vite starter CSS scaffold"
```

---

### Task 3: global.css — reset, typography, focus

**Files:**

- Modify: `frontend/src/styles/global.css` (sections: "CSS Reset & Base Styles", "Typography", "Focus Indicators (Accessibility)")

- [ ] **Step 1: Replace the three sections** (full replacement, banner to banner):

```css
/* ============================================================================
   CSS Reset & Base Styles
   ============================================================================ */

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-size: 100%;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-body);
  font-size: 1rem;
  line-height: 1.6;
  color: var(--color-body);
  background-color: var(--color-paper);
  min-height: 100vh;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Screen reader only content */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* ============================================================================
   Typography
   ============================================================================ */

h1,
h2,
h3,
h4,
h5,
h6 {
  font-family: var(--font-display);
  color: var(--color-pine);
  line-height: 1.25;
}

h1 {
  font-size: var(--text-h1);
  font-weight: 600;
}

h2 {
  font-size: var(--text-h2);
  font-weight: 500;
}

h3 {
  font-size: var(--text-h3);
  font-weight: 500;
}

p {
  margin-bottom: var(--space-4);
}

a {
  color: var(--color-pine);
  text-decoration: underline;
  text-underline-offset: 2px;
  transition: color var(--transition-fast);
}

/* ============================================================================
   Focus Indicators (Accessibility)
   ============================================================================ */

*:focus {
  outline: 2px solid var(--color-gold);
  outline-offset: 2px;
}

*:focus:not(:focus-visible) {
  outline: none;
}

*:focus-visible {
  outline: 2px solid var(--color-gold);
  outline-offset: 2px;
}
```

Note: if the old sections contain declarations not represented above that are load-bearing for layout (check `.sr-only` consumers and any `html`/`body` rules referenced in tests), keep them — but the colors/fonts above are authoritative.

- [ ] **Step 2: Verify**

Run: `npm test`
Expected: 171 pass (a11y suites assert focus visibility and sr-only behavior — both preserved).

- [ ] **Step 3: Commit**

```bash
git add src/styles/global.css
git commit -m "feat(frontend): retoken base styles — Public Sans body, Jost headings, gold focus"
```

---

### Task 4: Buttons and form fields

**Files:**

- Modify: `frontend/src/styles/global.css` (sections: "Button Component", "Form Components")

Button.tsx emits `button--{variant}` (`primary`, `outline`), `button--{size}` (`sm`/`md`/`lg`), `button--full-width`, `button--loading`, `button--disabled` (see `Button.tsx:38-42`).

- [ ] **Step 1: Replace the "Button Component" section** (full replacement; keep the existing `@keyframes spin` block and `.button-spinner`/`.spinner`/`.spinner-track`/`.spinner-head` layout rules, recoloring per the table after the block):

```css
/* ============================================================================
   Button Component
   ============================================================================ */

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1rem;
  padding: 0.625rem 1.625rem;
  border: 2px solid transparent;
  border-radius: var(--radius);
  cursor: pointer;
  transition:
    background-color var(--transition-fast),
    color var(--transition-fast),
    border-color var(--transition-fast);
}

.button--sm {
  font-size: var(--text-caption);
  padding: var(--space-1) var(--space-3);
}

.button--md {
  font-size: 1rem;
}

.button--lg {
  font-size: 1.125rem;
  padding: var(--space-3) var(--space-6);
}

.button--primary {
  background-color: var(--color-gold);
  color: var(--color-pine);
}

.button--primary:hover:not(:disabled) {
  border-color: var(--color-pine);
}

.button--outline {
  background-color: transparent;
  border-color: var(--color-pine);
  color: var(--color-pine);
}

.button--outline:hover:not(:disabled) {
  background-color: var(--color-pine);
  color: var(--color-cream);
}

.button:disabled,
.button--disabled {
  background-color: var(--color-sand);
  color: var(--color-muted);
  border-color: transparent;
  cursor: not-allowed;
}

.button--full-width {
  width: 100%;
}
```

Spinner recolor table (keep layout declarations):

| Selector         | Set                                                              |
| ---------------- | ---------------------------------------------------------------- |
| `.spinner-track` | `stroke: var(--color-sand)` (or `border-color` if div-based)     |
| `.spinner-head`  | `stroke: var(--color-pine)` (or `border-top-color` if div-based) |

- [ ] **Step 2: Replace the "Form Components" section** (full replacement):

```css
/* ============================================================================
   Form Components
   ============================================================================ */

.form-section {
  margin-bottom: var(--space-6);
}

.section-title {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  font-weight: 500;
  color: var(--color-pine);
  margin-bottom: var(--space-2);
}

.section-description {
  color: var(--color-body);
  margin-bottom: var(--space-4);
}

.form-row {
  display: flex;
  gap: var(--space-4);
}

.form-row > * {
  flex: 1;
}

.form-field {
  margin-bottom: var(--space-4);
}

.form-label {
  display: block;
  font-family: var(--font-body);
  font-weight: 500;
  font-size: var(--text-caption);
  color: var(--color-pine);
  margin-bottom: var(--space-1);
}

.required-indicator {
  color: var(--color-rust);
  margin-left: var(--space-1);
}

.form-input {
  width: 100%;
  font-family: var(--font-body);
  font-size: 1rem;
  color: var(--color-pine);
  background-color: var(--color-white);
  border: 1px solid var(--color-line);
  /* "fill in this line" — solid pine base line, the Paper Trail survivor */
  border-bottom: 2px solid var(--color-pine);
  border-radius: var(--radius);
  padding: 0.625rem 0.75rem;
  transition: border-color var(--transition-fast);
}

.form-input:hover {
  border-color: var(--color-pine);
}

.form-input:focus {
  outline: 2px solid var(--color-gold);
  outline-offset: 2px;
}

.form-field.has-error .form-input {
  border-color: var(--color-rust);
  border-bottom-color: var(--color-rust);
}

.form-help-text {
  font-size: var(--text-caption);
  color: var(--color-muted);
  margin-top: var(--space-1);
}

.form-error {
  font-size: var(--text-caption);
  color: var(--color-rust);
  margin-top: var(--space-1);
}
```

Note: `FormField.tsx` also renders `.form-input-wrapper` and `.form-input-icon`. Keep their existing layout rules; set icon color to `var(--color-muted)`.

- [ ] **Step 3: Verify**

Run: `npx vitest run src/components/common`
Expected: Button/FormField suites pass.
Then: `npm test` — 171 pass.

- [ ] **Step 4: Commit**

```bash
git add src/styles/global.css
git commit -m "feat(frontend): civic buttons and fill-in-this-line inputs"
```

---

### Task 5: Wizard shell + progress stripe

**Files:**

- Modify: `frontend/src/styles/global.css` (sections: "Container & Layout", "Wizard Layout", "Progress Indicator")

These sections have working layout (desktop-first with `max-width: 1023px`/`767px` breakpoints). **Use the mapping-table convention** — keep all structural declarations and breakpoints; set only:

- [ ] **Step 1: Apply shell mapping**

| Selector            | Set                                                                                                                                                        |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.wizard-container` | `max-width: 720px; margin: 0 auto; padding: var(--space-6) var(--space-4); background: transparent`                                                        |
| `.wizard-layout`    | `background-color: var(--color-paper)`                                                                                                                     |
| `.wizard-header`    | `background-color: var(--color-pine); padding: var(--space-4) var(--space-5); border-radius: var(--radius)` (remove any old background/border/shadow)      |
| `.wizard-title`     | `font-family: var(--font-display); color: var(--color-cream); font-weight: 600`                                                                            |
| `.wizard-subtitle`  | `color: var(--color-gold); font-family: var(--font-body); font-size: var(--text-caption)`                                                                  |
| `.wizard-content`   | `background-color: var(--color-white); border: 1px solid var(--color-sand); padding: var(--space-6); border-radius: var(--radius)` (remove any box-shadow) |
| `.wizard-footer`    | `border-top: 1px solid var(--color-sand)`                                                                                                                  |
| `.wizard-help-text` | `color: var(--color-muted); font-size: var(--text-caption)`                                                                                                |

- [ ] **Step 2: Apply progress stripe mapping** (the WPA poster stripe — flat squares, gold fill on sand track):

| Selector                                                                  | Set                                                                                                                                                                                |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.step-marker`                                                            | `background: var(--color-white); border: 2px solid var(--color-sand); border-radius: var(--radius); color: var(--color-muted); font-family: var(--font-display); font-weight: 600` |
| `.progress-step.completed .step-marker`                                   | `background: var(--color-pine); border-color: var(--color-pine); color: var(--color-cream)`                                                                                        |
| `.progress-step.current .step-marker`                                     | `background: var(--color-gold); border-color: var(--color-pine); color: var(--color-pine)`                                                                                         |
| `.step-checkmark`                                                         | `color: var(--color-cream)` (or `stroke` if SVG)                                                                                                                                   |
| `.step-label`, `.step-name`                                               | `color: var(--color-muted); font-size: var(--text-caption)`                                                                                                                        |
| `.progress-step.current .step-label`, `.progress-step.current .step-name` | `color: var(--color-pine); font-weight: 600`                                                                                                                                       |
| `.step-connector`                                                         | `background: var(--color-sand); height: 4px` (keep positioning)                                                                                                                    |
| `.step-connector.completed`                                               | `background: var(--color-gold)`                                                                                                                                                    |

Remove every `border-radius` > 0 and every `box-shadow` in these sections.

- [ ] **Step 3: Verify**

Run: `npx vitest run src/components/common src/pages`
Expected: ProgressIndicator + wizard page suites pass.

- [ ] **Step 4: Commit**

```bash
git add src/styles/global.css
git commit -m "feat(frontend): pine wizard shell + flat gold progress stripe"
```

---

### Task 6: Info box, error display, loading states

**Files:**

- Modify: `frontend/src/styles/global.css` (sections: "Info Box (Trauma-informed messaging)", "Error Display", "Loading States")

- [ ] **Step 1: Replace "Info Box" and "Error Display" sections** (full replacement):

```css
/* ============================================================================
   Info Box (Trauma-informed messaging)
   ============================================================================ */

.info-box {
  display: flex;
  gap: var(--space-3);
  background-color: var(--color-sand-tint);
  border: 1px solid var(--color-sand);
  border-left: 4px solid var(--color-gold);
  border-radius: var(--radius);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.info-icon {
  color: var(--color-pine);
  flex-shrink: 0;
}

.info-title {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--color-pine);
  margin-bottom: var(--space-1);
}

.info-message {
  color: var(--color-body);
  font-size: var(--text-caption);
  margin-bottom: 0;
}

/* ============================================================================
   Error Display
   ============================================================================ */

.wizard-error {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
  background-color: var(--color-white);
  border: 1px solid var(--color-rust);
  border-left: 4px solid var(--color-rust);
  border-radius: var(--radius);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.error-icon {
  color: var(--color-rust);
  flex-shrink: 0;
}

.error-title {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--color-rust);
  margin-bottom: var(--space-1);
}

.error-message {
  color: var(--color-body);
  font-size: var(--text-caption);
  margin-bottom: 0;
}

.error-dismiss {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--color-muted);
  cursor: pointer;
  font-size: 1rem;
  padding: var(--space-1);
}

.error-dismiss:hover {
  color: var(--color-pine);
}
```

- [ ] **Step 2: "Loading States" mapping** (keep layout/animation):

| Selector                              | Set                              |
| ------------------------------------- | -------------------------------- |
| `.wizard-loading`, `.loading-spinner` | text color `var(--color-muted)`  |
| `.wizard-loading-overlay`             | `background: var(--color-scrim)` |

- [ ] **Step 3: Verify + commit**

Run: `npm test` — 171 pass.

```bash
git add src/styles/global.css
git commit -m "feat(frontend): rust errors, gold info boxes — trauma-informed states"
```

---

### Task 7: UPL disclaimer band

**Files:**

- Modify: `frontend/src/styles/global.css` (section: "UPL Disclaimer Component" — the final section of the file)

- [ ] **Step 1: Replace the section** (full replacement). The quiet sand band — legally present, never alarming:

```css
/* ============================================================================
   UPL Disclaimer Component
   ============================================================================ */

.upl-disclaimer--inline {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-caption);
  color: var(--color-body);
  background-color: var(--color-sand-tint);
  border: 1px solid var(--color-sand);
  border-radius: var(--radius);
  padding: var(--space-2) var(--space-3);
}

.upl-disclaimer--inline .upl-disclaimer-icon {
  color: var(--color-pine);
  flex-shrink: 0;
}

.upl-disclaimer--banner {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
  background-color: var(--color-sand-tint);
  border: 1px solid var(--color-sand);
  border-left: 4px solid var(--color-pine);
  border-radius: var(--radius);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.upl-disclaimer-icon-wrapper {
  color: var(--color-pine);
  flex-shrink: 0;
}

.upl-disclaimer-icon-wrapper svg {
  width: 1.25rem;
  height: 1.25rem;
}

.upl-disclaimer-content {
  flex: 1;
}

.upl-disclaimer-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--text-caption);
  color: var(--color-pine);
  margin-bottom: var(--space-1);
}

.upl-disclaimer-text {
  font-size: var(--text-caption);
  color: var(--color-body);
  margin-bottom: 0;
}

.upl-disclaimer--checkbox {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
  font-size: var(--text-caption);
  color: var(--color-body);
}

.upl-disclaimer-checkbox {
  accent-color: var(--color-pine);
  margin-top: 0.2em;
}
```

- [ ] **Step 2: Verify + commit**

Run: `npx vitest run src/components/compliance` then `npm test`.

```bash
git add src/styles/global.css
git commit -m "feat(frontend): UPL disclaimer as quiet sand band, never a warning"
```

---

### Task 8: Form dashboard, form cards, UPL modal (new CSS — currently unstyled)

**Files:**

- Modify: `frontend/src/styles/global.css` (append two new sections at end of file)
- Modify: `frontend/src/components/forms/FormCard.tsx:45` (status modifier class)

`form-dashboard-*`, `form-card-*`, and `upl-modal-*` classNames exist in components but have **zero CSS today**. `FormStatus = 'generated' | 'downloaded' | 'filed'` (`types/api.ts:215`).

- [ ] **Step 1: Add status modifier to FormCard**

`FormCard.tsx:45` currently reads:

```tsx
<article className="form-card" aria-label={metadata.label}>
```

Change to (the destructured prop holding the `GeneratedForm` is visible at `FormCard.tsx:14-28` — it is the prop typed `GeneratedForm`; use its actual name, expected `form`):

```tsx
<article className={`form-card form-card--${form.status}`} aria-label={metadata.label}>
```

- [ ] **Step 2: Run FormCard tests to catch the className change**

Run: `npx vitest run src/components/forms`
Expected: PASS (tests select by role/label, not class). If a test asserts the exact class string, update that assertion to expect the modifier.

- [ ] **Step 3: Append new sections to global.css**:

```css
/* ============================================================================
   Form Dashboard & Form Cards
   ============================================================================ */

.form-dashboard {
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
}

.form-dashboard-header {
  margin-bottom: var(--space-5);
}

.form-dashboard-title {
  font-family: var(--font-display);
  font-size: var(--text-h1);
  font-weight: 600;
  color: var(--color-pine);
}

.form-dashboard-subtitle {
  color: var(--color-body);
}

.form-dashboard-loading,
.form-dashboard-empty {
  max-width: 640px;
  margin: var(--space-8) auto;
  text-align: center;
  color: var(--color-muted);
}

.form-dashboard-error {
  margin-bottom: var(--space-4);
}

.form-dashboard-progress {
  margin-bottom: var(--space-5);
}

.form-dashboard-progress-bar {
  height: 6px;
  background-color: var(--color-sand);
  border-radius: var(--radius);
  overflow: hidden;
}

.form-dashboard-progress-fill {
  height: 100%;
  background-color: var(--color-gold);
  transition: width var(--transition-fast);
}

.form-dashboard-progress-text {
  font-size: var(--text-caption);
  color: var(--color-muted);
  margin-top: var(--space-1);
}

.form-dashboard-generate-all {
  margin-bottom: var(--space-5);
}

.form-dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-4);
}

/* Card spine encodes status: sand = pending default, gold = generated/
   downloaded, sage = filed */
.form-card {
  background-color: var(--color-white);
  border: 1px solid var(--color-sand);
  border-left: 4px solid var(--color-sand);
  border-radius: var(--radius);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.form-card--generated,
.form-card--downloaded {
  border-left-color: var(--color-gold);
}

.form-card--filed {
  border-left-color: var(--color-sage);
}

.form-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-2);
}

.form-card-title {
  font-family: var(--font-display);
  font-size: var(--text-h3);
  font-weight: 600;
  color: var(--color-pine);
  margin-bottom: var(--space-1);
}

.form-card-description {
  font-size: var(--text-caption);
  color: var(--color-body);
  margin-bottom: 0;
}

.form-card-disclaimer {
  font-size: var(--text-caption);
  color: var(--color-muted);
}

.form-card-actions {
  display: flex;
  gap: var(--space-2);
  margin-top: auto;
  flex-wrap: wrap;
}

.form-card-filed-check {
  color: var(--color-sage);
  font-weight: 600;
  font-size: var(--text-caption);
}

/* ============================================================================
   UPL Confirmation Modal
   ============================================================================ */

.upl-modal-overlay {
  position: fixed;
  inset: 0;
  background-color: var(--color-scrim);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  z-index: 1000;
}

.upl-modal {
  background-color: var(--color-paper);
  border: 2px solid var(--color-pine);
  border-radius: var(--radius);
  max-width: 560px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.upl-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-sand);
}

.upl-modal-title {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  font-weight: 600;
  color: var(--color-pine);
}

.upl-modal-close {
  background: none;
  border: none;
  color: var(--color-muted);
  font-size: 1.25rem;
  cursor: pointer;
  padding: var(--space-1);
}

.upl-modal-close:hover {
  color: var(--color-pine);
}

.upl-modal-body {
  padding: var(--space-5);
}

.upl-modal-icon {
  color: var(--color-pine);
  margin-bottom: var(--space-3);
}

.upl-modal-acknowledgment {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
  background-color: var(--color-sand-tint);
  border: 1px solid var(--color-sand);
  padding: var(--space-3);
  margin-top: var(--space-4);
}

.upl-modal-checkbox {
  accent-color: var(--color-pine);
  margin-top: 0.2em;
}

.upl-modal-text {
  font-size: var(--text-caption);
  color: var(--color-body);
  margin-bottom: 0;
}

.upl-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--color-sand);
}
```

- [ ] **Step 4: Verify**

Run: `npx vitest run src/pages src/components/forms src/components/compliance`
Expected: PASS. Then `npm test` — full suite green.

- [ ] **Step 5: Commit**

```bash
git add src/styles/global.css src/components/forms/FormCard.tsx
git commit -m "feat(frontend): style dashboard, status-spine form cards, UPL modal"
```

---

### Task 9: Landing page — full poster

**Files:**

- Modify: `frontend/src/styles/global.css` (section: "Landing Page")
- Modify: `frontend/src/pages/LandingPage.tsx` (decorative stripe + error class; **no copy changes**)

- [ ] **Step 1: TSX — add decorative stripe and migrate inline error style**

In `LandingPage.tsx`, directly after the closing `</div>` of `landing-cta-group` (before the `{demoError && ...}` block), add:

```tsx
<div className="landing-stripe" aria-hidden="true">
  <span />
  <span />
  <span />
  <span />
  <span />
  <span />
</div>
```

And replace the inline-styled demo error (`LandingPage.tsx:72-78`):

```tsx
{
  demoError && (
    <p role="alert" className="landing-error">
      {demoError}
    </p>
  );
}
```

- [ ] **Step 2: Replace the "Landing Page" section CSS** (full replacement; keep the existing two responsive breakpoints at the end of the section, adjusting only colors within them):

```css
/* ============================================================================
   Landing Page — the one page that shouts (full poster)
   ============================================================================ */

.landing-page {
  min-height: 100vh;
  background-color: var(--color-cream);
  display: flex;
  flex-direction: column;
}

.landing-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 var(--space-5);
  width: 100%;
}

.landing-hero {
  padding: var(--space-8) 0 var(--space-7);
  border-bottom: 4px solid var(--color-pine);
}

.landing-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(var(--text-display), 4vw + 1rem, 3rem);
  color: var(--color-pine);
  line-height: 1.15;
  max-width: 18ch;
}

.landing-subtitle {
  font-size: 1.125rem;
  color: var(--color-body);
  max-width: 55ch;
  margin-top: var(--space-4);
}

.landing-cta-group {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-6);
  flex-wrap: wrap;
}

/* six-segment poster stripe — one per wizard step, decorative */
.landing-stripe {
  display: flex;
  height: 8px;
  margin-top: var(--space-6);
  max-width: 360px;
}

.landing-stripe span {
  flex: 1;
}

.landing-stripe span:nth-child(odd) {
  background-color: var(--color-gold);
}

.landing-stripe span:nth-child(even) {
  background-color: var(--color-pine);
}

.landing-error {
  color: var(--color-rust);
  margin-top: var(--space-3);
  font-size: var(--text-caption);
}

.landing-values {
  padding: var(--space-7) 0;
}

.landing-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}

.landing-card {
  background-color: var(--color-paper);
  border: 2px solid var(--color-pine);
  border-radius: var(--radius);
  padding: var(--space-5);
}

.landing-card-icon {
  color: var(--color-gold);
  margin-bottom: var(--space-3);
}

.landing-card-icon svg {
  width: 2rem;
  height: 2rem;
}

.landing-card-title {
  font-family: var(--font-display);
  font-size: var(--text-h2);
  font-weight: 600;
  color: var(--color-pine);
  margin-bottom: var(--space-2);
}

.landing-card-text {
  color: var(--color-body);
  font-size: var(--text-caption);
  margin-bottom: 0;
}

.landing-footer {
  margin-top: auto;
  background-color: var(--color-pine);
  padding: var(--space-5) 0;
}

.landing-disclaimer {
  color: var(--color-cream);
  font-size: var(--text-caption);
  margin-bottom: 0;
}

@media (max-width: 1023px) {
  .landing-cards {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .landing-hero {
    padding: var(--space-6) 0;
  }
}
```

(If the old section's breakpoints contain additional structural rules, merge them into the two blocks above rather than dropping them.)

- [ ] **Step 3: Verify**

Run: `npx vitest run src/pages`
Expected: LandingPage suite passes (the new stripe is `aria-hidden`, invisible to axe and queries).

- [ ] **Step 4: Commit**

```bash
git add src/styles/global.css src/pages/LandingPage.tsx
git commit -m "feat(frontend): landing as civic poster — cream canvas, six-step stripe"
```

---

### Task 10: Auth pages — pine/paper split

**Files:**

- Modify: `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/RegisterPage.tsx`
- Modify: `frontend/src/styles/global.css` (section: "Auth Pages (Login, Register)")

- [ ] **Step 1: TSX — wrap both pages.** In each file, the outermost element is `<div className="auth-page">` containing the `auth-card`. Change to:

```tsx
<div className="auth-page">
  <div className="auth-aside">
    <p className="auth-aside-brand">DigniFi</p>
    <p className="auth-aside-statement">
      Bankruptcy protection exists so people can start again. We help you understand and complete
      the official forms — with dignity.
    </p>
  </div>
  <div className="auth-main">{/* existing auth-card stays here, completely unchanged */}</div>
</div>
```

This is the **only new copy in the project**. It is informational (what the law provides + what the tool does), uses no advice language, and must go to UPL review with the PR description. Do not alter any other text.

- [ ] **Step 2: Replace the "Auth Pages" section CSS** (full replacement; preserve any existing checkbox-group layout rules, recolored to tokens):

```css
/* ============================================================================
   Auth Pages (Login, Register)
   ============================================================================ */

.auth-page {
  display: grid;
  grid-template-columns: 2fr 3fr;
  min-height: 100vh;
}

.auth-aside {
  background-color: var(--color-pine);
  color: var(--color-cream);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: var(--space-8);
  border-right: 6px solid var(--color-gold);
}

.auth-aside-brand {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1.25rem;
  color: var(--color-cream);
  margin-bottom: var(--space-4);
}

.auth-aside-statement {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 1.625rem;
  line-height: 1.35;
  color: var(--color-cream);
  max-width: 24ch;
  margin-bottom: 0;
}

.auth-main {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-paper);
  padding: var(--space-6) var(--space-4);
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background-color: var(--color-white);
  border: 1px solid var(--color-sand);
  border-top: 4px solid var(--color-gold);
  border-radius: var(--radius);
  padding: var(--space-6);
}

.auth-card--wide {
  max-width: 560px;
}

.auth-header {
  margin-bottom: var(--space-5);
}

.auth-title {
  font-family: var(--font-display);
  font-size: var(--text-h1);
  font-weight: 600;
  color: var(--color-pine);
  margin-bottom: var(--space-1);
}

.auth-subtitle {
  color: var(--color-body);
  font-size: var(--text-caption);
  margin-bottom: 0;
}

.auth-footer-text {
  font-size: var(--text-caption);
  color: var(--color-body);
  margin-top: var(--space-4);
  margin-bottom: 0;
  text-align: center;
}

.auth-link {
  color: var(--color-pine);
  font-weight: 500;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.auth-link:hover {
  color: var(--color-rust);
}

.auth-checkbox-group {
  margin-bottom: var(--space-4);
}

.auth-checkbox-label {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
  font-size: var(--text-caption);
  color: var(--color-body);
  cursor: pointer;
}

.auth-checkbox {
  accent-color: var(--color-pine);
  margin-top: 0.2em;
}

.auth-checkbox-text {
  flex: 1;
}

@media (max-width: 1023px) {
  .auth-page {
    grid-template-columns: 1fr;
  }

  .auth-aside {
    display: none;
  }
}
```

- [ ] **Step 3: Verify**

Run: `npx vitest run src/pages`
Expected: Login/Register suites pass. If a test asserts the DOM hierarchy `auth-page > auth-card` directly, update it to traverse through `auth-main`. axe note: `.auth-aside` text is real content, intentionally visible to screen readers; on tablet/mobile it is `display: none` (removed from the a11y tree, not merely visually hidden — acceptable for brand copy).

- [ ] **Step 4: Commit**

```bash
git add src/styles/global.css src/pages/LoginPage.tsx src/pages/RegisterPage.tsx
git commit -m "feat(frontend): split auth layout — pine mission panel, paper form"
```

---

### Task 11: Documents pages + remaining inline-style migration

**Files:**

- Modify: `frontend/src/styles/global.css` (append "Documents & Misc" section)
- Modify: `frontend/src/components/documents/FileDropZone.tsx`
- Modify: `frontend/src/components/documents/UploadQueue.tsx`
- Modify: `frontend/src/pages/DocumentUploadPage.tsx`
- Modify: `frontend/src/App.tsx` (ErrorBoundary)
- Modify: `frontend/src/components/wizard/steps/DebtsStep.tsx` ("From scan" badge)

- [ ] **Step 1: Append new CSS section to global.css**:

```css
/* ============================================================================
   Documents & Misc
   ============================================================================ */

.document-page {
  max-width: 640px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-4);
}

.text-muted {
  font-size: var(--text-caption);
  color: var(--color-muted);
}

.text-error {
  color: var(--color-rust);
}

.text-success {
  color: var(--color-sage);
  font-weight: 600;
}

.page-actions {
  margin-top: var(--space-6);
  display: flex;
  gap: var(--space-4);
}

.file-drop-zone {
  border: 2px dashed var(--color-gold);
  border-radius: var(--radius);
  background-color: var(--color-white);
  padding: var(--space-6);
  text-align: center;
  cursor: pointer;
}

.file-drop-zone[aria-disabled='true'] {
  cursor: not-allowed;
  opacity: 0.5;
}

.upload-queue {
  list-style: none;
  padding: 0;
}

.upload-queue-item {
  padding: var(--space-2) 0;
  display: flex;
  gap: var(--space-4);
}

.draft-badge {
  font-family: var(--font-body);
  font-weight: 500;
  font-size: 0.75rem;
  background-color: var(--color-sand-tint);
  color: var(--color-pine);
  border: 1px solid var(--color-gold);
  border-radius: var(--radius);
  padding: 0 6px;
  margin-left: 8px;
  vertical-align: middle;
}

.error-boundary {
  padding: var(--space-6);
  max-width: 600px;
  margin: 0 auto;
}

.error-boundary-detail {
  font-size: 0.8rem;
  overflow: auto;
  background-color: var(--color-sand-tint);
  padding: var(--space-4);
}
```

- [ ] **Step 2: FileDropZone.tsx** — replace the inline styles (`FileDropZone.tsx:35-45`):

```tsx
<div
  role="button"
  tabIndex={0}
  aria-label="Drop files here or click to upload"
  aria-disabled={disabled}
  onDrop={handleDrop}
  onDragOver={(e) => e.preventDefault()}
  onClick={() => !disabled && inputRef.current?.click()}
  onKeyDown={(e) => e.key === 'Enter' && !disabled && inputRef.current?.click()}
  className="file-drop-zone"
>
  <p>Drop PDF, JPEG, or PNG files here</p>
  <p className="text-muted">or click to browse</p>
```

(The `disabled` opacity/cursor now flows from the `aria-disabled` attribute selector.)

- [ ] **Step 3: UploadQueue.tsx** — replace the inline styles (`UploadQueue.tsx:60-63`):

```tsx
<ul aria-label="Upload queue" className="upload-queue">
  {items.map((item) => (
    <li key={item.docId} className="upload-queue-item">
```

- [ ] **Step 4: DocumentUploadPage.tsx** — replace all six inline styles (`DocumentUploadPage.tsx:71-110`):

```tsx
<main className="document-page">
  <h1>Upload your documents</h1>
  <p>{/* existing copy unchanged */}</p>
  <p className="text-muted">
    Your documents are processed locally and never sent to any external service.
  </p>
  {error && (
    <p role="alert" className="text-error">
      {error}
    </p>
  )}
  ...
  {allComplete && summary && (
    <p role="status" className="text-success">
      {summary}
    </p>
  )}
  <div className="page-actions">
    <button
      onClick={() => navigate('/intake')}
      disabled={uploading}
      className="button button--primary button--md"
    >
      {allComplete ? 'Continue to intake' : 'Skip for now'}
    </button>
  </div>
</main>
```

- [ ] **Step 5: App.tsx ErrorBoundary** — replace the two inline styles (`App.tsx:36-41`):

```tsx
<div className="error-boundary">
  <h1>Something went wrong</h1>
  <p>We encountered an unexpected error. Please try refreshing the page.</p>
  <pre className="error-boundary-detail">{this.state.error.message}</pre>
  <button
    onClick={() => (window.location.href = '/')}
    className="button button--outline button--md"
  >
    Return Home
  </button>
</div>
```

- [ ] **Step 6: DebtsStep.tsx "From scan" badge** — replace the inline style (`DebtsStep.tsx:195-208`):

```tsx
{
  debt.is_draft && (
    <span aria-label="Pre-filled from document scan" className="draft-badge">
      From scan
    </span>
  );
}
```

- [ ] **Step 7: Verify**

Run: `npm test`
Expected: full suite green (document/debts suites query by role/label).

- [ ] **Step 8: Commit**

```bash
git add src/styles/global.css src/components/documents/ src/pages/DocumentUploadPage.tsx src/App.tsx src/components/wizard/steps/DebtsStep.tsx
git commit -m "refactor(frontend): migrate inline styles to token-based classes"
```

---

### Task 12: PostTaskSurvey retoken

**Files:**

- Modify: `frontend/src/components/survey/PostTaskSurvey.css`

- [ ] **Step 1: Retoken.** The file's only raw hex is `#166534` (success green, line ~120) → replace with `var(--color-sage)`. Then sweep the file for non-hex colors (named colors, `rgb()`) and font-families: map grays → `var(--color-muted)`/`var(--color-sand)`, blues → `var(--color-pine)`, set headings to `var(--font-display)`, and any `border-radius` > 0 → `var(--radius)`.

- [ ] **Step 2: Verify + commit**

Run: `npx vitest run src/components/survey`

```bash
git add src/components/survey/PostTaskSurvey.css
git commit -m "refactor(frontend): retoken PostTaskSurvey styles"
```

---

### Task 13: Verification gates

**Files:** none created — this task only verifies and fixes regressions found.

- [ ] **Step 1: Grep gates**

```bash
cd /Volumes/Containers/DigniFi/frontend
grep -rn "style={{" src --include="*.tsx"
```

Expected: exactly one match — `pages/FormDashboard.tsx` progress-fill dynamic width (documented exception).

```bash
grep -rn "#[0-9a-fA-F]\{3,6\}" src --include="*.css" | grep -v "tokens.css"
```

Expected: no matches (all colors flow from tokens).

```bash
grep -rn "box-shadow" src --include="*.css" | grep -v "tokens.css"
ls src/index.css src/App.css 2>&1
```

Expected: no box-shadow matches; both scaffold files report "No such file or directory".

- [ ] **Step 2: Full frontend suite**

Run: `npm test`
Expected: 171 tests pass, including all vitest-axe accessibility suites.

- [ ] **Step 3: E2E persona journeys**

```bash
cd /Volumes/Containers/DigniFi && docker compose up -d
cd frontend && npm run e2e
```

Expected: 5/5 persona journeys green. (Remember: Vite HMR in Docker is stale after structural changes — restart the frontend container first: `docker compose restart frontend`.)

- [ ] **Step 4: Manual sweep checklist** (at 1024px and 1440px, `npm run dev` or Docker):

- [ ] Landing: cream poster, pine hero border, six-segment stripe, pine footer
- [ ] Login + Register: pine aside with gold spine ≥1024px; aside hidden below
- [ ] All 6 wizard steps: pine header, gold/sand progress, white content card, baseline inputs
- [ ] Form dashboard: spine colors change with status (generate → gold, mark filed → sage)
- [ ] UPL modal: pine border, sand acknowledgment band, gold confirm
- [ ] Documents: gold dashed drop-zone; "From scan" badge in Debts step
- [ ] Fee waiver page + survey: calm core, no unstyled regressions
- [ ] Keyboard pass: gold focus ring visible on every interactive element

- [ ] **Step 5: Fix anything found, then final commit**

```bash
git add -A
git commit -m "fix(frontend): visual QA corrections from New Deal Civic sweep"
```

(Skip if nothing to fix.)

---

## Out of scope (from spec)

Dark mode · copy rewrites beyond the one auth statement · mobile-first redesign · logo/brandmark · component behavior changes.
