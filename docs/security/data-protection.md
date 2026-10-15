# Data Protection & Encryption

## PII Classification

### Highly Sensitive (Field-Level Encryption Required)

- Social Security Numbers (SSN)
- Income amounts and sources
- Debt amounts and creditor names
- Bank account numbers
- Asset values and descriptions
- Expense amounts

### Sensitive (Database-Level Encryption)

- Full names and aliases
- Addresses (current and previous)
- Phone numbers and email addresses
- Employer information
- Family member information

### Authentication Data

- Passwords (PBKDF2-SHA256 hashed via Django)
- Admin session IDs (database-backed, used by the Django admin and /metrics/; HttpOnly cookie, Secure in production)
- JWT tokens (short-lived, HttpOnly)

## Current Implementation

### Field-Level Encryption

**Technology:** Fernet symmetric encryption (AES-128-CBC + HMAC)

**Implementation:**

- `EncryptedCharField` and `EncryptedTextField` from `django-encrypted-model-fields`, plus a custom `EncryptedDecimalField` in `backend/apps/intake/fields.py`
- Encryption keys stored in environment variable `FIELD_ENCRYPTION_KEY`
- Never commit encryption keys to git

**Encrypted Models:**

- `DebtorInfo.ssn` - Social Security Number
- `AssetInfo.current_value`, `amount_owed`, `account_number` - Asset values and account numbers
- `DebtInfo.amount_owed`, `DebtInfo.account_number` - Debt details
- `FeeWaiverApplication` `monthly_income`, `monthly_expenses`, `monthly_take_home_pay` - Fee waiver amounts
- `SOFAPriorIncome.gross_amount`, `SOFACreditorPayment.total_paid` - Financial affairs amounts
- `MeansTest.calculation_details` - Means test working
- `GeneratedForm.field_values` - Resolved form values
- `OCRResult.extracted_data` - Fields read from uploaded documents

**Not encrypted (among others):** `IncomeInfo` and `ExpenseInfo` amounts, `MeansTest` amounts (`calculated_cmi`, `disposable_income` and the rest), `IngestedAggregate.value` (pay-stub gross pay), `DebtInfo.creditor_name` and `monthly_payment`, `SOFACreditorPayment.creditor_name`, `SOFAPriorIncome.source`, `AssetInfo.description`

### Database Security

**Production Configuration:**

- PostgreSQL 15 with TLS connections
- Role-based access control (RBAC)
- Database credentials in environment variables
- Encrypted backups (pg_dump piped to gpg or cloud storage encryption)

**Development Configuration:**

- Local PostgreSQL instance in Docker
- No production data in development environments
- Synthetic test data only

### Transport Security

**HTTPS Enforcement:**

- All production traffic over TLS 1.3
- HSTS headers to prevent downgrade attacks
- Certificate pinning for mobile apps (future)

**API Security:**

- CORS restrictions (whitelist only)
- No credentials in URL parameters
- JWT tokens in Authorization header (not query string)

## Data Retention Policy

### User Data

**Retention Period:** 22 days after case filing or abandonment

**Auto-Deletion Triggers:**

- User marks case as "filed"
- User explicitly deletes account
- Session abandoned for 22 days (no activity)

**What Gets Deleted:**

- All intake session data
- Generated PDF forms
- Encrypted PII fields
- Asset/debt/income/expense records

### Audit Logs

**Retention Period:** 7 years (compliance requirement)

**What's Logged:**

- Form generation events
- PII access (who accessed what, when)
- Authentication events (login, logout, failures)
- API requests to sensitive endpoints

**Log Redaction:**

- No PII values in logs (only masked/hashed identifiers)
- Request rows hold method, path, status code and IP; the frontend's analytics events add session id, form type, step timings and survey answers (some free text). None of these events has an SSN or dollar-amount field.

## Encryption Key Management

### Current (MVP)

**Single Symmetric Key:**

- Stored in `FIELD_ENCRYPTION_KEY` environment variable
- 32-byte Fernet key (base64-encoded)
- Same key for all encrypted fields

