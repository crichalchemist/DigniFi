# Development Security

## Secure Coding Checklist

Before committing code, verify:

- [ ] No secrets in code (API keys, passwords, encryption keys)
- [ ] All user inputs validated
- [ ] SQL queries use ORM or parameterization
- [ ] Output encoding for all user-controlled data
- [ ] Authentication required on PII endpoints
- [ ] Authorization checks (users can only access their own data)
- [ ] Audit logging for sensitive actions
- [ ] Error messages don't reveal system internals
- [ ] Dependencies up to date with no known CVEs

## Environment Variables

### What Belongs in .env

**Always in environment (NEVER commit):**
- `SECRET_KEY` - Django secret key
- `FIELD_ENCRYPTION_KEY` - Fernet key for PII encryption
- `DATABASE_PASSWORD` - PostgreSQL password
- `JWT_SECRET` - JWT signing key (if separate from SECRET_KEY)
- `API_KEYS` - Third-party service keys (credit counseling, etc.)

**Example .env file:**
```bash
# Django
SECRET_KEY=<50-char-random-string>
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dignifi
DATABASE_PASSWORD=<strong-password>

# Encryption
FIELD_ENCRYPTION_KEY=<fernet-key>

# Email (production)
EMAIL_HOST_PASSWORD=<smtp-password>
```

### Generating Secrets

**SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**FIELD_ENCRYPTION_KEY:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Random Password:**
```bash
openssl rand -base64 32
```

### .env.example Template

**Commit .env.example (without real values):**
```bash
# Django
SECRET_KEY=changeme
DEBUG=True
ALLOWED_HOSTS=localhost

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dignifi

# Encryption
FIELD_ENCRYPTION_KEY=changeme
```

## Git Security

### Pre-Commit Checks

**Prevent Secrets in Commits:**

Install `detect-secrets`:
```bash
pip install detect-secrets
detect-secrets scan --baseline .secrets.baseline
```

**Pre-commit hook (.git/hooks/pre-commit):**
```bash
#!/bin/bash
detect-secrets-hook --baseline .secrets.baseline $(git diff --cached --name-only)
if [ $? -ne 0 ]; then
  echo "❌ Secrets detected! Aborting commit."
  exit 1
fi
```

### .gitignore

**Essential entries:**
```gitignore
# Environment variables
.env
.env.local
.env.*.local

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
env/

# Database
*.db
*.sqlite3

# Secrets
secrets/
*.pem
*.key
*.crt

# Generated files
/generated_forms/
/media/
```

### Checking Git History for Secrets

**Search for accidentally committed secrets:**
```bash
# Search all history for patterns
git log -p --all -S 'password' --source --name-only

# Check for specific file types
git log --all --full-history -- '**/.env*'

# Use automated tool
pip install truffleHog
truffleHog --regex --entropy=True .
```

**If secret found in history:**
1. Rotate the secret immediately (generate new value, update in production)
2. Use `git filter-repo` to remove from history (or BFG Repo-Cleaner)
3. Force push to remote (coordinate with team)
4. Notify team to re-clone repository

## Code Review Guidelines

### Security-Focused Review

**For All PRs:**
- Run test suite (backend + frontend + E2E)
- Check for hardcoded secrets
- Verify input validation
- Check authentication/authorization

**For PII-Handling PRs:**
- Confirm encrypted fields used for PII
- Verify audit logging added
- Check user isolation (can't access other users' data)
- Confirm error messages don't leak PII

**For Authentication/Auth PRs:**
- Verify permission_classes on new viewsets
- Check rate limiting configuration
- Confirm CSRF protection (if applicable)
- Test with unauthenticated requests

### Review Checklist Template

```markdown
## Security Review

- [ ] No secrets in code
- [ ] Input validation on all user inputs
- [ ] Output encoding where needed
- [ ] Authentication required
- [ ] Authorization enforced (user isolation)
- [ ] Audit logging added
- [ ] Error handling doesn't leak info
- [ ] Tests cover security cases
- [ ] Dependencies scanned (npm audit / safety check)
```

