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
- **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data.
- **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
- **Form 103B needs a FeeWaiverApplication** — its generator raises without one. `generate_all` yields 12/13 forms for filers who don't qualify for the waiver.
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

## Architecture (quick)

- **Backend:** Django 5.0 + DRF, Python 3.11, PostgreSQL 15, `encrypted-model-fields` (Fernet PII encryption)
- **Frontend:** React 19 + Vite 7 + TypeScript, Context API (not Redux), react-router-dom v7
- **PDF:** pypdf fills official AO court templates. Each generator in `backend/apps/forms/services/` implements `pdf_field_map() -> dict[str, str]` mapping session data to PDF field names. `PDFFormFiller.fill(form_type, field_map)` loads from `data/forms/pdfs/`.
- **PDF templates:** 64 official AO court PDFs in `data/forms/pdfs/` (committed). Baked into Heroku image.
- **OCR service:** Gemini 2.0 Flash via Google AI API (`GEMINI_API_KEY`). No local model — document processing calls the API directly.
- **Auth:** JWT (simplejwt). Access in memory, refresh in localStorage. `GET /api/token/obtain/` + `/api/token/refresh/`.
- **E2E:** 5 AI persona briefs in `docs/testing/persona-briefs/`. `seed_demo_data` creates synthetic sessions with all intake data.

## File Map (what lives where)

**Backend apps:**

- `apps/intake/models.py` — IntakeSession, DebtorInfo, IncomeInfo, ExpenseInfo, AssetInfo, DebtInfo, FeeWaiverApplication
- `apps/intake/fields.py` — Custom `EncryptedDecimalField`
- `apps/intake/views.py` — IntakeSessionViewSet, AssetViewSet, DebtViewSet
- `apps/intake/serializers.py` — nested serializers; DRF silently drops unknown fields (mismatch with frontend)
- `apps/intake/management/commands/seed_demo_data.py` — 5 AI personas
- `apps/eligibility/services/means_test_calculator.py` — § 707(b) logic, annualizes CMI
- `apps/forms/services/` — 13 generators + `pdf_filler.py` (`FORM_TEMPLATES` dict + `PDFFormFiller`)
- `apps/forms/views.py` — GeneratedFormViewSet (generate, generate_all, download, mark_filed)
- `apps/documents/` — OCR pipeline: LlamaCppProvider, DocumentProcessor, DraftDebtCreator
- `apps/audit/models.py` — AuditLog
- `config/settings/test.py` — sqlite `:memory:`, fast hashers
- `config/settings/base.py` — DRF config, throttle rates (`auth: 30/minute`)

**Frontend:**

- `src/App.tsx` — Routes, ErrorBoundary, IntakeLayout (shared provider via Outlet)
- `src/context/AuthContext.tsx` — JWT auth, silent refresh
- `src/context/IntakeContext.tsx` — Session state
- `src/api/client.ts` — typed API client, `getAccessToken()`, `downloadForm()`
- `src/pages/IntakeWizard.tsx` — 6-step wizard orchestrator
- `src/pages/FormDashboard.tsx` — Generate All, download, mark filed
- `src/components/compliance/UPLConfirmationModal.tsx` — gates form generation
- `src/types/api.ts` — TypeScript interfaces matching DRF serializers
- `src/test/setup.ts` — vitest globals, MSW, vitest-axe matchers
- `e2e/journeys/` — Playwright journey specs
- `e2e/playwright.config.ts` — Chromium only, 60s timeout, `reuseExistingServer`

**Data:**

- `data/forms/pdfs/` — 64 official AO court PDF templates (committed)
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
