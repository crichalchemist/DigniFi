# DigniFi Technical Architecture Analysis

Based on the project documents, DigniFi describes a platform with several functional requirements but leaves the technical architecture largely implicit. This document outlines what a viable architecture would require.

---

## Core System Components

### 1. Intake & Decision Engine

The "Smart Chapter Selection & Fee Waiver Engine" implies a rules-based logic layer, likely structured as:

- A decision tree or finite state machine encoding eligibility criteria under 11 U.S.C. § 707(b) (means test), asset exemption thresholds, and fee waiver qualifications under 28 U.S.C. § 1930(f)
- District-specific rule modules (94 federal districts have varying local rules, median income thresholds, and exemption schedules)
- Input validation against IRS standards for income calculation and expense allowances

This isn't sophisticated AI in the generative sense—it's deterministic logic with conditional branching. A graph database or hierarchical rule engine (Drools, OpenL Tablets, or custom Python/Node logic) would suffice.

### 2. Form Generation Pipeline

"Auto-Populated Court Forms" mapping to official PDFs requires:

- A structured data model capturing all fields across Official Bankruptcy Forms (Forms 101–128, plus schedules A/B through J)
- PDF manipulation layer (likely PyPDF2, pdfrw, or Adobe PDF Services API) capable of populating fillable fields or generating flat PDFs from templates
- Schema validation ensuring required fields are complete before generation
- Version control for form updates (Administrative Office of U.S. Courts periodically revises forms)

### 3. Data Layer

Minimum viable persistence:

- Relational database (PostgreSQL) for user accounts, case data, filing history, calendar events
- Document storage (S3-compatible object storage or local filesystem for MVP) for uploaded documents, generated forms, and audit trails
- Encryption at rest and in transit—mandatory given PII sensitivity (SSN, income data, creditor information)

### 4. AI/NLP Components: Trauma-Informed Language & User Empowerment

DigniFi's generative AI is **not** used for legal advice or decision-making, but for **trauma-informed, court-appropriate language generation** to support user dignity and self-advocacy:

**Primary Use Case:**
- Generate calming, supportive language for filers, especially if required to appear in court (e.g., 341 meeting of creditors)
- Provide plain-language explanations of bankruptcy processes, deadlines, and next steps
- Offer empowerment scripts and responses to reduce anxiety and support dignity during high-stress interactions

**Technical Approach:**
- Generative AI (RAG or fine-tuned LLM) trained on bankruptcy law, court procedures, local rules, and trauma-informed language principles
- Vector database (pgvector, Pinecone, or Weaviate) for semantic search over bankruptcy code sections, procedures, and local rules
- Strict UPL guardrails: all outputs labeled as informational support, never personalized legal advice
- Content controls ensuring responses are empowering, non-judgmental, and trauma-sensitive

**Alternative (MVP):**
- Pre-written explainer content keyed to specific form fields or process stages
- Conditional display logic with customizable message templates
- No generative component; managed by content team

### 5. Case Management & Calendar

- Event-driven architecture tracking deadlines (341 meeting of creditors, plan confirmation dates, discharge milestones)
- Notification service (email, SMS, push) with configurable reminders
- Integration points for court electronic filing calendars (CM/ECF has RSS feeds for case updates)

### 6. Credit Counseling Integration

The "Integrated Credit Certification Modules" must interface with DOJ-approved credit counseling and debtor education providers. Options:

- Direct API integration with approved agencies
- OAuth-based certificate verification
- PDF upload and parsing for completion certificates

### 7. Financial Data Import (Plaid & Credit Karma)

