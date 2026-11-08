---
name: New Deal Civic
description: Trauma-informed Chapter 7 filing interface, where civic authority reads as care
colors:
  pine: '#2e4034'
  gold: '#d9a441'
  cream: '#f2ecd9'
  paper: '#fdfcf8'
  white: '#ffffff'
  body: '#4d5345'
  muted: '#5d6356'
  rust: '#9c4a2e'
  sage: '#5b7c52'
  sand: '#e7e2d2'
  sand-tint: '#f6f3e9'
  line: '#b8b2a0'
  scrim: 'rgba(46, 64, 52, 0.55)'
typography:
  display:
    fontFamily: "'Jost', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: 'clamp(2.125rem, 4vw + 1rem, 3rem)'
    fontWeight: 600
    lineHeight: 1.15
  h1:
    fontFamily: "'Jost', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: '1.5rem'
    fontWeight: 600
    lineHeight: 1.25
  h2:
    fontFamily: "'Jost', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: '1.1875rem'
    fontWeight: 500
    lineHeight: 1.25
  h3:
    fontFamily: "'Jost', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: '1rem'
    fontWeight: 500
    lineHeight: 1.25
  body:
    fontFamily: "'Public Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: '1rem'
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "'Public Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: '0.875rem'
    fontWeight: 500
    lineHeight: 1.6
  caption:
    fontFamily: "'Public Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: '0.875rem'
    fontWeight: 400
    lineHeight: 1.6
  button:
    fontFamily: "'Jost', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: '1rem'
    fontWeight: 600
rounded:
  radius: '0'
spacing:
  space-1: '0.25rem'
  space-2: '0.5rem'
  space-3: '0.75rem'
  space-4: '1rem'
  space-5: '1.5rem'
  space-6: '2rem'
  space-7: '2.5rem'
  space-8: '3rem'
components:
  button-primary:
    backgroundColor: '{colors.gold}'
    textColor: '{colors.pine}'
    typography: '{typography.button}'
    rounded: '{rounded.radius}'
    padding: '0.625rem 1.625rem'
  button-outline:
    backgroundColor: 'transparent'
    textColor: '{colors.pine}'
    typography: '{typography.button}'
    rounded: '{rounded.radius}'
    padding: '0.625rem 1.625rem'
  button-outline-hover:
    backgroundColor: '{colors.pine}'
    textColor: '{colors.cream}'
  button-disabled:
    backgroundColor: '{colors.sand}'
    textColor: '{colors.muted}'
  button-sm:
    padding: '0.25rem 0.75rem'
  button-lg:
    padding: '0.75rem 2rem'
  input-default:
    backgroundColor: '{colors.white}'
    textColor: '{colors.pine}'
    typography: '{typography.body}'
    rounded: '{rounded.radius}'
    padding: '0.625rem 0.75rem'
  input-readonly:
    backgroundColor: '{colors.sand}'
    textColor: '{colors.pine}'
  app-header:
    backgroundColor: '{colors.pine}'
    textColor: '{colors.cream}'
    height: '44px'
  wizard-header:
    backgroundColor: '{colors.pine}'
    textColor: '{colors.cream}'
    padding: '1rem 1.5rem'
  wizard-content:
    backgroundColor: '{colors.white}'
    rounded: '{rounded.radius}'
    padding: '{spacing.space-6}'
  step-marker:
    backgroundColor: '{colors.white}'
    textColor: '{colors.muted}'
    size: '3rem'
  step-marker-current:
    backgroundColor: '{colors.gold}'
    textColor: '{colors.pine}'
    size: '3rem'
  step-marker-completed:
    backgroundColor: '{colors.pine}'
    textColor: '{colors.cream}'
    size: '3rem'
  form-card:
    backgroundColor: '{colors.white}'
    rounded: '{rounded.radius}'
    padding: '{spacing.space-4}'
  landing-card:
    backgroundColor: '{colors.paper}'
    rounded: '{rounded.radius}'
    padding: '{spacing.space-5}'
  upl-disclaimer-banner:
    backgroundColor: '{colors.sand-tint}'
    textColor: '{colors.body}'
    rounded: '{rounded.radius}'
    padding: '{spacing.space-4}'
  upl-disclaimer-inline:
    backgroundColor: '{colors.sand-tint}'
    textColor: '{colors.body}'
    typography: '{typography.caption}'
    padding: '0.5rem 0.75rem'
  error-box:
    backgroundColor: '{colors.white}'
    textColor: '{colors.body}'
    padding: '{spacing.space-4}'
  upl-modal:
    backgroundColor: '{colors.paper}'
    rounded: '{rounded.radius}'
    width: 'min(100%, 560px)'
  auth-card:
    backgroundColor: '{colors.white}'
    padding: '{spacing.space-6}'
    width: 'min(100%, 420px)'
  draft-badge:
    backgroundColor: '{colors.sand-tint}'
    textColor: '{colors.pine}'
    typography: '{typography.label}'
    padding: '0 6px'
  file-drop-zone:
    backgroundColor: '{colors.white}'
    padding: '{spacing.space-6}'
