# AI Assistant Context

**DigniFi** — trauma-informed bankruptcy filing platform (Chapter 7, ILND pilot district). Django REST API + React 19 frontend. Deployed on Heroku. Provides legal _information_, never _advice_ (UPL boundaries are non-negotiable).

## Quick Commands

```bash
docker compose up                              # Start all 4 services (db, backend, frontend, odl-hybrid)
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
- **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data.
- **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
- **Form 103B needs a FeeWaiverApplication** — its generator raises without one. `generate_all` yields 17/18 forms for filers who don't qualify for the waiver. (103B is the only generator with a conditional precondition; Form 121's raises are about missing DebtorInfo / malformed SSN, which a complete intake always satisfies.)
- **SSN on forms** — Form 101's `Debtor1.SSNum` PDF field is 4 chars (last-4 only); full SSN appears on Form 121. pypdf truncates from the front.
- **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`.
- **Analytics auth** — `trackEvent()` must use `getAccessToken()` for Bearer header, not raw fetch.
- **heroku.yml release** — must be one command string (not argv list). `heroku releases:output` is empty; use `heroku logs --dyno release`.
- **CI ruff is pinned** — `ci.yml` installs `ruff==0.8.5`. Unpinned ruff broke CI when new rules shipped.
- **opendataloader-pdf needs a JRE** — both Dockerfiles install `default-jre-headless`. Without it, PDF upload errored (tests mock the module so CI can't catch it).
- **opendataloader-pdf healthcheck** — 60s start_period; backend `depends_on: odl-hybrid` condition `service_healthy`.
- **Pre-commit prettier** — reformats staged files on first commit; re-`git add` and commit again.
- **Colima volume mounts** — Colima only mounts `$HOME` by default; `/Volumes/Containers` must be added in `~/.colima/default/colima.yaml`.
- **Compose backend** — command must chain `python manage.py migrate && ...` before `runserver`.
- **Frontend tests use MSW** — network requests are intercepted in `src/test/setup.ts`. Write MSW handlers for new API calls.
- **E2E needs full stack** — Playwright tests (`frontend/e2e/journeys/`) require backend running, migrations applied, and `seed_demo_data` loaded.
- **Backend test settings** — `DJANGO_SETTINGS_MODULE=config.settings.test` uses sqlite `:memory:`, no postgres. E2E tests use `config.settings.development` (needs postgres).
- **FIELD_ENCRYPTION_KEY** — must be a real Fernet key (32 url-safe base64 bytes). CI uses `U9HKckkKBeT8wag2jMcOx2Cez2M2jtvNG4qxSHuYcAo=` (synthetic, encrypts nothing).
- **UPL compliance** — all user-facing text must be information, never advice. See `docs/UPL_COMPLIANCE.md`.
- **Nested `CLAUDE.md` files are empty stubs** — they are auto-generated `claude-mem` placeholders (~170 bytes each) reading `*No recent activity*`. This root file is the only real one; don't go looking for per-app conventions in them.
- **OCR provider is config-driven** — `_get_processor()` branches on `settings.OCR_PROVIDER` (`openai` | `gemini`) and lazy-imports the provider, so a missing SDK/key surfaces at OCR time, not app boot. `OCR_MODEL` empty ⇒ the provider's own default. Don't hardcode a provider.
- **`openai_provider.py`, never `openai.py`** — a module named `openai.py` inside `providers/` would shadow the installed `openai` package.
- **Prod throttling lives in `production.py`, not `base.py`** — base defines only the `auth` scope (`30/minute`); production adds `DEFAULT_THROTTLE_CLASSES` with `anon: 60/minute`, `user: 120/minute`, `auth: 5/minute`. Reading base alone wrongly concludes endpoints are unthrottled — polling ~14 documents exhausts `user` fast.
- **Document upload sits mid-wizard** — the flow is `login → /intake` step 1 → `/documents` → `/intake` steps 2–8, so uploads pre-fill the money steps. `IntakeWizard.handleNext` detours when `nextStep === 2`. Nothing currently links back to `/documents` after a skip. E2E journeys pass the detour with `DocumentsPage.skip()` (`e2e/pages/documents.page.ts`) after step 1.
- **`updateCurrentStep` is POST `/intake/sessions/{id}/update_step/`** — _not_ the PATCH that saves step data. Mocking the PATCH to assert step advancement silently captures the wrong call and passes vacuously.
- **Upload is synchronous despite the 202** — `views.py` uses `with ThreadPoolExecutor(...)`, whose `__exit__` calls `shutdown(wait=True)`, so `{"status": "processing"}` is returned _after_ OCR completes and holds a gunicorn worker. No `Future` is retained — that's the tell.
- **`hybrid="docling-fast"` can't work on Heroku** — it needs the `odl-hybrid` sidecar on `localhost:5002` from `docker-compose.yml`; Heroku runs a single container. It's caught and falls back to vision OCR, so the `Hybrid server is not available` log noise is not the failure.
- **Vision fallback reads page 1 only** — `_pdf_to_image_bytes(pdf_bytes, page_index=0)`; multi-page creditor bills extract partially even on success.
- **The wizard re-reads the session on every mount** — `IntakeWizard` fixes the session id at mount (context session, else `current_session_id`), calls `loadSession(id)`, and renders no step until it returns, so steps and autosave start from server data, not the context copy (which predates any upload on `/documents`). A failed read shows a "Try again" alert for the same id; a 404 starts a new session. `loadSession`/`createSession` resolve with the session, and `loadSession` clears `current_session_id` only on a 404, but the provider's own startup load still clears it on any error (DIG-11).

## Architecture (quick)

- **Backend:** Django 5.0 + DRF, Python 3.11, PostgreSQL 15, `encrypted-model-fields` (Fernet PII encryption)
- **Frontend:** React 19 + Vite 7 + TypeScript, Context API (not Redux), react-router-dom v7
- **PDF:** pypdf fills official AO court templates. Each generator in `backend/apps/forms/services/` implements `pdf_field_map() -> dict[str, str]` mapping session data to PDF field names. `PDFFormFiller.fill(form_type, field_map)` loads from `data/forms/pdfs/`.
- **PDF templates:** 67 official AO court PDFs in `data/forms/pdfs/` (committed). Baked into Heroku image.
- **Forms:** 18 generators registered in `apps/forms/registry.py` (`FORM_REGISTRY` / `get_all_form_types()`). `generate_all` iterates the registry inside one `transaction.atomic()`.
- **OCR service:** provider-agnostic. `OCR_PROVIDER` selects `openai` (default, `gpt-4o`, `OPENAI_API_KEY`) or `gemini` (`gemini-2.0-flash`, `GEMINI_API_KEY`); `OCR_MODEL` overrides the model so a model change is a config var, not a deploy. No local model — both call a hosted API directly.
- **Auth:** JWT (simplejwt). Access in memory, refresh in localStorage. `GET /api/token/obtain/` + `/api/token/refresh/`.
- **E2E:** 5 AI persona briefs in `docs/testing/persona-briefs/` (deshawn, james, maria, priya, sarah) driving 6 journey specs — one per persona plus `sofa-journey.spec.ts`. `seed_demo_data` creates synthetic sessions with all intake data.

## File Map (what lives where)

**Backend apps:**

- `apps/intake/models.py` — IntakeSession, DebtorInfo, IncomeInfo, ExpenseInfo, AssetInfo, DebtInfo, FeeWaiverApplication
- `apps/intake/fields.py` — Custom `EncryptedDecimalField`
- `apps/intake/views.py` — IntakeSessionViewSet, AssetViewSet, DebtViewSet
- `apps/intake/serializers.py` — nested serializers; DRF silently drops unknown fields (mismatch with frontend)
- `apps/intake/management/commands/seed_demo_data.py` — 5 AI personas
- `apps/eligibility/services/means_test_calculator.py` — § 707(b) logic, annualizes CMI
- `apps/forms/registry.py` — `FORM_REGISTRY` (18 form_type → generator) + `get_all_form_types()` in filing order
- `apps/forms/services/` — 18 generators + `pdf_filler.py` (`FORM_TEMPLATES` + `PDFFormFiller`), `fill_resolver.py` + `derivations.py` (schema-driven fill engine)
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
- `e2e/journeys/` — 6 Playwright journey specs (5 personas + SOFA)
- `e2e/playwright.config.ts` — Chromium only, 60s timeout, `reuseExistingServer`

**Data:**

- `data/forms/pdfs/` — 67 official AO court PDF templates (committed)
- `backend/apps/districts/fixtures/ilnd_2025_data.json` — ILND median income & exemptions

**Infra:**

- `docker-compose.yml` — 4 services: db (postgres:15), backend, frontend, odl-hybrid (opendataloader-pdf)
- `Dockerfile.heroku` — multi-stage (Node → Python), bakes PDF templates + static assets
- `heroku.yml` — release phase runs migrations (single command string)
- `.github/workflows/ci.yml` — lint → backend tests → frontend tests → E2E (sequential gates)

## Key Docs

- PRD: `/docs/internal/DigniFi_PRD_v0_3.md`
- UPL compliance: `docs/UPL_COMPLIANCE.md`
- Trauma-informed design: `docs/TRAUMA_INFORMED_DESIGN.md`
- Plain language guide: `docs/PLAIN_LANGUAGE_GUIDE.md`
