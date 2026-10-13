# Forms foundation: one fill path, checked against the verified field index

**Status:** approved in brainstorming on 2026-10-10. This is step 1 of the forms project. The draft was revised after an adversarial review that found 36 issues, 16 of them blocking, and again after a re-review that found 17 more; every one is resolved below.

**Branch:** `feat/forms-rebinding`, on top of the field-index commit `941c873`.

**Production:** nothing deploys until all four forms steps are done. The only exception is the DIG-124 data wipe (§7).

## 1. Why

The generated court packet is hollow, and CI has been green the whole time. The verified field index (`data/forms/field_index/`: 17 templates, 3,003 widgets) and its audit of all 735 schema bindings show:

- **44 bindings print a correct value.** Another 2 print only after a pay stub is read. 6 signature boxes are blank on purpose, because ILND requires a handwritten signature. Don't quote the audit files' raw "460 correct": that figure counts box targeting, not output.
- **288 bindings are real defects.** The audit's "broken" bucket holds 294, which adds 4 unclear rows and 2 legal-review rows. Of the 288 defects, 167 are latent: they print nothing today only because nothing writes answers.
- **383 bindings are always empty.** For 382 of them, the cause is that no schema has a `ui` block, so nothing asks the filer.
- **Whole features are missing.** No checkbox ever ticks. Schedules A/B, C, D, E/F, G and H list no rows. Debtor 2 boxes receive the filer's own data.
- **No test checks that a value lands in the right box.** The 238 generator tests check `generate()`, whose output never reaches the PDF. 21 tests assert today's broken bindings.

## 2. Where this step fits

| Step                          | What it does                                                                                                                                                                        | Must come after                |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| **1. Foundation (this spec)** | One fill path; bindings addressed by full name and checked against the index; exact checkbox states; the packet list; the read-back oracle and known-defects list                   | —                              |
| 2. Rebind                     | Move every binding for data intake already collects to its right line; fix the fields the API drops; empty the known-defects list for those forms                                   | 1                              |
| 3. Schedule rows              | Data-model additions (priority, dates, addresses, contingent/disputed, consumer/business, codebtor link); rows on A/B, C, D, E/F, G and H; Form 108; exemptions chosen by the filer | 1, 2                           |
| 4. Form questions             | `ui` blocks and gates for the ~560 asked fields, including SOFA (Form 107)                                                                                                          | 1, 2, and 107's index verified |

Step 2 must land before, or together with, anything that writes answers. Otherwise the 167 latent defects turn into wrong printed values.

## 3. Owner decisions (2026-10-10)

- **Scope:** "Done" means the full packet for a single filer. Joint filing is out, and Debtor 2 boxes stay blank.
- **Approach A:** the schema engine is the only fill path. Bindings name widgets by the index's `full_name`, and a new filler matches full names only. Rejected: B (the generators as the only path) and any hybrid.
- **Design:** this spec's design was approved in four parts: scope, addressing, one path, and the oracle.
- **DIG-124:** wipe production's stored `form_data` now. The code fix ships with this step.

## 4. Scope

**In scope:**

- one fill path, with generator code removed;
- the schema format;
- a one-off schema conversion;
- a new filler;
- startup validation against the index;
- an encrypted snapshot of each generated form;
- the packet list, in the backend and on the dashboard;
- preconditions and the error contract;
- the three-tier oracle and the known-defects list.

**Out of scope:**

- **Step 2:** moving bindings to their right lines (122A-1, Schedules I and J, 101, 103B and others); which fields print blank instead of `0.00`; option-group mappings for collected data; fields the API drops.
- **Step 3:** row bindings, the data model, Form 108 and exemptions.
- **Step 4:** questions, gates and SOFA.
- **Not planned:** joint filing, packet merging and flattening.

## 5. Design

### 5.1 Schema format

`FieldSpec` in `backend/apps/forms/schema.py` changes in four ways.

