# DigniFi Product Requirements Document v0.2

**Document Version:** 0.2  
**Date:** January 3, 2026  
**Status:** Draft — Revised with Political & Organizational Frame  
**Author:** Generated via PRD Discovery Process; revised with founder input  
**Founder:** Courtney Richardson, Northwestern University

---

## Preface: What This Is

DigniFi is not a startup. It is infrastructure for legal self-defense, built by someone who needed it and offered freely to everyone the system harms.

This PRD describes both the technical product and the political project. The two are inseparable. A tool that helps people file bankruptcy is useful. A tool that documents how the system fails—and builds power to change it—is transformative.

The founder will be the first user. The validation is public. The mission is not to reform the system but to route around it while exposing its failures.

---

## Executive Summary

DigniFi is a trauma-informed digital platform that enables low-income Americans to file bankruptcy without an attorney, while simultaneously documenting and challenging the systemic barriers that make such a tool necessary.

**The problem:** Pro se Chapter 7 filers achieve ~30% success rates versus 95%+ for attorney-represented cases. Pro se Chapter 13 success rates are approximately 2.3%. These are not individual failures. They are the predictable outcomes of a system designed to extract compliance through complexity and punish the under-resourced.

**The solution:** A free, publicly available tool that:
- Provides deterministic eligibility guidance (legal information, not legal advice)
- Auto-populates court forms with error prevention and forced attention to critical provisions
- Explains legal requirements in plain language
- Preserves dignity through trauma-informed design
- Documents its own use to expose systemic failure

**The founder's role:** Courtney Richardson will file bankruptcy using DigniFi as a public case study. This is not a marketing tactic. It is the validation methodology: radical vulnerability as proof-of-concept, documentation, and political testimony.

**Organizational structure:** 501(c)(4) political action nonprofit. This enables unlimited lobbying, explicit political positioning, and freedom from the constraints that limit 501(c)(3) legal aid organizations.

**Coalition strategy:** DigniFi operates within an ecosystem of debt abolition advocates, disability justice organizations, family court reform activists, and critical legal scholars. Legal aid clinics are partners, not the primary coalition.

---

## Table of Contents

