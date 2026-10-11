# AI Assistant Context

**DigniFi** — trauma-informed bankruptcy filing platform (Chapter 7, ILND pilot district). Django REST API + React 19 frontend. Deployed on Heroku. Provides legal _information_, never _advice_ (UPL boundaries are non-negotiable).

## Quick Commands

```bash
docker compose up                              # Start all 3 services (db, backend, frontend)
docker compose exec backend python -m pytest    # Backend tests (uses sqlite :memory:, no postgres needed)
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py loaddata ilnd_2025_data   # Required before seed
docker compose exec backend python manage.py seed_demo_data            # Loads 5 AI personas

cd frontend && npm test                        # Frontend tests (vitest)
cd frontend && npm run e2e                     # E2E (requires backend running + seeded)
cd frontend && npm run lint:fix && npm run format
cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.5)
```

## Gotchas (things agents get wrong)

- **DRF pagination** — list endpoints return `{count, results}`, not bare arrays. Always `Array.isArray` guard.
- **React 19 + navigate()** — calling `navigate()` in render body crashes the reconciler. Use `useEffect`.
- **Vite HMR in Docker** — type/structure changes don't hot-reload; restart the frontend container.
- **Enum mismatches are silent** — frontend/backend enum drift only surfaces at runtime; check both when adding fields.
- **Nested debts and assets save by id** — `IntakeSessionSerializer.update` upserts `debts`/`assets` through `_save_rows_by_id`: a row carrying one of this session's ids updates only the keys it sends, a row without one (or with an unknown or foreign id) is created on this session, and a stored row missing from the payload is **deleted**, so send every row you want to keep. A nested `session` is ignored. Fields the browser never receives (`account_number`, `source_document`, `is_secured`) survive a re-save. `DebtViewSet`/`AssetViewSet` keep the base serializers, so per-item create never takes a client id.
- **Debt and asset amounts are readable, as strings** — the owner gets `DebtInfo.amount_owed` and `AssetInfo.current_value`/`amount_owed` back (SSN and `account_number` stay write-only). DRF sends decimals as strings (`"2500.00"`), so the wizard converts them with `hydrateAmounts` (`utils/parseAmount.ts`) as session data enters step state; a raw string in a step's `reduce` joins as text (`$02500.00100.50`). A stored amount wider than `DecimalField(12, 2)` makes every read of that session 500, so every write path must bound it (`DraftDebtCreator` stores it as 0; documents `validate` returns 400).
- **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data.
- **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
- **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 ≥ median_income_threshold` (never `above_median_calculated`, which is sticky, DIG-128); 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words; any other failure is a 500 logged by exception type only.
- **SSN on forms** — Form 101's `Debtor1.SSNum` PDF field is 4 chars (last-4 only); full SSN appears on Form 121. pypdf truncates from the front.
- **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. `generate_all` covers only the packet and deletes the rows of forms that no longer apply. `GET /api/forms/packet/?session=<id>` returns `{session, form_types}` in filing order, and the dashboard renders from it.
- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: template hash, full names, widget types, export states, `/Opt` values, duplicate bindings, TBD). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box, `{}` is unmapped and prints nothing.
- **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails today, each with its DIG ticket. Fixing a defect turns its xfail into a failure until you delete the entry. Regenerate it with `data/forms/field_index/tools/record_known_defects.py` (usage in its docstring) and review the diff by hand.
- **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, and the API never returns it. `form_data` is blank; its column is dropped one release after this code is live. A filed form downloads its stored `field_values`; an unfiled one is resolved fresh on every download.
- **Analytics auth** — `trackEvent()` must use `getAccessToken()` for Bearer header, not raw fetch.
- **heroku.yml release** — must be one command string (not argv list). `heroku releases:output` is empty; use `heroku logs --dyno release`.
- **CI ruff is pinned** — `ci.yml` installs `ruff==0.8.5`. Unpinned ruff broke CI when new rules shipped.
- **opendataloader-pdf needs a JRE** — both Dockerfiles install `default-jre-headless`. Without one, every PDF falls back to vision. `TestRealJvmContract` (`apps/documents/tests/test_processor.py`) runs the real CLI wherever `java` is on PATH and skips with a visible reason elsewhere (`-rs` in CI); every other test uses a stand-in for the module.
- **No PDF sidecar** — the `odl-hybrid` service and the `opendataloader-pdf[hybrid]` extra are gone; the backend runs the Java CLI itself. A stack or venv built before the removal still has them: run `docker compose up --build --remove-orphans` and recreate `backend/.venv` (`pip install -r` never uninstalls docling or torch).
- **Pre-commit prettier** — reformats staged files on first commit; re-`git add` and commit again.
- **Colima volume mounts** — Colima only mounts `$HOME` by default; `/Volumes/Containers` must be added in `~/.colima/default/colima.yaml`.
- **Compose backend** — command must chain `python manage.py migrate && ...` before `runserver`.
- **Frontend tests use MSW** — network requests are intercepted in `src/test/setup.ts`. Write MSW handlers for new API calls.
- **E2E needs full stack** — Playwright tests (`frontend/e2e/journeys/`) require backend running, migrations applied, and `seed_demo_data` loaded. `scanned-bill-journey` also needs `OPENAI_BASE_URL=http://127.0.0.1:4010/v1` in both the backend's and Playwright's environment, plus `OCR_PROVIDER=openai` and a dummy `OPENAI_API_KEY` for the backend; the spec starts the fake OpenAI server itself (`e2e/fixtures/fake-openai.ts`). Without the wiring it skips locally (printing why) and fails in CI. Export the dummy key: exported variables beat the repo-root `.env`, which may hold a real one.
- **`OPENAI_BASE_URL` comes from the SDK, not settings** — `OpenAIProvider` passes only the key; the `openai` SDK reads `OPENAI_BASE_URL` from the environment itself. An empty value (`OPENAI_BASE_URL=` in `.env`) is not ignored: the SDK uses `''` as the base URL and every OCR call fails.
- **Backend test settings** — `DJANGO_SETTINGS_MODULE=config.settings.test` uses sqlite `:memory:`, no postgres. E2E tests use `config.settings.development` (needs postgres).
- **FIELD_ENCRYPTION_KEY** — must be a real Fernet key (32 url-safe base64 bytes). CI uses `U9HKckkKBeT8wag2jMcOx2Cez2M2jtvNG4qxSHuYcAo=` (synthetic, encrypts nothing).
- **UPL compliance** — all user-facing text must be information, never advice. See `docs/UPL_COMPLIANCE.md`.
- **Nested `CLAUDE.md` files are empty stubs** — they are auto-generated `claude-mem` placeholders (~170 bytes each) reading `*No recent activity*`. This root file is the only real one; don't go looking for per-app conventions in them.
- **OCR provider is config-driven** — `_get_processor()` branches on `settings.OCR_PROVIDER` (`openai` | `gemini`) and lazy-imports the provider, so a missing SDK/key surfaces at OCR time, not app boot. `OCR_MODEL` empty ⇒ the provider's own default. Don't hardcode a provider.
- **`openai_provider.py`, never `openai.py`** — a module named `openai.py` inside `providers/` would shadow the installed `openai` package.
- **Prod throttling lives in `production.py`, not `base.py`** — base defines only the `auth` scope (`30/minute`); production adds `DEFAULT_THROTTLE_CLASSES` with `anon: 60/minute`, `user: 120/minute`, `auth: 5/minute`. Reading base alone wrongly concludes endpoints are unthrottled — polling ~14 documents exhausts `user` fast.
- **Document upload sits mid-wizard** — the flow is `login → /intake` step 1 → `/documents` → `/intake` steps 2–8. A scanned bill or credit report pre-fills Amounts Owed; pay stubs feed Schedule I through `IngestedAggregate`, never the Income step. `IntakeWizard.handleNext` detours when `nextStep === 2`. Nothing currently links back to `/documents` after a skip. The persona journeys pass the detour with `DocumentsPage.skip()` (`e2e/pages/documents.page.ts`) after step 1; `scanned-bill-journey` uploads with `uploadBill()` and clicks Continue.
- **`updateCurrentStep` is POST `/intake/sessions/{id}/update_step/`** — _not_ the PATCH that saves step data. Mocking the PATCH to assert step advancement silently captures the wrong call and passes vacuously.
- **Upload is synchronous despite the 202** — `views.py` uses `with ThreadPoolExecutor(...)`, whose `__exit__` calls `shutdown(wait=True)`, so `{"status": "processing"}` is returned _after_ OCR completes and holds a gunicorn worker. No `Future` is retained — that's the tell.
- **PDFs: text layer first, then up to 3 scanned pages** — `processor.py` runs `opendataloader_pdf.convert(..., format="markdown", image_output="off", include_header_footer=True)` with no hybrid arguments. Text of at least `_MIN_TEXT_LENGTH` (30) characters goes to the text prompt; otherwise `_pdf_to_page_images()` sends up to `_MAX_SCANNED_PAGES` (3) JPEG pages to vision, and a PDF with no pages fails. Without `image_output="off"` a scan's image placeholders reach the text prompt; without `include_header_footer=True` the letterhead naming the creditor is dropped.
- **`extract()` takes a list of page images** — `BaseOCRProvider.extract(images: list[bytes], prompt)`: `[]` means text mode, a photo upload is a one-item list, and pages go in page order (one OpenAI `image_url` part or one Gemini inline part each). `classify()` still takes bytes. Never hand a provider `[]` for a scan.
- **An empty OpenAI reply raises `EmptyModelReply`** — `OpenAIProvider._complete` retries a blank or whitespace-only reply once, but never a refusal or `finish_reason == "content_filter"`. The error names `finish_reason` and whether a refusal was present, never its text. `_parse_result` records only the reply's length ("model reply was not valid JSON (N characters)"), so `error_message` never holds model output. Gemini still returns `""` (DIG-35).
- **The wizard re-reads the session on every mount** — `IntakeWizard` fixes the session id at mount (context session, else `current_session_id`), calls `loadSession(id)`, and renders no step until it returns, so steps and autosave start from server data, not the context copy (which predates any upload on `/documents`). A failed read shows a "Try again" alert for the same id; a 404 starts a new session. `loadSession`/`createSession` resolve with the session, and `loadSession` clears `current_session_id` only on a 404, but the provider's own startup load still clears it on any error (DIG-11).
- **An empty scan is FAILED, not done** — `documents/views._record_findings` judges each type: a bill needs a creditor name, a pay stub must pass `PayStubExtraction`, the check the income aggregate applies (gross pay + both pay-period dates required; an invalid optional field such as a negative `net_pay` also fails it), a credit report needs one readable tradeline. Otherwise `OCRResult.status="failed"`, `failure_reason="nothing_found"`; any exception is `processing_error`. A bill with a creditor but no readable balance is `completed` with a $0 draft; a report of only $0 accounts is `completed` with no debts. Other document types are not judged.
- **The documents API never returns `error_message` or `extracted_data`** — `_serialize_ocr` returns `status`, `failure_reason`, `confidence_scores`, `overall_confidence`, `user_validated`. `error_message` is operations-only (exception class, `finish_reason`); read it in a Django shell. The pipeline's catch-all handlers (`_run_processing`, `AggregateIngestionService.recalculate`) log only the exception's type with `logger.error`, never `logger.exception`: logs reach Sentry, and a DB error's DETAIL quotes row values (DIG-105).
- **Scanned amounts are bounded** — `draft_debt._bounded_amount` stores a non-numeric, negative, non-finite or ≥1e10 balance as 0, and `TradelineItem.amount_owed` has `le=9999999999.99`: a wider value makes `DecimalField(12,2)` raise on every read of the session.
- **Prompt hints are per type and shared** — `_FIELD_HINTS` in `documents/services/providers/prompts/image_extraction.py` feeds both the vision and the text prompt (`text_extraction.py` imports it). A type with no hint is asked for "all visible fields as key-value pairs" and never returns the keys its importer reads; the `CREDIT_REPORT` hint's keys must stay in step with `TradelineItem`, and `test_prompts.py` checks that they do.
- **Income stores only the 6-month array** — `IncomeInfo.monthly_income` is canonical (means test, Schedule I, 122A-1); the Income step's ten per-source boxes are never stored. The API adds read-only `total_monthly_income` (the mean of the stored months, to the cent). `IncomeInfoStep` switches to per-source amounts only when a source key is _present_ in its data; otherwise it re-emits the stored months unchanged. The wizard saves `{income_info: {monthly_income}}` only, because echoing a wizard-created row's blank `marital_status` back is a 400.
- **Expense names are the backend's** — the Expenses step and the wizard's hydration use `EXPENSE_FIELDS` (`types/api.ts`), the 13 `ExpenseInfo` names that Schedule J, 122A-2 and the means test read; the E2E page object fills `input[name=<key>]` from the personas' canonical keys. DRF drops any other name silently: the old frontend names (`car_payment`, `food_groceries`, `other_necessary_expenses`, ...) saved as $0 until DIG-45. The API returns these amounts as decimal strings; the wizard converts them with `hydrateAmounts` when it loads the session.
- **Upload areas decide the document type** — `DocumentUploadPage`'s `UPLOAD_AREAS` maps "Bills and statements" → `creditor_bill`, "Pay stubs" → `pay_stub`, "Credit report" → `credit_report`. The backend stores whatever type is sent (`user_declared_type`) and never classifies. Each `FileDropZone` is named `${label}: drop files here or click to upload` with its file input inside.
- **MSW can't parse jsdom uploads with `request.formData()`** — undici rejects jsdom's `File`, so the read fails. Read multipart fields from `await request.text()`, as `sentDocumentType` in `DocumentUploadPage.test.tsx` does.
- **Upload page locator contract** — E2E depends on each zone's name `${label}: drop files here or click to upload` (file input inside), `<ul aria-label="Upload queue">`, a read row's "✓ Done", the h1 "Upload your documents", the `role="alert"` region, and the button reading exactly "Skip for now" until a file is read, then "Continue". Don't reword them.
- **Upload rows check themselves** — each `UploadQueue` row polls its document at once, then every 3 s, waits 6 s, 12 s, 24 s… on 429/5xx/network errors, and shows "unchecked" after 2 minutes. `pollDocument` still goes through `apiFetch`'s `withRetry`, so a 5xx is retried 3× inside each check. The page reads only `status`, `failure_reason` and the area's type, never `error_message`. Files send one at a time; areas and the button are disabled only while a file is sending, not while rows are checking.
- **`uploadDocument` uses raw `fetch`** — `apiFetch` forces `Content-Type: application/json`, which breaks the multipart boundary. It handles its own 401 (one `attemptTokenRefresh()`, one retry) and throws `APIClientError` with the HTTP status; a 400 is how the server refuses a file type.
- **user-event hangs under vitest fake timers** — RTL's `asyncWrapper` drains every user-event action with a `setTimeout(0)` that only a `jest` global advances, so `userEvent.setup({ advanceTimers })` doesn't help. Under `vi.useFakeTimers()` use `fireEvent` + `act(() => vi.advanceTimersByTimeAsync(ms))`, step the clock in ≤1 s increments when each timer's reply schedules the next one, and switch back to real timers before any `userEvent` action, `findBy` or `waitFor`.

