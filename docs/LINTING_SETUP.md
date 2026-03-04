# Code Quality & Formatting Setup

This document explains the automated linting and formatting workflow for DigniFi.

## Overview

We use **pre-commit hooks** to automatically lint and format code before every commit. This ensures:

- Consistent code style across the project
- Fewer merge conflicts
- Code quality checks run automatically
- No manual formatting needed

## Tools Used

### Frontend (JavaScript/TypeScript)

- **ESLint** - Linting (catches bugs and enforces coding standards)
- **Prettier** - Formatting (consistent code style)

### Backend (Python)

- **Ruff** - Fast linting (replaces flake8, isort, pyupgrade)
- **Black** - Formatting (opinionated code formatter)

### Both

- **Pre-commit hooks** - Runs checks automatically before each commit
- General file checks (trailing whitespace, end-of-file, merge conflicts)

## One-Time Setup

### 1. Install Pre-Commit (Python)

```bash
# If using Docker (recommended)
docker compose exec backend pip install pre-commit

# Or locally
pip install pre-commit
```

### 2. Install Git Hooks

```bash
# From project root
pre-commit install
```

This creates a `.git/hooks/pre-commit` file that runs automatically.

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
# Prettier is already in package.json
```

### 4. (Optional) Run on All Files

```bash
# From project root - formats all existing files
pre-commit run --all-files
```

This will show you any existing formatting issues.

## What Happens on Commit

When you run `git commit`, the following happens automatically:

1. **General Checks:**

   - Removes trailing whitespace
   - Fixes end-of-file newlines
   - Checks for merge conflicts
   - Validates JSON/YAML syntax
   - Prevents large files (>500KB)

2. **Python (Backend):**

   - **Ruff** lints and auto-fixes import sorting
   - **Black** formats code to consistent style

3. **JavaScript/TypeScript (Frontend):**

   - **Prettier** formats to consistent style
   - **ESLint** lints and auto-fixes issues

4. **Result:**
   - ✅ If all checks pass → commit proceeds
   - ❌ If checks fail → commit blocked, files auto-fixed
   - Re-stage fixed files and commit again

## Manual Commands

### Frontend

```bash
cd frontend

# Check formatting (no changes)
npm run format:check

# Auto-fix formatting
npm run format

# Lint (check for errors)
npm run lint

# Lint and auto-fix
npm run lint:fix
```

### Backend

```bash
cd backend

# Format with Black
black .

# Lint with Ruff
ruff check .

# Lint and auto-fix
ruff check --fix .
```

### Run Pre-Commit Manually

```bash
# Run on staged files only
pre-commit run

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
pre-commit run eslint --all-files
```

## Configuration Files

- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `.prettierrc.json` - Prettier formatting rules
- `.prettierignore` - Files to skip with Prettier
- `backend/pyproject.toml` - Black and Ruff configuration
- `frontend/eslint.config.js` - ESLint rules

## CI/CD Integration

Pre-commit hooks run locally, but we also run the same checks in CI:

```yaml
# .github/workflows/ci.yml
- name: Lint Frontend
  run: cd frontend && npm run lint

- name: Format Check Frontend
  run: cd frontend && npm run format:check

- name: Lint Backend
  run: cd backend && ruff check .

- name: Format Check Backend
  run: cd backend && black --check .
```

## Skipping Hooks (Emergency Only)

**Not recommended**, but if you need to bypass hooks:

```bash
# Skip pre-commit hooks (use with caution)
git commit --no-verify -m "Emergency fix"
```

Only use this for hotfixes or when hooks are broken. CI will still catch issues.

## Troubleshooting

### Hook Failed: "command not found"

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Reinstall hooks
pre-commit uninstall
pre-commit install
```

### Prettier: "No files matching pattern"

Make sure you're running from the correct directory:

```bash
cd frontend
npm run format
```

### Black/Ruff: "command not found"

Install development dependencies:

```bash
cd backend
pip install -r requirements/development.txt
```

### Hook Too Slow

Pre-commit caches dependencies. First run is slow, subsequent runs are fast.

To skip for a specific commit:

```bash
git commit --no-verify -m "message"
```

## Customizing Rules

### Prettier (Frontend Formatting)

Edit `.prettierrc.json`:

```json
{
  "semi": true,
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2
}
```

### Black (Backend Formatting)

Edit `backend/pyproject.toml`:

```toml
[tool.black]
line-length = 100
target-version = ['py311']
```

### Ruff (Backend Linting)

Edit `backend/pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["E", "W", "F", "I", "C", "B"]
ignore = ["E501"]  # line too long
```

### ESLint (Frontend Linting)

Edit `frontend/eslint.config.js` (already configured).

## Best Practices

1. **Commit Often:** Small commits with auto-formatting are easier than large reformats
2. **Let Tools Format:** Don't manually format - let Prettier/Black do it
3. **Review Changes:** Pre-commit may auto-fix things - review before pushing
4. **Keep Updated:** Run `pre-commit autoupdate` quarterly

## Resources

- [Pre-commit](https://pre-commit.com/)
- [Prettier](https://prettier.io/)
- [Black](https://black.readthedocs.io/)
- [Ruff](https://docs.astral.sh/ruff/)
- [ESLint](https://eslint.org/)

---

**Last Updated:** March 2026
