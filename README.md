# DigniFi - Trauma-Informed Bankruptcy Filing Platform

**Mission**: Democratize access to bankruptcy relief for low-income, pro se Americans by translating complex legal processes into plain-language guidance and auto-populated court forms.

**⚠️ CRITICAL**: This platform provides legal **INFORMATION**, never legal **ADVICE**. All development must respect UPL (Unauthorized Practice of Law) boundaries.

## Project Status

🚧 **Pre-MVP Development** - Scaffolding complete, building core features

**Pilot District**: Northern District of Illinois (ILND)
**MVP Scope**: Chapter 7 bankruptcy filing assistance

## Quick Start

### Prerequisites

- Docker & Docker Compose
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
docker-compose up -d

# 4. Run migrations
docker-compose exec backend python manage.py migrate

# 5. Create superuser
docker-compose exec backend python manage.py createsuperuser

# 6. Access the application
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000/api
# - Admin: http://localhost:8000/admin
```

### Local Development (Without Docker)

**Backend:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
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
npm start
```


## Project Structure

```text
dignifi/
├── backend/                 # Django REST API
│   ├── apps/               # Django applications
│   │   ├── users/          # Authentication & profiles
│   │   ├── audit/          # UPL compliance logging
│   │   ├── districts/      # District-specific rules
│   │   ├── intake/         # Data collection
│   │   ├── eligibility/    # Means test calculator
│   │   ├── forms/          # Bankruptcy form generation
│   │   └── ...
│   ├── config/             # Django settings
│   └── requirements/       # Python dependencies
├── frontend/               # React TypeScript SPA
│   └── src/
│       ├── components/     # React components
│       ├── pages/          # Page components
│       └── services/       # API client
├── data/                   # District data & forms
│   ├── districts/ilnd/     # Illinois Northern District
│   ├── forms/pdfs/         # Official bankruptcy forms
│   └── content/            # Plain-language explainers
└── docs/                   # Documentation
```

## Technology Stack

- **Backend**: Django 5.0, Django REST Framework, PostgreSQL
- **Frontend**: React 18, TypeScript, Redux Toolkit
- **PDF Generation**: PyPDF2
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Encryption**: django-encrypted-model-fields (for PII)
- **Infrastructure**: Docker, Docker Compose

## Core Features (MVP)

- ✅ User authentication & profiles
- ✅ Multi-step intake flow
- ✅ Chapter 7 means test calculator (11 U.S.C. § 707(b))
- ✅ Fee waiver eligibility (28 U.S.C. § 1930(f))
- ✅ Form 101 PDF generation
- ✅ Illinois ILND district configuration
- ✅ UPL compliance audit logging
- ✅ Plain-language content system

## Development Guidelines

### UPL Compliance (CRITICAL)

**Never use these phrases:**
- ❌ "You should file Chapter 7"
- ❌ "I recommend..."
- ❌ "Based on your situation, file X"

**Always use information-only language:**
- ✅ "You may be eligible for Chapter 7 if..."
- ✅ "Chapter 7 typically requires..."
- ✅ "This information is not legal advice"

See `docs/UPL_COMPLIANCE.md` for complete guidelines.

### Plain Language

- Target 6th-8th grade reading level (Flesch-Kincaid)
- Define legal terms on first use
- Use trauma-informed language (see `docs/TRAUMA_INFORMED_DESIGN.md`)

### Data Security

- **Encrypt all PII** (SSN, income data, creditor information)
- Never log PII in error messages
- Use HTTPS in production
- JWT tokens expire after 30 minutes

## Testing

**Backend:**

```bash
docker-compose exec backend pytest
# With coverage
docker-compose exec backend pytest --cov=apps
```

**Frontend:**

```bash
cd frontend
npm test
```


## API Documentation

API documentation is auto-generated and available at:
- **Swagger UI**: [Swagger UI](http://localhost:8000/api/schema/swagger-ui/)
- **ReDoc**: [ReDoc](http://localhost:8000/api/schema/redoc/)

See `docs/API.md` for detailed endpoint documentation.

## Contributing

1. Review `docs/UPL_COMPLIANCE.md` - UPL boundaries are non-negotiable
2. Follow plain-language guidelines (`docs/PLAIN_LANGUAGE_GUIDE.md`)
3. Use trauma-informed design principles (`docs/TRAUMA_INFORMED_DESIGN.md`)
4. All PRs must pass linting (black, ruff, ESLint, Prettier)
5. Maintain 80%+ test coverage

## Token Optimization Strategy

This project uses a multi-tier AI model strategy to optimize development costs:

- **Tier 1 (Free)**: GPT-4.1/Gemini for boilerplate code
- **Tier 2 (Relaxed)**: Claude Sonnet for creative/complex tasks
- **Tier 3 (Premium)**: Claude Code for UPL-critical decisions

See `.claude/MULTI_TIER_STRATEGY.md` for details.

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

**⚠️ Legal Disclaimer**: This software provides legal information only and does not constitute legal advice. Users should consult a licensed attorney for legal advice specific to their situation.