## Architecture (quick)

- **Backend:** Django 5.0 + DRF, Python 3.11, PostgreSQL 15, `encrypted-model-fields` (Fernet PII encryption)
- **Frontend:** React 19 + Vite 7 + TypeScript, Context API (not Redux), react-router-dom v7
- **PDF:** pypdf fills official AO court templates. Each schema in `data/forms/schemas/` binds a field to a widget's full name in the field index (`data/forms/field_index/<template stem>.index.json`). `build_field_values(form_type, session)` checks the form's preconditions and resolves its schema; `PDFFormFiller().fill(form_type, values)` fills exactly those full names in the template from `data/forms/pdfs/` and raises `UnknownField` for any other name.
- **PDF templates:** 67 official AO court PDFs in `data/forms/pdfs/` (committed). Baked into Heroku image.
- **Forms:** 17 form types in `apps/forms/registry.py` (`FORM_REGISTRY` / `get_all_form_types()` / `packet(session)`). `generate_all` gives each form its own savepoint.
- **OCR service:** provider-agnostic. `OCR_PROVIDER` selects `openai` (default, `gpt-4o`, `OPENAI_API_KEY`) or `gemini` (`gemini-2.0-flash`, `GEMINI_API_KEY`); `OCR_MODEL` overrides the model so a model change is a config var, not a deploy. No local model — both call a hosted API directly.
- **Auth:** JWT (simplejwt). Access in memory, refresh in localStorage. `GET /api/token/obtain/` + `/api/token/refresh/`.
- **E2E:** 5 AI persona briefs in `docs/testing/persona-briefs/` (deshawn, james, maria, priya, sarah) driving 7 journey specs — one per persona plus `sofa-journey.spec.ts` and `scanned-bill-journey.spec.ts` (an upload read through a fake OpenAI server). `seed_demo_data` creates synthetic sessions with all intake data.