**`pdf_field` holds a full name.** It must equal a `full_name` row in the form's index file, for example `Debtor1.Name`, never `Name`.

- The index file is `<FORM_INDEX_DIRECTORY>/<template stem>.index.json`, where the stem is the schema's `template_filename` without `.pdf`.
- `FORM_INDEX_DIRECTORY` is a new setting next to `FORM_SCHEMAS_DIRECTORY` in `config/settings/base.py`. It points at `data/forms/field_index/`.

**`choices` replaces `on_states` for checkboxes and radio buttons.** It is a dict from a normalised answer value to an export state.

- **Single box:** `{"true": "<state>"}`.
- **Option group:** one key per option, `{"<option value>": "<state>"}`.
- **Index states:** the index stores `on_state` in its raw, `#`-encoded form with no leading slash, such as `Chapter#207`. Everywhere a state is compared (the conversion, check 5, the filler and tier 1), it goes through one function: `export_state(on_state) = "/" + on_state with #xx escapes decoded`, which gives `/Chapter 7`.
- **Required:** `choices` is required for `checkbox` and `radio` bindings and forbidden on every other type.
- **Empty means not mapped yet.** An empty dict means "not mapped yet". The binding emits nothing, a check that happens before any value lookup. Tier 1 records it as an `unmapped_choice` known defect (§6).

**Normalisation for a mapped binding:**

- **Single box:** ticks for `yes`, `y`, `true`, `1` and `on`, case-insensitively, and stays off for `no`, `n`, `false`, `0`, `off`, empty and `None`.
- **Option group:** the value is lower-cased and looked up in `choices`.
- **Unknown value:** one that is neither a known key nor empty raises `UnmappedChoice`.

**`choice` bindings are text-valued.** All 17 `choice` bindings are the district ComboBox (`/Ch`), and it has no on-state. Its value must be one of the widget's `/Opt` entries.

- The filler writes it like text (§5.3), and tier 1 reads back `/V`.
- Check 5 validates constant values against `/Opt`.
- A derived value outside `/Opt` raises at fill time.

**Placeholder and unproducible rows are removed.**

- **Placeholders:** rows with `source: "constant"` and an empty or null `value` print nothing (1,194 rows). They are removed, and step 3 adds real row bindings.
- **Schedule J's 51 `TBD` rows** are removed too. Nothing produces their values, they sit outside the 735 audited bindings, and step 2 rebinds Schedule J. The exception is its district box, which gets the same `derived district_name` binding as the other 16 forms. A removed row produces no test case, so it can't go on the strict known-defects list. Instead, the conversion report lists each one, and a comment on DIG-52 and DIG-61 records them for step 2.

**"Leave blank" is already possible.** A derivation may return `None` to leave its box blank, because `_emit` already skips `None`. Step 1 changes no derivation; step 2 decides, field by field, where blank replaces `0.00`.

**`ingest_form_schema` is retired.** The management command `ingest_form_schema`, its tests and its `build_draft_schema` helper are retired. The command drafted short names and wiped curated keys (DIG-127). From now on, schemas are edited by hand and checked by §5.4.

### 5.2 One-off conversion

`data/forms/field_index/tools/convert_schemas.py` rewrites the 17 remaining schemas once. `form_122b.json` is deleted first (§5.6). The script's output is committed with it.

The conversion **moves no binding to a different line.** A binding the audit calls `wrong_box` keeps its wrong target, and tier 2 lists it.

Counts below exclude the placeholder and `TBD` rows that rule 7 removes.