**Generation:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Storage:**

- Development: `.env` file (gitignored)
- Production: Environment variables or secret manager (AWS Secrets Manager, HashiCorp Vault)

### Planned Improvements

**Key Rotation (6 months post-launch):**

- Multi-key envelope encryption
- Rotate data encryption keys quarterly
- Keep old keys for decryption of historical data
- Re-encrypt on access (lazy rotation)

**Hardware Security Module (12 months post-launch):**

- AWS CloudHSM or Azure Key Vault
- FIPS 140-2 Level 3 compliance
- Key generation and storage in HSM
- Application never has direct key access

## Backup Security

### Current (MVP)

**Local Backups:**

- Docker volume backups (filesystem encryption relies on host OS)
- Manual pg_dump for database snapshots
- Not encrypted at rest (MVP limitation)

### Production Requirements

**Encrypted Backups:**

- S3-compatible storage with server-side encryption (AES-256)
- Separate encryption keys for backups
- Automated daily backups with 7-year retention (audit logs)
- 30-day retention for user data backups (then purge)

**Backup Testing:**

- Quarterly restore drills
- Verify data integrity after restore
- Document restore procedures (disaster recovery runbook)

## Data Minimization

### What We Don't Collect

**Never Stored:**

- Credit card numbers (PCI DSS compliance)
- Bank account passwords
- Biometric data
- Location tracking data
- Browsing history outside the app

**Why:** Data not collected cannot be breached. Only collect what's legally required for bankruptcy forms.

### User Rights

**Right to Access:**

- Users can download all their data (JSON export)
- API endpoint: none yet (no export action exists)

**Right to Deletion:**

- Users can delete their account and all data
- API endpoint: `DELETE /api/intake/sessions/{id}/`
- Audit logs preserved (compliance requirement)

**Right to Correction:**

- Users can edit all intake data before form generation
- Intake data stays editable after forms are generated; a form marked filed keeps the answers it was filed with

## Compliance

### GLBA (Gramm-Leach-Bliley Act)

**Applicability:** May apply as a financial services platform

**Requirements:**

- Safeguards Rule: Implement data security program (✓ Field encryption, audit logs)
- Privacy Rule: Privacy policy explaining data use (⚠️ only a short privacy section in the Terms)
- Pretexting Rule: Prevent identity theft (✓ Authentication required for all access)

### CCPA/CPRA (California Privacy Rights)

**Applicability:** Users in California

**Requirements:**

- Right to know what data is collected (⚠️ not yet: the Terms do not list it)
- Right to deletion (⚠️ session delete API only; no account deletion yet)
- Right to opt-out of data sales (N/A - we don't sell data)
- Privacy policy disclosure (⚠️ only a short privacy section in the Terms)

### State Breach Notification Laws

**All 50 states have breach notification laws**

**Typical Requirements:**

- Notify affected users within 30-90 days
- Notify state attorney general (if > 500 residents affected)
- Provide credit monitoring (if SSNs compromised)
- Document breach in incident report

**DigniFi Response Plan:** See `docs/security/compliance.md#breach-notification`

## File Storage Security

### Generated PDFs (Current MVP)

**Storage Location:** none. Each form's values are kept encrypted in `GeneratedForm.field_values`, and the PDF is filled on each download.

**Security Limitations:**

- No generated PDF is stored; the form values are encrypted at rest (field-level)
- Each download is recorded in the audit log
- Suitable for internal clinic network only

**Deletion:** Auto-deleted after 22 days along with user data

### Planned: S3-Compatible Storage

**Encryption:**

- Server-side encryption (SSE-S3 or SSE-KMS)
- Separate bucket encryption keys
- Encryption at rest and in transit

**Access Control:**

- Pre-signed URLs with 15-minute expiration
- IAM roles for application access (no API keys)
- Bucket policies restrict by IP range

**Audit Logging:**

- S3 access logs to separate bucket
- CloudTrail for API calls
- Alert on unusual access patterns

---

**Last Updated:** March 2026
