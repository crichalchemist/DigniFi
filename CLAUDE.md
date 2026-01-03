# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DigniFi** is a trauma-informed digital platform that simplifies bankruptcy filing (Chapter 7 and Chapter 13) for low-income, pro se (self-represented) Americans. The platform aims to democratize access to bankruptcy relief by translating complex legal processes into plain-language guidance, auto-populated court forms, and dignified user experiences.

**Current Stage:** Pre-development / PRD phase. Backend logic maps exist conceptually, but no codebase has been implemented yet.

**Mission-Critical Constraint:** All development must respect Unauthorized Practice of Law (UPL) boundaries. The platform provides legal *information*, never legal *advice*.

## Key Documentation

### Product Requirements Document
Primary specification: `/Product Docs/DigniFi_PRD_v0.1.md`

This comprehensive PRD includes:
- Research synopsis with competitive analysis (Upsolve as primary comparator)
- Problem framing using MITRE canvas methodology
- Opportunity solution tree with prioritized features
- Experiment plan (paper prototype → legal clinic pilot → public beta)
- Full product specification with user flows and acceptance criteria
- Simulated stakeholder gate reviews
- Decisions log and assumptions requiring validation

### Supporting Documentation
- `/Product Docs/Dignifi Brief.pdf` - Executive summary and founder vision
- `/Product Docs/dignifi_technical_architecture.md` - Technical analysis and architecture recommendations
- `/Product Docs/Strategic Communication Plan.pdf` - Go-to-market and stakeholder communication strategy

## Architectural Principles

### Technology Recommendations (from technical architecture analysis)

**Initial Stack (Single-Server MVP):**
- **Backend:** Python/Django or Node.js
- **Frontend:** React or Vue SPA
- **Database:** PostgreSQL (encrypted at rest)
- **Document Storage:** S3-compatible object storage or local filesystem
- **PDF Generation:** PyPDF2, pdfrw, or Adobe PDF Services API

**Scaling Path:**
- Docker containerization
- Kubernetes or Docker Swarm orchestration
- CDN for static assets
- Load balancing for high availability

### Core System Components

1. **Intake & Decision Engine**
   - Rules-based logic encoding bankruptcy eligibility criteria (11 U.S.C. § 707(b) means test)
   - District-specific rule modules (94 federal districts have varying local rules)
   - Fee waiver qualification logic (28 U.S.C. § 1930(f))
   - Consider: Graph database, Drools, OpenL Tablets, or custom Python/Node logic

2. **Form Generation Pipeline**
   - Structured data model for Official Bankruptcy Forms 101-128 and Schedules A/B through J
   - PDF manipulation layer for fillable field population
   - Schema validation ensuring required fields are complete
   - Version control system for form updates (Administrative Office updates forms periodically)

3. **AI/NLP Components** (MVP: Pre-written content; Future: RAG)
   - **MVP Approach:** Pre-written explainer content keyed to form fields (avoids UPL risk)
   - **Future Approach:** RAG system with embedding model over bankruptcy code sections
   - Vector database options: Pinecone, Weaviate, pgvector
   - **Critical:** All outputs must be labeled as legal information, not advice

4. **Case Management & Calendar**
   - Event-driven architecture for deadline tracking (341 meeting, plan confirmation, discharge)
   - Notification service (email, SMS, push)
   - CM/ECF integration for court calendar updates (RSS feeds)

5. **Credit Counseling Integration**
   - Interface with DOJ-approved credit counseling providers
   - OAuth-based certificate verification or PDF upload/parsing

## Compliance & Legal Boundaries

### UPL (Unauthorized Practice of Law) Rules

**ALWAYS PERMITTED:**
- Explaining what the law says (general information)
- Providing process information
- Auto-populating forms with user-provided data
- Showing eligibility criteria
- Linking to official court resources

**NEVER PERMITTED:**
- Recommending specific legal actions ("you should file Chapter 7")
- Interpreting law for user's specific situation
- Advising whether to file
- Predicting case outcomes
- Representing users in court proceedings

**Language Patterns:**
- ✅ "You may be eligible for Chapter 7 if..."
- ✅ "Chapter 7 typically requires..."
- ❌ "You should file Chapter 7"
- ❌ "Based on your situation, I recommend..."

**Required Safeguards:**
- Disclaimers at every decision point
- Audit logging of all guidance provided to users
- Regular legal audits by UPL experts
- User agreement acknowledging software does not provide legal advice

### Data Security Requirements

- Encryption at rest and in transit (PII: SSN, income data, creditor information)
- SOC 2 Type II controls if handling financial data at scale
- State data protection law compliance (California, Illinois BIPA)
- Breach notification infrastructure

## Development Priorities

### MVP Scope (Single-District First)

