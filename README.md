# DigniFi - Trauma-Informed Bankruptcy Filing Platform

**Mission**: Democratize access to bankruptcy relief for low-income, pro se Americans by translating complex legal processes into plain-language guidance and auto-populated court forms.

**CRITICAL**: This platform provides legal **INFORMATION**, never legal **ADVICE**. All development must respect UPL (Unauthorized Practice of Law) boundaries.

## Project Status

**MVP Complete** — Full-stack application validated through AI persona testing (Mar 2026)

**Pilot District**: Northern District of Illinois (ILND)
**MVP Scope**: Chapter 7 bankruptcy filing assistance
**Next Milestone**: Paper prototype testing with target demographic

### Test Results (Mar 2026)

| Suite             | Count        | Status          |
| ----------------- | ------------ | --------------- |
| Backend (pytest)  | 413          | Passing         |
| Frontend (vitest) | 165          | Passing         |
| E2E persona tests | 5/5 personas | All steps green |

## Quick Start

### Prerequisites

- Docker & Docker Compose (or Colima on macOS)
- Python 3.11+ (for local development without Docker)
- Node.js 18+ (for local development without Docker)

### Running with Docker (Recommended)

```bash
# 1. Copy environment file
cp backend/.env.example backend/.env

# 2. Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add the output to FIELD_ENCRYPTION_KEY in backend/.env

# 3. Start services
docker compose up -d

# 4. Run migrations
docker compose exec backend python manage.py migrate

# 5. Load ILND district data
docker compose exec backend python manage.py loaddata ilnd_2025_data

# 6. Seed demo personas (optional — for testing)
docker compose exec backend python manage.py seed_demo_data

# 7. Access the application
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000/api
# - Admin: http://localhost:8000/admin
```

### Verify Everything Works

```bash
# Backend tests
docker compose exec backend pytest -q

# Frontend tests
cd frontend && npx vitest run

# Quick persona smoke test (requires Playwright)
python3 test_maria_quick.py
```

### Code Quality Setup (Recommended)

Set up automatic linting and formatting before every commit:

```bash
# One-time setup
./scripts/setup-linting.sh

# Or manually:
pip install pre-commit
pre-commit install
```

This installs pre-commit hooks that automatically:

- Format code with Prettier (frontend) and Black (backend)
- Lint with ESLint (frontend) and Ruff (backend)
- Fix trailing whitespace and other issues

See [docs/LINTING_SETUP.md](docs/LINTING_SETUP.md) for details.

### Local Development (Without Docker)

**Backend:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/development.txt
cp .env.example .env
# Edit .env with your local database settings
python manage.py migrate
python manage.py runserver
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```text
dignifi/
├── backend/                 # Django REST API
│   ├── apps/
│   │   ├── users/          # Authentication & profiles
│   │   ├── audit/          # UPL compliance + analytics logging
│   │   ├── districts/      # District-specific rules & data
│   │   ├── intake/         # Data collection (6-step wizard)
│   │   ├── eligibility/    # Means test calculator
│   │   └── forms/          # 13 bankruptcy form generators
│   ├── config/             # Django settings (base, dev, prod)
│   └── requirements/       # Python dependencies
├── frontend/               # React 19 + TypeScript SPA
│   ├── src/
│   │   ├── components/     # UI components (wizard, forms, compliance, survey)
│   │   ├── pages/          # IntakeWizard, FormDashboard, Login, Register
│   │   ├── context/        # AuthContext, IntakeContext
│   │   ├── api/            # Typed API client
│   │   └── utils/          # Analytics, helpers
│   └── e2e/                # Playwright page objects & journey specs
├── docs/                   # Reference documentation
│   ├── testing/            # Persona briefs & orchestration protocol
│   ├── reports/            # Usability test reports
│   └── plans/              # Design documents
├── Product Docs/           # PRD, briefs, architecture analysis
├── test_persona_full_flow.py  # 5-persona E2E test script
└── test_maria_quick.py        # Quick smoke test
```

## Technology Stack

