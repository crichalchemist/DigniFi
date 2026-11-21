# Court-form field index

Ground truth for every fillable box on the 18 templates in `../pdfs/` that the app fills. Form 122B has no fillable fields. Built 2026-10-09.

## Files

- `<template-stem>.index.json`: one row per widget. Each row has `full_name`, `page`, `tag`, `rect`, `type`, `on_state`, `tooltip`, `line`, `label`, `column`, `kind`, `option_text` and `basis`.
- `ilnb_list_of_creditors.index.json`: the court's two-page List of Creditors, taken from its pro se bundle. Its rows were adjudicated by hand (every box read and rendered against the bundle) and are read off the template by `tools/build_list_of_creditors.py`, basis `adjudicated`, with no vision run. Never hand-edit it: change the tool and run it again.
- `form_b101.index.json`: Form 101 (11/26), written by `tools/build_form_101_index.py`. Never hand-edit it: change the tool and run it again. See "Form 101 (11/26)" below.
- `audit/<schema>.audit.json`: every schema binding checked against the index. For each binding it records the field it targets, what it writes, its verdicts and the correct target.
- `audit/<schema>.unbound.json`: boxes a complete filing needs that no binding fills.
- `audit/verification.json`: an independent re-check of every non-correct verdict, plus a sample of correct ones. **Where it disagrees with a per-schema audit file, `verification.json` wins.** It modifies 13 verdicts and adds 18 the audit files mark correct.
- `audit/step2_verification.json`: forms step 2's own placements, the bindings the audit never judged. Each row has `verification.json`'s shape plus `producer`, the whole binding key (`derived:phone`), and cites the box's label in the index. Tier 2 (`backend/apps/forms/tests/test_oracle_tier2.py`) reads these rows before the audit's, matching on box and binding key, and fails on a row that no binding matches.
- The audit, unbound and verification files are the 2026-10-09 audit's record. Later steps don't edit them, so some boxes listed as unbound are bound now.
- `audit/ocr_cross.json`: where the vision reading and the text-layer reading disagreed.
- `tools/`: the scripts that built the index (`form_ocr.py`, `ocr_crosscheck.py`, `field_index.py`), the one-off conversion of the schemas to full-name bindings (`convert_schemas.py`), the recorder of failing oracle cases in `known_defects.json` (`record_known_defects.py`), `build_list_of_creditors.py`, which extracts the List of Creditors template from the bundle and writes its index, its schema and its 32 audit rows in `audit/step2_verification.json`, `build_form_101_index.py`, which writes Form 101 (11/26)'s index and renders its tagged pages, and the schema-writing tools `build_schedule_a_b.py`, `build_claims_schedules.py`, `build_schedule_c.py`, `build_form_122a2.py` and `build_form_101.py` (which also writes `../schemas/form_101.limits.json`), each of which writes its form's schema in `../schemas/` and its own rows in `audit/step2_verification.json`. Never hand-edit a schema a tool writes: change the tool and run it again.

## How each row was established (`basis`)

| basis           | meaning                                                                             | rows |
| --------------- | ----------------------------------------------------------------------------------- | ---- |
| `adjudicated`   | a reviewer looked at the tagged page image and decided                              | 1335 |
| `sampled_ok`    | vision agreed with the text layer, and a reviewer spot-checked it against the image | 516  |
| `vision_agreed` | vision agreed with the text layer; not looked at                                    | 400  |
| `pattern`       | a table row extrapolated from one row checked in the image                          | 626  |
| `header`        | page header (name, case number, district)                                           | 132  |
| `form_control`  | the template's Print, Save As, Reset and Attach buttons                             | 63   |

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

## Filling facts

- pypdf fills a key into every field whose full name **or short name** matches. Bind by full name. Some fields (`Quest11` on 122A-1, `Executed on`) can be targeted alone only by a filler that matches full names.
- A checkbox ticks only when the value equals its decoded export value. `/Chapter 7` works; `/Yes` and `/Chapter#207` do not.

Tracked in Plane as DIG-67 (this index) and DIG-63 and DIG-68 to DIG-83 (the defects it found).