---

# Design System: New Deal Civic

<!-- Derived from the shipped code on develop (478868d): frontend/src/styles/tokens.css and global.css, read against the approved spec docs/superpowers/specs/2026-06-10-frontend-aesthetics-design.md. Token keys match the CSS custom properties: colors.pine is var(--color-pine), spacing.space-4 is var(--space-4), typography.h1 uses var(--text-h1), rounded.radius is var(--radius). -->

## Overview

**Creative North Star: "The Federal Clerk's Desk"**

A public office that takes the filer seriously. New Deal Civic borrows from WPA-era civic design (flat geometry, poster stripes, sturdy color) because a fresh start is a legal right, not a favor, and the interface should look like that sentence. It is proudly institutional without being cold: civic gravity, not civic gray.

The system runs at two intensities: a bold shell and a calm core. The shell carries the identity at full strength: the pine header band, the progress row, the gold buttons, and the landing page, which is the one page that shouts. The core is where a filer spends most of an hour entering income and amounts owed, and it goes quiet: a near-white page, white fields, 1px sand borders, pine text. Color appears only where it guides. Gold marks the action and the step you are on, rust marks a correction, and sage marks something settled.

Everything is square and flat. There are no rounded corners and no shadows; depth comes from three warm whites, from borders, and from pine bands. Jost, a Futura revival, builds the structure: headings, buttons, the wordmark. Public Sans, the US Web Design System's typeface, carries everything a filer reads or types. The approved spec rejected generic SaaS (navy and teal, rounded cards), condensed all-caps display type, and typewriter costume, of which only the input's pine base line survives.

**Key Characteristics:**

- Square corners everywhere (`var(--radius)` is 0); the only round shapes are loading spinners.
- No shadows anywhere. Depth comes from surface steps (cream, paper, white) and borders (1px sand for quiet edges, 2px pine for emphasis).
- Bold shell, calm core: pine bands and gold on the frame, quiet white work surfaces inside it.
- Gold is the action and progress color: primary buttons, the current step, completed progress. It never carries text on a light surface.
- Rust for errors and sage for success; never alarm red.
- Jost for headings, buttons and the wordmark; Public Sans for everything read or typed.
- No text smaller than 14px (0.875rem).
- Motion is 150ms color and border feedback plus loading spinners, all collapsed under reduced motion.
- Light only: there is no dark theme, like the paper forms themselves.

## Colors

A sturdy civic palette: one structural pine, one action gold, two state colors, and a ramp of warm whites and sands that keep the work surface quiet.

### Primary