- **Backend**: Python 3.11, Django 5.0, Django REST Framework, PostgreSQL 15
- **Frontend**: React 19, Vite 7, TypeScript (Context API for state management)
- **PDF Generation**: PyPDF2 (13 form generators)
- **Authentication**: JWT (djangorestframework-simplejwt) with silent refresh
- **Encryption**: django-encrypted-model-fields (Fernet) for PII
- **Testing**: pytest, vitest, Playwright, vitest-axe (accessibility)
- **CI/CD**: GitHub Actions (lint, backend tests, frontend tests, E2E)
- **Infrastructure**: Docker, Docker Compose

## Core Features

- User authentication with JWT (access in memory, refresh in localStorage)
- 6-step intake wizard: Debtor Info → Income → Expenses → Assets → Debts → Review
- Chapter 7 means test calculator (11 U.S.C. § 707(b))
- Fee waiver eligibility assessment (28 U.S.C. § 1930(f))
- 13 bankruptcy form generators (Form 101 through Schedules A/B–J)
- UPL confirmation modal gates all form generation
- Post-task usability survey (3 Likert + 2 open text)
- Fire-and-forget analytics via AuditLog API
- WCAG 2.1 AA accessibility (ARIA labels, keyboard nav, skip links)
- Trauma-informed language throughout ("amounts owed" not "debt")

## Development Guidelines

### UPL Compliance (CRITICAL)

**Never use these phrases:**

- "You should file Chapter 7"
- "I recommend..."
- "Based on your situation, file X"

**Always use information-only language:**

- "You may be eligible for Chapter 7 if..."
- "Chapter 7 typically requires..."
- "This information is not legal advice"

See `docs/UPL_COMPLIANCE.md` for complete guidelines.

### Plain Language

- Target 6th-8th grade reading level (Flesch-Kincaid)
- Define legal terms on first use
- Use trauma-informed language (see `docs/TRAUMA_INFORMED_DESIGN.md`)

### Data Security

- **Encrypt all PII** (SSN, income data, creditor information)
- Never log PII in error messages
- Use HTTPS in production
- JWT access tokens expire after 30 minutes
- Synthetic SSNs for testing use IRS-reserved 900-xx range

## Testing

```bash
# Backend (413 tests)
docker compose exec backend pytest -q

# Frontend (165 tests)
cd frontend && npx vitest run

# Full persona E2E (5 personas × full flow)
python3 test_persona_full_flow.py

# Quick smoke test (Maria only)
python3 test_maria_quick.py
```

## API Documentation

Key endpoints:

| Method | Path                                              | Description                             |
| ------ | ------------------------------------------------- | --------------------------------------- |
| POST   | `/api/token/obtain/`                              | JWT login                               |
| POST   | `/api/token/refresh/`                             | Refresh access token                    |
| POST   | `/api/intake/sessions/`                           | Create intake session                   |
| PATCH  | `/api/intake/sessions/{id}/`                      | Update session data (nested serializer) |
| POST   | `/api/intake/sessions/{id}/complete/`             | Finalize intake                         |
| POST   | `/api/intake/sessions/{id}/calculate_means_test/` | Run means test                          |
| POST   | `/api/forms/generate_all/`                        | Generate all 13 forms                   |
| GET    | `/api/forms/?session={id}`                        | List generated forms                    |

## Contributing

1. Review `docs/UPL_COMPLIANCE.md` — UPL boundaries are non-negotiable
2. Follow plain-language guidelines (`docs/PLAIN_LANGUAGE_GUIDE.md`)
3. Use trauma-informed design principles (`docs/TRAUMA_INFORMED_DESIGN.md`)
4. All PRs must pass CI (lint, backend tests, frontend tests)
5. Maintain 80%+ test coverage

## Deployment

**Production checklist:**

- [ ] Generate new `DJANGO_SECRET_KEY`
- [ ] Generate new `FIELD_ENCRYPTION_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure HTTPS/SSL
- [ ] Set up database backups
- [ ] Configure email service
- [ ] Review security settings in `config/settings/production.py`

## License

[To be determined - likely AGPL-3.0 or similar copyleft license]

## Contact

**Project Lead**: Courtney Richardson
**Organization**: DigniFi (Social Impact Startup)

---

**Legal Disclaimer**: This software provides legal information only and does not constitute legal advice. Users should consult a licensed attorney for legal advice specific to their situation.
