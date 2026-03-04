# GitHub Presentation Cleanup Plan

**Date:** 2026-03-03
**Status:** Approved
**Goal:** Prepare DigniFi repository for open source release, portfolio showcase, and partnership outreach

## Context

DigniFi MVP is complete with 413 backend tests, 165 frontend tests, and validated AI persona testing. The repository needs comprehensive cleanup and documentation enhancement for public GitHub presentation targeting:
- Open source contributors
- Portfolio/resume showcase
- Legal clinic partnership discussions

## Current State Assessment

### Build Artifacts (476MB to clean)
- Duplicate virtual environments: `.venv` (293MB) + `venv` (183MB)
- Cache directories: `.pytest_cache` (20K), `.ruff_cache` (56K)
- Empty root `node_modules/` (4K symlink)
- `TODO.txt` at root (693B)
- `test-results/` with persona screenshots (340K) - **KEEP for portfolio evidence**

### Git Status
- 4 deleted `.claude/` files pending commit
- `test-results/` not in `.gitignore`
- No LICENSE file
- Missing community health files

### Documentation Gaps
- No CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md
- README lacks badges, screenshots, architecture overview
- No developer tooling (Makefile/justfile)

## Implementation Plan

### Phase 1: Immediate Cleanup (Files & Git)

**Remove Build Artifacts:**
```bash
rm -rf venv .venv .pytest_cache .ruff_cache
rm -rf node_modules  # Empty symlink at root
rm TODO.txt
```

**Update .gitignore:**
```gitignore
# Add to existing .gitignore
/test-results/
/TODO.txt
venv/
.venv/
```

**Git Housekeeping:**
```bash
git add .claude/COPILOT_INTEGRATION.md .claude/COPILOT_QUICKSTART.md .claude/MULTI_TIER_STRATEGY.md .claude/mcp.json.example
git commit -m "docs: remove obsolete Claude configuration files"
```

**Keep test-results/ committed** - Portfolio evidence of AI persona testing methodology

### Phase 2: Documentation & Legal

**2.1 Add LICENSE**

Choose license based on mission philosophy:
- **MIT** - Permissive, allows commercial legal clinic forks
- **AGPL-3.0** - Copyleft, ensures derivatives remain open (mission protection)
- **Apache 2.0** - Permissive + patent grant (contributor protection)

**Recommendation:** MIT for maximum accessibility to legal clinics

**2.2 Create CONTRIBUTING.md**

Required sections:
- **UPL Compliance Requirements** - All contributions must respect legal information vs. advice boundary
- **Trauma-Informed Language Standards** - Dignity-preserving terminology
- **Development Workflow** - Fork, branch, PR process
- **Testing Requirements** - All PRs must maintain 100% test pass rate
- **Code Review Criteria** - UPL review, accessibility, plain language
- **How to Run Tests** - Backend (pytest), Frontend (vitest), E2E (Playwright)
- **Environment Setup** - Docker (recommended) vs. local

**2.3 Create SECURITY.md**

Critical for bankruptcy platform handling PII:
- **Responsible Disclosure Policy** - Private reporting channel before public disclosure
- **PII Handling Guidelines** - Field-level encryption requirements, SSN protection
- **Security Contact** - Email or secure form
- **Supported Versions** - What's actively maintained
- **Known Security Considerations** - E.g., local deployment only (no cloud in MVP)

**2.4 Create CODE_OF_CONDUCT.md**

Use **Contributor Covenant 2.1** as base, customize for:
- Trauma-informed communication standards
- Zero tolerance for victim-blaming language
- Respectful discussion of vulnerable populations

**2.5 Product Docs Strategy**

Keep committed:
- `Dignifi Brief.pdf` (95KB) - Executive summary
- `Strategic Communication Plan.pdf` (134KB) - Go-to-market strategy
- `UI_UX_RESEARCH.md` - Design rationale

Reference in README: "See Product Docs/ for comprehensive requirements and research"

### Phase 3: README Enhancement

**3.1 Above-the-Fold Additions**

