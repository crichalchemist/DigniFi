# Forms step 3a2: drawing engine

- **Status:** approved by the owner, 2026-10-17. Factual corrections from the code survey followed the same day (§3, §4.3, §4.5, §8). Corrections from the build followed on 2026-10-19 (§4.3, §4.5, §5.2, §5.3, §6, §8, §9, §10, §11). Four of them change what was approved, and each says so: "This is a build ruling for the owner to review."
- **Drawn from:** the step 3 umbrella spec, `docs/superpowers/specs/2026-10-16-forms-step3-design.md`: §4.6, §5.4, §6.1 and §8.2 risk 1.
- **Branch:** `feat/forms-step3a2`, from develop `06111b6` (3a1 merged). The PR targets develop.
- **Tags** such as `[Q8]` trace each part to the umbrella's map of answers and tickets.

The umbrella settles what 3a2 delivers. This spec turns it into a design for the code as it stands, records the owner's three calls, and changes one recorded decision, the drawing method, with the evidence for the change (§3).

## 1. What 3a2 does

1. **Every form prints through one engine** `[Q8]`. Each widget gets its own value, drawn with the template's own layout, and the page is flattened, so the packet has no fillable fields left.
2. **Refusals instead of silent damage.** A letter the form's font can't print, or a value too long for its box even in small print, is refused in plain words, and the dashboard links each refusal to the step or page that fixes it. Today the first prints as "?" and the second is cut off.
3. **Extra rows** `[Q8]` `[Q9]` continue on copies of the form's extra page, or on an attached sheet when the template has none. This is proven on synthetic schemas; the first real rows arrive in 3e2, 3b and 3c.
4. **Filed forms redraw exactly what was filed**, page copy by page copy.
5. **Generate All checks without drawing** `[DIG-137]`, and the browser stops retrying it. Download draws.
6. **The oracle is rebuilt** to read what is drawn on the page.
7. **PyMuPDF is pinned.**

Nothing in 3a2 deploys: production waits for steps 3 to 5 and DIG-146.

## 2. The owner's calls

The umbrella left the font to this spec. Two more calls came up while scoping. The owner answered all three on 2026-10-17.

- **3a2.Q1, letters the form can't print: refuse in plain words.**
  - The forms keep the template's own font.
  - A value with a letter that font can't draw is refused. The refusal names the letter and the box, and sends the filer to the step or page that holds the value.
  - Nothing ever prints as "?". A Unicode font can follow in a later PR if real filers need it.
- **3a2.Q2, a value too long for its box: shrink, then refuse.**
  - The value shrinks down to 6 pt and wraps in multi-line boxes.
  - If it still doesn't fit, it is refused in plain words, naming the box and the step or page that fixes it.
  - Nothing is ever cut off.
- **3a2.Q3, timing: check without drawing.**
  - Generate All, Generate and Regenerate run every check drawing runs, then store the result without drawing. Download draws.
  - A command times a full persona packet locally against a budget, and the deploy steps time it on the Eco dyno.
  - The browser stops retrying Generate All.

## 3. Why the drawing method changes `[SPIKE]`

The umbrella (§5.4, Appendix A row SPIKE) recorded the method from two flattening spikes: PyMuPDF `insert_text` at each widget's rectangle, then `delete_widget` on every widget. Those spikes tested only plain text and checkboxes. Testing more of the 17 packet templates on 2026-10-17 showed the method fails three ways:

- **It drops the template's layout.**
  - 547 text boxes are right-aligned and 51 are comb boxes, which spread one character into each printed cell. The SSN on Forms 101 and 121 is in a comb box.
  - 94 boxes are multi-line.
  - `insert_text` draws one left-aligned line, so amounts move left, Form 121's SSN crams into the first cells, and descriptions run off the box.
  - Today's filler (pypdf 6.13.1) honours alignment and comb cells. The exception is a comb box whose `MaxLen` is set on its parent field, which pypdf doesn't read: Schedule D's two `account number` boxes would print every digit in the first cell. The engine reads `MaxLen` from the parent too (§4.3). pypdf wraps only auto-size boxes, so 3a2's check does the wrapping itself.
