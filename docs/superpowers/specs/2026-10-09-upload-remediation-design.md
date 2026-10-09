# Upload Remediation — Design Spec

**Date:** 2026-10-09
**Status:** Approved in brainstorming; pending owner review of this document
**Branch:** `fix/upload-remediation`
**Supersedes in part:** `2026-06-20-document-ingestion-prefill-v2-design.md`, which assumed:

- **§2:** the hybrid sidecar is discoverable at `odl-hybrid:5002` and can run as a Heroku dyno. Neither holds.
- **§7:** a credit report with zero tradelines counts as COMPLETED.

**Tickets fixed (Plane, project DIG):**

- **Core:** DIG-1, 2, 3, 4, 5, 6, 7, 9, 13, 41, 45, 52
- **Traceability:** DIG-21, 30, 37

---

## 1. Why

A live local triage on 2026-10-09 drove the upload flow end to end with synthetic files. In the normal flow, an upload has no effect the filer can see.

**What happened:**

- **Step 5 (Amounts Owed):** a scanned bill created a draft debt that step 5 never showed, and the next save deleted it.
- **Pay stub:** became a debt owed to the employer.
- **2-page bill:** reported "✓ Done" with every field empty.
- **Failures:** three uploads failed while the page reported "Found: 5 creditor bills."
- **E2E:** the uncommitted reorder broke every E2E journey.

**Design review:** a design workflow followed — six area designers, six adversarial reviewers and a completeness critic, all reading the code. Two more designer and reviewer pairs covered the income and expense additions. Together they found three more defects, each of which turns the fixes above into silent data loss unless it ships alongside them:

- **Replace-all save.** It deletes and recreates nested debts and assets. Autosave fires about 2 s after the filer lands on a step, so once amounts become readable, every visit to step 5 would recreate the rows. Write-only `account_number`, the scan link and `is_secured` would be lost (DIG-21). Re-sending a row loaded from the server raises a 500 today (DIG-37).
- **Income step.** It rebuilds `monthly_income` from per-source boxes the server never stores, so reopening Income writes six zeros (DIG-41).
- **Expense step.** It sends five field names the backend does not know. DRF drops them silently, so car, food and other costs save as $0 (DIG-45). Schedule J also binds several expense fields to the wrong PDF lines, which today print $0 and would print real numbers in the wrong places once DIG-45 ships.

## 2. Decisions