```markdown
# DigniFi - Trauma-Informed Bankruptcy Filing Platform

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Tests](https://img.shields.io/badge/tests-578%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11-blue)
![React](https://img.shields.io/badge/react-19-blue)

**Making bankruptcy accessible to all Americans through plain-language guidance and auto-generated court forms.**

![DigniFi Demo](test-results/demo_maria_final.png)
*AI persona testing validates full Chapter 7 filing workflow*
```

**3.2 New Sections**

Add between Mission and Quick Start:

**Features:**
```markdown
## ✨ Features

- **13 Auto-Generated Bankruptcy Forms** - All Chapter 7 Official Forms (101-128 + Schedules A/B–J)
- **Means Test Calculator** - 11 U.S.C. § 707(b) compliance with CMI and median income comparison
- **Fee Waiver Qualification** - Automatic 28 U.S.C. § 1930(f) eligibility determination
- **Trauma-Informed UX** - Dignity-preserving language, 6th-8th grade reading level
- **Field-Level Encryption** - PII protection (SSN, income, debts) using Fernet encryption
- **Accessibility First** - WCAG 2.1 AA compliant with screen reader optimization
- **6-Step Guided Wizard** - Debtor info → Income → Expenses → Assets → Debts → Review
- **UPL-Compliant Guardrails** - Legal information, never advice
```

**Architecture Overview:**
```markdown
## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌────────────┐
│   React 19  │ ───► │  Django 5.0  │ ───► │ PostgreSQL │
│   + Vite 7  │      │     + DRF    │      │     15     │
└─────────────┘      └──────────────┘      └────────────┘
   TypeScript           Python 3.11         Encrypted PII
   Context API          Service Layer       Field-Level
```

**Stack:**
- **Frontend:** React 19, TypeScript, Vite 7, Context API
- **Backend:** Django 5.0, Django REST Framework, Python 3.11
- **Database:** PostgreSQL 15 with encrypted-model-fields
- **Testing:** pytest (413), vitest (165), Playwright (E2E)
- **CI/CD:** GitHub Actions (lint, tests, E2E)
- **Deployment:** Docker Compose (local MVP)
```

**Screenshots Section:**
```markdown
## 📸 Screenshots

### Intake Wizard
![Debtor Info Step](docs/screenshots/wizard-debtor-info.png)
*Plain-language guidance at every step*

### Form Dashboard
![Generated Forms](docs/screenshots/form-dashboard.png)
*All 13 forms generated with single click after UPL confirmation*

### AI Persona Testing
![Persona Results](test-results/demo_james_final.png)
*5 AI personas validate complete filing workflow*
```

**Roadmap:**
```markdown
## 🛣️ Roadmap

**Current (Mar 2026):** MVP Complete - ILND pilot district ready

**Next Up:**
- [ ] Paper prototype testing with target demographic at legal clinic
- [ ] Legal clinic pilot partnership (6-month supervised filing program)
- [ ] Chapter 13 form generators
- [ ] Multi-district expansion (94 federal districts)
- [ ] Credit counseling provider API integration
- [ ] Mobile-responsive design (currently desktop-first)

See [Product Docs/DigniFi_PRD_v0_3.md](Product%20Docs/DigniFi_PRD_v0_3.md) for full product roadmap.
```

**Legal Disclaimer (Prominent):**
```markdown
## ⚖️ Legal Disclaimer

**IMPORTANT:** DigniFi provides legal **INFORMATION**, never legal **ADVICE**. This platform:

✅ Explains what bankruptcy law says (general information)
✅ Auto-populates court forms with your data
✅ Shows eligibility criteria based on federal statute

❌ Does NOT recommend specific legal actions
❌ Does NOT interpret law for your situation
❌ Does NOT provide legal representation

