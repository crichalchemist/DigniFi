# Contributing to DigniFi

Thank you for your interest in contributing to DigniFi! This project aims to democratize access to bankruptcy relief for low-income Americans, and your contributions help expand access to justice.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Critical: UPL Compliance](#critical-upl-compliance)
- [Trauma-Informed Language Standards](#trauma-informed-language-standards)
- [Development Workflow](#development-workflow)
- [Testing Requirements](#testing-requirements)
- [Code Review Criteria](#code-review-criteria)
- [Environment Setup](#environment-setup)
- [Getting Help](#getting-help)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Critical: UPL Compliance

**Unauthorized Practice of Law (UPL)** is our most important constraint. Crossing from legal *information* to legal *advice* creates legal liability and could shut down the project.

### What's Permitted ✅

- Explaining what the law says (general information)
- Providing process information ("Chapter 7 requires this form")
- Auto-populating forms with user-provided data
- Showing eligibility criteria from statute
- Linking to official court resources
- Explaining what different options mean

### What's NOT Permitted ❌

- Recommending specific legal actions ("You should file Chapter 7")
- Interpreting law for a user's specific situation
- Advising whether to file bankruptcy
- Predicting case outcomes
- Representing users in court proceedings
- Telling users what they "need" to do

### Language Patterns

**Safe:**
- "You may be eligible for Chapter 7 if..."
- "Chapter 7 typically requires..."
- "The means test compares your income to..."
- "Bankruptcy law defines dischargeable debt as..."

**Unsafe:**
- "You should file Chapter 7" → Advice
- "Based on your income, I recommend..." → Advice
- "You need to file immediately" → Advice
- "Your debt will be discharged" → Prediction

### Required Safeguards

All PRs that add or modify user-facing guidance MUST:

1. **Include UPL review comment** - Explain why the language is information, not advice
2. **Add disclaimer if needed** - High-risk features need prominent disclaimers
3. **Log user interactions** - Decision points must be audit-logged
4. **Reference statute** - Cite specific USC or court rules when describing law

## Trauma-Informed Language Standards

Our users face financial crisis, often with accompanying mental health challenges, domestic violence, or disability. Language matters.

### Dignity-Preserving Terminology

**Use:** Amounts owed, financial obligations
**Avoid:** Debt (when used judgmentally)

**Use:** Person experiencing bankruptcy, filer
**Avoid:** Debtor (when possible), bankrupt person

**Use:** Financial hardship, crisis
**Avoid:** Failure, irresponsibility

### Tone Guidelines

- **Never blame or shame** - System failures, not personal failures
- **Acknowledge difficulty** - "This is a complex process" not "This is easy"
- **Offer reassurance** - Normalize the bankruptcy process
- **Preserve agency** - "You can choose" not "You must"
- **Plain language** - 6th-8th grade reading level (Flesch-Kincaid score)

### Example Transformations

❌ "You failed to provide income information"
✅ "We still need your income information to continue"

❌ "Your debt is too high for Chapter 7"
✅ "Chapter 7 may not be available based on the means test"

❌ "Error: Invalid input"
✅ "This field needs a number between 0 and 999,999"

## Development Workflow

### Getting Started

1. **Fork the repository** - Work in your own fork
2. **Create a feature branch** - `git checkout -b feature/your-feature-name`
3. **Set up environment** - See [Environment Setup](#environment-setup)
4. **Make your changes** - Follow code style guidelines in [CLAUDE.md](CLAUDE.md)
5. **Write tests** - All new code needs tests (see [Testing Requirements](#testing-requirements))
6. **Commit with clear messages** - Use conventional commits format
7. **Push and create PR** - Fill out the PR template completely

### Branch Naming

- `feature/` - New functionality
- `fix/` - Bug fixes
- `docs/` - Documentation only
- `refactor/` - Code refactoring
- `test/` - Test additions or fixes
- `chore/` - Maintenance tasks

### Commit Message Format

Use conventional commits:

```
type(scope): subject

Body explaining what and why (not how)

Co-Authored-By: Your Name <your.email@example.com>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Example:**
```
feat(forms): add Schedule I form generator

Implements Official Form 122A-1 Schedule I (Current Monthly Income)
with field-level validation and encrypted data storage.

Includes UPL-compliant guidance explaining income categories.

Co-Authored-By: Jane Doe <jane@example.com>
```

## Testing Requirements

**All PRs must maintain 100% test pass rate.** Adding new features requires adding tests.

### Test Types

1. **Backend Unit Tests** (pytest)
   - Models, serializers, services, utilities
   - `just test-backend` or `docker compose exec backend pytest`

2. **Frontend Unit Tests** (vitest)
   - Components, hooks, utilities, context
   - `just test-frontend` or `cd frontend && npm run test`

3. **Integration Tests**
   - API endpoints, form generation, means test calculator
   - Included in pytest suite

4. **E2E Tests** (Playwright)
   - Full user journeys, persona-based scenarios
   - `python3 test_maria_quick.py` (quick smoke test)
   - `python3 test_persona_full_flow.py` (full 5-persona suite)

### Running Tests Locally

```bash
# All tests
just test

# Just backend
just test-backend

# Just frontend
just test-frontend

# E2E smoke test
just test-e2e

# Full persona suite
just test-personas
```

### Test Coverage

While we don't enforce coverage metrics, aim for:
- **Critical paths:** 100% (means test, form generation, UPL boundaries)
- **Business logic:** 90%+
- **UI components:** 80%+
- **Utilities:** 90%+

### Writing Good Tests

- **Test behavior, not implementation** - Focus on outcomes
- **Use descriptive test names** - `test_means_test_fails_when_cmi_exceeds_median`
- **Arrange-Act-Assert pattern** - Clear test structure
- **Test edge cases** - Zero, negative, null, extremely large values
- **Test error conditions** - How does it fail gracefully?

## Code Review Criteria

Reviewers will check:

### 1. UPL Compliance
- [ ] No legal advice in user-facing text
- [ ] Appropriate disclaimers on decision points
- [ ] Audit logging for guidance features
- [ ] Statutory citations where appropriate

### 2. Trauma-Informed Language
- [ ] Dignity-preserving terminology
- [ ] No blame/shame language
- [ ] Plain language (6th-8th grade level)
- [ ] Acknowledges user difficulty

### 3. Technical Quality
- [ ] Tests pass (backend + frontend + E2E)
- [ ] Code follows project style (see CLAUDE.md)
- [ ] No security vulnerabilities (PII handling, injection, XSS)
- [ ] Proper error handling
- [ ] Performance considerations

### 4. Accessibility
- [ ] WCAG 2.1 AA compliance (if UI changes)
- [ ] Screen reader tested
- [ ] Keyboard navigation works
- [ ] Sufficient color contrast
- [ ] ARIA labels on form fields

### 5. Documentation
- [ ] README updated if needed
- [ ] Inline comments for complex logic
- [ ] API changes documented
- [ ] Type hints present (Python)

## Environment Setup

### Docker (Recommended)

```bash
# Clone and setup
git clone https://github.com/yourusername/dignifi.git
cd dignifi
just setup

# Start development
just dev

# In another terminal, verify tests pass
just test
```

### Local Development (Without Docker)

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements/development.txt

# Create .env
cp .env.example .env
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add output to FIELD_ENCRYPTION_KEY in .env

# Run migrations
python manage.py migrate
python manage.py loaddata ilnd_2025_data

# Run server
python manage.py runserver
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Database:**
```bash
# Install PostgreSQL 15+
# macOS: brew install postgresql@15
# Ubuntu: apt-get install postgresql-15
# Windows: Download from postgresql.org

# Create database
createdb dignifi_db
```

See [README.md](README.md) for complete setup instructions.

## Getting Help

### Questions?

- **General questions:** Open a [Discussion](https://github.com/yourusername/dignifi/discussions)
- **Bug reports:** Open an [Issue](https://github.com/yourusername/dignifi/issues/new?template=bug_report.md)
- **UPL uncertainty:** Open a [UPL Concern Issue](https://github.com/yourusername/dignifi/issues/new?template=upl_concern.md)
- **Accessibility issues:** Open an [Accessibility Issue](https://github.com/yourusername/dignifi/issues/new?template=accessibility.md)

### Areas We Need Help With

- **District Support** - Implementing 93 more federal districts (we have ILND only)
- **Accessibility Improvements** - Testing with screen readers, improving keyboard nav
- **Plain Language Refinement** - Simplifying legal explanations
- **Translation/Localization** - Spanish translation (highest priority)
- **Chapter 13 Support** - Complex repayment plan calculators
- **Form Updates** - Monitoring and updating when courts revise official forms

### Recognition

Contributors will be acknowledged in:
- Repository README
- Release notes
- Annual project reports (if applicable)

Thank you for helping expand access to justice! 🙏