1. **Exact match.** A `pdf_field` that already equals an index `full_name` is kept. That covers 708 bindings.
2. **One or several candidates.** The candidates are the fields whose last name segment equals `pdf_field`.
   - **Exactly one candidate:** use it. That covers 2 bindings, 122A-1 `Quest4` and `2`. The second resolves to `Debto2.Quest2.2`, a Debtor 2 widget, so rule 4 drops it.
   - **Several candidates:** keep the Debtor 1 candidate the key fills today (`Debtor1.*`, `Debto1.*`, or the unprefixed field on the same line). The audit's target is used only to break a tie between candidates, and never to move a binding to a different line. For 11 bindings, all on 122A-1, the audit's right target is a different line or `leave blank`. Those keep today's box, and the audit's verdict goes on the known-defects list for step 2.
3. **Zero candidates.** These are decided here, so the script never has to stop:
   - 103B `Debtor` → `Debtor 1`. This is DIG-64's box; the old name doesn't exist on the template.
   - 121 `Debtor2a.First name`, `Middle name` and `Last name` are dropped, because joint filing is out.
   - A/B `17` is dropped, because the audit records no target for it.
   - Any other zero-candidate binding found at run time stops the script.
4. **Debtor 2 targets.** Two kinds of binding are dropped, because joint filing is out (§3) and these boxes stay blank:

   - bindings whose resolved target is a Debtor 2 widget;
   - bindings gated on the `has_joint_filer` predicate, which reads the answer `joint_filer_gate`.

   A widget counts as Debtor 2 when any of these holds:

   - its full name contains `Debtor 2` or `Debtor2`, or starts with `Debto2.`;
   - its index `label` or `column` names Debtor 2 or the non-filing spouse. Examples: Form 107's `Income 4a Debtor 2`, 101's `Suffix Sr Jr II III_2`, 121's `Check Box2`, and 122A-1 column B.

   The gate rule also drops the two amended-filing bindings on 106Dec and 106Sum, the dict-shaped `on_states` behind DIG-75's crash. Step 2 rebinds that box. The report lists every drop, with a count.

5. **Form controls.** Bindings that target widgets with index `basis: form_control` are dropped. These are the Print, SaveAs, Reset and attach push buttons, such as 101 `Button.Print1` and 107 `attach`. The index's `kind` field doesn't mark them reliably.
6. **Choice states:**
   - A single-box `on_states` becomes `choices: {"true": export_state(on_state)}`.
   - A multi-widget group becomes `choices: {}`. The three constant `"/Yes"` bindings on Form 101 groups (`Check Box1`, `Check Box5`, `Check Box16`) keep their value and get `choices: {}`. They emit nothing until step 2 maps them, and each has a tier 1 `unmapped_choice` case. `Check Box1` is the chapter box.
7. **Placeholders and `TBD` rows** are removed (§5.1). A row with a `choices` key is never treated as a placeholder.
8. **Report.** The script writes a per-schema report of every rename, drop and conversion, including an old→new name map. The report is attached to the PR, and tier 2 uses the map to join renamed bindings to their audit rows.

### 5.3 Filler

`PDFFormFiller.fill(form_type, field_values)` keeps its signature. Keys are full names. Values are text, an `/Opt` entry for combo boxes, or an export state for buttons.

**Exact matching.** The filler walks each page's widget annotations itself and computes each widget's qualified name from its `/T` chain. It fills a widget only when that qualified name equals a key exactly. It no longer calls `update_page_form_field_values`, which also matches a key against a parent's partial `/T`. That partial match caused the `Name` and `Executed on` collisions (DIG-63).

**Text and combo boxes.**

- The filler sets the field's `/V` and builds the appearance stream with pypdf's `TextStreamAppearance.from_text_annotation`, then installs it as the widget's `/AP /N`. Both the builder and the install step are pypdf internals.
- pypdf stays pinned at 6.13.1. A test exercises both steps on a real template and fails if either changes.
- `/NeedAppearances` is set to false, so viewers use the stored appearance streams, as they do today.

**Checkboxes and radio buttons.**

- The filler sets the field's `/V` to the state.
- On every widget of that field, `/AS` becomes that state where it is a key of the widget's `/AP /N`, and `/Off` otherwise.
- A state that is in no widget's `/AP /N` raises an error. The old silent `/Off` is gone.

