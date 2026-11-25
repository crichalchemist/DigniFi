# Court-form field index

Ground truth for every fillable box on the 20 templates in `../pdfs/` that the app fills. Form 122B has no fillable fields. Built 2026-10-09.

## Files

- `<template-stem>.index.json`: one row per widget. Each row has `full_name`, `page`, `tag`, `rect`, `type`, `on_state`, `tooltip`, `line`, `label`, `column`, `kind`, `option_text` and `basis`.
- `ilnb_list_of_creditors.index.json`: the court's two-page List of Creditors, taken from its pro se bundle. Its rows were adjudicated by hand (every box read and rendered against the bundle) and are read off the template by `tools/build_list_of_creditors.py`, basis `adjudicated`, with no vision run. Never hand-edit it: change the tool and run it again.
- `form_b101.index.json`: Form 101 (11/26), written by `tools/build_form_101_index.py`. Never hand-edit it: change the tool and run it again. See "Form 101 (11/26)" below.
- `form_b101a_fillable.index.json`: Form 101A (12/15), the court's older fillable copy, written by `tools/build_form_101a_index.py`. Never hand-edit it: change the tool and run it again. See "Form 101A (12/15)" below.
- `audit/<schema>.audit.json`: every schema binding checked against the index. For each binding it records the field it targets, what it writes, its verdicts and the correct target.
- `audit/<schema>.unbound.json`: boxes a complete filing needs that no binding fills.
- `audit/verification.json`: an independent re-check of every non-correct verdict, plus a sample of correct ones. **Where it disagrees with a per-schema audit file, `verification.json` wins.** It modifies 13 verdicts and adds 18 the audit files mark correct.
- `audit/step2_verification.json`: forms step 2's own placements, the bindings the audit never judged. Each row has `verification.json`'s shape plus `producer`, the whole binding key (`derived:phone`), and cites the box's label in the index. Tier 2 (`backend/apps/forms/tests/test_oracle_tier2.py`) reads these rows before the audit's, matching on box and binding key, and fails on a row that no binding matches.
- The audit, unbound and verification files are the 2026-10-09 audit's record. Later steps don't edit them, so some boxes listed as unbound are bound now.
- `audit/ocr_cross.json`: where the vision reading and the text-layer reading disagreed.
- `tools/`: the scripts that built the index (`form_ocr.py`, `ocr_crosscheck.py`, `field_index.py`), the one-off conversion of the schemas to full-name bindings (`convert_schemas.py`), the recorder of failing oracle cases in `known_defects.json` (`record_known_defects.py`), `build_list_of_creditors.py`, which extracts the List of Creditors template from the bundle and writes its index, its schema and its 32 audit rows in `audit/step2_verification.json`, `build_form_101_index.py`, which writes Form 101 (11/26)'s index and renders its tagged pages, `build_form_101a_index.py`, which does the same for Form 101A (12/15), and the schema-writing tools `build_schedule_a_b.py`, `build_claims_schedules.py`, `build_schedule_c.py`, `build_form_122a2.py`, `build_form_101.py` (which also writes `../schemas/form_101.limits.json`) and `build_form_101a.py` (which writes `../schemas/form_101a.json` and `../schemas/form_101a.limits.json`), each of which writes its form's schema in `../schemas/` and its own rows in `audit/step2_verification.json` (`build_form_101a.py` writes its seven rows there too). Never hand-edit a schema a tool writes: change the tool and run it again.

## How each row was established (`basis`)

| basis           | meaning                                                                             | rows |
| --------------- | ----------------------------------------------------------------------------------- | ---- |
| `adjudicated`   | a reviewer looked at the tagged page image and decided                              | 1350 |
| `sampled_ok`    | vision agreed with the text layer, and a reviewer spot-checked it against the image | 516  |
| `vision_agreed` | vision agreed with the text layer; not looked at                                    | 400  |
| `pattern`       | a table row extrapolated from one row checked in the image                          | 626  |
| `header`        | page header (name, case number, district)                                           | 132  |
| `form_control`  | the template's Print, Save As, Reset and Attach buttons                             | 66   |

- **Checked box by box:** every widget on 122A-1, 122A-1 Supp, 122A-2, Schedule I and Schedule J.
- **Checked by pattern:** the repeating rows on Schedules C, D, E/F, G and H.

## Method

1. Render each page with every widget outlined and tagged.
2. Ask OpenAI gpt-5.5 for each tag's printed line, label, column and kind. On calibration pages gpt-4o was wrong by one line while reporting high confidence, so it is not used.
3. Read the same line number from the PDF text layer, and compare checkbox export values with the option text.
4. Claude agents settle disagreements from the images, then an independent reviewer re-checks the binding verdicts.

## Form 101 (11/26)