| Topic              | Decision                                                                                                                                                                                   | Rejected                                                                                                                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Scope              | DIG-1, 2, 3, 4, 5, 6, 7, 9, 13, 41, 45, plus traceability DIG-21/30/37 and the Schedule J bindings                                                                                         | Data-loss-only PR; every upload ticket in one PR                                                                                                                                     |
| Branching          | Health/SPA commits ship as their own PR. `fix/upload-remediation` branches from them.                                                                                                      | One PR for everything                                                                                                                                                                |
| Saving nested rows | **Upsert by id.** A sent row with an id updates only the fields sent. A row without an id is created. A stored row absent from the payload is deleted. A client-sent `session` is ignored. | Keeping replace-all (silent field loss); preserving drafts on save (resurrects drafts the filer deleted); per-item CRUD for debts and assets (rewrites two steps' save and autosave) |
| Stale wizard       | **Re-read the session on every wizard mount.** Steps render only after the re-read returns.                                                                                                | Refreshing only when leaving `/documents` (the header logo link and browser Back bypass it)                                                                                          |
| Money fields       | Debt `amount_owed` and asset `current_value`/`amount_owed` become readable to the owner. SSN and `account_number` stay write-only.                                                         | Keeping them write-only                                                                                                                                                              |
| PDF reading        | **Drop the hybrid sidecar everywhere.** Java-only opendataloader reads text-layer PDFs. Scans get vision on up to 3 pages. One code path, one `OPENAI_API_KEY`.                            | Hosting the sidecar (no auth on client or server, no default timeout, Heroku H12, every option still sends content to OpenAI); configurable sidecar (local and prod diverge)         |
| Document type      | Three labelled upload areas: bills and statements, pay stubs, credit report                                                                                                                | Per-file picker; auto-classify                                                                                                                                                       |
| E2E proof          | A local fake OpenAI server; the backend reads `OPENAI_BASE_URL`                                                                                                                            | Seeding drafts through the API (skips upload); vitest only                                                                                                                           |
| Schedule J         | Fix the field bindings in this PR, alongside DIG-45                                                                                                                                        | A separate PR behind a deploy gate                                                                                                                                                   |

## 3. Prerequisites

1. **Merge PR #14** (`fix/ci-e2e-cors-origin`, BIZ-77) into `main`. E2E on `main` has been red since PR #13, so no later PR can show green E2E without it.
2. Rebase `fix/health-checks-and-keep-warm` (4 commits) onto `main` and open its PR.
3. Branch `fix/upload-remediation` from that tip. Stage each commit by file or hunk. The working tree also holds unrelated changes (README landing image, `DESIGN.md`, `assets/`, `.serena/`), and those stay out.

## 4. Design

### 4.1 Saving nested debts and assets — DIG-21, DIG-37

`backend/apps/intake/serializers.py`:

- **Nested serializers.** Add nested-only subclasses with a writable id, `NestedDebtInfoSerializer(DebtInfoSerializer)` and `NestedAssetInfoSerializer(AssetInfoSerializer)`, each with `id = serializers.IntegerField(required=False)`. `IntakeSessionSerializer` uses them for `debts` and `assets`. `DebtViewSet` and `AssetViewSet` keep the base serializers, so per-item create never accepts a client id.
- **`update()`, for each list that is present:**
  1. Map the session's existing rows by id.
  2. For each item, pop `session` and `id`.
  3. If the id is one of this session's rows, set only the keys present in the item, then save.
  4. Otherwise create a row on this session. An unknown or foreign id never touches another session.
  5. Delete this session's rows whose ids were not sent.
- **Unchanged:**
  - Debtor, income and expense records keep `update_or_create`.
  - `intake/views.py:111-112` still clears `is_draft` on any PATCH that includes debts. That behavior is documented under §6 and belongs to DIG-14.

Because PATCH is partial, nested rows validate partially. A row the browser loaded and sent back keeps `account_number`, `source_document` and `is_secured`, none of which it ever received.

### 4.2 Fresh session on every wizard mount — DIG-1, DIG-30

- **`frontend/src/pages/IntakeWizard.tsx`, on mount with a known session id:**
  - It calls `loadSession(id)`. While the call runs, it shows "Loading your information..." and no step.
  - On success it fills step state from the fresh session.
  - On failure it shows a calm alert ("We couldn't get your latest information just now. Please try again in a moment.") with a **Try again** button. It renders no step, so autosave cannot fire on stale data.
  - Session creation for a filer with no saved session stays as it is.
- **Acceptance criterion:** step components mount only after the re-read has filled them, so the first autosave runs on server data.
- **`frontend/src/context/IntakeContext.tsx`:** `loadSession` removes `current_session_id` only on a 404, the code DRF returns for a session that is gone or not yours. A 429, a 5xx or a network error leaves the resume pointer intact. The provider's own startup effect keeps its current behavior (DIG-11 tracks it).
- **`DocumentUploadPage`:** Continue and Skip simply navigate to `/intake`, because the wizard mount handles the refresh.
- **Cost:** one extra GET per wizard entry, and two on a cold app load. Accepted.

### 4.3 Readable amounts — DIG-2

- **Serializers:** drop `write_only` from `DebtInfoSerializer.amount_owed` (`serializers.py:191`) and from `AssetInfoSerializer.current_value` and `amount_owed` (`:155-158`). Keep the explicit `DecimalField` declarations.
- **Wizard hydration:** a single helper converts DRF decimal strings to numbers as data enters wizard state, for assets, debts and expenses (§4.5). An unparseable string becomes `undefined`, never `NaN`.
- **Out-of-range amounts.** A stored amount wider than 12 digits makes `DecimalField(12,2).to_representation` raise `InvalidOperation`, which 500s every session read; I verified this. Bounds land before amounts become readable (§4.7). Once amounts are readable, the documents `validate` endpoint returns 400 for an `amount_owed` that fails `DecimalField(max_digits=12, decimal_places=2)`.

### 4.4 Income step keeps what was saved — DIG-41

The model stores only `IncomeInfo.monthly_income`, a 6-month array. It is the canonical value: the means test (CMI = sum/6), Schedule I, 106Sum, 107, 122A-1, Schedule J and the seed data all read it. The step's ten per-source boxes are never stored.

- **Backend.**
  - Add `IncomeInfo.calculate_total_monthly_income()`, which returns the 6-month mean quantized to cents. It mirrors `ExpenseInfo`'s total method.
  - `IncomeInfoSerializer` exposes `total_monthly_income` as a read-only `SerializerMethodField` that delegates to that method.
  - No migration.
- **`IncomeInfoStep.tsx`:**
  - A module-level `SOURCE_FIELDS` list (ten keys) drives the sum.
  - The step is in per-source mode once any source key is _present_ in its data (`f in formData`), not when one holds a value. Typing writes the key, and server payloads never carry it.
  - Without source keys, the step shows the saved total. It re-emits `monthly_income` exactly as stored and adds the note: "Your saved total is $3,200.00 a month. We keep only the total, not the amount from each source, so the boxes below start empty. If you enter amounts below, they will replace the saved total."
  - With source keys, it rebuilds `monthly_income` as six copies of the sum, as today.
- **`IntakeWizard.tsx` income save:** send `{ income_info: { monthly_income } }` only. Echoing hydrated server fields back (`marital_status: ''`) returns 400 today and strands the filer on Income.
- **Existing rows:** no backfill. Zeros already written cannot be told apart from a real $0 income (§7).

### 4.5 Expenses saved under the names the forms read — DIG-45

The backend names are canonical: model, serializer, Schedule J, 122A-2, means test and seed data.

- **`types/api.ts`:**
  - Rename `car_payment`→`vehicle_payment`, `car_insurance`→`vehicle_insurance`, `gas_transportation`→`vehicle_maintenance`, `food_groceries`→`food_and_groceries`, `other_necessary_expenses`→`other_expenses`.
  - Add `clothing` and `child_support_paid`.
  - Export `EXPENSE_FIELDS`, the 13 canonical keys.
- **`ExpenseInfoStep.tsx`:**
  - Rename only. The transportation field keeps its label and help, including bus or train fare, because Schedule J line 12 groups gas, maintenance and transit fares.
  - Add inputs for clothing and child support paid.
  - Sum with `EXPENSE_FIELDS`.
- **Wizard hydration** converts expense decimal strings to numbers, using the §4.3 helper.
- **E2E:**
  - `wizard.page.ts` `fillExpenses` fills `input[name=<key>]` directly; drop `EXPENSE_FIELD_MAP`.
  - `maria-happy-path` asserts that the fee-waiver form prefills the full expense total.
- **Existing rows:** every expense row saved through the wizard since `169b34e` holds 0 in the seven affected fields. Nothing can be recovered (§7).

### 4.6 Schedule J field bindings — DIG-52

The template is `form_b106j.pdf`. Its field names match the printed line numbers; I checked this by comparing each widget's position with the label beside it. The schema binds most expenses to the wrong field names. Fix these files so each expense lands on its labelled line:

- `data/forms/schemas/schedule_j.json`
- the child-support fold in `backend/apps/forms/services/derivations.py` (`schedule_j_other_expenses`, ~544-546)
- the plan doc `docs/superpowers/plans/2026-06-04-pdf-field-mappings.md` (~577-587)
- `backend/apps/forms/tests/test_pdf_field_maps.py:207-213`, which asserts the wrong fields today

| Expense field            | Bound today to                   | Correct field       | Printed line                                        |
| ------------------------ | -------------------------------- | ------------------- | --------------------------------------------------- |
| `rent_or_mortgage`       | `10` (personal care)             | `4`                 | Rental or home ownership expenses                   |
| `home_maintenance`       | `14` (charitable contributions)  | `4c`                | Home maintenance, repair, and upkeep                |
| `utilities`              | `12` (transportation)            | `6d` + `Other 6d`   | Utilities, other (see note)                         |
| `food_and_groceries`     | `15a` (life insurance)           | `7`                 | Food and housekeeping supplies                      |
| `childcare`              | `15b` (health insurance)         | `8`                 | Childcare and children's education                  |
| `clothing`               | `15c` (vehicle insurance)        | `9`                 | Clothing, laundry, and dry cleaning                 |
| `medical_expenses`       | `16` (taxes)                     | `11`                | Medical and dental expenses                         |
| `vehicle_maintenance`    | `17a` (Vehicle 1 payments)       | `12`                | Transportation: gas, maintenance, bus or train fare |
| `vehicle_insurance`      | `17c` (other installments)       | `15c`               | Vehicle insurance                                   |
| `insurance_not_deducted` | `20a` (other-property mortgages) | `15d` + `Other 15d` | Other insurance (see note)                          |
| `vehicle_payment`        | `17b` (Vehicle 2 payments)       | `17a`               | Car payments for Vehicle 1                          |
| `child_support_paid`     | added into `21`                  | `18`                | Alimony, maintenance, and support                   |
| `other_expenses`         | `21`, plus child support         | `21` + `Other 21`   | Other                                               |

**Combined amounts.** The wizard collects some amounts as one figure where the form splits them:

- `utilities` ("Gas, electric, water, etc.") covers lines 6a–6c together.
- `insurance_not_deducted` ("Health, life, or disability insurance not deducted from paycheck") covers 15a, 15b and 15d together.

Putting a combined figure on a category line such as 6a or 15b would state a breakdown the filer never gave. Each one goes on the line's "Other" row instead. A derived rule fills the matching "Specify" box ("All utilities, combined"; "Health, life, or disability, combined") only when the amount is above zero; otherwise the box stays blank. `Other 21` reads "Other necessary expenses" on the same condition. The line totals and line 22a are unaffected. This placement is a judgment call for the owner to confirm; collecting the split itself is out of scope.

**Unchanged:** `22a` (total expenses) and `23a` (income) keep their current rules. Lines 22c, 23b and 23c stay blank (DIG-61). The source of 23a belongs to DIG-56.

**Test:** for each canonical expense field, a distinct amount lands in the PDF field whose on-page label matches that expense's line. The label check reads widget rects and label positions from the template with pypdf, so it fails if a binding drifts.

### 4.7 Extraction outcomes and filer-safe failure reasons — DIG-7

- **Model:**
  - Add `OCRFailureReason(TextChoices)` with values `nothing_found` and `processing_error`.
  - Add `OCRResult.failure_reason` (blank default) in `documents` migration `0006`. (`intake` already has an unrelated `0006`.)
  - `error_message` stays an operations field. It records exception class names and `finish_reason`, never model output.
- **Empty means unread**, judged per document type:

  | Type          | Unread when                         | Partial result                                                                     |
  | ------------- | ----------------------------------- | ---------------------------------------------------------------------------------- |
  | creditor bill | no creditor name                    | creditor but no balance → COMPLETED draft with amount 0, for the filer to complete |
  | pay stub      | no gross pay or no pay-period dates | —                                                                                  |
  | credit report | no readable tradelines              | tradelines that are all $0 → COMPLETED with no new debts                           |

  An unread document becomes FAILED with `nothing_found`; this overrides the June spec §7. A processing exception becomes FAILED with `processing_error`.

- **`DraftDebtCreator`:**
  - Handles `None` safely: no creditor name means no debt and no crash.
  - Maps a non-finite, negative or ≥1e10 amount to 0.
- **`PayStubExtraction`:** `confidence_score` defaults to 0. Today the processor pops the score before storage, so every real pay stub fails validation and none reaches Schedule I.
- **`TradelineItem`:**
  - `account_type` and `account_status` become optional.
  - Numbers coerce to strings.
  - `creditor_name` is stripped, with `min_length=1`.
  - `amount_owed` gets `le=9999999999.99`.
  - Each line validates on its own, so one bad account does not discard the report.
- **Credit-report prompt hint:**
  - Add a `CREDIT_REPORT` entry to `_FIELD_HINTS` (`prompts/image_extraction.py`). Without it the model is never asked for accounts.
  - The hint asks for `tradelines[]` with `creditor_name`, `account_number`, `amount_owed`, `account_type`, `account_status` and `credit_limit`.
  - It tells the model to skip any account whose creditor or balance it cannot read, to write amounts as plain numbers, and to use 0 for a credit balance.
- **Logging:** `aggregator.py` logs the exception class, not the pay-stub values.
- **API (`documents/views.py` `_serialize_ocr`):**
  - Returns `status`, `failure_reason`, `confidence_scores`, `overall_confidence` and `user_validated`.
  - Stops returning `error_message` and the decrypted `extracted_data`, which no frontend code reads.
  - `OCRResult.ocr_provider` records `settings.OCR_PROVIDER` instead of defaulting to "gemini".

### 4.8 PDF reading without the sidecar — DIG-4

**`processor.py`:**

- **Conversion:** `opendataloader_pdf.convert(input_path=[path], output_dir=out, format="markdown", image_output="off", include_header_footer=True)`.
  - **No hybrid arguments.** One JVM launch per document, not three.
  - **`image_output="off"`:** a scanned PDF yields empty text and routes to vision. Without it, image placeholders reach the text prompt.
  - **`include_header_footer=True`:** keeps the letterhead, where creditor names and account numbers usually sit.
- **Routing:**
  - Text of at least `_MIN_TEXT_LENGTH` characters goes to the text prompt.
  - Otherwise `_pdf_to_page_images(pdf_bytes)` renders up to `_MAX_SCANNED_PAGES` (3) JPEG pages for vision.
  - A PDF with no pages fails.
  - A missing JVM or module still falls back to vision.
- **Provider interface:** `BaseOCRProvider.extract(images: list[bytes], prompt)`. An empty list means text mode.
  - OpenAI sends one `image_url` part per page, in order.
  - Gemini sends one inline part per page.
  - A direct photo upload is a one-item list.
  - `classify()` stays unchanged (DIG-39).

### 4.9 Empty model replies — DIG-9

- **Empty reply:** `OpenAIProvider._complete` treats `not (content or "").strip()` as empty.
  - It retries once, unless the reply carried a refusal or `finish_reason == "content_filter"`.
  - On final failure it raises an error that names `finish_reason` and states whether a refusal was present. It never includes the refusal text.
- **Parse errors:** `processor._parse_result` reports "model reply was not valid JSON (N characters)" and drops the `raw[:200]` excerpt.
- **Not changed here:** Gemini parity (DIG-35) and an OpenAI client timeout (DIG-29) remain follow-ups.

### 4.10 The upload page — DIG-3, DIG-5, DIG-13

`DocumentUploadPage.tsx`, `UploadQueue.tsx`, `FileDropZone.tsx`:

- **Upload areas.** Three labelled areas, built from an `UPLOAD_AREAS` list:

  | Area                 | Type sent       |
  | -------------------- | --------------- |
  | Bills and statements | `creditor_bill` |
  | Pay stubs            | `pay_stub`      |
  | Credit report        | `credit_report` |

  - Each area is a `<section>` with an `<h2>` and help text (copy table, §5).
  - `FileDropZone` takes a `label`, and its `aria-label` becomes `${label}: drop files here or click to upload`. The zone is disabled while a file is sending or no session exists yet.

- **Queue rows:**
  - A row appears the moment a file is chosen.
  - States: waiting → uploading → checking → done | failed (reason by `failure_reason` and type) | not uploaded | unchecked.
  - Files send one at a time. Each row polls its own status every 3 s and backs off on 429, 5xx or network errors. After the time limit it shows "unchecked" instead of hanging.
- **Retry:** the areas stay visible after a batch, so a filer can add or re-send files.
- **Summary:** counts only files that were read, by type, in plain words.
- **Button:**
  - Reads "Skip for now" until at least one file is read, then "Continue".
  - Disabled while a file is sending.
  - Its labels must stay exactly these, because E2E depends on them.
- **Copy:**
  - Stays inline, matching every other page.
  - Keeps the OpenAI disclosure.
  - Drops the false promise "you can review and correct anything before submitting".
  - Promises nothing about Income pre-fill.
- **Expired login:** `api/client.ts` `uploadDocument` handles a 401 with a refresh token by calling `attemptTokenRefresh()` and retrying once. It then throws `APIClientError` with the status code. Access tokens last 30 minutes.
- **Locator contract** for E2E:
  - the drop-zone `aria-label` pattern
  - `<ul aria-label="Upload queue">`
  - a done row containing "Done"
  - the h1 "Upload your documents"
  - the `role="alert"` error region

### 4.11 Removing the sidecar — DIG-4

- `docker-compose.yml`: delete the `odl-hybrid` service and the backend's `depends_on` entry for it.
- `backend/requirements/base.txt`: `opendataloader-pdf[hybrid]` → `opendataloader-pdf`. This also removes torch and CUDA from the backend image, most of DIG-16.
- The commit body tells developers to run `docker compose up --build --remove-orphans` and reinstall their venv.

### 4.12 E2E — DIG-6

- **Page objects:**
  - `register.page.ts` and `login.page.ts` wait for `/intake`.
  - A new `DocumentsPage.skip()` clicks "Skip for now".
  - Each of the six journeys calls it after step 1.
- **New `scanned-bill-journey.spec.ts`:**
  - `e2e/fixtures/fake-openai.ts` starts a `node:http` server on `127.0.0.1:4010`. It answers `POST /v1/chat/completions` with a canned creditor-bill JSON.
  - The CI E2E job starts the backend with `OPENAI_BASE_URL=http://127.0.0.1:4010/v1` and a dummy key.
  - Off CI, the spec skips with a visible reason when that wiring is absent; in CI it is required.
- **The scanned-bill journey's steps:**
  1. Upload a synthetic bill and see "Done".
  2. Continue to step 5 and see the creditor, debt type and amount.
  3. Save, reload, and see them again.
  4. Assert `completions >= 1`.
  - The "From scan" badge is not asserted after reload, because the save clears `is_draft`.
  - Account-number preservation is proven by backend tests, since the field is write-only.

## 5. Copy table

All copy is legal information, never advice, written per `TRAUMA_INFORMED_DESIGN.md` and `PLAIN_LANGUAGE_GUIDE.md`. The frontend reads only `status`, `failure_reason` and `document_type`.

| State                                                                     | Text                                                                                                                                                                                                    |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| done                                                                      | ✓ Done                                                                                                                                                                                                  |
| failed · nothing_found · bill                                             | We couldn't find the name of the company you owe in this file. You can upload a different page, or add this bill yourself in a later step.                                                              |
| failed · nothing_found · pay stub                                         | We couldn't find the pay amount and pay dates in this file. You can upload a different page, or type your income in yourself in a later step.                                                           |
| failed · nothing_found · credit report                                    | We couldn't find any accounts in this file. You can upload a different file, or add your bills yourself in a later step.                                                                                |
| failed · processing_error or legacy blank                                 | We couldn't read this file. You can try again, or type the details in yourself in a later step.                                                                                                         |
| not uploaded                                                              | This file didn't upload. You can try again. (On a 400, add: "Please use a PDF, JPEG, or PNG file.")                                                                                                     |
| unchecked                                                                 | We couldn't check on this file. If we read it, what we found will still be used.                                                                                                                        |
| wizard refresh failed                                                     | We couldn't get your latest information just now. Please try again in a moment.                                                                                                                         |
| help · bills                                                              | …will show up in the Amounts Owed step, marked "From scan." You can check or change it there.                                                                                                           |
| help · pay stubs                                                          | …used for your income form (Schedule I).                                                                                                                                                                |
| help · credit report                                                      | Accounts with a balance will show up in the Amounts Owed step, marked "From scan." If you also uploaded a bill for the same account, it may show up twice. We may miss some, so please check that list. |
| income · saved total note (the amount is the saved total, e.g. $3,200.00) | Your saved total is $3,200.00 a month. We keep only the total, not the amount from each source, so the boxes below start empty. If you enter amounts below, they will replace the saved total.          |

## 6. Known behavior and residuals

- **The "From scan" badge disappears quickly.** Any debt save clears `is_draft` (`intake/views.py:111-112`), and autosave saves step 5 about 2 s after arrival. The server therefore marks drafts confirmed without any action by the filer. The badge stays only until the next remount. Tracked by DIG-14 (review UI).
- **Uploads remain synchronous (DIG-8).** Reading up to 3 pages by vision, plus one retry, raises worst-case latency against Heroku's 30 s router limit. Accepted. DIG-29 tracks an OpenAI client timeout.
- **Partial reads still exist (DIG-40).** The text prompt truncates at 4000 characters, and vision reads at most 3 pages. The credit-report help copy says "We may miss some."
- **Wizard-entered secured debts.** `is_secured` and `collateral_description` are absent from `DebtInfoSerializer.Meta.fields`, so wizard-entered secured debts still save as unsecured (DIG-26). Upsert by id now preserves the flag on scanned drafts.
- **Duplicates (DIG-10)** and **revisiting `/documents` shows an empty list (DIG-25)** remain.

## 7. Deploy gates and operations

DIG-58 tracks these checks. Run them before deploying. Production checks are read-only, through `heroku run python manage.py shell`, and print ids and counts only:

1. **Out-of-range amounts:** `DebtInfo` and `AssetInfo` rows whose decrypted amount is non-finite or ≥1e10. Each would 500 its session once amounts are readable; fix them first.
2. **Zeroed income:** `IncomeInfo` rows with a non-empty `marital_status` and an all-zero `monthly_income` (DIG-41). Count them only. $0 is a valid answer, so there is no backfill.
3. **Zeroed expenses:** `ExpenseInfo` rows saved through the wizard (`data_source='manual'`, excluding demo users) with all seven affected fields at 0 (DIG-45). The data is unrecoverable; contact affected filers directly.
4. **Key:** `OPENAI_API_KEY` is set on Heroku (check its length, not its value).
5. **After deploy:** `heroku run python manage.py showmigrations documents` shows `0006` applied, and `/health/detailed/` returns ok.
6. **The owner's own intake** (run on v30/v31): re-enter Expenses, regenerate the forms and redo the fee-waiver application before filing anything. This PR does not fix the other court-form defects, so check those forms by hand even after it ships:
   - Form 122A-1: DIG-49, 51, 53, 56, 59
   - Form 122A-2: DIG-50, 60
   - In-app means test transport allowance: DIG-62
   - Schedule I: DIG-36, 56
   - Schedule J lines 22c–23c: DIG-61

## 8. Tests

Tests are named for outcomes and mock only boundaries: the OpenAI client, the network and the opendataloader JVM.

- **Backend, saving (§4.1–4.3):**
  - A filer who corrects an amount on a debt loaded from the server can save it, and an asset sibling covers the same case.
  - A nested row naming another user's session lands on the owner's session only.
  - Re-saving a session exactly as received keeps amounts, account numbers and scan links.
  - Amounts are readable while SSN and account numbers stay private.
  - Only the owner can read amounts.
- **Backend, income (§4.4):**
  - A returning filer gets the saved income total.
  - Saving income amounts keeps the household details.
  - An income PATCH with a blank `marital_status` returns 400.
- **Backend, expenses and Schedule J (§4.5–4.6):**
  - An expense-step save reaches every Schedule J line, asserted through the generator.
  - Each expense lands on its labelled Schedule J field.
- **Backend, `test_processing_outcomes.py`** (real processor and provider; only `openai_provider.OpenAI` patched):
  - The balance on page 2 of a text PDF reaches the model.
  - A scanned PDF sends at most three page images, in order.
  - A PDF with no pages fails instead of completing empty.
  - An empty reply is retried once, and its cause is recorded.
  - A cover page with no account details is reported as nothing found.
  - A bill without a creditor creates no debt and doesn't crash.
  - A bill with a creditor but an unreadable balance becomes a draft for the filer to complete.
  - A pay-stub upload produces monthly income for Schedule I.
  - A credit report with no readable accounts is reported as nothing found.
  - One bad account line keeps the rest of the report.
  - A report showing only paid-off accounts is done, with no new debts.
  - A reading failure shows the filer a reason code, never provider text.
- **Backend, units:**
  - The credit-report prompt asks for every field the importer needs.
  - Negative or non-numeric balances are not recorded.
  - A real-JVM contract test runs where Java exists and is skipped visibly where it does not (`-rs` in CI).
- **Vitest:**
  - **Wizard:** a debt read from an uploaded bill shows at Amounts Owed after the filer continues from uploads, without a reload. A failed refresh keeps the saved place and lets the filer retry.
  - **IntakeContext:** a temporary load failure keeps the resume pointer.
  - **Income:** a returning filer sees the saved income instead of $0 and saves no zeros. Changing nothing keeps each month as stored. Entering source amounts replaces the total. A filer can record $0.
  - **Expenses:** the step sends canonical names. Clothing and child support count in the total.
  - **Upload page:** each area sends its own type. The summary counts only files that were read. Each failure gets its own plain reason. Rows appear at once. A busy server doesn't strand a file. An unchecked file still lets the filer move on. The button reads "Skip for now" until a file is read. Files send one at a time. An upload after an expired login succeeds.
  - **Timer tests** wait for the heading under real timers, then switch to fake timers with `userEvent.setup({ advanceTimers })`.
- **E2E:** the six journeys pass with the detour, `scanned-bill-journey` passes, and `maria-happy-path` asserts the fee-waiver expense prefill.

## 9. Commit sequence

Each commit passes on its own:

- **Backend:** `pytest` with `config.settings.test`, `ruff check .` (0.8.5) and `manage.py makemigrations --check --dry-run`.
- **Frontend:** `vitest`, `tsc` and `eslint`.
- **E2E:** runs at commit 3 and at the tip.

| #   | Message                                                                         | Tickets              |
| --- | ------------------------------------------------------------------------------- | -------------------- |
| 1   | docs(spec): design the October upload remediation                               | all                  |
| 2   | feat(documents): read uploads with OpenAI, selected by OCR_PROVIDER             | —                    |
| 3   | feat(intake): ask for documents after the filer's basic information             | DIG-6                |
| 4   | fix(intake): save nested debts and assets by id                                 | DIG-21, DIG-37       |
| 5   | fix(intake): re-read the session whenever the wizard opens                      | DIG-1, DIG-30        |
| 6   | fix(documents): read every page of a PDF without the hybrid sidecar             | DIG-4                |
| 7   | chore(infra): drop the odl-hybrid sidecar and the [hybrid] extra                | DIG-4, DIG-16 (part) |
| 8   | fix(documents): retry an empty OpenAI reply once and record why                 | DIG-9                |
| 9   | fix(documents): report a scan that found nothing as failed, not done            | DIG-7                |
| 10  | fix(documents): ask the model for each account on a credit report               | DIG-3                |
| 11  | fix(intake): show filers the amounts they already entered                       | DIG-2                |
| 12  | fix(intake): keep saved income when the Income step reopens                     | DIG-41               |
| 13  | fix(forms): put each Schedule J expense on its labelled line                    | DIG-52               |
| 14  | fix(intake): save expenses under the names the court forms read                 | DIG-45               |
| 15  | feat(frontend): give bills, pay stubs and credit reports their own upload areas | DIG-3                |
| 16  | fix(frontend): show each file's real outcome and let the filer retry            | DIG-5, DIG-13        |
| 17  | test(e2e): follow a scanned bill from upload to Amounts Owed                    | DIG-1, DIG-6         |

**Commit contents:**

- **Commit 1:** also sets the June spec's status to "Superseded in part by 2026-10-09-upload-remediation-design.md".
- **Commit 2:** adds tests for provider selection (the openai default, the gemini branch, the `OCR_MODEL` override, an unknown provider failing at read time). It also adds `OPENAI_API_KEY`, `OCR_PROVIDER` and `OCR_MODEL` to both `.env.example` files and updates the provider line in the README.
- **Commit 3:** carries the E2E page-object fixes, so E2E is never committed broken.
- **Commits 4–17:** each updates the CLAUDE.md gotchas its own code makes true or false.

## 10. Follow-ups (filed, not in this PR)

DIG-8, 10, 11, 12, 14, 15, 16 (the `.dockerignore` part), 17, 18–20, 22–29, 31–36, 38–40, 42–44, 46–51, 53–57 and 59–62. DIG-58 is the deploy-check task in §7.