**Errors and template names.**

- A key that names no widget raises `UnknownField`. Once validation passes, that can't happen.
- A template without an `/AcroForm` raises `TemplateHasNoForm`.
- The template filename lives only in each schema's `template_filename`, and the duplicate `FORM_TEMPLATES` table in `pdf_filler.py` is removed.

**Unchanged:** there is still no flattening, and still one PDF per form.

### 5.4 Validation at startup

A Django system check (`apps/forms/checks.py`) validates every registered form. It runs on `manage.py check`, `runserver` and `migrate`. Each problem is a `forms.E0xx` error naming the form and the field.

**Where it runs:**

- **Production:** gunicorn runs no system checks. Heroku's release phase does run `migrate`, and `migrate` runs them, so a bad schema fails the release and never reaches filers.
- **Tests:** pytest-django doesn't run system checks. A test therefore calls the same validation function for every form, and CI fails on the same errors.

**Shipping the index.** `Dockerfile.heroku` copies `data/forms/field_index/*.index.json` into the image, next to the schemas and templates it already copies. The `audit/` files are test-only and stay out of the image.

**The checks:**

1. A schema and an index file exist for every registered form.
2. `template_version` equals the template's SHA-256. The three schemas whose hash is wrong today are corrected.
3. Every `pdf_field` is an index `full_name`.
4. **Types match:**

   - a `text` binding targets a text widget;
   - a `choice` binding targets a combo box;
   - a `checkbox` or `radio` binding targets a CheckBox or RadioButton widget.

   Bindings to push buttons are rejected.

5. **States and options exist:**
   - every state in `choices` is `export_state()` of an `on_state` among that field's widgets;
   - a constant `choice` value is one of the field's `/Opt` entries.
6. No two bindings name the same full name, except bindings in different `repeat` rows of the same group.
7. No source is `TBD`. Every `rule`, every `conditional_on` predicate and every `binding` namespace exists.

`validate_schema` remains the shared implementation. Today it runs on only 2 of the 18 schemas.

### 5.5 One generation path

**Generators are deleted.** All 18 `*_generator.py` modules go, with their `generate()`, `preview()` and the 238 tests of their output.

- Every one of those modules had the same three-line `pdf_field_map()`. One function replaces it: `build_field_values(form_type, session) -> dict[str, str]`, which checks preconditions (§5.7), loads the schema and calls `resolve()`.
- The row builders in `schedule_d`, `schedule_ef` and `schedule_ab` stay in git history at `941c873`, for step 3 to lift from there.
- Schedule C's exemption picking is deleted (§7).

**Callers outside `apps/forms` change with them.** These lines were found by searching the tree:

- `apps/intake/views.py:15` imports `Form101Generator` at module level for the `preview_form_101` action (`:239-267`). The action and its import are removed, so the intake URLconf no longer depends on deleted code. With them go `api.intake.previewForm101` in `client.ts` and `TestForm101Preview` in `apps/intake/tests/test_e2e_intake.py`.
- `apps/eligibility/tests/test_means_test_calculator.py:28` imports `get_generator`, which it uses at `:1048`. The test switches to `build_field_values`.
- `apps/forms/tests/test_engine_form_agnostic.py:12` imports `build_draft_schema`. Its cases are rewritten against the new loader, or deleted where they only exercised ingest.
- `_UPL_DISCLAIMER` (`forms/views.py:30`) moves to `apps/forms/constants.py`. Two places still import it: `apps/content/management/commands/check_reading_level.py:158` and `apps/audit/tests/test_upl_compliance.py:25`.

A plan step is complete only when a search for `Generator\b`, `get_generator`, `build_draft_schema`, `pdf_field_map` and `form_data` across `backend/` and `frontend/src/` returns nothing except migrations and the blanked `form_data` model field, which stays until its column is dropped.