**PRD Priority Classification:**
- **P0 (Must-Have for MVP):** Intake flow, Chapter 7 basic eligibility, Form 101 generation, fee waiver logic, UPL compliance framework
- **P1 (Should-Have for Pilot):** Calendar/reminders, credit counseling integration, pilot district rules
- **P2 (Nice-to-Have):** Multi-language support, mobile app, document upload
- **P3 (Future):** Chapter 13 support, all 94 districts, eviction defense expansion

### Critical Technical Risks to Validate

1. **District Variability:** 94 federal districts with differing rules—start with ONE district
2. **Form Version Drift:** Forms change; need automated monitoring of updates
3. **UPL Liability:** Crossing from information to advice creates legal risk
4. **Pro Se E-Filing Constraints:** Many courts limit e-filing for pro se litigants
5. **PDF Form Complexity:** Official forms may have non-standard field names/structure

## Development Workflow

### When Building Features

1. **UPL Check First:** Before implementing any guidance/recommendation feature, verify it provides information (not advice)
2. **Plain Language:** Target 6th-8th grade reading level for all user-facing text
3. **Trauma-Informed Design:** Avoid shame/blame language; preserve user dignity
4. **Error Prevention Over Correction:** Guide users to correct inputs rather than fixing after submission
5. **Audit Everything:** Log all user interactions with decision engines and guidance systems

### Testing Requirements

1. **Legal Compliance Testing:** Every guidance string reviewed for UPL violations
2. **Form Accuracy Testing:** Generated PDFs must match official court forms exactly
3. **Accessibility Testing:** WCAG 2.1 AA compliance (many users face disabilities)
4. **Reading Level Testing:** Automated readability scoring (Flesch-Kincaid)

## Validation Strategy

### Experiment Sequence (from PRD)

1. **Paper Prototype (2-3 weeks):** 10-15 user tests with target demographic
2. **Legal Clinic Pilot (6 months):** Partnership with community legal clinic, supervised filings
3. **Public Beta:** Measured success criteria (discharge rates, fee waiver approvals, completion rates)

### Success Metrics

- Pro se discharge rate improvement (baseline: 30% → target: 60%+)
- Fee waiver approval rate
- Form completion without errors
- Time to complete intake (target: <45 minutes)
- User dignity/respect perception (qualitative)

## District-Specific Implementation

### Pilot District Selection Criteria

When choosing initial district for MVP:
1. **UPL-Friendly:** State bar has clear legal tech guidance or regulatory sandbox
2. **Pro Se E-Filing:** Court allows electronic filing for pro se litigants
3. **Geographic Access:** Proximity to legal clinic partner for pilot
4. **Form Standardization:** District uses standard federal forms without excessive local modifications

### District Rule Modules

Each district implementation requires:
- Median income thresholds (updated annually by Census Bureau)
- State-specific exemption schedules (homestead, vehicle, tools of trade)
- Local court rules and procedures
- E-filing requirements and limitations
- Trustee assignment patterns

## Key Decisions & Assumptions

### Documented Decisions (see PRD Section 7)

1. Single-district MVP before scaling to 94 districts (budget/complexity trade-off)
2. Chapter 7 only for MVP; Chapter 13 deferred (complexity/risk)
3. Pre-written guidance over AI/LLM generation (UPL risk mitigation)
4. Legal clinic pilot pathway vs. direct-to-consumer (supervised validation)
5. Local server deployment initially (cost control, data sovereignty)

### Assumptions Requiring Validation

1. Pro se filers can successfully complete guided intake in <60 minutes
2. Legal clinics will partner for supervised pilot (unconfirmed)
3. PDF form manipulation is technically feasible across form versions
4. Pre-written content can achieve trauma-informed tone at scale
5. Single-district success will de-risk multi-district expansion

## References & Resources

### Bankruptcy Law
- 11 U.S.C. § 707(b) - Means Test for Chapter 7 Eligibility
- 28 U.S.C. § 1930(f) - Fee Waiver Provisions
- Official Bankruptcy Forms 101-128: https://www.uscourts.gov/forms/bankruptcy-forms

### Competitive Intelligence
- **Upsolve:** Nonprofit, Chapter 7 only, 17,000+ users, LSC-funded
- Study Upsolve's UX patterns, intake flow, and UPL compliance disclaimers

### Technical Resources
- PACER (Public Access to Court Electronic Records): https://pacer.uscourts.gov/
- CM/ECF (Case Management/Electronic Case Filing) standards
- DOJ-Approved Credit Counseling Agencies: https://www.justice.gov/ust/list-credit-counseling-agencies-approved-pursuant-11-usc-111

### Inspirational Frameworks
- "Dignity Not Debt" - Corporate legal systems prioritize profit over people
- "It's Not You, It's Capitalism" - System gaslights individuals for structural failures
- Trauma-informed design principles for vulnerable populations

## Contact & Context

**Founder:** Courtney Richardson, Northwestern University Communication Studies student
**Organizational Model:** Social impact startup, prize-funding dependent
**Development Status:** Pre-code; PRD and architecture analysis complete
**Next Milestone:** Paper prototype for user testing