**Plaid Integration:**
- Securely connect user bank accounts via Plaid Link (OAuth)
- Retrieve account balances, transaction history, and liabilities (credit cards, loans, debts)
- Map creditor data to bankruptcy form fields (name, type, balance, account #)
- Reduces manual data entry, improves accuracy, streamlines intake process
- Requires: Plaid developer account, user consent flow, encrypted storage of import data
- Risk: Privacy concerns; must provide clear consent messaging and data usage explanation

**Credit Karma Integration:**
- No public API (as of 2026); support user-uploaded credit reports (PDF/CSV)
- Implement document parsing (OCR or PDF text extraction) to extract creditor information
- Alternative for users unwilling/unable to connect Plaid
- Requires: Robust PDF/CSV parsing, creditor data normalization, user transparency

**Compliance:** All imported PII must be encrypted at rest, data minimized, and retention policies enforced.

### 8. PACER/CM-ECF Integration: Current State & Systemic Advocacy

**Current Technical Constraints:**
- No official public API for e-filing or automated case status retrieval
- PACER (pacer.uscourts.gov) offers web portal access; some courts offer RSS feeds for case updates
- CM/ECF (Case Management/Electronic Case Files) is the e-filing system, requires separate credentials per court
- E-filing for pro se filers is limited: most districts require in-person or mail filing; some pilot e-filing portals exist

**DigniFi Approach:**
- Generate court-ready PDFs for user download and manual filing
- Provide step-by-step instructions for e-filing (where available) or in-person/mail filing
- Never store PACER or CM/ECF credentials; always inform users of manual steps required
- (Aspirational) If/when official APIs become available, implement case status tracking and e-filing submission

**Systemic Change Goal:**
- Partner with legal aid organizations and court systems to advocate for expanded e-filing, standardized forms, and digital-first access for pro se filers
- Track and report user pain points to inform advocacy and court outreach
- Support broader adoption of technology-enabled pro se support

### 9. Illinois/Chicago Local Rules & District-Specific Requirements

**Northern District of Illinois (ILND) Specifics:**
- Maintains district-specific local rules, exemption schedules, median income thresholds
- E-filing for pro se filers: Limited; registration required, but not all documents eligible for electronic submission
- Chicago-specific exemptions and procedural rules apply

**DigniFi Implementation:**
- Modular support for district-specific rules, forms, and exemptions with rapid update capability
- Maintains accurate, current data for ILND and all 93 other federal districts
- Plain-language guidance on local requirements and filing procedures
- Integration with systemic change advocacy to push for simplified, standardized local rules

**Systemic Change Focus:**
- Support efforts to standardize local rules across districts, reducing procedural barriers for pro se filers
- Advocate for digital-first court processes and expanded e-filing access

---

## Infrastructure Considerations

The Strategic Communication Plan mentions "local server will house the MVP" and "bare-metal scaling capacity." This suggests:

- Initial deployment: Single-server architecture (monolith) running on owned or rented hardware
- Stack: Likely Python/Django or Node.js backend, React or Vue frontend, PostgreSQL database
- No cloud dependency initially—potentially for cost control or data sovereignty concerns

### Scaling Path

- Containerization (Docker) for reproducibility
- Orchestration (Kubernetes or Docker Swarm) when multi-node becomes necessary
- CDN for static assets
- Load balancing for high availability

---

## Compliance Architecture

This is where the architecture becomes non-trivial.

### Unauthorized Practice of Law (UPL) Boundaries

- All outputs must be framed as information, not advice
- No personalized recommendations that cross into legal judgment
- Clear disclaimers at decision points
- Audit logging of all guidance provided to users

### Data Security

- SOC 2 Type II or equivalent controls if handling financial data at scale
- PII handling compliant with state data protection laws (California, Illinois BIPA if biometric authentication is used)
- Breach notification infrastructure

### Court System Integration

- CM/ECF (Case Management/Electronic Case Filing) integration requires PACER credentials and adherence to court e-filing standards
- Some districts require attorney signatures for electronic filing; pro se filers often must file paper copies or use limited e-filing portals
- This is a significant constraint: DigniFi may generate forms but cannot file them directly in most jurisdictions without user action

---

## Architecture Diagram (Conceptual)

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                           │
│  (React/Vue SPA or React Native mobile app)                 │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS
┌─────────────────────▼───────────────────────────────────────┐
│                    API Gateway                              │
│  (Authentication, rate limiting, request routing)           │
└─────────────────────┬───────────────────────────────────────┘
                      │
       ┌──────────────┼──────────────┬──────────────┐
       ▼              ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ Intake     │ │ Document   │ │ Calendar   │ │ Guidance   │
│ Service    │ │ Generation │ │ Service    │ │ Service    │
│            │ │ Service    │ │            │ │ (RAG/LLM)  │
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
      │              │              │              │
      └──────────────┴──────┬───────┴──────────────┘
                            │
              ┌─────────────▼─────────────┐
              │      Data Layer           │
              │  PostgreSQL + Object Store│
              │  + Vector DB (optional)   │
              └───────────────────────────┘
```

---

## Implementation Status & Technology Stack

**Current Implementation (Validated via comprehensive system design analysis):**
- Backend: Django 5.0 + Django REST Framework with modular app architecture
- Frontend: React 19 + TypeScript + Vite
- Database: PostgreSQL 15 with Fernet field-level encryption for PII
- Infrastructure: Docker Compose for development; local server deployment for MVP
- Security: JWT authentication, audit logging, UPL compliance middleware
- Forms: pypdf integration for PDF generation and form population

**Key Architectural Decisions:**
- Domain-driven design with service layer (MeansTestCalculator, Form101Generator)
- Encrypted model fields for SSN, account numbers, and sensitive financial data
- Audit logging for all authenticated requests with UPL-sensitive action flagging
- Token rotation and blacklisting for JWT security
- 10-year audit log retention for compliance

---

## Critical Technical Risks & Mitigation

### 1. District Variability
**Risk:** 94 federal districts with differing local rules, exemption schedules, and procedural requirements. Maintaining accurate, current logic for each is a substantial ongoing burden.
**Mitigation:** Modular district-specific data models (MedianIncome, ExemptionSchedule, LocalRule). Automated monitoring and rapid update capability. Systemic advocacy to standardize rules across districts.

### 2. Form Version Drift
**Risk:** Official forms change. Without automated monitoring of Administrative Office updates, the platform could generate outdated or invalid filings.
**Mitigation:** Version control for form updates. Monitoring system for Administrative Office releases. Field mapping documentation. Regular testing against official forms.

### 3. UPL Liability
**Risk:** If the AI guidance crosses from information to advice, or if users rely on the platform and experience dismissals or adverse outcomes, the platform may face regulatory scrutiny or civil liability.
**Mitigation:** Strict UPL guardrails. All outputs labeled as informational support, not legal advice. Audit logging of all UPL-sensitive actions. Clear disclaimers at decision points. AI used only for trauma-informed language support, not legal decision-making.

### 4. Pro Se Filing Constraints
**Risk:** Many courts limit e-filing for pro se litigants. DigniFi may prepare documents but cannot guarantee users can file them electronically, creating a last-mile problem.
**Mitigation:** Comprehensive e-filing/in-person filing instructions. Aspirational PACER/CM-ECF integration when APIs become available. Systemic advocacy for expanded e-filing access. Transparent communication of filing limitations by district.

### 5. Scalability vs. Accuracy Tradeoff
**Risk:** A local-server MVP is fine for testing, but scaling requires robust infrastructure without sacrificing the compliance review process described in the communications plan.
**Mitigation:** Containerized architecture (Docker) supports scaling to Kubernetes. Read replicas for PostgreSQL. S3/object storage for generated forms and documents. API versioning for backwards compatibility.

### 6. Third-Party Integration Risks (Plaid, Credit Karma, PACER)
**Risk:** Dependency on third-party APIs with uncertain availability, pricing, and support.
**Mitigation:** Graceful degradation if APIs unavailable. Fallback to manual data entry or user-uploaded documents. No hard dependency on any single integration. Monitor API changes and court system updates.

---

## Systemic Change & Advocacy Framework

DigniFi's architecture is designed not only to serve individual users but to catalyze systemic change in bankruptcy access and pro se support:

1. **Data-Driven Advocacy:** Track user pain points, procedural barriers, and filing constraints to inform advocacy and court outreach.
2. **Standardization Efforts:** Partner with legal aid organizations and court systems to push for standardized forms, simplified local rules, and digital-first processes.
3. **E-Filing Expansion:** Support efforts to expand CM/ECF e-filing access for pro se filers; advocate for official APIs to enable direct integration.
4. **User Empowerment:** Provide trauma-informed language support and court-appropriate communication tools to help users self-advocate.
5. **Transparency & Accountability:** Publish aggregate data on district variability, filing constraints, and systemic barriers to inform policy discussions.

---

## Conclusion

The architecture is achievable with a small team, but the complexity lies less in the technology than in maintaining legal accuracy across jurisdictions, navigating the regulatory boundary between legal information and legal advice, and coordinating systemic advocacy efforts.

Key success factors:
- **Technical:** Modular design, robust encryption, compliance logging, and clear separation of concerns
- **Legal:** Strict UPL guardrails, AI used only for trauma-informed language (not advice), audit trails, and transparent disclaimers
- **Social:** Systemic advocacy for expanded e-filing, standardized rules, and pro se support infrastructure
- **Operational:** Rapid update capability for district rules/forms, monitoring of court system changes, and user feedback integration