**The registry** maps each `form_type` to `applies(session)` (§5.6) and `requires(session)` (§5.7) instead of a generator class. `get_all_form_types()` keeps its filing order.

**`GeneratedForm.form_data` is replaced by `field_values`.** This is an encrypted text field holding the resolved values as JSON. It uses the project's existing `encrypted-model-fields` package (`EncryptedTextField`), the same Fernet mechanism used for SSNs and OCR data.

- **Migrations.** This step's migration does three things. Existing values are not copied (§7).

  - It adds `field_values`.
  - It gives `form_data` a default of `dict`. The column is NOT NULL with no default today, and the new code never writes it.
  - It blanks every `form_data` value.

  The `form_data` column itself is dropped by a migration in the release _after_ this code is live. During a release phase, the old code is still serving traffic and still reads the column.

- **API.** The serializer stops returning `form_data` and never exposes `field_values`.

**Endpoints:**

- **`generate`** checks `applies` and `requires`, resolves the values, test-fills the PDF, and stores `field_values` and `template_version`. A form that doesn't apply returns 422 ("this form isn't part of your packet"). Today, Form 103B for a filer with no fee waiver returns an unhandled 500. Without the `applies` check, the schema path would print a $0.00 fee-waiver application.
- **`regenerate`** does the same for an existing row.
- **`generate_all`:**
  - It covers only the forms that apply.
  - It deletes the session's rows for forms that no longer apply.
  - It gives each form its own savepoint (`transaction.atomic()` per form), so one form's database error can't poison the rest.
  - Its response keeps the `{generated, errors}` shape.
- **`download`:**
  - **A form not yet marked filed** is resolved fresh, its stored `field_values` and `template_version` are refreshed, and it's filled. The filer always downloads their current answers, and needs no regenerate button. Once every form exists, the dashboard offers no other way to refresh them.
  - **A form marked filed** always fills from its stored `field_values`, so what was filed matches what the filer reviewed.
  - **A filed row with no stored values** (one from before this change) is resolved fresh once and stored.
  - **A form that no longer applies** returns 422.
- **`packet` (new):** `GET /api/forms/packet/?session=<id>` returns the ordered list of form types that apply. The dashboard uses it (below).
- **`preview`** is removed.

**Frontend:**

- **Dashboard.** It renders cards and its "N of M" total from the `packet` list instead of the static `FORM_TYPE_METADATA` table. The table keeps titles and order but loses `form_122b`, as does the `FormType` union.
- **Dead callers removed:** `api.forms.preview` and `api.forms.generateForm101` in `client.ts`, plus `Form101Preview.tsx`, which no page renders and whose endpoint doesn't exist. Their MSW handlers go too.
- **Types.** The `GeneratedForm` type drops `form_data`.
- **E2E.** `dashboard.page.ts` stops waiting for the literal `of 18`. The five journeys that generate forms each pass their own packet size: Sarah, Maria, DeShawn and James, plus `sofa-journey.spec.ts`, which uses James's packet. Priya never reaches the dashboard. `FormDashboard.test.tsx` follows.

**Model.** `form_122b` leaves `FORM_TYPE_CHOICES`, and a data migration deletes existing `form_122b` rows.

**`seed_demo_data`** checks forms with `build_field_values` instead of `generate()`.

**A stray script is deleted.** `backend/test_schedule_ab_logic.py` sits at the backend root, outside the test tree, and names `ScheduleABGenerator`.

### 5.6 The packet list