## Dependency Security

### Automated Scanning

**Python (Safety):**
```bash
pip install safety
safety check --full-report
```

**Node.js (npm audit):**
```bash
cd frontend
npm audit
npm audit fix  # Apply patches
```

**GitHub Dependabot:**
- Enabled by default on GitHub
- Automatic PRs for security updates
- Configure in `.github/dependabot.yml`

### Update Policy

**Security Patches:**
- Apply within 7 days of disclosure
- Test in staging before production
- Critical (P0) patches may require immediate deployment

**Minor Updates:**
- Review quarterly
- Check changelog for breaking changes
- Update in development first

**Major Updates:**
- Evaluate impact (breaking changes)
- Test thoroughly in staging
- Plan migration (may require code changes)

### Known Vulnerabilities

**Check before merge:**
```bash
# Backend
safety check
bandit -r backend/

# Frontend
npm audit
npm outdated
```

**Allow exceptions (document why):**
```yaml
# .safety-policy.yml
security:
  ignore-vulnerabilities:
    # Vulnerability in dev-only dependency
    - 12345: "Used only in tests, not in production"
```

## Testing Security

### Security Test Cases

**Authentication:**
```python
def test_unauthenticated_access_denied(api_client):
    response = api_client.get('/api/intake/sessions/')
    assert response.status_code == 401
```

**Authorization:**
```python
def test_user_cannot_access_other_user_data(authenticated_client, other_user_session):
    response = authenticated_client.get(f'/api/intake/sessions/{other_user_session.id}/')
    assert response.status_code == 404  # Or 403
```

**Input Validation:**
```python
def test_invalid_ssn_rejected(authenticated_client):
    response = authenticated_client.post('/api/intake/debtor-info/', {
        'ssn': 'invalid-format'
    })
    assert response.status_code == 400
    assert 'ssn' in response.json()
```

**SQL Injection (Django ORM protects, but test anyway):**
```python
def test_special_chars_in_search(authenticated_client):
    # Should not cause error or return unexpected results
    response = authenticated_client.get('/api/creditors/?q=test\' OR 1=1--')
    assert response.status_code == 200
```

### Negative Testing

**Test what SHOULDN'T work:**
- Unauthenticated access to protected endpoints
- Users accessing other users' data
- Invalid input formats
- Expired tokens
- Excessive requests (rate limiting)

## Local Development Security

### Docker Security

**Don't run as root:**
```dockerfile
# Create non-root user
RUN useradd -m -u 1000 app
USER app
```

**Limit container permissions:**
```yaml
# docker-compose.yml
services:
  backend:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

### Database Security

**Development Database:**
- Use different credentials than production
- No production data in development
- Synthetic test data only

**PostgreSQL Configuration:**
```sql
-- Create limited user for app
CREATE USER dignifi_app WITH PASSWORD 'dev_password';
GRANT CONNECT ON DATABASE dignifi TO dignifi_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dignifi_app;
```

## Security Tools

### Recommended Tools

**Python:**
- `bandit` - Find common security issues in Python code
- `safety` - Check dependencies for known vulnerabilities
- `detect-secrets` - Prevent secrets in git commits

**JavaScript:**
- `npm audit` - Check dependencies
- `eslint-plugin-security` - ESLint security rules
- `retire.js` - Find vulnerable JS libraries

**General:**
- `git-secrets` - Prevent secrets in git
- `truffleHog` - Find secrets in git history
- `OWASP ZAP` - Web application security scanner (manual)

### CI/CD Integration

**GitHub Actions (.github/workflows/security.yml):**
```yaml
name: Security Scan

on: [push, pull_request]

jobs:
  python-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Safety
        run: |
          pip install safety
          safety check --json
      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r backend/ -f json -o bandit-report.json

  javascript-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: Run npm audit
        run: cd frontend && npm audit --audit-level=moderate
```

---

**Last Updated:** March 2026
