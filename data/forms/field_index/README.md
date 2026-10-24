# Court-form field index

Ground truth for every fillable box on the 17 AO templates in `../pdfs/` that the app fills. Form 122B has no fillable fields. Built 2026-10-09.

## Files

- `<template-stem>.index.json`: one row per widget. Each row has `full_name`, `page`, `tag`, `rect`, `type`, `on_state`, `tooltip`, `line`, `label`, `column`, `kind`, `option_text` and `basis`.
- `audit/<schema>.audit.json`: every schema binding checked against the index. For each binding it records the field it targets, what it writes, its verdicts and the correct target.
- `audit/<schema>.unbound.json`: boxes a complete filing needs that no binding fills.
- `audit/verification.json`: an independent re-check of every non-correct verdict, plus a sample of correct ones. **Where it disagrees with a per-schema audit file, `verification.json` wins.** It modifies 13 verdicts and adds 18 the audit files mark correct.
- `audit/step2_verification.json`: forms step 2's own placements, the bindings the audit never judged. Each row has `verification.json`'s shape plus `producer`, the whole binding key (`derived:phone`), and cites the box's label in the index. Tier 2 (`backend/apps/forms/tests/test_oracle_tier2.py`) reads these rows before the audit's, matching on box and binding key, and fails on a row that no binding matches.
- The audit, unbound and verification files are the 2026-10-09 audit's record. Later steps don't edit them, so some boxes listed as unbound are bound now.
- `audit/ocr_cross.json`: where the vision reading and the text-layer reading disagreed.
- `tools/`: the scripts that built the index (`form_ocr.py`, `ocr_crosscheck.py`, `field_index.py`), the one-off conversion of the schemas to full-name bindings (`convert_schemas.py`), and the recorder of failing oracle cases in `known_defects.json` (`record_known_defects.py`).

## How each row was established (`basis`)

| basis           | meaning                                                                             | rows |
| --------------- | ----------------------------------------------------------------------------------- | ---- |
| `adjudicated`   | a reviewer looked at the tagged page image and decided                              | 1118 |
| `sampled_ok`    | vision agreed with the text layer, and a reviewer spot-checked it against the image | 551  |
| `vision_agreed` | vision agreed with the text layer; not looked at                                    | 486  |
| `pattern`       | a table row extrapolated from one row checked in the image                          | 626  |
| `header`        | page header (name, case number, district)                                           | 155  |
| `form_control`  | the template's Print, Save As, Reset and Attach buttons                             | 67   |

- **Checked box by box:** every widget on 122A-1, 122A-1 Supp, 122A-2, Schedule I and Schedule J.
- **Checked by pattern:** the repeating rows on Schedules C, D, E/F, G and H.

## Method

1. Render each page with every widget outlined and tagged.
2. Ask OpenAI gpt-5.5 for each tag's printed line, label, column and kind. On calibration pages gpt-4o was wrong by one line while reporting high confidence, so it is not used.
3. Read the same line number from the PDF text layer, and compare checkbox export values with the option text.
4. Claude agents settle disagreements from the images, then an independent reviewer re-checks the binding verdicts.

## Filling facts

- pypdf fills a key into every field whose full name **or short name** matches. Bind by full name. Some fields (`Quest11` on 122A-1, `Executed on`) can be targeted alone only by a filler that matches full names.
- A checkbox ticks only when the value equals its decoded export value. `/Chapter 7` works; `/Yes` and `/Chapter#207` do not.

Tracked in Plane as DIG-67 (this index) and DIG-63 and DIG-68 to DIG-83 (the defects it found).