| Form                                                                                      | Applies when                                                                                                                                                                                                                                                                                 |
| ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 101, 106A/B, 106C, 106D, 106E/F, 106G, 106H, 106I, 106J, 106Sum, 106Dec, 107, 121, 122A-1 | Always                                                                                                                                                                                                                                                                                       |
| 122A-2                                                                                    | The session's stored `MeansTest` shows annualized income at or above the median: `calculated_cmi × 12 ≥ median_income_threshold`. Both fields are rewritten on every calculation. With no `MeansTest` row, it doesn't apply, and 122A-1's `requires` reports the missing calculation (§5.7). |
| 103B                                                                                      | A `FeeWaiverApplication` exists for the session                                                                                                                                                                                                                                              |
| 122A-1Supp                                                                                | The filer claims an exemption from the presumption of abuse. Nothing collects that yet, so it never applies until step 4.                                                                                                                                                                    |

- **Removed: 122B.** It goes from the registry, the model choices, its schema and the frontend. It is the Chapter 11 statement, and its download raised a 500 (DIG-125).
- **Not added: 106J-2.** It covers a spouse's separate household.
- **Later: 108.** It is added in step 3.
- **Packet size.** A packet therefore holds 14 to 16 forms.
- **Always a yes or no.** `applies` never raises. `packet` therefore always returns a list, and generate-all deletes a stored 122A-2 row whenever `applies` is false.
- **Why not `above_median_calculated`.** That flag is sticky: `calculate()` sets it true and never resets it, and the wizard's live preview saves calculations during intake. A filer who briefly entered above-median income would keep 122A-2 for good. The same code also gives above-median filers who pass the expense test the below-median message. Both are DIG-128.
- **Known inconsistency.** Line 13 of 122A-1 and `MeansTest` use different household sizes (DIG-51). Step 2 fixes that; until then, `applies` follows `MeansTest`, the figure the app already shows the filer.

### 5.7 Preconditions and the error contract

Generator constructors used to raise on missing data. Those checks now live in each registry entry's `requires(session)`, which raises `PreconditionMissing` with a plain-words reason.

- **101 and 121:** a `DebtorInfo` must exist.
- **121:** additionally needs a valid nine-digit SSN.
- **122A-1:** a `MeansTest` row must exist ("the eligibility check hasn't been run").
- **103B:** covered by `applies`.

`build_field_values` calls `requires` first, so no form resolves silently from missing data. For example, Form 121's "no SSN" box can no longer tick for a session with no `DebtorInfo`.

**Expected failures return 422,** with a body that names the form and the problem:

- `PreconditionMissing`;
- a form that doesn't apply;
- `RepeatOverflow` (more entries than the form has slots);
- `UnmappedChoice`;
- `TemplateHasNoForm`.

**Anything else returns 500.** It is logged with `logger.error` and the exception's type only, never its message or a traceback. That keeps filer data out of Sentry (the DIG-105 rule).

## 6. The oracle

All three tiers run in the backend test suite. The budget is about 30 seconds:

- one fill of all forms takes about 4.3 s;
- the text-marker pass takes about 5.3 s;
- the choice cases are batched, and done one at a time they took 44 s;
- tier 3 fills only the forms each persona table asserts.

**Tier 1, read-back (mechanics).** This runs on every binding of every form.

- **Text and combo boxes:** each binding gets a unique marker. For a combo box, the marker is one of its `/Opt` values. The form is filled with the real filler and every widget is read back. The marker must appear in exactly the named widget and nowhere else. A marker found nowhere during a batched run is re-checked alone, because a batch can hide one (Schedule C `2.3`).
- **Checkboxes and radio buttons:** each `choices` entry is set in turn, and `/AS` is read, never `/V`. Only the expected widget may be on; every other widget of the field must be `/Off`. Groups that share no widgets are batched.
- **Empty `choices`:** each binding with empty `choices` gets one `unmapped_choice` case. It fails until the binding is mapped.
- **Defect classes** are `no_widget`, `collision`, `spill` and `unmapped_choice`. After step 1, `no_widget`, `collision` and `spill` must be zero: those are what the conversion and the filler fix.
- **What the prototype showed:** it found 100 mechanical defects: 67 dead checkboxes, 27 spills into other widgets, 5 bindings with no widget and 1 hidden by batching. A further 102 came from comparing against the audit, which is tier 2's job.

