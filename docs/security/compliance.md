# Compliance & Legal Requirements

## Overview

DigniFi operates at the intersection of legal services, financial services, and technology. This creates complex compliance obligations across multiple regulatory domains.

## Unauthorized Practice of Law (UPL)

### Core Principle

**Legal Information vs. Legal Advice:**
- **Information** (✅ Permitted): Explaining what the law says, providing forms, showing eligibility criteria
- **Advice** (❌ Prohibited): Recommending specific actions, interpreting law for user's situation, predicting outcomes

### UPL Compliance Requirements

**1. No Attorney-Client Relationship:**
- Disclaimers at every decision point
- No representation in court
- No personalized legal advice

**2. Audit Trail:**
- Log all guidance provided to users
- Track user decisions and form submissions
- Records may be subpoenaed in UPL investigations

**3. Language Patterns:**
```
✅ Permitted:
- "You may be eligible for Chapter 7 if..."
- "Chapter 7 typically requires..."
- "The law says..."

❌ Prohibited:
- "You should file Chapter 7"
- "Based on your situation, I recommend..."
- "You will win/lose your case"
```

**4. Required Disclaimers:**
```
This platform provides legal information, not legal advice.
We cannot tell you whether to file bankruptcy or which chapter to choose.
For legal advice about your specific situation, consult a licensed attorney.
```

### Security Implications

**Incident Response:**
- If guidance crosses into advice → legal counsel review required
- Audit logs may be evidence in UPL investigations
- Platform must never appear to provide legal advice

## Data Protection Laws

### Federal Laws

#### GLBA (Gramm-Leach-Bliley Act)

**Applicability:** May apply as a financial services platform

**Three Rules:**

1. **Financial Privacy Rule:**
   - Provide privacy policy to users
   - Explain what data is collected and why
   - Allow opt-out of data sharing (if applicable)
   - **DigniFi Status:** ✅ Privacy policy published

2. **Safeguards Rule:**
   - Implement written information security program
   - Designate security coordinator
   - Conduct risk assessments
   - Implement safeguards (encryption, access controls)
   - **DigniFi Status:** ✅ Field-level encryption, audit logging

3. **Pretexting Protection:**
   - Prevent identity theft
   - Verify user identity before providing access
   - **DigniFi Status:** ✅ Authentication required for all PII access

#### FCRA (Fair Credit Reporting Act)

**Applicability:** If providing credit information or score interpretation

**Requirements:**
- Accuracy of credit information
- Dispute resolution process
- User consent before accessing credit reports

**DigniFi Status:** Currently not applicable (users provide own credit info)

### State Laws

#### California CCPA/CPRA

**Applicability:** Users in California (>= $25M revenue or >50K CA residents)

**Consumer Rights:**
1. **Right to Know:** What data is collected, how it's used, who it's shared with
2. **Right to Delete:** Request deletion of personal information
3. **Right to Opt-Out:** Opt-out of sale of personal information
4. **Right to Correct:** Correct inaccurate information
5. **Right to Non-Discrimination:** Cannot charge more for exercising privacy rights

**DigniFi Implementation:**
- ✅ Privacy policy explains data collection
- ✅ Account deletion API endpoint
- ✅ No data sales (not applicable)
- ✅ Users can edit intake data
- ✅ No price discrimination

#### Illinois BIPA (Biometric Information Privacy Act)

**Applicability:** Only if collecting biometric data (fingerprints, facial recognition)

**DigniFi Status:** Not applicable (no biometric collection)

#### State Breach Notification Laws

**All 50 states have breach notification laws**

**Common Requirements:**
- Notify affected residents within 30-90 days
- Notify state attorney general (if > 500 residents)
- Provide free credit monitoring (if SSNs compromised)
- Disclose nature of breach, data types affected, remediation steps

**California (SB 1386) - Most Stringent:**
- Notification "without unreasonable delay"
- Notify California AG within 48 hours (if > 500 CA residents)

**New York SHIELD Act:**
- Requires "reasonable" data security measures
- Stricter penalties for non-compliance

## Bankruptcy-Specific Compliance

### E-Filing Requirements

**PACER/CM-ECF System:**
- Electronic filing required in most districts
- Pro se filers may have limited e-filing access
- Document format: PDF/A (long-term archival format)

**Redaction Rules:**
- SSN must be redacted (show last 4 digits only)
- Minor children identified by initials only
- Financial account numbers redacted (last 4 digits only)
- Birth dates truncated (year only)

**DigniFi Compliance:**
- Generated PDFs follow redaction rules
- Forms use XXX-XX-1234 format for SSN display
- Account numbers automatically truncated

### Credit Counseling Requirement

**11 U.S.C. § 109(h):**
- Debtor must complete credit counseling within 180 days before filing
- Counseling must be from DOJ-approved provider
- Certificate must be filed with petition

**DigniFi Integration:**
- Links to DOJ-approved providers
- Certificate upload functionality
- Validation that certificate is < 180 days old

### Fee Waiver Requirements

**28 U.S.C. § 1930(f):**
- Fee waiver available if income < 150% of poverty guidelines
- Application submitted with Form 103B
- Judge may grant or deny

**DigniFi Implementation:**
- Automatic fee waiver calculation based on income
- Form 103B generated if eligible
- Disclaimers that waiver is not guaranteed

## Data Retention & Destruction

### Retention Periods

**User Data:**
- **Active sessions:** Until case filed or 22 days of inactivity
- **Deleted accounts:** Immediate destruction (soft delete for 30 days, then purge)
- **Generated forms:** 22 days after case filing or abandonment