- **The template.** `../pdfs/form_b101.pdf` is the court's file, downloaded on 2026-11-20 from https://www.uscourts.gov/sites/default/files/document/form_b101.pdf (HTTP 200, 432,125 bytes, `Last-Modified: Thu, 12 Nov 2026 14:10:20 GMT`), sha256 `f9b8f6b2d11540fce286914c153003aa058ca125b6171e78f3bb440f810c5950`, the same bytes the step 4 survey read. 8 pages, 279 widgets (177 text, 85 check boxes, 14 radio kids in 7 groups, 3 signature fields), 271 names.
- **The method.** Every widget read on the tagged render by hand; no vision run. `tools/build_form_101_index.py render <dir>` draws every page with each widget outlined and tagged; `index` writes one row per widget from the tool's hand table, keyed by page and rectangle (not by name: the court's names are generated by position), with basis `adjudicated`. A box whose name and tooltip say nothing (`undefined`, `xx`, `fill_28`, `[1]`, `[2]`) has a label saying what the render shows, such as "Debtor 1, line 3: last 4 of the ITIN, digit 3 of 4" or "Part 7, attorney: date, the slash gap between month and day". `backend/apps/forms/tests/test_form_101_template.py` fails on any difference between the committed index and what the tool reads.
- **The 06/24 record.** `form_b_101_0624_fillable_clean.pdf` and its index are retired in forms step 4b. `audit/form_101.audit.json`, `audit/form_101.unbound.json` and the 71 `form_101` rows of `audit/verification.json` describe the 06/24 template and are kept unedited.

## Form 101A (12/15)

- **The template.** `../pdfs/form_b101a_fillable.pdf` is the court's older fillable copy of Form 101A, Initial Statement About an Eviction Judgment Against You, downloaded on 2026-11-18 from https://www.uscourts.gov/sites/default/files/form_b101a.pdf, 75,274 bytes, sha256 `4c79ea2730408b7bbc28a22a86e3698187f960eb5d97d11be4b671cdf62c327b`. 1 page, 18 widgets (12 text, 1 combo, 2 check boxes, 3 push buttons). The owner chose it on 2026-11-18 (B57), and counsel C-46 sees the choice.
- **Same words as the current publication.** Read with pypdf and with whitespace removed, its page text equals `form_b101a_0.pdf`'s except the two footer URLs, the lengths of the underscore blanks and `(State)`, which only `_0` prints; `test_form_101a_template.py` proves exactly this (pypdf returns no button caption). `form_b101a_0.pdf` stays as the current publication, and the eviction quotes are pinned to it.
- **The method.** As for Form 101: `tools/build_form_101a_index.py render <dir>` tags the widgets on the page image, and `index` writes one row each from a hand table keyed by page and rectangle (PyMuPDF's normalised rectangle, never the PDF `/Rect`), basis `adjudicated`; the three push buttons are `form_control` rows.
- **The revision check.** The court's Form 101A page was read on 2026-11-18 and again on 2026-11-22 (revision 12/15, effective 2015-12-01, no newer one), and the court's "Pending or Recent Changes" page was read whole on 2026-11-22: it lists no change to Form 101A or 101B.
- **Two traps.** `Check Box12`'s on-state is literally `No` (it is the first certification box, the state-law right to stay, not an answer), and `Check Box13`'s is `Yes` (the rent deposit); neither is ever ticked by DigniFi, since the certification is sworn. `Name of landlord` and `Date` have inverted rectangles in the PDF, so the tool keys its table on the normalised ones.

## Form 108 (12/15)

- **The template.** `../pdfs/form_b108.pdf` is the court's Form 108, Statement of Intention for Individuals Filing Under Chapter 7, read on 2026-11-24 from https://www.uscourts.gov/sites/default/files/form_b108.pdf, 87,667 bytes, sha256 `fe51d222d87f461b8695e3d9b7a061e768b2a75824511d167cfba736ca35e8fe`. 2 pages, 83 widgets (39 text, 39 check boxes, 1 combo, 4 push buttons) under 58 full names. Every widget has a tooltip, so no vision run was needed.
- **The method.** As for Form 101A: `tools/build_form_108_index.py render <dir>` tags the widgets on the page image, and `index` writes one row each from a hand table keyed by page and rectangle (PyMuPDF's normalised rectangle), basis `adjudicated`; the four push buttons are `form_control` rows. `form_b108.index.json` is written by the tool and never hand-edited.
- **Traps.** Kids share names: the four intention boxes of a creditor row share `check1 1<row>`, its No and Yes share `check2 1<row>`, and a lease row's No and Yes share `check2<row>` (one space apart from Part 1's, and a different question). Only the rectangle names a kid, so each carries the form's own words in `option_text`. In Part 1's row d the Yes box sits above the redeem box, the other way round in rows a to c. `Explain1 <row>` (50.5 pt) and `Explain2 <row>` (169.8 pt) are the two boxes of one wrapped line.

## Filling facts

- pypdf fills a key into every field whose full name **or short name** matches. Bind by full name. Some fields (`Quest11` on 122A-1, `Executed on`) can be targeted alone only by a filler that matches full names.
- A checkbox ticks only when the value equals its decoded export value. `/Chapter 7` works; `/Yes` and `/Chapter#207` do not.

Tracked in Plane as DIG-67 (this index) and DIG-63 and DIG-68 to DIG-83 (the defects it found).