**Unauthorized Practice of Law (UPL) Compliance:** All features are designed to stay within legal information boundaries. See [CLAUDE.md](CLAUDE.md#compliance--legal-boundaries) for development guidelines.

**We strongly recommend consulting with a bankruptcy attorney or legal clinic before filing.**
```

**Contributing & Acknowledgments:**
```markdown
## 🤝 Contributing

We welcome contributions that expand access to justice! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- UPL compliance requirements
- Trauma-informed language standards
- Development workflow and testing requirements

**Special focus areas:**
- Additional district support (93 districts to go!)
- Accessibility improvements
- Plain-language content refinement
- Translation/localization

## 🙏 Acknowledgments

**Creator:** Courtney Richardson, Northwestern University Communication Studies

**Inspiration:**
- [Upsolve](https://upsolve.org) - Nonprofit bankruptcy filing platform serving 17,000+ users
- "Dignity Not Debt" movement
- Legal Services Corporation (LSC) technology innovation initiatives

**Research Foundation:**
- MITRE Opportunity Canvas methodology
- Trauma-informed design principles for vulnerable populations
- Plain Language Action and Information Network (PLAIN) guidelines
```

**3.3 Restructure for Navigation**

Add table of contents after badges:
```markdown
## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Screenshots](#-screenshots)
- [Quick Start](#quick-start)
  - [Docker (Recommended)](#running-with-docker-recommended)
  - [Local Development](#local-development-without-docker)
- [Testing](#testing)
- [Roadmap](#-roadmap)
- [Legal Disclaimer](#-legal-disclaimer)
- [Contributing](#-contributing)
- [License](#license)
- [Acknowledgments](#-acknowledgments)
```

Move "Project Status" to appear immediately after Features section.

### Phase 4: Developer Experience Tooling

**4.1 Create justfile**

```just
# DigniFi Development Commands

# Show available commands
default:
    @just --list

# Initial project setup (first-time only)
setup:
    @echo "🔧 Setting up DigniFi development environment..."
    cp backend/.env.example backend/.env || true
    @echo "\n⚠️  Generate encryption key and add to backend/.env:"
    @echo "python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    docker compose build
    docker compose up -d
    just migrate
    just loaddata
    @echo "\n✅ Setup complete! Run 'just dev' to start development."

# Start development environment
dev:
    docker compose up

# Start in detached mode
dev-daemon:
    docker compose up -d

# Stop all services
stop:
    docker compose down

# Restart services
restart:
    docker compose restart

# View logs
logs service="":
    @if [ "{{ service }}" = "" ]; then \
        docker compose logs -f; \
    else \
        docker compose logs -f {{ service }}; \
    fi

# Run database migrations
migrate:
    docker compose exec backend python manage.py migrate

# Load ILND district data
loaddata:
    docker compose exec backend python manage.py loaddata ilnd_2025_data

# Seed demo persona data
seed-demo:
    docker compose exec backend python manage.py seed_demo_data

# Create Django superuser
createsuperuser:
    docker compose exec backend python manage.py createsuperuser

# Run backend tests
test-backend:
    docker compose exec backend pytest -v

# Run frontend tests
test-frontend:
    cd frontend && npm run test

# Run all tests (backend + frontend)
test:
    @echo "🧪 Running backend tests..."
    docker compose exec backend pytest -q
    @echo "\n🧪 Running frontend tests..."
    cd frontend && npm run test -- --run

# Run E2E persona tests (requires Playwright)
test-e2e:
    @echo "🎭 Running AI persona E2E tests..."
    python3 test_maria_quick.py

# Run full persona test suite
test-personas:
    @echo "🎭 Running full 5-persona test suite..."
    python3 test_persona_full_flow.py

# Run linters (backend + frontend)
lint:
    @echo "🔍 Linting backend..."
    docker compose exec backend ruff check .
    @echo "\n🔍 Linting frontend..."
    cd frontend && npm run lint

# Format code
format:
    @echo "✨ Formatting backend..."
    docker compose exec backend ruff format .
    @echo "\n✨ Formatting frontend..."
    cd frontend && npm run format

# Clean build artifacts
clean:
    @echo "🧹 Cleaning build artifacts..."
    rm -rf venv .venv
    rm -rf .pytest_cache .ruff_cache
    rm -rf backend/__pycache__ backend/**/__pycache__
    rm -rf frontend/node_modules/.vite
    rm -rf frontend/dist
    @echo "✅ Clean complete"

# Deep clean (includes Docker volumes)
clean-all: clean
    @echo "🧹 Deep cleaning (Docker volumes)..."
    docker compose down -v
    rm -rf backend/media/generated_forms/*
    @echo "✅ Deep clean complete"

# Shell into backend container
shell-backend:
    docker compose exec backend python manage.py shell

# Shell into database
shell-db:
    docker compose exec db psql -U dignifi -d dignifi_db

# Generate new encryption key
generate-key:
    @python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Health check
health:
    @echo "🏥 Checking service health..."
    @curl -sf http://localhost:8000/api/health/ > /dev/null && echo "✅ Backend: OK" || echo "❌ Backend: DOWN"
    @curl -sf http://localhost:5173 > /dev/null && echo "✅ Frontend: OK" || echo "❌ Frontend: DOWN"

# Show environment info
info:
    @echo "📊 DigniFi Environment Info"
    @echo "=========================="
    @echo "Backend: http://localhost:8000/api"
    @echo "Frontend: http://localhost:5173"
    @echo "Admin: http://localhost:8000/admin"
    @echo "\nDocker containers:"
    @docker compose ps
```

**4.2 Verify .editorconfig**

Check existing `.editorconfig` covers:
- Python (4 spaces, LF, UTF-8)
- JavaScript/TypeScript (2 spaces, LF, UTF-8)
- Markdown, YAML, JSON
- Trim trailing whitespace
- Insert final newline

**4.3 Docker Compose Improvements**

Add to `docker-compose.yml`:

```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    volumes:
      - backend_media:/app/media  # Named volume instead of anonymous
    profiles: ["dev", "prod"]

  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dignifi"]
      interval: 10s
      timeout: 5s
      retries: 5
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Named volume

volumes:
  backend_media:
  postgres_data:
```

**4.4 Environment Variable Documentation**

Enhance `backend/.env.example`:

```env
# DigniFi Environment Configuration
# Copy to .env and fill in required values

# ============================================
# REQUIRED: Generate with justfile command:
#   just generate-key
# ============================================
FIELD_ENCRYPTION_KEY=

# Django Settings
DEBUG=True
SECRET_KEY=your-dev-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (Docker defaults)
DB_NAME=dignifi_db
DB_USER=dignifi
DB_PASSWORD=dignifi_dev_password
DB_HOST=db
DB_PORT=5432

# CORS (Frontend URLs)
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Rate Limiting (requests per minute)
THROTTLE_RATE_ANON=100/minute
THROTTLE_RATE_AUTH=30/minute

# Logging
LOG_LEVEL=INFO

# Optional: Sentry DSN for error tracking
# SENTRY_DSN=
```

Add validation script `scripts/check_env.sh`:

```bash
#!/bin/bash
# Check required environment variables

if [ ! -f backend/.env ]; then
    echo "❌ backend/.env not found! Run 'just setup' first."
    exit 1
fi

source backend/.env

if [ -z "$FIELD_ENCRYPTION_KEY" ]; then
    echo "❌ FIELD_ENCRYPTION_KEY not set in backend/.env"
    echo "   Run: just generate-key"
    exit 1
fi

if [ -z "$SECRET_KEY" ]; then
    echo "⚠️  WARNING: SECRET_KEY using default (insecure for production)"
fi

echo "✅ Environment configuration valid"
```

### Phase 5: Final Polish & Verification

**5.1 Repository Hygiene**

```bash
# Search for potential secrets in git history
git log -p | grep -E "(password|secret|api_key)" --color

# Check for TODO/FIXME comments that should be issues
rg "TODO|FIXME|XXX|HACK" --glob "!docs/**" --glob "!*.md"

# Verify no hardcoded URLs
rg "localhost|127.0.0.1" --glob "!*.md" --glob "!.env.example" --glob "!justfile"
```

**5.2 Asset Optimization**

```bash
# Compress persona screenshots if needed (>100KB each)
for img in test-results/*.png; do
    size=$(stat -f%z "$img")
    if [ $size -gt 102400 ]; then
        echo "Consider compressing: $img ($size bytes)"
    fi
done
```

**5.3 Final Verification Checklist**

```markdown
## Pre-Release Checklist

- [ ] All tests pass
  - [ ] Backend: `just test-backend` (413 tests)
  - [ ] Frontend: `just test-frontend` (165 tests)
  - [ ] E2E: `python3 test_maria_quick.py`
- [ ] Documentation complete
  - [ ] LICENSE file added
  - [ ] CONTRIBUTING.md created
  - [ ] SECURITY.md created
  - [ ] CODE_OF_CONDUCT.md added
  - [ ] README enhanced with screenshots, badges, roadmap
- [ ] Developer experience
  - [ ] justfile commands work from clean clone
  - [ ] `just setup` succeeds for new developer
  - [ ] `just test` runs all test suites
  - [ ] `.env.example` has clear instructions
- [ ] Repository hygiene
  - [ ] No secrets in git history
  - [ ] All build artifacts in .gitignore
  - [ ] No personal notes in code
  - [ ] test-results/ screenshots committed
- [ ] Docker compose works
  - [ ] `docker compose up` from clean clone
  - [ ] Health checks pass
  - [ ] Migrations run successfully
  - [ ] Frontend accessible at :5173
  - [ ] Backend API at :8000/api
```

**5.4 GitHub Repository Configuration**

**Repository Settings:**
- **Description:** "Trauma-informed bankruptcy filing platform making Chapter 7 accessible through plain-language guidance and auto-generated court forms"
- **Website:** https://dignifi.app (if domain exists) or link to Product Docs
- **Topics:** `bankruptcy`, `legal-tech`, `django`, `react`, `social-impact`, `access-to-justice`, `trauma-informed-design`, `pro-se`, `chapter-7`

**Issue Templates:**

Create `.github/ISSUE_TEMPLATE/`:

1. `bug_report.md` - Standard bug template
2. `feature_request.md` - Feature proposal
3. `upl_concern.md` - UPL compliance issue (critical for legal boundary violations)
4. `accessibility.md` - WCAG/a11y issues

**Pull Request Template:**

Create `.github/pull_request_template.md`:
```markdown
## Description
<!-- What does this PR do? -->

## UPL Compliance Check
<!-- Does this change any user-facing guidance or recommendations? -->
- [ ] This PR does not provide legal advice
- [ ] All guidance stays within "legal information" boundaries
- [ ] User-facing text reviewed for UPL compliance

## Testing
- [ ] Backend tests pass (`just test-backend`)
- [ ] Frontend tests pass (`just test-frontend`)
- [ ] Manual testing completed

## Accessibility
- [ ] WCAG 2.1 AA compliant (if UI changes)
- [ ] Screen reader tested (if UI changes)
- [ ] Keyboard navigation works (if UI changes)

## Plain Language
- [ ] User-facing text is 6th-8th grade reading level
- [ ] Trauma-informed language standards followed
```

**Pin Important Discussions:**
- Pin issue: "📋 Roadmap: Chapter 13 Support" (when created)
- Pin issue: "🤝 Seeking Legal Clinic Partnership for Pilot" (when created)

## Success Criteria

Repository is ready for public presentation when:

1. ✅ Clean `git status` (no uncommitted artifacts)
2. ✅ New contributor can run `just setup` and have working environment
3. ✅ All tests pass on fresh clone
4. ✅ README answers: What is this? Why does it matter? How do I use it?
5. ✅ Legal disclaimers are prominent and unambiguous
6. ✅ Community health files present (LICENSE, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT)
7. ✅ Developer tooling (justfile) makes common tasks easy
8. ✅ GitHub repository configured with topics, issue templates, PR template
9. ✅ No secrets or PII in git history
10. ✅ Portfolio-worthy presentation (screenshots, badges, clear value prop)

## Post-Cleanup Actions

After merging this cleanup:

1. **Tag Release:** `git tag v0.1.0-mvp` (semantic versioning start)
2. **Create GitHub Release:** Include release notes summarizing MVP features
3. **Social Announcement:** Share on relevant communities (r/opensource, legal tech forums)
4. **Outreach:** Contact legal clinics with link to repository
5. **Documentation:** Write blog post about AI persona testing methodology (portfolio piece)

## References

- [GitHub Community Health Files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions)
- [choosealicense.com](https://choosealicense.com/) - License selector
- [Contributor Covenant](https://www.contributor-covenant.org/) - Code of Conduct template
- [just command runner](https://github.com/casey/just) - Alternative to Make
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/) - Accessibility reference