- **Courthouse Pine** (#2e4034): The structural voice. Header and auth bands, the landing footer, every heading, form labels and entered text, links, outline buttons, the 2px emphasis border on landing cards, the modal and the drop zone, and the focus ring on light surfaces. Recorded contrast: 10.77:1 on paper, 9.36:1 on cream.

### Secondary

- **Relief Brass** (#d9a441): The action and progress color. The primary button fill, the current step marker, completed step connectors, the dashboard progress fill, the 2px underline beneath the app header, the landing poster stripe and card icons, the draft badge's border, and the focus ring on pine surfaces. Pine on gold and gold on pine are both 4.92:1. Gold on a light surface is decorative only: 2.19:1 on paper, 1.74:1 on sand.

### Tertiary

- **Honest Alert** (#9c4a2e): Errors. Field borders and base lines in error, error messages, the error box border and icon, the required-field asterisk, and row-removal actions. Warm, not alarm red: a correction, not a siren. 5.96:1 on paper. Beyond errors, rust marks required fields and removal actions, and auth-page links turn rust on hover.
- **Fresh Start** (#5b7c52): Success. The filed check and the filed form card's left edge, success text, and the survey's thank-you. 4.60:1 on paper, which passes AA by 0.10, so neither color may be lightened.

### Neutral

- **Poster Cream** (#f2ecd9): The landing canvas, and the color of text, icons and the step checkmark on pine. Also the hover fill of the means-test toggle and the fill of its result block.
- **Clean Sheet** (#fdfcf8): The page. The body background behind the wizard, dashboard, auth form panel, review sections, landing cards and the UPL modal.
- **Form White** (#ffffff): The fill-in layer. Inputs, the wizard's content panel, the auth card, form cards, the drop zone, the error box and pending step markers.
- **Courthouse Ink** (#4d5345): Body text. 7.75:1 on paper.
- **Muted Ink** (#5d6356): Help text, captions, save status, review field labels. The lightest color allowed to carry text: 6.04:1 on paper.
- **Sand Border** (#e7e2d2): Quiet 1px borders and dividers, the progress track, the disabled button fill, and the read-only input fill.
- **Sand Tint** (#f6f3e9): The disclaimer band. UPL disclaimers, the info box, the modal's acknowledgment block, the draft badge and the error boundary's detail panel.
- **Divider Line** (#b8b2a0): The quiet frame around inputs and answer fields, and the rules and indent line on the Assets step. A frame color, not a text color.
- **Overlay Scrim** (rgba(46, 64, 52, 0.55)): Pine at 55%, behind the UPL modal and the full-screen loading overlay.

### Named Rules

**The Gold Means Go Rule.** Gold marks action and progress: the primary button, the step you are on, the steps you have finished. It never carries normal-size text on a light surface (it tops out near 3.95:1 there); on light surfaces it is a fill or a decorative edge. Links on light surfaces are pine.

**The Three Whites Rule.** Cream is the poster (the landing canvas), paper is the page, white is what you fill in. A new surface takes the white its role calls for; it never introduces a fourth.

**The Rust Rule.** Rust is the only error color. Never alarm red (`#ef4444`, `#dc2626` or any red-500 family): a filer disclosing debts needs a correction, not an alarm.

## Typography

**Display Font:** Jost (with -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif)
**Body Font:** Public Sans (with -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif)

**Character:** Jost brings 1930s geometric structure, the actual typeface of the era the palette borrows from. Public Sans was designed for government-service legibility. Together they read as a competent public institution: clear, unhurried, a little formal, never stiff. Both are self-hosted through `@fontsource` at weights 400, 500 and 600, so a bankruptcy site makes no third-party font request.

### Hierarchy

- **Display** (Jost 600, clamp(2.125rem, 4vw + 1rem, 3rem), line-height 1.15, max 18ch): The landing headline only.
- **H1** (Jost 600, 1.5rem, line-height 1.25): Page and step titles, the dashboard and auth titles.
- **H2** (Jost 500, 1.1875rem, line-height 1.25): Section headings. The named title classes (section titles, landing card titles, the modal title) set this size at 600.
- **H3** (Jost 500, 1rem, line-height 1.25): Minor headings. Form card titles set it at 600.
- **Body** (Public Sans 400, 1rem, line-height 1.6, Courthouse Ink): Everything a filer reads. The landing subtitle steps up to 1.125rem with a 55ch measure.
- **Label** (Public Sans 500, 0.875rem, Courthouse Pine): Form field labels and the draft badge.
- **Caption** (Public Sans 400, 0.875rem, Muted Ink): Help text, errors (in rust), save status, disclaimers, card descriptions and metadata. The most used size in the system.
- **Button** (Jost 600, 1rem): Button faces. Small buttons drop to 0.875rem, large ones rise to 1.125rem.

### Named Rules

**The 14px Floor Rule.** Nothing smaller than 0.875rem (`var(--text-caption)`) carries text. A new size below it is a defect, not a choice. `docs/TRAUMA_INFORMED_DESIGN.md` asks for a 16px minimum: body copy here is 16px, but help text, errors, captions and disclaimers are 14px, as `tokens.css` and the approved spec set them. Which rule governs those is open (DIG-182); until it is settled, build to `tokens.css`.

**The Jost Builds, Public Sans Speaks Rule.** Jost carries structure: headings, buttons, the wordmark, step numbers, card and section titles. Public Sans carries everything a filer reads or types: body copy, labels, help text, errors, input values, the header's name and sign-out link.

**The Mixed Case Rule.** Mixed case everywhere; all-caps display was rejected as shouty. Two small labels currently break this (the progress step's status line and the means-test toggle, both uppercase with 0.04em tracking). They are drift to remove, not a pattern to copy.

## Layout

Desktop-first. Base styles target 1024px and wider, and two breakpoints step down: at 1023px the landing cards stack to one column, the auth page drops its pine panel and the wizard container goes full width with 1.5rem gutters; at 767px the gutters narrow to 1rem and the landing hero tightens.

Work happens in one centered column. The wizard and legal pages run at 720px, the document upload, filing-fee page and dashboard empty states at 640px, and the SOFA page at 800px. Only the landing page and the form dashboard widen, to 1100px. The auth card is 420px (560px for the wide variant) and the UPL modal 560px.

Spacing follows a 4px-based scale from `space-1` (0.25rem) to `space-8` (3rem). Paragraphs and form fields sit `space-4` apart, form sections `space-6`, and panels pad at `space-4` to `space-6`. Grids are few: the landing's three value cards, the dashboard's auto-fill cards (minimum 300px), and the review step's auto-fit fields (minimum 220px). Tap targets on the Assets step's yes/no choices and buttons are at least 44px, and the app header is 44px tall.

### Named Rules

**The One Column Rule.** A filer works in a single centered column. Width grows only where cards need a grid (landing, dashboard); a work step never splits into side-by-side panels.

## Elevation & Depth

Flat by default. There is no `box-shadow` anywhere in the system. Depth comes from the three whites stacked in order (cream canvas, paper page, white fill-in surface), from borders, and from solid pine bands for the header, auth panel and landing footer. Overlays use the pine scrim, not a shadow. Borders come in two weights: 1px Sand Border for quiet edges and dividers, and 2px Courthouse Pine for emphasis (landing cards, the UPL modal, outline buttons, the dashed drop zone, the input's base line). Two heavier marks exist on purpose: the 4px pine rule under the landing hero and the 4px progress connectors.

### Named Rules

**The Administrative Flat Rule.** No `box-shadow`, ever. A component reaching for a shadow takes a border and a surface step instead. Focus rings are outlines, not shadows.

**The Two Weights Rule.** Borders are 1px sand (quiet) or 2px pine (emphasis). Buttons carry a transparent 2px border at rest so a hover can reveal it without moving the layout.

## Shapes

Square, without exception: every corner uses `var(--radius)`, which is 0. The only circles are loading spinners. The form language is the printed form: rectangles, rules and frames. A text field is a white box with a quiet Divider Line frame and a solid 2px pine base line, the "fill in this line" nod. Progress is drawn as square 3rem markers joined by 4px bars, and the landing page repeats it as a poster stripe of six alternating gold and pine segments (8px tall, at most 360px wide). The dashboard's progress bar is a 6px sand track with a gold fill, and the drop zone is marked by a 2px dashed pine border.

## Components

### Buttons

Official and sturdy, like a form's action stamp.

- **Shape:** Square (radius 0), with a 2px border that is transparent at rest.
- **Primary:** Relief Brass fill, Courthouse Pine text, Jost 600 at 1rem, padding 0.625rem 1.625rem. Hover reveals the 2px pine border; the fill does not change. For the main action in its context (Continue, Generate All, a form card's Download).
- **Outline:** Transparent, 2px pine border, pine text. Hover fills it pine with cream text. The workhorse for every other action (Answer Questions, Mark as Filed, Try Again, "+ Add Contract", Remove).
- **Focus:** The global ring: 2px pine outline, offset 2px.
- **Disabled:** Sand fill, Muted Ink text, no border, not-allowed cursor. Never opacity.
- **Sizes:** Small (0.875rem, padding 0.25rem 0.75rem), medium (the default), large (1.125rem, padding 0.75rem 2rem), plus a full-width modifier.
- **Loading:** The button disables itself, swaps its label for the loading text ("Loading..." by default) and centers a spinner (sand track, pine head) over it. `.button--loading` is meant to hide the label, but `.button:disabled` outranks it, so the label shows in muted text under the spinner and the width follows the loading text. That is drift; don't build on it.
- **Unstyled variants:** `secondary` and `text` exist in the component's props but have no styles, so they fall back to the browser's default button. Use outline until they are designed.

### Inputs / Fields

- **Anatomy:** Label above (Public Sans 500, 0.875rem, pine; a rust asterisk marks required), field, then help text (caption, Muted Ink) and the error message (caption, rust). FormField, FormTextarea and FormSelect render this anatomy.
- **Style:** Form White fill, 1px Divider Line frame, 2px pine base line, square, padding 0.625rem 0.75rem, Public Sans 1rem in pine. A leading icon sits inset at 0.75rem and pushes the text to 2.5rem.
- **Hover:** The whole frame turns pine.
- **Focus:** 2px pine outline, offset 2px.
- **Error:** Frame and base line turn rust; the message appears below. Never a red fill.
- **Read-only:** Sand fill with a Divider Line base line and a not-allowed cursor (the prefilled account email).
- **Choices:** Native checkboxes and radios tinted pine (`accent-color`). On the Assets step they are 20px inside rows at least 44px tall.

### Cards / Containers

- **Corner Style:** Square (radius 0) throughout.
- **Form card (dashboard):** Form White, 1px sand border, padding 1rem, a Jost 600 title. Status recolors the 1px left edge: gold when generated or downloaded, sage when filed. The card's status text says the same thing, so the edge is decoration, not the only signal.
- **Landing value card:** Clean Sheet with a 2px pine border, padding 1.5rem, a 2rem gold icon, a Jost 600 title at H2 size and caption text.
- **Wizard content panel:** Form White, 1px sand border, padding 2rem.
- **Review section:** Clean Sheet, 1px sand border, padding 1rem 1.5rem, its title underlined by a 1px sand rule.
- **Info box:** Sand Tint, 1px sand border, padding 1rem, a pine icon and a Jost 600 title.
- **Error box:** Form White with a 1px rust border, a rust icon and Jost 600 title, the message in Courthouse Ink, and a muted dismiss control that turns pine on hover.
- **Shadow Strategy:** None; see Elevation & Depth.

### Navigation

- **App header:** A 44px pine band with a 2px gold underline. The wordmark is Jost 1.125rem in cream with 0.01em tracking and turns gold on hover. The user's name and the sign-out link sit at the right in Public Sans caption, cream, and the link turns gold on hover.
- **Wizard header:** A pine band holding the cream Jost title, a gold caption subtitle and the progress indicator.
- **Progress indicator:** An ordered row of 3rem square markers joined by 4px connectors. Pending: white with a 2px sand border and a muted Jost 600 number. Current: gold fill, pine border, pine number. Completed: pine fill, cream border, cream checkmark, with a gold connector behind it. Step names are cream caption, and the current one is gold at 600.
- **Skip link:** A pine box with cream text that appears top-left on focus, ringed in gold.
- **Links:** Pine, underlined with a 2px offset. Auth-page links add weight 500 and turn rust on hover.
- **Footers:** The landing footer is a pine band with the disclaimer in cream caption. The site footer is a caption line carrying the source-code link.
- **Focus on pine:** Inside the wizard header, the auth panel and the landing footer, focus rings switch to gold. The app header is missing from that list, so its wordmark and sign-out link get a pine ring on pine, which can't be seen. That is an accessibility defect, not the pattern: a new pine surface joins the gold-ring list.

### UPL Disclaimer

The legal-information notice appears at every decision point as quiet reassurance, never a warning.

- **Inline:** A Sand Tint chip with a 1px sand border, padding 0.5rem 0.75rem, a 1rem pine icon and caption text in Courthouse Ink.
- **Banner:** The same surface as a full-width block with padding 1rem, a 1.25rem pine icon, and a Jost 600 caption-size title over caption text.
- **Checkbox:** A pine-tinted native checkbox whose label is the disclaimer.

### UPL Confirmation Modal

The gate before any court form is prepared: Generate All and a pending form card's Generate both open it, and nothing is generated until the filer ticks the acknowledgment and presses Continue. Clean Sheet with a 2px pine border, at most 560px wide and 90% of the viewport tall, over the pine scrim. A 1px sand rule separates its header (a Jost 600 H2-size title and a muted close control) and its footer (actions aligned right). Inside, the acknowledgment checkbox sits in a Sand Tint block with a 1px sand border.

### Means-Test Preview

A compact, collapsible estimate above the wizard step. Clean Sheet with a 1px sand border. Its full-width toggle is Jost 600 caption in pine and fills cream on hover, and its chevron rotates 180° when open. The result is a cream block with a 1.25rem pine icon (rust when the result needs review). Details are a label and value list: labels in Muted Ink, values right-aligned in pine at 600.

### Landing Poster

The one page that shouts. A cream canvas holds the display headline in pine (max 18ch) and a 1.125rem subtitle, followed by the call-to-action buttons and the six-segment gold and pine poster stripe. A 4px pine rule closes the hero. Below it sit three value cards, and the page ends with a pine footer band.

### Auth Split

A two-column page (2fr / 3fr). The pine panel carries the cream brand line and a mission statement in Jost 500 at 1.625rem (line-height 1.35, max 24ch). The paper panel centers a Form White card with a 1px sand border and padding 2rem. Below 1024px the pine panel is hidden.

### Small Pieces

- **Draft badge:** A Sand Tint tag with a 1px gold border and pine label text (Public Sans 500, 0.875rem), padding 0 6px. It marks a debt drafted from a scanned document.
- **File drop zone:** Form White with a 2px dashed pine border and padding 2rem. Pine because gold fails non-text contrast for an interactive boundary on a light surface. When disabled it drops to 50% opacity.
- **Loading overlay:** The pine scrim over the whole screen with a cream spinner.

## Do's and Don'ts

### Do:

- **Do** take every color, space, radius and transition from `tokens.css` (`var(--color-pine)`, `var(--space-4)`, `var(--radius)`, `var(--transition-fast)`). Component CSS carries no hex values.
- **Do** declare a new token in `tokens.css` before you use it. A `var()` with no declaration silently drops the whole property (the SOFA page's section borders are missing for this reason).
- **Do** give the main action a gold fill with pine text, and every other action the pine outline.
- **Do** use a 2px pine focus ring with a 2px offset on light surfaces, and a gold ring on pine surfaces.
- **Do** pick surfaces by role: cream for the poster, paper for the page, white for what the filer fills in.
- **Do** use rust for errors and sage for success, and keep the recorded contrast ratios when touching either.
- **Do** keep every text size at 0.875rem or larger.
- **Do** limit transitions to color, background and border at 150ms; the global reduced-motion rule collapses them.
- **Do** keep tap targets at least 44px on wizard choices and their buttons.

### Don't:

- **Don't** add `box-shadow` to anything. Depth is a border plus a surface step.
- **Don't** round a corner. `var(--radius)` is 0; spinners are the only circles.
- **Don't** put gold text, or a gold focus ring, on a light surface (2.19:1 on paper).
- **Don't** use alarm red (`#ef4444`, `#dc2626`, any red-500) for errors, warnings or emphasis.
- **Don't** set labels, buttons or navigation in uppercase. The two uppercase labels in the code today are drift.
- **Don't** use the Button `secondary` or `text` variants until they are styled; use `outline`.
- **Don't** show a disabled button by lowering its opacity; use the sand fill and muted text.
- **Don't** add a third typeface or load fonts from a CDN; Jost and Public Sans are self-hosted.
- **Don't** bring in the rejected looks: rounded SaaS cards, navy and teal, gradients, condensed all-caps display type, or typewriter costume beyond the input's base line.