- **It erases parts of the form.** On Form 103B the empty checkbox squares are drawn by the widgets themselves, so deleting an unticked widget removes its square from the printed page.

Speed did not decide it. With every widget of the 17 templates filled, the spike's `insert_text` took 12.1 s locally against 5.5 s for the method below, but it made one call per widget, which could be made faster.

**The method 3a2 uses:**

- pypdf builds each widget's appearance from that widget's own value, with the code today's filler already uses.
- PyMuPDF's `Document.bake()` turns every remaining widget into page content.

Tested on the same templates, this method:

- keeps alignment and comb cells, and draws pre-wrapped lines whole at 10, 8 and 6 pt;
- prints different values in shared-name boxes, such as Schedule I's two "Assistance 8f" boxes and A/B's two "24.1" boxes;
- renders ticks with the template's own check mark;
- keeps 103B's squares;
- leaves no fillable field.

The umbrella's goal is unchanged: one printing path, values drawn per widget, the page flattened.

## 4. The engine `[Q8]`

### 4.1 Today

`PDFFormFiller.fill(form_type, values)` (`apps/forms/services/pdf_filler.py`) takes `{full name: value}`. It sets the field's `/V`, builds an appearance with pypdf's `TextStreamAppearance` (an internal API, pinned and checked by `test_pdf_filler.py`), and returns a fillable PDF. Every widget that shares a full name shows the same value.

Two kinds of silent damage happen today:

- **A value wider than a fixed-size box is clipped at the box's edge.** "Sentinel" prints as "Sen" in Schedule D's entry-number box.
  - pypdf wraps only the 10 auto-size boxes, so in a fixed-size multi-line box, such as Form 107's descriptions, a long value prints as one line and is cut off too.
  - The seeded personas hit this today: the email on Form 101 for James, DeShawn and Andrés, the annualized income on 122A-1 lines 12b and 13c for Maria and Priya, and one 122A-2 amount for Priya.
- **A letter outside the font's encoding prints as "?".** Wąsowicz prints as "W?sowicz", Dvořák as "Dvo?ák" and Nguyễn as "Nguy?n". pypdf logs a warning and nothing else happens.

### 4.2 Widgets and their address

- **A widget is (page, tag).** The field index (`data/forms/field_index/<stem>.index.json`) gives each widget a tag that is unique on its page (`T1`, `T2`, …) and its rectangle.
  - The index is not in the PDF's widget order: 14 of the 17 templates differ.
  - The engine therefore finds each template widget's index row by page and rectangle, within 0.6 pt. This match is one-to-one on all 3,003 widgets.
- **A schema still names a box by its full name.** A binding with only `pdf_field` fills every widget with that name, as it does today, which the per-page header boxes need. Every existing schema, audit row, tier 2 key and `known_defects.json` key stays valid.
- **The per-widget selector.** A binding may also give `tag`, and it then fills only the widget with that `page` and `tag`. The startup check (`apps/forms/checks.py`) refuses a `tag` that isn't one of that full name's widgets on that page.
  - In `field_values`, a per-widget value's key is `<full name>@<page>:<tag>`. No full name in the 17 indexes contains `@`, and a startup check keeps it that way.
  - No production schema uses the selector in 3a2. Later PRs use it for the shared-name boxes: Schedule D's entry-number and account boxes, Schedule I's "Time employed" and "Assistance 8f", and A/B's 24.1 and 24.2.
- **Widgets the template doesn't print are removed before baking.** These are widgets without the PDF Print flag: exactly the 67 Print, Save As, Reset and Attach buttons. Baking them would print the buttons. One Schedule D box on page 3 is flagged not to show on screen but to print; it stays, as it would print from the fillable form.
- **Stacked duplicates.** Schedule D page 2 has 8 pairs of same-name widgets laid over each other, offset by about 0.6 pt: `4_3`, plus seven `_3` checkboxes (Contingent, Unliquidated, Disputed and the four lien kinds). The engine removes the second widget of each pair by tag order, so a value prints once. A pair is two widgets with the same full name on the same page whose overlap is more than half of the smaller one.

### 4.3 Checking: `check()`

`PDFFormFiller.check(form_type, values)` takes the resolved values and returns a plan: each widget, its value and its font size. It changes nothing and draws nothing. It refuses:

- **A key that names no widget, a tick state the box doesn't have, or a combo choice the box doesn't list**, as `fill()` does today (`UnknownField`, `InvalidFieldValue`).
- **A letter the box's font can't print** (`UnprintableLetter`).
  - Printable letters are exactly the ones the box's font encoding maps to a glyph. The check and the drawing both encode with the template's own font, so the two can't disagree. 567 text and combo widgets on five templates (101, 122A-2, A/B, C and D) carry a font of their own without the template's encoding, and pypdf would encode with that font first and print "?" for letters the template's font draws. The drawing removes it from each widget it draws.
  - Today that covers é, ñ, ü, ø, ë, Ł, Š and Œ, and it excludes ą, ć, ę, ń, ś, ź, ż, ř, ş and ễ.
  - The check first composes the text (Unicode NFC), so a letter typed as a base letter and a combining mark, as text pasted from some systems arrives, is checked and drawn as the one letter: e followed by a combining acute accent is é. A character Unicode treats as the same as a letter the form prints, such as the Ångström sign (Å) or the Kelvin sign (K), prints as that letter. A mark with no composed letter, such as n̈, is refused at its mark.
  - In a single-line box a line break prints as a space; in a multi-line box it starts a new line. A line break is wherever Python's `str.splitlines()` breaks a line, so a vertical tab and a form feed are line breaks too.
  - A tab and every Unicode space separator print as a plain space: the template's font draws the no-break space as "€" and has no glyph for the others. Format characters, such as the soft hyphen and the zero-width space, are left out, since the font has no glyph for them either. Any other control character that isn't a line break is refused. This is a build ruling for the owner to review.
  - In a comb box, `(`, `)` and `\` are refused too: pypdf draws each cell's character as its own string, and these break it. This is a build ruling for the owner to review.
  - A refused character that isn't a letter gets the letter sentence of §4.5 for now. Its wording for such characters is the owner's to settle.
- **A value that doesn't fit** (`ValueTooLong`):

  - **A single-line box** fits a value whose width, plus pypdf's padding on each side, is no wider than the box. The padding is 2 pt for most boxes; pypdf makes it twice the box's border margin, so Form 103B's 14 boxes with a 3 pt border get 6 pt. A single-line box's height isn't checked. pypdf centres the line in the box, and at the box's own size only Ç's cedilla reaches outside it: up to 0.108 pt below 37 boxes, where the box cuts that hairline off, as it does today. Nine of them are bound: Form 101's `Debtor1.Name` page headers on pages 2 to 9, and its `Attorney.Sig`. This is a build ruling for the owner to review.
  - **A comb box** fits a value no longer than its cell count (`MaxLen`). Shrinking doesn't help a comb box. Where `MaxLen` sits on the parent field, as on Schedule D's account boxes, the engine reads it there and gives it to the widget, so the digits land in their cells.
  - **A multi-line box** fits a value whose wrapped lines, at pypdf's own line spacing, are no taller than the box's height less one padding (twice its border margin). pypdf hangs the first line from the font's top at the box's height plus its border margin, so the box would cut the mark off a capital such as É; the drawing lowers the first line by that one padding, so it prints whole. The check wraps the value itself, at word boundaries, using Helvetica's widths and the box's width less the padding on each side. It hands pypdf the lines joined by line breaks, which pypdf draws one per line. A single word wider than the box doesn't fit.
  - **Any other box with a `MaxLen`** fits a value no longer than `MaxLen`.

  The check starts at the box's own size. That size is 10 pt for 1,959 boxes, 9 pt for 65 and 12 pt for 19, and the 10 auto-size boxes start at the size pypdf picks today. It shrinks in 0.5 pt steps to 6 pt. The first size that fits goes in the plan; if none fits, the value is refused.

The check measures with the font widths and padding pypdf uses when it draws, and §9's tests prove the two agree on every text box.

**What this means for the personas.** Their 604 text values, checked on 2026-10-17, include no letter the font can't print and no value too long even at 6 pt, so no persona is refused. The 7 values that are cut off today shrink instead (§4.1).

### 4.4 Drawing: `fill()`

`PDFFormFiller.fill(form_type, values)` runs `check()` and draws its plan:

1. pypdf clones the template.
2. For each planned widget it sets the value and builds that widget's own appearance at the planned size. Ticks set the widget's `/AS` and the field's `/V` to the box's state, so the template's own check mark (ZapfDingbats) is what prints. Combo boxes draw their chosen option as text.
3. It removes the widgets the template doesn't print and the second widget of each stacked pair (§4.2).
4. PyMuPDF bakes every remaining widget into the page content and sets `/AcroForm` to null. Unfilled widgets bake as they would print today, so 103B's empty squares stay.
5. It returns the PDF bytes. The PDF has no fillable field left.

The output can no longer be filled in a PDF viewer (umbrella §4.6). A correction goes through DigniFi and a regeneration.

### 4.5 Refusals and where they send the filer

`UnprintableLetter` and `ValueTooLong` are 422 refusals in plain words, like `PreconditionMissing`. `_failure` already sends a refusal's `step` or `page` (3a1). Each message names the box by its schema label. The wording below is a draft for the owner's review:

- "The court form can't print the letter “ą” in “Last name”. Change it to a letter without the mark."
- "“Name of Financial Institution” is too long to fit on the court form, even in small print. Shorten it."

Where each refusal sends the filer depends on where the value came from:

| The value comes from                              | The refusal carries                                                                                        |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| a derived rule (77 rules feed text boxes)         | the `step` (a `WIZARD_STEPS` key) or `page` that holds the rule's input, from one map beside `DERIVATIONS` |
| an asked answer, `answer:<form_type>.<key>`       | `page`: `/ask/<form_type>`, with the form type the binding names                                           |
| SOFA, `sofa.…`                                    | `page`: `/sofa`                                                                                            |
| an ingested value (the pay stub's employer name)  | `page`: `/documents`                                                                                       |
| a `db_aggregate` value (no schema binds one yet)  | `page`: `/documents`                                                                                       |
| the fee-waiver application (`fee_waiver_*` rules) | `page`: `/fee-waiver`, except 103B line 6, which reads the Expenses step                                   |
| a constant                                        | nothing: a constant that fails is a defect in DigniFi, and a test checks every constant                    |

A test fails on any derived rule that feeds a text or combo box and is missing from the map. A rule whose input no filer edits is in the map with no link: the district name in the forms' district boxes, which comes from DigniFi's own data; the median on 122A-1 line 13, which comes from the district's table; and five Schedule I rules (occupation and the employer's address) that read fields no model has, so they always print blank.

An asked answer is written only on `/ask/<form_type>`, and no schema field yet carries the `ui` that page shows, so today a filer can't give an answer in DigniFi and none can be refused. The link is there for the steps that add questions.

**Getting the filer there.** Today the dashboard links a refusal's `page` only when Generate All is refused as a whole. Three gaps stop a letter or length refusal from reaching its fix:

- Generate All's per-form errors are listed as plain text, under "You can try generating them individually below".
- A single form's refused Generate or Download shows nothing: `FormCard` catches the error and drops it, and `downloadForm` throws "Download failed (422)" without reading the body.
- The wizard can't open at a named step; it always opens at the session's saved step, which is Review once the intake is complete.

3a2 closes all three:

- **Each refusal links to its fix.** Every per-form refusal on the dashboard, from Generate All, Generate or Download, shows its message. One that names a wizard step, or a page the dashboard has link words for, also shows a link. The dashboard has no Regenerate button. A `step` links to `/intake?step=<key>` and a `page` to that page. "Finish your intake" still shows at most once on the dashboard.
- **The retry advice narrows.** "You can try generating them individually below" shows only when a form in Generate All's list names no fix the dashboard can link to.
- **`downloadForm` reads the refusal's body**, as `handleAPIError` does.
- **The wizard opens at the step named in `?step=`**, when the key is one of `WIZARD_STEPS`, after its usual session read; otherwise it opens at the saved step as today.

### 4.6 PyMuPDF pinned

`pymupdf` is unpinned in `backend/requirements/base.txt`. 3a2 pins it at the version installed and tested, 1.27.2.3. `pypdf==6.13.1` stays pinned, since the engine still uses its internal `TextStreamAppearance`.

## 5. Rows `[Q8]` `[Q9]`

### 5.1 Slots, copies and sheets

A repeat group (`repeat`, `repeat_capacity` and `row` on its bindings, as today) fills its slots on the form's own pages in row order. What happens to rows past the last slot depends on the template:

- **The template has an extra page.** Rows continue on copies of that page (§5.2). The forms are:
  - D page 2;
  - E/F pages 2 and 4;
  - G page 2;
  - H page 2;
  - C Part 2;
  - the notice parts, D Part 2 and E/F Part 3, by copying their page.
- **The template has no extra page.** Rows continue on an attached sheet (§5.3). The forms are A/B, Schedule I's employers, 122A-2 and 103B.

Totals never come from the printed slots: the derivations already add up every row, so a form's totals include rows printed on copies and sheets.

`RepeatOverflow` and its 422 sentence are removed. A group can no longer have too many rows.

### 5.2 Continuation copies

- **The group names its extra page.** A repeat group declares which template page continues it, and that page's own slots come first.
- **Copies are drawn alone.** Each further copy draws that one template page with the copy's rows and the form's page headers, bakes it, and inserts it right after the previous copy. A page header is a box on that page whose full name prints on another page too, such as "Debtor 1" and "Case number"; a group's own boxes are never one. Copies never share field objects with each other or with the form.
- **Numbers on each copy.**
  - **Entry numbers.** A group may declare an entry-number box and a pattern such as `2.{n}`, where `n` is the row's position in the whole group. Each slot's entry-number box then shows the row's number as the form writes it: 2.3, 2.4 and so on.
  - **Page numbers.** The continuation pages of D, E/F, G and H have a `page ___ (this page number)` box, and 106C page 2 also has `of ___`. A group may declare these boxes. Each page then shows its position in the form as printed, with the copies counted.
- **No overflow, no change.** When no row overflows, the form prints exactly as today, its extra page included.
- **One group per form continues on copies.** The page numbers count one group's copies, so the startup check (forms.E007) refuses a form with more than one group that names an extra page. A group whose rows go on an attached sheet doesn't count. Several forms of §5.1 need more than one, such as E/F with pages 2 and 4, so 3c lifts the limit and counts every group's copies in the page numbers. This is a build ruling for the owner to review.

### 5.3 Attached sheets

An attached sheet is drawn by PyMuPDF on a plain US Letter page with 0.75 in margins, and appended right after its form:

- **The header**, repeated on every page of the sheet: the filer's name, the form's official title with "(attached sheet)", and a blank "Case number (if known)".
- **The rows.** Each row is labelled with the form line it continues, under the same columns as the form's row. The group declares the column labels and widths.
- **Long text** wraps inside its cell, and the sheet runs to as many pages as its rows need.
- **The same rules as the form:** Helvetica at 10 pt, the letter check of §4.3, and no text ever cut off. PyMuPDF draws its Helvetica in WinAnsiEncoding, which lacks 13 letters the forms print, Ł, ł and ı among them, so the sheet's Helvetica takes the encoding all 17 templates give theirs. The sheet then prints exactly the letters the forms print.

The same generator will make Schedule I's 8a business and rental statement (3e2) and the additional-employers page. A sheet is part of its form's output, with no registry entry, schema or field index, so startup check forms.E001 is unchanged.

### 5.4 What 3a2 proves, and on what

No production schema has a repeat group (checked again 2026-10-17). 3a2 proves copies, numbering and sheets on synthetic schemas built over the real templates: a D group one row past page 2's slots, and an A/B group one row past its line. The first production rows bind in 3e2 (the 8a statement), 3b (A/B) and 3c (D, E/F, G and H, and the List of Creditors).

## 6. Stored values and filed forms

`GeneratedForm.field_values` (encrypted JSON) changes shape. It now holds the checked plan's parts, in printing order:

For example, with synthetic values from three forms:

```json
{
  "version": 2,
  "parts": [
    { "kind": "form", "values": { "Debtor 1": "Andrés Kettleby", "Quest11@2:T20": "3370.00" } },
    { "kind": "copy", "page": 2, "number": 1, "values": { "undefined_12": "2.6" } },
    {
      "kind": "sheet",
      "group": "ab_line_3",
      "title": "Official Form 106A/B, Schedule A/B: Property",
      "columns": [
        { "label": "Make", "width": 300 },
        { "label": "Current value of the portion you own", "width": 168 }
      ],
      "name": "Andrés Kettleby",
      "rows": [{ "line": "3.5", "cells": ["2014 Honda Fit", "4200.00"] }]
    }
  ]
}
```

A `form` part holds the values for the template's own pages. A `copy` part holds one copy of extra page `page`, the `number`-th. A `sheet` part holds one group's rows on its attached sheet, with what the sheet prints them under: its title, its columns' labels and widths, and the filer's name for its header. `check()` and `fill()` take a sheet's title, columns and rows from its part, never from the schema. A refusal still looks there: for a refused cell's link to its fix, and for the label of the form's name box when the filer's name is refused.

- **A filed form** downloads by drawing its stored parts, so it shows exactly what was filed, copy by copy and sheet by sheet, even after it has left the packet (DIG-155).
- **A row stored in today's shape** (`{full name: value}`, with no `version`) is read as one `form` part. Production v31 predates `field_values`, so it holds no such row. `main`, the copy self-hosters run, has stored rows in this shape since forms step 1, so a self-hoster's database can hold a filed one (§11). A test proves a form filed in today's shape still downloads.
- **The API never returns `field_values`**, as today.

## 7. Generate All, download and timing `[DIG-137]`

- **Generate All, Generate and Regenerate check without drawing.** Each resolves the form's values, runs `check()` and stores the parts. A letter or length refusal comes back like today's other per-form refusals: in Generate All's `errors` with the form type, or as a single form's 422, with its `step` or `page`.
- **Download draws.**
  - An unfiled form is resolved, checked and drawn fresh, and its parts are stored again.
  - A filed form draws its stored parts.
- **No retry on Generate All.** `formsAPI.generateAll` (`frontend/src/api/client.ts`) calls `apiFetchOnce` instead of `apiFetch`, so a slow or failed run is never repeated behind the filer's back. Today `withRetry` retries a 5xx three times, which can start four runs at once. The dashboard shows the error, and the filer can press again.
- **Timing.**
  - A management command, `time_packet --session <id>`, times one session's Generate All checks and the download of each form in its packet, and writes nothing.
  - The build runs it locally on each of the six personas' packets (14 or 15 forms each; Priya's is the one with 122A-2). The budgets, for every persona, are Generate All at 5 s or less and each download at 3 s or less.
  - A miss stops the build and comes back to the owner. The budget is not moved to fit.
  - The deploy steps run the same command on the Eco dyno, with a ceiling of 15 s each, half of Heroku's 30 s router timeout.

## 8. The oracle, rebuilt (umbrella §6.1)

- **Reading back.** One helper, `pdf_readback.read_drawn`, replaces `pdf_readback.read_widgets`. It reads a drawn PDF the way a person would, inside each widget's exact rectangle from the field index. It reads each page's characters once (PyMuPDF `get_text("rawdict")`), and a character belongs to a widget when its centre lies inside the widget's rectangle: two pairs of boxes overlap by about 2 pt, so a glyph that only touches a rectangle would put a neighbour's tick in it.

  - **a widget's text** is the Helvetica characters in its box;
  - **a box is ticked** when a ZapfDingbats character, the check mark, lies inside it.

  The templates print their own words in Arial, Wingdings and Times. Left blank and baked, 23 widgets still print a default of their own in Helvetica: the 18 district boxes' placeholder, A/B's three "0%" boxes on line 19, and a "2" in one box each on C and G. The helper bakes each blank template once and reads a box that prints exactly its blank text as blank, so nothing the template prints can pass for a drawn value. A drawn value equal to that text, such as "2" or "0%" in those boxes, reads blank too, so tier 1's text sentinels always hold a letter.

  The helper refuses a PDF that still has a widget, with a `ValueError` rather than a failed assertion: MuPDF reads an unbaked widget's appearance as text, and a listed defect's xfail must never take a missing bake for its defect. For copies, the helper maps each output page back to its template page through the plan's parts. An attached sheet's pages have no widget; a second helper, `read_sheets`, reads them line by line under the sheet's columns.

- **Tier 1 (sentinels).**
  - Every text and combo binding gets a short unique value, shrunk to fit like any value. Each must print in the widgets its key names and nowhere else.
  - Every tick choice is tried, and the check mark must appear only in that choice's widgets.
  - A new engine check gives every drawn widget of every shared text or combo full name in the 17 templates its own sentinel through the per-widget selector, and reads each widget back separately. A box has no value of its own, so each widget of a shared box name is ticked alone through its own key, one draw per position: it must print its tick, and its siblings none.
  - Tier 1 thereby covers the shared-name boxes the old filler could not separate, the 18 combo boxes and the 2 radio buttons.
- **Tier 2 (bindings against the audit)** keeps its (box, binding key) join and its asserted-case count. It compares schemas with the audit and reads no PDF, so the engine leaves it as it is.
- **Tier 3 (personas' printed values)** keeps its persona cases and reads drawn text. Copies and sheets are covered by §9's capacity tests on the synthetic schemas of §5.4, until the first production rows bring them into tier 3 in 3e2, 3b and 3c.
- **Known defects.** `known_defects.json` keeps its key shape (form type, full name, tier, case) and stays `[]`.

## 9. Testing

Tests are named for what they protect. New tests:

- **Rows:**
  - `extra_rows_print_on_copies_of_the_extra_page`;
  - `entry_and_page_numbers_continue_on_each_copy`;
  - `extra_rows_print_on_an_attached_sheet`;
  - `a_long_sheet_runs_to_a_second_page`;
  - `totals_count_rows_printed_on_copies_and_sheets`.
- **Filed forms:**
  - `a_filed_form_downloads_exactly_what_was_filed`;
  - `a_form_filed_before_3a2_still_downloads`.
- **Refusals:**
  - `a_letter_the_form_cannot_print_is_refused`, with é, ñ, ü and Ł printing and ą, ř and ễ refused;
  - `a_long_value_shrinks_before_it_is_refused`;
  - `no_value_is_ever_cut_off`: on every text box, a value that just fits prints whole, and one that just doesn't is refused. A read-back alone can't prove it. MuPDF's text extraction leaves out a character the box's clip hides entirely, which is how today's Form 101 email reads back as "deshawn.washington.synthetic@", but it reads a character the clip hides in part as whole. So the test also measures each character against its box, allowing for §4.3's cedilla, up to 0.108 pt below 37 boxes;
  - `every_refusal_names_where_to_fix_it`: the rule-to-step map covers every derived rule that feeds a text or combo box.
- **What the page shows:**
  - `the_packet_has_no_fillable_fields_left`;
  - `print_buttons_never_print`;
  - `unticked_boxes_keep_their_squares` (103B);
  - `a_stacked_duplicate_prints_once` (Schedule D page 2);
  - `amounts_stay_right_aligned`: a right-aligned box's text ends at its right padding;
  - `ssn_digits_fill_their_cells`: each digit of Form 121's SSN sits in its own comb cell;
  - `every_constant_prints`: every constant binding passes `check()`.
- **Every drawn PDF opens cleanly** in pypdf and PyMuPDF, with its page count. The build also traces MuPDF's "No common ancestor in structure tree" message, which Form 101 prints when opened; it may come from the template's tagging rather than the engine.
- **Timing:** `time_packet` runs once under the budgets of §7. It is not part of CI.
- **The frontend (vitest)**, whose tests carry these meanings in prose names, as the frontend's tests are named:
  - `a_refused_form_links_to_the_step_that_fixes_it`, for each of Generate All, Generate and Download;
  - `a_refused_download_shows_its_reason`;
  - `the_wizard_opens_at_the_step_a_link_names`, plus an unknown `?step=` opening the saved step;
  - `generate_all_is_sent_once_on_a_server_error`.

**Existing tests that change:**

- tiers 1 and 3 (§8);
- `test_pdf_filler.py`, which keeps its pin on `TextStreamAppearance` and adds `check()`;
- `test_download_action.py` and the filed-form tests in `test_form_views.py`;
- the `RepeatOverflow` tests, which become capacity tests;
- the frontend's Generate All test, which now expects one request on a 5xx.

**Every gate stays green:** backend tests, vitest, every E2E journey (the SOFA journey downloads Form 107, so E2E draws a real PDF), `known_defects.json` at `[]`, and develop's CI after the merge.

## 10. Docs

CLAUDE.md's gotchas are rewritten in the same PR (umbrella §5.1):

- **"`field_values`, not `form_data`"**: the parts shape, the filed redraw, and the legacy shape.
- **"Schemas are checked at startup"**: the `tag` selector and the `@` check.
- **"Known form defects are strict xfails"**: tiers 1 and 3 read drawn text.
- **"Blank, not 0.00"**: its repeat note becomes copies and sheets; `RepeatOverflow` is gone.
- **"GenerateAll vs single"**: no drawing, the letter and length refusals, and no retry.
- **The Architecture "PDF" line**: pypdf builds each widget's appearance, PyMuPDF bakes it, and the output is not fillable.
- **The File Map line for `pdf_filler.py`**, plus the sheet generator's module.

The umbrella spec's §5.4 and its SPIKE row get a one-line pointer to this spec's §3, so a later reader doesn't follow the old method.

`docs/security/deployment.md` gains a short "Forms step 3: before deploying" list under its Production Readiness Checklist:

- 3a1's three steps, which today live only in PR #26's description:
  - load `ilnd_2025_data` right after the release;
  - reseed with `seed_demo_data --reset`;
  - count completed sessions that hold a draft debt.
- 3a2's step: run `time_packet` on the Eco dyno.

## 11. Not in 3a2

- **Any production repeat group, and any production use of the per-widget selector.** These come in 3e2, 3b and 3c.
- **More than one group per form that continues on copies** (§5.2). 3c lifts the limit.
- **Two-digit entry numbers on Schedule D.** The entry-number box of page 2's first row is too narrow for a two-digit number even at 6 pt. A group's 12th row, numbered 2.12, is the first with two digits to land there, so `check()` refuses the form once a group has 12 rows. The refusal names the box by its field-index label and links nowhere. How such numbers print is an open question for the owner, and real Schedule D rows don't bind until it is answered (3c).
- **Correcting a scanned value the form can't print.** Schedule I's employer name comes only from a pay stub. When it holds a letter the form can't print, or is too long for its box even at 6 pt, the refusal links to `/documents` (§4.5's table), where nothing can change it, so Schedule I can't be prepared. How the filer corrects it is an open question for the owner: a correction field on the upload page (the documents API's `validate` already re-reads the pay stub), no link and a sentence of its own, or a bound when the pay stub is read.
- **A self-hoster's filed form that the check now refuses.** `main` draws a filed form's stored values as they are, so a letter the form can't print came out as "?" and a long value was cut off. After 3a2, a filed form holding such a letter, or a value too long for its box even at 6 pt, downloads as a refusal naming the letter or the box, with no link, since nothing changes what was filed. Production v31 stores no values. Whether to keep the refusal, draw a form filed before 3a2 without it, misprints included, or check self-hosters' filed rows before `main` is promoted is an open question for the owner. Until it is answered, the refusal stays.
- **A Unicode font** (3a2.Q1).
- **Dropping unused extra pages from the packet.** They print as today.
- **Background generation.**
- **Any deploy.**

## 12. Defects found while scoping

These three are on production now. 3a2 fixes all three. They still get tickets, filed with the owner's yes:

- **A value wider than its box is cut off at the edge, with no warning**, and a fixed-size multi-line box never wraps.
  - Examples: "Sentinel" as "Sen", a long creditor name as "A c", and the seeded personas' Form 101 emails and 122A-1 lines 12b and 13c.
  - It goes unnoticed because tier 1 reads `/V`, not the drawn page.
- **Letters outside the form font's encoding print as "?", with no warning.** Examples: Wąsowicz as W?sowicz, Dvořák as Dvo?ák, Nguyễn as Nguy?n. pypdf only logs a warning.
- **A refused Generate or Download on the dashboard shows the filer nothing.** `FormCard` catches the error and drops it ("Error handled by parent", but the parent doesn't). `downloadForm` throws a generic "Download failed (422)" without reading the refusal's words.