## File Map (what lives where)

**Backend apps:**

- `apps/intake/models.py` — IntakeSession, DebtorInfo, IncomeInfo, ExpenseInfo, AssetInfo, DebtInfo, FeeWaiverApplication
- `apps/intake/fields.py` — Custom `EncryptedDecimalField`
- `apps/intake/views.py` — IntakeSessionViewSet, AssetViewSet, DebtViewSet
- `apps/intake/serializers.py` — nested serializers; DRF silently drops unknown fields (mismatch with frontend)
- `apps/intake/management/commands/seed_demo_data.py` — 5 AI personas
- `apps/eligibility/services/means_test_calculator.py` — § 707(b) logic, annualizes CMI
- `apps/forms/registry.py` — `FORM_REGISTRY` (17 form_type → `PacketForm(applies, requires)`) in filing order, `packet()`, `build_field_values()`
- `apps/forms/services/` — `pdf_filler.py` (`PDFFormFiller`, exact full names), `fill_resolver.py` + `derivations.py` (schema-driven fill engine)
- `apps/forms/field_index.py` + `apps/forms/checks.py` — the field index loader and the schema system check
- `apps/forms/views.py` — GeneratedFormViewSet (generate, generate_all, download, mark_filed)
- `apps/documents/services/providers/` — `base.py` (`BaseOCRProvider`), `openai_provider.py`, `gemini.py`, `prompts/`
- `apps/documents/services/` — `processor.py` (DocumentProcessor), `draft_debt.py`, `aggregator.py` (AggregateIngestionService)
- `apps/audit/models.py` — AuditLog
- `config/settings/test.py` — sqlite `:memory:`, fast hashers
- `config/settings/base.py` — DRF config, OCR provider vars, `auth: 30/minute` throttle
- `config/settings/production.py` — anon/user throttle classes, Sentry DSN (see gotcha above)