**Tier 2, the right line (meaning).** Each binding's `pdf_field` is compared with the full name the verified audit says it should hit.

- **Joining renamed bindings.** Bindings are joined to their audit and verification rows through the conversion report's old→new name map (§5.2).
- **When a binding is asserted:**

  - `verification.json` has a row for it, whatever the widget's basis; or
  - the index `basis` of the binding's target widget is `adjudicated` or `sampled_ok`.

  Everything else is `unverified` and isn't asserted. That mostly means Form 107's never-checked rows, which step 4 verifies.

- **Special audit targets:**
  - `leave blank`: the binding must be absent, or resolve to `None`.
  - An empty target on a row marked correct: the binding's own `pdf_field`.
  - A target with a trailing annotation: the annotation is stripped first.
- **Defect class:** `wrong_box` only. That is the one failure the comparison can detect. Wrong values and data gaps are tier 3's job.

**Tier 3, personas (values).** Each of the 5 seeded personas gets a hand-written table of values a correct packet must print.

- **Where the values come from:** the persona briefs in `docs/testing/persona-briefs/`, never the app's own derivations.
- **Examples:**
  - 101: name, address and the chapter box;
  - 106Sum: totals;
  - 122A-1: lines 11 to 14;
  - Schedules I and J: totals.
- **Above and below the median:** at least one persona sits above the median and one below, so the 122A-2 rule is exercised both ways.
- **Method:** the persona's forms are filled and those widgets are read back.
- **What it catches:** value-level defects that tier 1 can't see, such as an annual figure in a monthly box.
- **Defect classes:**

  - `wrong_value`: the box prints the wrong figure.
  - `no_source`: the box needs data intake doesn't collect. It carries that data gap's ticket.

  Data gaps outside the persona tables are tracked only by their tickets.

- **Legal readings:** any expected value that depends on a legal reading is flagged for the owner to confirm before it's committed.

**The known-defects list** is `backend/apps/forms/tests/known_defects.json`.

- **Entries:** each is keyed by `(form_type, pdf_field, tier, case)`, with its defect class and DIG ticket. `case` is the persona for tier 3, the choice key for a tier 1 checkbox case and the binding key for tier 2 (step 2 spec §7.2); otherwise it's empty. A defect that shows for some personas and not others can therefore be listed exactly.
- **Strict expected failures:** matching cases are marked `xfail(strict=True)`. A new break fails CI, and so does a fix until its entry is deleted.
- **No orphans:** the test session fails if any entry matches no test that ran. So the list's length is exactly the number of known defects left.
- **Who maintains it:** step 1 creates it. Step 2 empties it for collected data, and steps 3 and 4 add and remove entries as their bindings land.

**Tests removed:**

- the 238 generator tests and `TestForm101Preview` (§5.5);
- the 21 tests asserting broken bindings, whose cases move to the list;
- the required-field coverage tests that loop over zero fields, replaced by §5.4;
- `test_ingest_command.py` and the ingest cases of `test_engine_form_agnostic.py`;
- the generate-all test that swallowed 122B's `PyPdfError` and checked only byte length.

**Coverage:** backend coverage must stay at or above CI's 90% floor. The deleted generator tests covered deleted code, so the ratio holds, and the plan measures it after the deletion.

## 7. Security and UPL

**DIG-124.** Form 121's full SSN was stored as plain JSON and returned by the forms API. Production runs the same code.

- **The wipe.** The owner approved wiping production's stored `form_data` now, with a one-off Heroku command:
  1. Count the rows with non-empty `form_data`, and the Form 121 rows among them, printing counts only.
  2. Run `GeneratedForm.objects.update(form_data={})`.
  3. Confirm the count is zero.