1. [Foundational Frame](#1-foundational-frame)
2. [Research Synopsis](#2-research-synopsis)
3. [Problem Framing](#3-problem-framing)
4. [Opportunity Solution Tree](#4-opportunity-solution-tree)
5. [Validation Strategy: Radical Vulnerability](#5-validation-strategy-radical-vulnerability)
6. [Product Requirements](#6-product-requirements)
7. [Political Strategy & Coalition Architecture](#7-political-strategy--coalition-architecture)
8. [Risks & Decisions Log](#8-risks--decisions-log)
9. [Appendix](#9-appendix)

---

## 1. Foundational Frame

### 1.1 What DigniFi Is

DigniFi is:
- **A tool** that enables pro se bankruptcy filing
- **A case study** documented through the founder's own use
- **A political project** challenging barriers to legal access
- **Infrastructure** designed for extension to other legal domains (family law, eviction defense, consumer debt)

DigniFi is not:
- A legal services provider
- A reform organization seeking court cooperation
- A startup optimizing for growth or revenue
- Neutral on the question of whether the system is just

### 1.2 Organizational Identity

**Legal Structure:** 501(c)(4) social welfare organization

**Why (c)(4) over (c)(3):**

| Dimension | 501(c)(3) | 501(c)(4) |
|-----------|-----------|-----------|
| Lobbying | Limited (typically <20% of budget) | Unlimited |
| Political campaign activity | Prohibited | Permitted (if not primary purpose) |
| Donor tax deduction | Yes | No |
| Foundation grants | Yes | Limited (some foundations have (c)(4) grant programs) |
| Messaging freedom | Constrained | Full |

The (c)(4) structure enables DigniFi to:
- Lobby for e-filing policy changes without limitation
- Explicitly critique the judicial system
- Engage in political education and advocacy
- Partner with political organizations that (c)(3)s cannot

**Funding Strategy:**
- Prize funding (immediate)
- Individual donors (not tax-deductible, but aligned with mission)
- Donor-advised funds that support (c)(4) work
- Foundation grants from non-charitable funds (Omidyar, Ford Foundation's BUILD program, etc.)
- Potential earned revenue from API licensing to ethical legal tech partners (future)

### 1.3 Theory of Change

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         THEORY OF CHANGE                                    │
└─────────────────────────────────────────────────────────────────────────────┘

Individual Level:
  [Person in debt crisis] 
      → [Uses DigniFi] 
      → [Files successfully / or fails with documentation of why]
      → [Discharge / or evidence of systemic barrier]

Systemic Level:
  [DigniFi documents patterns of failure]
      → [Coalition amplifies findings]
      → [Media exposes gap between system's claims and reality]
      → [Political pressure on courts and legislators]
      → [Policy change: e-filing access, simplified procedures, fee waiver expansion]

Movement Level:
  [DigniFi proves model in bankruptcy]
      → [Architecture extends to family law, eviction, consumer debt]
      → [Network of legal self-defense tools]
      → [Shift in power: people navigate systems without gatekeepers]
```

### 1.4 What Success Looks Like

**Year 1:**
- Founder completes bankruptcy filing using DigniFi (documented publicly)
- Tool available in one federal district
- 50-200 users complete filings
- Coalition partnerships formalized with 5+ organizations
- White paper published on e-filing barriers

**Year 3:**
- Tool available in 10+ districts
- 1,000+ successful discharges
- Chapter 13 support operational
- E-filing policy campaign launched
- Family law extension in development

**Year 10:**
- National coverage across all 94 bankruptcy districts
- Extensions to eviction defense, family court, consumer debt
- E-filing restrictions eliminated or substantially reduced for pro se filers
- Model replicated internationally

---

## 2. Research Synopsis

### 2.1 Market & Context

**Scale of Need:**
- 500,000+ Americans file bankruptcy annually
- 92% of civil legal problems among low-income Americans receive inadequate or no legal assistance
- 29.7% of individual Chapter 7 debtors have incomes below 150% of poverty line (fee waiver eligible)

**Outcome Disparities:**
- Pro se Chapter 7 success rate: ~30%
- Attorney-represented Chapter 7 success rate: 95%+
- Pro se Chapter 13 success rate: ~2.3%
- Nearly 90% of Chapter 13 repayment plans fail within five years

**Racial Dimensions:**
- Black consumers disproportionately steered into Chapter 13 even when Chapter 7 offers more immediate relief
- Bankruptcy outcomes correlate with race independent of income
- The "neutral" system produces racially disparate results

**Timing:**
- COVID-era debt protections expired
- Household debt at historic highs
- Legal aid chronically underfunded
- Remote/hybrid court operations normalized (COVID proved e-filing feasibility)

### 2.2 The 2005 Problem: BAPCPA and Attorney Failure

The Bankruptcy Abuse Prevention and Consumer Protection Act of 2005 (BAPCPA) introduced the means test—a presumption that filers with above-median income are "abusing" bankruptcy.

But BAPCPA includes escape valves that attorneys routinely fail to use:

**Form 122A-2 (Chapter 7 Means Test Calculation) includes:**
- Line 44: Special Circumstances checkbox
- Lines 45-47: Explanation section for additional expenses or income adjustments
- "Any other circumstances that demonstrate additional expenses or income adjustments for which there is no reasonable alternative"

**Common qualifying circumstances:**
- Job loss or income reduction
- Medical expenses for self or family member
- Caregiving obligations
- Gig economy income volatility
- Divorce-related expenses
- Disability accommodations

**The failure mode:** Attorneys either don't know about these provisions, don't think to ask, or don't document properly. The result: filers who could have qualified for Chapter 7 discharge are steered into Chapter 13 repayment plans that fail at 90% rates.

**DigniFi's response:** The intake flow makes it impossible to proceed without addressing special circumstances. The system forces the question. Users cannot skip to form generation without explicitly confirming whether special circumstances apply—and if they indicate any potentially qualifying circumstance, the system prompts for documentation.

This is not legal advice. It is ensuring the law as written is actually applied.

### 2.3 E-Filing: A Policy Target, Not Just a Constraint

**Current state:**
- CM/ECF (Case Management/Electronic Case Filing) is the federal courts' e-filing system
- Most bankruptcy courts restrict or prohibit pro se e-filing
- Pro se filers must print forms, travel to courthouse, file in person
- This creates time costs, transportation barriers, and increased error rates

**The contradiction:**
- COVID-19 forced courts to expand e-filing temporarily
- Courts demonstrated e-filing is technically feasible for pro se filers
- Restrictions were reimposed as courts "returned to normal"
- The barrier is policy, not technology

**DigniFi's position:** E-filing restrictions are an access-to-justice issue. They disproportionately burden low-income, disabled, and geographically isolated filers. They are subject to challenge under:
- Constitutional access-to-courts doctrine
- ADA Title II (for disabled filers)
- Administrative rulemaking processes

DigniFi will:
1. Document every e-filing rejection experienced by users
2. Quantify the burden (time, cost, failure rate) imposed by paper-only filing
3. Support coalition advocacy for policy change
4. Provide legal research to partners pursuing litigation or administrative challenges

### 2.4 Competitive Landscape

| Entity | Model | What They Do Well | What They Don't Do |
|--------|-------|-------------------|--------------------|
| **Upsolve** | 501(c)(3) nonprofit | Free Chapter 7; $800M+ debt discharged; legal aid partnerships | Chapter 7 only; screens for safe cases; limited political advocacy |
| **Attorneys** | Fee-for-service ($1,500-3,000) | High success rates; handle complexity | Cost-prohibitive; capacity-limited; BAPCPA failures common |
| **Bankruptcy Mills** | Low-cost attorneys ($500-1,000) | Lower than full-service fees | Often predatory; high dismissal rates |
| **Legal Aid Clinics** | Free; attorney-supervised | Professional quality; no cost | Overwhelmed; limited capacity; geographic constraints |
| **DIY/Court Forms** | Self-service | No cost | 70%+ failure rate; no guidance |

**DigniFi's differentiation:**
- Chapter 7 AND 13 (Upsolve doesn't do 13)
- Forced attention to BAPCPA special circumstances (attorneys often miss)
- Trauma-informed UX (not just functional)
- Political advocacy mission (not just service delivery)
- Founder-as-first-user validation (not just client testimonials)

---

## 3. Problem Framing

### 3.1 The Problem Is Not Complexity

The conventional framing: "Bankruptcy is too complex for ordinary people."

The actual problem: **The system is designed to extract compliance through complexity and punish those without resources to navigate it.**

Complexity is not an accident. It is a feature. Legal jargon excludes. Procedural requirements create traps. Fee structures punish poverty. The result is predictable: the under-resourced fail, and their failure is attributed to individual inadequacy rather than systemic design.

### 3.2 Problem Statement

Low-income Americans who need bankruptcy relief encounter a system that:
- Obscures critical protections (like BAPCPA special circumstances) behind complexity
- Charges fees that exceed the monthly income of eligible filers
- Dismisses pro se filers for paperwork errors that attorneys would correct
- Restricts e-filing access, imposing time and transportation burdens
- Steers Black and Brown filers into Chapter 13 plans designed to fail
- Strips dignity through shame-inducing language and punitive procedures

This is not a market failure. It is a political condition. DigniFi addresses both the immediate need (helping people file) and the underlying condition (documenting and challenging systemic barriers).

### 3.3 What DigniFi Cannot Solve

- DigniFi cannot practice law or provide legal advice
- DigniFi cannot guarantee outcomes
- DigniFi cannot change the law directly (but can support those who can)
- DigniFi cannot serve filers with complex cases requiring attorney judgment
- DigniFi cannot eliminate the need for policy change

The tool is necessary but not sufficient. The political project is what makes the tool matter beyond individual discharges.

---

## 4. Opportunity Solution Tree

### 4.1 North Star Metric

**Primary:** Number of successful bankruptcy discharges assisted by DigniFi

**Secondary (equally important):**
- Policy changes achieved through advocacy supported by DigniFi documentation
- Coalition growth (organizations formally partnered)
- Extension to other legal domains (family law, eviction, consumer debt)

### 4.2 Opportunity Mapping

| ID | Opportunity | Impact | Effort | Coalition Value |
|----|-------------|--------|--------|-----------------|
| O1 | Reduce form errors causing dismissals | High | Medium | Medium |
| O2 | Force attention to BAPCPA special circumstances | High | Low | High (documents attorney failure) |
| O3 | Increase fee waiver approval rates | High | Low | Medium |
| O4 | Document e-filing barriers | Medium | Low | High (policy ammunition) |
| O5 | Provide plain-language guidance | Medium | Medium | Low |
| O6 | Track deadlines to prevent missed dates | Medium | Low | Low |
| O7 | Reduce shame/anxiety during process | Medium | High | Medium |
| O8 | Connect to credit counseling providers | Low | Low | Low |

### 4.3 Prioritized Solutions (MVP)

**P0 (Must Have):**
- Form auto-population with validation
- Means test calculator with forced special circumstances review
- Fee waiver eligibility screening
- E-filing rejection documentation (capture and log every barrier)

**P1 (Should Have):**
- Plain-language contextual guidance (pre-written, not AI)
- Deadline tracking and reminders
- Progress saving and session resumption

**P2 (Nice to Have):**
- Chapter comparison tool
- Trauma-informed UX patterns beyond MVP baseline
- Mobile optimization

**Deferred:**
- Chapter 13 support (v1.1)
- AI-powered guidance (requires extensive guardrails)
- Multilingual support
- Family law extension (v2.0+)

---

## 5. Validation Strategy: Radical Vulnerability

### 5.1 The Founder as First User

Courtney Richardson will file bankruptcy using DigniFi. This is not a test case in a controlled environment. It is the founder's actual bankruptcy, documented publicly.

**What gets documented:**
- The intake process (video/written diary)
- Every interaction with the tool
- Form generation and review
- The filing attempt (paper or e-filing, depending on district policy)
- Court responses, if any
- The 341 meeting of creditors
- The outcome (discharge, dismissal, or other)
- Post-filing reflections

**What this accomplishes:**
1. **Validates the tool** under real conditions, not simulated ones
2. **Demonstrates commitment** (the founder has skin in the game)
3. **Creates narrative** that coalition partners and media can amplify
4. **Provides evidence** of how the system treats a prepared, informed pro se filer
5. **Immunizes against criticism** ("you don't understand what users go through")

### 5.2 Documentation Protocol

| Phase | What's Documented | Format | Publication |
|-------|-------------------|--------|-------------|
| Pre-filing | Financial situation; why bankruptcy; prior attorney failure | Written narrative | Blog/essay |
| Intake | Screen recordings; time stamps; decision points | Video + timestamps | Edited documentary segments |
| Form generation | Generated forms (redacted as needed); error flags | Screenshots + commentary | Technical blog post |
| Filing | Method (paper/e-filing); barriers encountered; time/cost | Written + photo/video | Blog post |
| 341 meeting | Preparation; experience; questions asked | Audio (if permitted) or written | Blog post |
| Outcome | Discharge/dismissal; timeline; any complications | Official documents + narrative | Summary report |
| Reflection | What worked; what failed; what the system revealed | Long-form essay | Publication (Medium, personal site, partner outlets) |

### 5.3 Privacy and Consent

The founder consents to public documentation of their own bankruptcy.

**Boundaries:**
- Creditor names may be redacted if they include individuals (not corporations)
- Family members will not be identified without their consent
- Income and asset details will be disclosed (this is the point)
- The founder retains editorial control over what is published

**For other users (post-founder validation):**
- Opt-in consent for any case study participation
- Anonymized data collection by default
- Aggregate statistics published; individual cases only with explicit consent

### 5.4 Success and Failure Conditions

**If the filing succeeds:**
- Proof of concept: a non-attorney can build a tool that works
- Narrative: "I built what I needed, and now it's free for everyone"
- Next step: open to other users in pilot district

**If the filing fails:**
- Documented evidence of systemic failure
- Narrative: "Even a prepared, informed filer with a tool designed to prevent errors was failed by this system"
- Next step: forensic analysis of failure point; policy advocacy intensifies

Either outcome serves the mission. The point is not to win one case. The point is to make visible what the system does.

---

## 6. Product Requirements

### 6.1 Scope (MVP)

**In Scope:**
- Chapter 7 consumer bankruptcy (individual filers)
- Single federal district (selection criteria below)
- Web-based platform (responsive for mobile)
- Core intake and form generation (Forms 101-106, Schedules A-J, Form 122A-1/2)
- Means test calculator with forced special circumstances review
- Fee waiver eligibility screening
- Deadline tracking and reminders
- Pre-written contextual guidance
- Document checklist and upload
- E-filing barrier documentation (log every rejection)

**Out of Scope (MVP):**
- Chapter 13 (deferred to v1.1)
- Joint filings
- Business bankruptcy
- Direct e-filing integration
- AI-generated guidance
- Attorney matching or referral
- Post-discharge credit rebuilding
- Multilingual support
- Native mobile apps

### 6.2 Critical Feature: Special Circumstances Enforcement

The intake flow must force attention to BAPCPA special circumstances (Form 122A-2, Lines 44-47).

**Implementation:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SPECIAL CIRCUMSTANCES REVIEW (Required before form generation)             │
└─────────────────────────────────────────────────────────────────────────────┘

Screen 1: Introduction
  "The law provides that even if your income is above the median, you may 
   still qualify for Chapter 7 if you have 'special circumstances' that 
   justify additional expenses or income adjustments.
   
   This is important. Many attorneys fail to ask about this. DigniFi will not."

Screen 2: Checklist (user must review each item)
  □ Job loss or significant income reduction in the past 6 months
  □ Medical expenses for yourself or a family member
  □ Disability-related expenses
  □ Caregiving responsibilities (children, elderly parents, etc.)
  □ Divorce or separation affecting your finances
  □ Active military duty or recent deployment
  □ Expenses for a child's education needs
  □ Home or vehicle necessary for work that requires maintenance
  □ Other circumstances that created unavoidable expenses
  
  [User must check each box as "Applies" or "Does not apply"]
  [If any "Applies" is checked, proceed to documentation screen]

Screen 3: Documentation (if any special circumstances apply)
  "You indicated that [circumstances] apply to your situation.
   
   The law requires you to explain these circumstances in your own words and
   provide documentation (such as medical bills, termination letters, etc.).
   
   This explanation will be included in your bankruptcy forms. The more 
   specific you are, the stronger your case for Chapter 7 eligibility."
   
  [Text field: 500 character minimum, 2000 character maximum]
  [Document upload: optional but recommended]

Screen 4: Confirmation
  "You have reviewed all special circumstances categories.
   
   [If circumstances apply]: Your explanation has been saved and will be 
   included in Form 122A-2.
   
   [If no circumstances apply]: You have confirmed that none of the listed
   special circumstances apply to your situation. If your income is above
   the median for your household size, you may not qualify for Chapter 7.
   
   [Button: Continue to form generation]"
```

**Why this matters:** This is the feature that would have changed the founder's outcome. The system checks what attorneys fail to check.

### 6.3 Technical Architecture

**Stack:**

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Backend | Python/Django | Rapid development; strong PDF libraries |
| Frontend | React | Component reusability; future pattern library |
| Database | PostgreSQL | Robust; free; pgvector for future RAG |
| Document Storage | Local filesystem (MVP) | Cost control |
| PDF Generation | PyPDF2 + ReportLab | Open-source; form field population |
| Hosting | Local server (MVP) | Per founder constraints |
| Email | Mailchimp (transactional) | Already in use |

**Architecture Diagram:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      Client Layer                               │
│  (React SPA, responsive web)                                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTPS
┌─────────────────────▼───────────────────────────────────────────┐
│                    API Gateway                                  │
│  (Authentication, rate limiting, request routing)               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
       ┌──────────────┼──────────────┬──────────────┐
       ▼              ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│ Intake     │ │ Document   │ │ Calendar   │ │ Barrier    │
│ Service    │ │ Generation │ │ Service    │ │ Logging    │
│            │ │ Service    │ │            │ │ Service    │
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
      │              │              │              │
      └──────────────┴──────┬───────┴──────────────┘
                            │
              ┌─────────────▼─────────────┐
              │      Data Layer           │
              │  PostgreSQL + File Store  │
              └───────────────────────────┘
```

**New Component: Barrier Logging Service**

This service captures every obstacle users encounter:
- E-filing rejections (with error messages, timestamps, district)
- Form rejections by courts (if reported back)
- Deadline failures and causes
- User-reported barriers (optional feedback)

Data is aggregated for policy advocacy. Individual records are anonymized unless user consents to case study participation.

### 6.4 Data Model Extensions

**Beyond standard intake data, DigniFi tracks:**

```
BarrierLog:
  - id: UUID
  - user_id: UUID (nullable, for anonymous logging)
  - barrier_type: enum [E_FILING_REJECTED, FORM_REJECTED, DEADLINE_MISSED, 
                        COURT_ACCESS, TRANSPORTATION, OTHER]
  - district: string
  - timestamp: datetime
  - description: text
  - documentation: file reference (optional)
  - consent_for_advocacy: boolean

PolicyDataPoint:
  - id: UUID
  - district: string
  - metric_type: enum [EFILING_REJECTION_RATE, PROSE_DISMISSAL_RATE, 
                       FEE_WAIVER_APPROVAL_RATE, AVG_TIME_TO_DISCHARGE]
  - value: decimal
  - period_start: date
  - period_end: date
  - source: string
  - notes: text
```

### 6.5 User Flow (Chapter 7)

[Retained from v0.1 with additions]

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CHAPTER 7 FILING INTAKE                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. WELCOME & CONSENT                                                        │
│    - Platform explanation (not legal advice)                                │
│    - UPL disclaimer acknowledgment                                          │
│    - Privacy policy consent                                                 │
│    - Optional: consent to barrier logging for advocacy                      │
│    - [User clicks "I Understand, Let's Begin"]                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. INITIAL SCREENER (5 min)                                                 │
│    - Household size                                                         │
│    - Gross income (last 6 months)                                           │
│    - Primary debt types                                                     │
│    - Prior bankruptcy history                                               │
│    - [System calculates: Means test preliminary result]                     │
│    - [System calculates: Fee waiver eligibility]                            │
│    - NOTE: Even if above median, special circumstances may qualify user     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. DOCUMENT CHECKLIST                                                       │
│    [Retained from v0.1]                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. DETAILED INTAKE (45-60 min, can save & resume)                           │
│    [Retained from v0.1]                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. SPECIAL CIRCUMSTANCES REVIEW (REQUIRED - see 6.2)                        │
│    - User must review all special circumstances categories                  │
│    - If any apply, user must provide explanation and optional documentation │
│    - Cannot proceed to form generation without completing this step         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. REVIEW & CONFIRMATION                                                    │
│    [Retained from v0.1, with special circumstances summary added]           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 7. FORM GENERATION                                                          │
│    [Retained from v0.1]                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 8. FILING GUIDANCE & BARRIER LOGGING                                        │
│    - Filing instructions for specific court                                 │
│    - E-filing availability check (with link if available)                   │
│    - If e-filing unavailable: log this as barrier + explain paper filing    │
│    - Deadline reminders                                                     │
│    - [After filing attempt: prompt user to report outcome]                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.6 Acceptance Criteria Additions

**Feature: Special Circumstances Review**

```gherkin
Scenario: User cannot skip special circumstances review
  Given a user has completed detailed intake
  When the user attempts to proceed to form generation
  Then the user must first complete the special circumstances review
  And the system should not allow bypassing this step

Scenario: User indicates special circumstances apply
  Given a user is on the special circumstances review screen
  When the user checks "Applies" for "Job loss or significant income reduction"
  Then the user should be prompted to provide a written explanation
  And the explanation field should require minimum 500 characters
  And the user should see an option to upload supporting documents

Scenario: Special circumstances included in generated forms
  Given a user has indicated special circumstances apply
  And the user has provided an explanation
  When forms are generated
  Then Form 122A-2 should have Line 44 (Special Circumstances) checked
  And Lines 45-47 should contain the user's explanation
```

**Feature: Barrier Logging**

```gherkin
Scenario: E-filing unavailability logged
  Given a user has generated forms
  And the user's district does not allow pro se e-filing
  When the user views filing instructions
  Then the system should log a barrier event of type E_FILING_REJECTED
  And the user should see an explanation that e-filing is not available
  And the user should see paper filing instructions

Scenario: User reports filing outcome
  Given a user has downloaded their forms
  When 30 days have passed since download
  Then the user should receive an email asking about their filing outcome
  And the user should have the option to report: Filed / Not Yet Filed / Abandoned
  And if Filed, the user should be asked about any barriers encountered
```

---

## 7. Political Strategy & Coalition Architecture

### 7.1 Coalition Structure

DigniFi operates within three overlapping coalition circles:

**Circle 1: Debt Abolition & Economic Justice**
- Debt Collective
- Dignity Not Debt coalition
- Consumer rights organizations (NCLC, etc.)
- Community organizations doing mutual aid

**Circle 2: Legal Access & Reform**
- Legal aid organizations (selective partnerships)
- Law school clinics
- Access-to-justice researchers
- Court reform advocates

**Circle 3: Intersecting Justice Movements**
- Disability justice organizations (ADA angle on e-filing)
- Family court reform advocates (extension pathway)
- Reentry/formerly incarcerated advocacy (bankruptcy intersects with reentry)
- Racial justice organizations (documenting disparate impact)

### 7.2 Partnership Tiers

| Tier | Relationship | Examples | What DigniFi Provides | What Partner Provides |
|------|--------------|----------|----------------------|----------------------|
| **Core Alliance** | Formal partnership; shared strategy | Debt Collective, Dignity Not Debt | Data, tool access, joint messaging | Coalition infrastructure, amplification |
| **Research Partners** | Data sharing; co-authored publications | Law school clinics, critical legal scholars | Access to barrier data, case studies | Academic legitimacy, research capacity |
| **Service Partners** | Referral relationships | Legal aid clinics, credit counselors | Tool access for clients | Supervised validation environment |
| **Amplification Partners** | Informal; signal boost | Journalists, influencers, aligned orgs | Stories, data, access | Media reach, audience |

### 7.3 E-Filing Policy Campaign

**Objective:** Eliminate or substantially reduce e-filing restrictions for pro se bankruptcy filers

**Strategy:**

1. **Document** (Year 1)
   - Log every e-filing rejection through DigniFi
   - Quantify burden: time, cost, failure rate attributable to paper filing
   - Identify districts with best and worst practices
   - Publish white paper with findings

2. **Coalition** (Year 1-2)
   - Convene working group: disability advocates (ADA angle), legal aid, court reform
   - Draft model local rule for pro se e-filing
   - Gather organizational sign-ons

3. **Pressure** (Year 2-3)
   - Submit comments to Judicial Conference Committee on Court Administration
   - Congressional briefings (Judiciary Committee staff)
   - Media: pitch to reporters covering courts and access to justice
   - Direct outreach to bankruptcy judges through bar association channels

4. **Litigation Support** (If Needed)
   - Provide data and documentation to partners pursuing legal challenges
   - Potential claims: ADA Title II (disabled filers), due process (burden on access)
   - DigniFi does not litigate directly (not a legal services org) but supports those who do

### 7.4 Media Strategy: Radical Vulnerability

**Core Principle:** The founder's story is the story. Not case studies of anonymous users. The person who built the tool, using it, in public.

**Narrative Arc:**
1. "I was failed by the system" (the 2005 attorney failure, the family court silencing)
2. "I built what I needed" (DigniFi development)
3. "I'm using it myself" (the public bankruptcy filing)
4. "Now it's free for everyone" (launch)
5. "Here's what the system does" (documentation of barriers)
6. "Here's how we change it" (policy campaign)

**Target Outlets:**
- ProPublica (systemic failure, investigative)
- The Marshall Project (courts and justice)
- The Appeal (criminal/civil legal system critique)
- Reveal / Center for Investigative Reporting
- Local outlets in pilot district
- Legal trade press (ABA Journal, National Law Journal)

**What Makes This Different:**
- Not a success story ("our app helped 1000 people")
- A witness account ("here's what I experienced, what the data shows, and what it means")
- The outcome matters less than the documentation

---

## 8. Risks & Decisions Log

### 8.1 Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **UPL complaint or investigation** | Medium | Critical | Conservative framing; legal review; disclaimers; audit logging |
| **Founder's bankruptcy fails** | Medium | Medium | Either outcome serves mission; failure = documented systemic evidence |
| **Coalition partners distance themselves** | Medium | Medium | (c)(4) structure allows independence; don't depend on any single partner |
| **Courts retaliate against advocacy** | Low | Medium | Document everything; public record; coalition support |
| **Funding insufficient** | Medium | High | Lean scope; diversified funders; founder capacity for bootstrap |
| **Data breach** | Low | Critical | Encryption; minimal retention; incident response plan |
| **Form version drift** | Medium | High | Monitoring process; version flagging |
| **Technical complexity exceeds founder capacity** | Medium | Medium | Modular architecture; potential technical co-founder |

### 8.2 Open Decisions

| Decision | Owner | Deadline | Notes |
|----------|-------|----------|-------|
| Pilot district selection | Founder | Before prototype | N.D. Illinois likely (proximity) but evaluate UPL climate |
| Technical co-founder needed? | Founder | Before MVP development | Skill assessment in progress |
| Documentation publication platform | Founder | Before filing | Personal site? Substack? Partner outlet? |
| Coalition formalization timeline | Founder | Q1 2026 | Initial outreach to Debt Collective, Dignity Not Debt |
| Family law extension scoping | Founder | Post-MVP | Architecture should anticipate but not block on this |

### 8.3 Assumptions Log

| ID | Assumption | Risk if Wrong | Validation |
|----|------------|---------------|------------|
| A1 | Founder can complete own bankruptcy using tool | Validation methodology fails | The attempt itself is validation |
| A2 | Special circumstances enforcement reduces Chapter 13 steering | Feature doesn't improve outcomes | Clinic pilot comparison data |
| A3 | Coalition partners will engage with (c)(4) | Limited partnership options | Early outreach conversations |
| A4 | Media interested in radical vulnerability narrative | Limited amplification | Pitch to 3-5 outlets before launch |
| A5 | E-filing data useful for policy advocacy | Barrier logging not actionable | Review with policy partners |

---

## 9. Appendix

### 9.1 Glossary

[Retained from v0.1, with additions:]

| Term | Definition |
|------|------------|
| **BAPCPA** | Bankruptcy Abuse Prevention and Consumer Protection Act of 2005; introduced means test |
| **Special Circumstances** | Provisions under BAPCPA (Form 122A-2) allowing debtors to claim additional expenses or income adjustments that overcome presumption of abuse |
| **501(c)(4)** | Social welfare nonprofit; unlimited lobbying; donations not tax-deductible |
| **Radical Vulnerability** | Validation and communication strategy based on founder's public use of tool |
| **Barrier Logging** | Systematic documentation of obstacles users encounter for policy advocacy |

### 9.2 Form Reference

[Retained from v0.1]

### 9.3 District Selection Criteria

| Criterion | Weight | Notes |
|-----------|--------|-------|
| Founder proximity | High | Enables in-person validation, court visits |
| Pro se filing volume | High | Sufficient sample size |
| E-filing policy | Medium | Restrictive policy = more barrier data |
| Legal aid presence | Medium | Potential service partners |
| UPL case law | High | Favorable climate reduces regulatory risk |
| Local rule complexity | Medium | Simpler = faster MVP |

**Primary Candidate:** Northern District of Illinois (Chicago)
- Founder proximity: High
- Pro se volume: High
- E-filing: Limited (good for barrier documentation)
- Legal aid: Multiple organizations
- UPL: Moderate (requires careful framing)

### 9.4 Coalition Contact List (Draft)

| Organization | Contact Point | Status | Notes |
|--------------|---------------|--------|-------|
| Debt Collective | [TBD] | Not yet contacted | Primary coalition target |
| Dignity Not Debt | [TBD] | Not yet contacted | Cited in founding documents |
| NCLC Bankruptcy Team | [TBD] | Not yet contacted | Policy expertise |
| [Chicago-area legal aid] | [TBD] | Not yet contacted | Service partner potential |
| [Northwestern Law Clinic] | [TBD] | Not yet contacted | Research partner potential |

---

## What to Validate Next

1. **[ ] Founder bankruptcy preparation** - Gather documents; confirm district; timeline for filing

2. **[ ] Coalition outreach** - Initial conversations with Debt Collective, Dignity Not Debt

3. **[ ] Technical spike: Special circumstances flow** - Build the forced review interface

4. **[ ] Documentation platform decision** - Where will the radical vulnerability narrative be published?

5. **[ ] Legal review of (c)(4) formation** - Confirm structure; incorporation timeline

---

*Document generated via PRD Discovery Process | January 3, 2026*  
*Revised with founder input on political strategy and validation methodology*  
*DigniFi: Relief Without Shame. Dignity by Design.*