**Frontend:**

- `src/App.tsx` — Routes, ErrorBoundary, IntakeLayout (shared provider via Outlet)
- `src/context/AuthContext.tsx` — JWT auth, silent refresh
- `src/context/IntakeContext.tsx` — Session state
- `src/api/client.ts` — typed API client, `getAccessToken()`, `downloadForm()`
- `src/pages/IntakeWizard.tsx` — 8-step wizard orchestrator (`WIZARD_STEPS`: debtor_info, income_info, expense_info, assets, debts, contracts, codebtors, review); detours to `/documents` after step 1
- `src/pages/DocumentUploadPage.tsx` — upload + OCR queue; auto-creates a session if none exists
- `src/pages/FormDashboard.tsx` — Generate All, download, mark filed
- `src/pages/SOFAStep.tsx` (`/sofa`), `FeeWaiverPage.tsx` (`/fee-waiver`) — post-intake branches; `handleComplete` routes to one or the other on `qualifies_for_fee_waiver`
- `src/pages/AskModulePage.tsx` — `/ask/:formType`
- `src/pages/LandingPage.tsx`, `LoginPage.tsx`, `RegisterPage.tsx`, `TermsPage.tsx` — public routes; all three auth entry points send authenticated users to `/intake`
- `src/components/compliance/UPLConfirmationModal.tsx` — gates form generation
- `src/types/api.ts` — TypeScript interfaces matching DRF serializers
- `src/test/setup.ts` — vitest globals, MSW, vitest-axe matchers
- `e2e/journeys/` — 7 Playwright journey specs (5 personas + SOFA + scanned bill)
- `e2e/fixtures/fake-openai.ts` — fake OpenAI Chat Completions server (`startFakeOpenAI`, `CANNED_BILL`) for `scanned-bill-journey`
- `e2e/playwright.config.ts` — Chromium only, 60s timeout, `reuseExistingServer`

**Data:**

- `data/forms/pdfs/` — 67 official AO court PDF templates (committed)
- `backend/apps/districts/fixtures/ilnd_2025_data.json` — ILND median income & exemptions

**Infra:**

- `docker-compose.yml` — 3 services: db (postgres:15), backend, frontend
- `Dockerfile.heroku` — multi-stage (Node → Python), bakes PDF templates + static assets
- `heroku.yml` — release phase runs migrations (single command string)
- `.github/workflows/ci.yml` — lint → backend tests → frontend tests → E2E (sequential gates)

## Key Docs

- PRD: `/docs/internal/DigniFi_PRD_v0_3.md`
- UPL compliance: `docs/UPL_COMPLIANCE.md`
- Trauma-informed design: `docs/TRAUMA_INFORMED_DESIGN.md`
- Plain language guide: `docs/PLAIN_LANGUAGE_GUIDE.md`