- **Backups.** The daily Heroku Postgres backups taken before the wipe still hold those values. Expiring or replacing those backups is part of the runbook and the owner's call.
- **The exposure window.** Until step 1 deploys at the end of the forms project, every form generated on the live site stores the SSN again. Forms shouldn't be generated on the live site until then.
- **Ticket status.** DIG-124 stays open until step 1 is live in production.

**Exemptions.** Deleting `schedule_c_generator.py` removes code that picked statutes and amounts for the filer under 735 ILCS 5/12-901.

- What it did: it gave the homestead statute to any real property, and applied the wildcard exemption to each asset separately.
- Who saw it: the API returned its choices in the `generate` response, in `form_data` and from `preview`, though no screen showed them.
- What replaces it: step 3 brings exemptions back as the filer's own choice, with information only (`docs/UPL_COMPLIANCE.md`).

**Logging.** Filler and resolver errors log the exception's type only (§5.7).

**Test data.** Persona tables and markers use only synthetic data, with SSNs from the IRS-reserved 900 range.

## 8. Success criteria

1. **Validation:** all 17 schemas pass §5.4. A schema error fails `manage.py check`, `runserver`, `migrate` (and so the Heroku release) and the test suite.
2. **Tier 1:** it passes for every binding, with zero `no_widget`, `collision` and `spill` entries on the known-defects list. Every `unmapped_choice` entry carries a ticket.
3. **Tiers 2 and 3:** they pass, or each failure is listed with a ticket. The list's size, by tier and class, is reported in the PR.
4. **No exposure:** the API returns no `form_data`, and `field_values` is encrypted at rest. A test reads the raw database column and finds no SSN.
5. **Packet:** generate-all and `packet` return only the forms that apply, with 122B gone and 122A-2 present only above the median. A form that doesn't apply returns 422 from `generate`.
6. **Preconditions:** each `requires` case returns 422 with its reason. For example, Form 121 for a session without a `DebtorInfo` returns 422, not a PDF.
7. **Search:** the search in §5.5 returns nothing.
8. **Coverage and E2E:** backend coverage is at least 90%. The five journeys that generate forms (Sarah, Maria, DeShawn, James and the SOFA journey) pass with their updated packet sizes.

## 9. Tickets

**Closed by this step:**

- DIG-63 (collisions);
- DIG-64 (the 103B name box, and silently dropped bindings);
- DIG-67 (no test checks the printed form);
- DIG-125 (122B);
- DIG-127 (ingest).

**Partly addressed here, finished later:**

| Ticket  | Here in step 1             | Finished in                          |
| ------- | -------------------------- | ------------------------------------ |
| DIG-68  | checkbox mechanics         | per-box mappings, steps 2 and 4      |
| DIG-69  | one path                   | rows, step 3                         |
| DIG-71  | Debtor 2 bindings dropped  | — (joint filing is out)              |
| DIG-72  | the conditional packet     | result sections, step 2              |
| DIG-75  | the dict `on_states` crash | the amended-filing binding, step 2   |
| DIG-81  | generator deleted          | exemptions, step 3                   |
| DIG-83  | shared names               | identical export states, step 3      |
| DIG-124 | code fix and wipe          | closes when step 1 is live           |
| DIG-126 | — (106J-2 is moot)         | 108, step 3                          |
| DIG-77  | —                          | row boxes, step 2; questions, step 4 |

**Later steps:**

- **Step 2:** DIG-36, 49–53, 56, 59–62, 65, 66, 73, 74, 76, 78, 79, 80, 82, 120, 128.
- **Step 3:** DIG-119, 121–123.
- **Step 4:** DIG-70.

## 10. Open questions for later steps

Each is asked when its step starts:

- income per source (DIG-36/49/56), which reverses the upload PR's spec §4.4;
- where Schedule J puts combined utilities and insurance;
- 122A-1 scope (the 51/53/56/65 chain);
- the exemptions experience;
- the 17 tickets that need a legal reading, decided as one batch.