**Audit Logs:**
- **Retention:** 7 years (compliance requirement)
- **Purpose:** Fraud investigation, UPL defense, breach forensics
- **Storage:** Encrypted, append-only, tamper-evident

**Backups:**
- **User data backups:** 30 days retention
- **Audit log backups:** 7 years retention
- **Backup encryption:** AES-256 with separate keys

### Secure Destruction

**Data Deletion Process:**
1. User triggers deletion (account delete or auto-deletion after 22 days)
2. Soft delete: Mark records as deleted, preserve for 30 days (in case of dispute)
3. Hard delete: Overwrite with random data, remove from database
4. Backup purge: Mark for deletion in next backup cycle
5. Log destruction event in audit log

**Media Sanitization (Physical Drives):**
- NIST SP 800-88 guidelines
- Secure erase (ATA SECURE ERASE command)
- Physical destruction for decommissioned drives

## Breach Notification

### Breach Definition

**What Constitutes a Breach:**
- Unauthorized access to PII
- Accidental disclosure of PII
- Loss or theft of devices containing PII
- Ransomware affecting PII
- Insider theft of data

**What is NOT a Breach:**
- Encrypted data exposure (if keys not compromised)
- Authorized employee access for legitimate purposes
- User error (e.g., sharing own password)

### Notification Timeline

**California (Strictest - Use as Baseline):**
- **Discovery:** Within 48 hours of discovering breach
- **Notification:** "Without unreasonable delay"
- **AG Notification:** If > 500 CA residents affected

**Other States:**
- Typically 30-90 days from discovery
- Some require notification "as soon as possible"

### Notification Content

**Required Information:**
1. **Date of breach** (or estimated date range)
2. **Type of data compromised** (SSN, income data, etc.)
3. **Number of affected users**
4. **Steps taken to contain breach**
5. **Remediation measures** (password reset, encryption strengthening)
6. **User actions** (change password, monitor credit)
7. **Contact information** for questions

**Example Notification:**
```
Subject: Important Security Notice - Data Breach at DigniFi

Dear [User],

We are writing to inform you of a data security incident that may have affected your personal information.

What Happened:
On [Date], we discovered unauthorized access to our database containing user intake information.

What Information Was Involved:
The compromised data includes names, email addresses, and intake session data for approximately [N] users. Social Security Numbers were stored in encrypted format and we have no evidence that encryption keys were compromised.

What We Are Doing:
- We have secured the affected systems
- We are conducting a forensic investigation
- We have notified law enforcement
- We are enhancing our security measures

What You Can Do:
- Change your DigniFi password immediately
- Monitor your credit reports for suspicious activity
- Consider placing a fraud alert on your credit file
- Call us at [Phone] with any questions

We take this incident very seriously and apologize for any inconvenience.

Sincerely,
DigniFi Security Team
```

### Credit Monitoring Obligation

**When Required:**
- SSN compromised
- Financial account numbers compromised
- Sufficient data for identity theft

**Services:**
- 1-2 years of free credit monitoring
- Identity theft insurance
- Credit report access

**Providers:**
- Experian IdentityWorks
- Equifax Identity Restoration
- LifeLock

## SOC 2 Compliance (Future)

### SOC 2 Type II

**Timeline:** 6-12 months post-funding

**Trust Service Criteria:**
1. **Security:** Access controls, encryption, monitoring
2. **Availability:** Uptime, disaster recovery
3. **Processing Integrity:** Data accuracy, completeness
4. **Confidentiality:** NDA, data classification
5. **Privacy:** GDPR/CCPA compliance

**Audit Process:**
1. Gap assessment (3 months)
2. Remediation (3-6 months)
3. Readiness assessment (1 month)
4. SOC 2 Type I audit (1 month)
5. Wait 6 months (controls must be in operation)
6. SOC 2 Type II audit (1 month)

**Cost:**
- Auditor fees: $15K-$50K (depending on scope)
- Remediation costs: Variable (tooling, consulting)
- Ongoing compliance: $10K-$20K/year

### Benefits

**Business:**
- Required for enterprise sales
- Differentiates from competitors
- Reduces cyber insurance premiums

**Security:**
- Forces formalization of security controls
- Regular third-party validation
- Demonstrates commitment to security

## Regulatory Roadmap

### Current (MVP)

- ✅ UPL compliance (disclaimers, audit logging)
- ✅ Field-level PII encryption
- ✅ Basic breach notification plan
- ✅ Privacy policy published

### Short-term (3-6 Months)

- [ ] GLBA compliance audit
- [ ] Enhanced breach notification procedures
- [ ] Multi-state breach notification compliance
- [ ] Credit monitoring vendor selection

### Medium-term (6-12 Months)

- [ ] SOC 2 Type I audit
- [ ] Penetration testing
- [ ] CCPA/CPRA full compliance (if applicable)
- [ ] Document retention policy enforcement

### Long-term (12+ Months)

- [ ] SOC 2 Type II certification
- [ ] ISO 27001 certification (if scaling)
- [ ] Annual third-party security audits
- [ ] Cyber insurance policy

## Contact & Resources

### Legal Counsel

**UPL Concerns:** Consult with legal counsel before making platform changes that involve user guidance

**Data Breach:** Notify legal counsel immediately upon breach discovery

### Regulatory Agencies

**FTC (Federal Trade Commission):**
- GLBA enforcement
- Data breach reporting (if FTC jurisdiction)
- https://www.ftc.gov/

**DOJ Bankruptcy Trustee:**
- Credit counseling agency approvals
- Bankruptcy fraud investigations
- https://www.justice.gov/ust

**State Attorneys General:**
- Breach notification
- State data protection law enforcement
- Varies by state

---

**Last Updated:** March 2026
