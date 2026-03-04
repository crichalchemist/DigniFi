# Security Policy

## Overview

DigniFi handles sensitive Personally Identifiable Information (PII) for individuals in financial crisis. Security is mission-critical. This document outlines our security practices, how to report vulnerabilities, and guidelines for contributors.

## Supported Versions

| Version | Supported          | Notes |
| ------- | ------------------ | ----- |
| 1.x.x   | :white_check_mark: | Current MVP release |
| < 1.0   | :x:                | Development/testing only |

## Reporting a Vulnerability

**DO NOT** open public GitHub issues for security vulnerabilities.

### Private Disclosure Process

1. **Email:** security@dignifi.org (or create GitHub private security advisory)
2. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact (who is affected, what data is at risk)
   - Affected versions
   - Suggested fix (if you have one)
   - Your contact information for follow-up

**What to Expect:**
- **Acknowledgment:** Within 48 hours
- **Initial Assessment:** Within 5 business days
- **Status Updates:** Every 7 days until resolved
- **Fix Timeline:** Critical vulnerabilities within 30 days, others within 90 days
- **Public Disclosure:** After fix is deployed, or 90 days (whichever comes first)

### Disclosure Policy

- We follow coordinated disclosure (90-day embargo)
- We will credit researchers who report responsibly
- We may offer bounties once funded (currently bootstrapped)

### Severity Levels

**Critical (P0) - Immediate Response Required:**
- Unauthorized access to user PII
- Authentication bypass
- Remote code execution
- SQL injection or command injection
- Mass data exfiltration

**High (P1) - Fix Within 7 Days:**
- XSS vulnerabilities affecting PII
- Privilege escalation
- Insecure cryptographic storage
- Session fixation

**Medium (P2) - Fix Within 30 Days:**
- CSRF on sensitive endpoints
- Information disclosure (non-PII)
- Insecure dependencies with known exploits
- Denial of service vectors

**Low (P3) - Fix Within 90 Days:**
- Security headers missing
- Information leakage in errors
- Weak password policies
- Clickjacking vulnerabilities

## Security Documentation

Detailed security guidance is organized by topic:

- **[Data Protection & Encryption](docs/security/data-protection.md)** - PII handling, encryption, data retention
- **[Authentication & Authorization](docs/security/authentication.md)** - JWT, permissions, rate limiting
- **[Input Validation](docs/security/input-validation.md)** - XSS, SQLi, CSRF prevention patterns
- **[Development Security](docs/security/development.md)** - Code review checklist, testing, git security
- **[Deployment Security](docs/security/deployment.md)** - Production checklist, infrastructure hardening
- **[Compliance](docs/security/compliance.md)** - GLBA, CCPA, UPL, breach notification

## Code Review Checklist

Quick checklist for all contributions:

- [ ] No secrets in code (use environment variables)
- [ ] Input validation on all user inputs
- [ ] Parameterized queries (no string concatenation)
- [ ] Authentication checks on all endpoints
- [ ] Encrypted fields for PII (SSN, income, debts)
- [ ] Audit logging for sensitive actions
- [ ] Error handling doesn't leak system details
- [ ] Dependencies up to date with no known CVEs

## Security Roadmap

**Short-term (Next 3 Months):**
- [ ] Implement MFA for user accounts
- [ ] Add account lockout after failed login attempts
- [ ] Externalize audit logs to secure storage
- [ ] Implement key rotation mechanism
- [ ] Add security headers (CSP, HSTS, etc.)

**Medium-term (3-6 Months):**
- [ ] SOC 2 Type II preparation
- [ ] Penetration testing
- [ ] SIEM integration
- [ ] Encrypted S3 storage for generated forms
- [ ] Automated security scanning in CI/CD

**Long-term (6-12 Months):**
- [ ] HSM for encryption keys
- [ ] Real-time anomaly detection
- [ ] Bug bounty program
- [ ] Third-party security audit annually
- [ ] ISO 27001 certification (if scaling)

## Acknowledgments

We thank security researchers who have responsibly disclosed vulnerabilities:

- *None yet - be the first!*

## Contact

**Security Team:** security@dignifi.org
**GitHub:** Create a private security advisory

**Project Maintainer:** Courtney Richardson

---

**Last Updated:** March 2026
**Next Review:** June 2026 (quarterly review cycle)
