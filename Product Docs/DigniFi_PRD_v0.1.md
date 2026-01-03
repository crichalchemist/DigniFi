# DigniFi Product Requirements Document v0.1

**Document Version:** 0.1
**Date:** January 3, 2026
**Status:** Draft for Validation
**Author:** Generated via PRD Discovery Process
**Founder:** Courtney Richardson, Northwestern University

---

## Executive Summary

DigniFi is a trauma-informed digital platform designed to democratize bankruptcy relief for low-income Americans who face a system that obscures critical information behind legalese, charges prohibitive attorney fees ($1,500-3,000), and dismisses pro se filers over avoidable paperwork errors.

The platform addresses a stark reality: pro se Chapter 7 filers achieve only ~30% success rates compared to 95%+ for attorney-represented cases, while pro se Chapter 13 success rates hover near 2.3%.[^1] This disparity represents not individual failure but systemic design that punishes the under-resourced.

DigniFi's core value proposition is enabling low-income individuals to file bankruptcy successfully without an attorney by providing:
- Deterministic eligibility guidance (not legal advice)
- Auto-populated court forms with error prevention
- Plain-language explanations of legal requirements
- Trauma-informed user experience that preserves dignity

**Business Context:** Startup MVP; social impact venture; lived-experience founder; Northwestern University student; prize-funding dependent; legal clinic pilot pathway.

**Primary Constraints (in priority order):**
1. **Regulatory Compliance (UPL)** - Existential; platform must remain on the "legal information" side of the line
2. **Budget Efficiency** - Prize-funded; maximize impact per dollar; open-source tools preferred

**Validation Approach:** Single-district MVP before scaling to all 94 federal districts.

---

## Table of Contents

1. [Research Synopsis](#1-research-synopsis)
2. [MITRE-Style Problem Framing Canvas](#2-mitre-style-problem-framing-canvas)
3. [Opportunity Solution Tree](#3-opportunity-solution-tree)
4. [Proof-of-Life Experiment Plan](#4-proof-of-life-experiment-plan)
5. [Product Requirements Document](#5-product-requirements-document)
6. [Simulated Gate Reviews](#6-simulated-gate-reviews)
7. [Risks & Decisions Log](#7-risks--decisions-log)
8. [Appendix](#8-appendix)

---

## 1. Research Synopsis

### 1.1 Market & Context Snapshot

**Market Size:**
- 500,000+ Americans file bankruptcy annually[^2]
- 92% of civil legal issues among low-income Americans receive little to no legal assistance[^3]
- 29.7% of individual Chapter 7 debtors have incomes below 150% of poverty line (fee waiver eligible)[^4]

**Market Timing Factors:**
- COVID-era debt protections expired
- Household debt at historic highs
- Legal aid chronically underfunded
- Remote/hybrid court hearings now standard in all 50 states[^3]

**Racial Equity Dimension:**
- Black consumers disproportionately steered into Chapter 13 repayment even when Chapter 7 offers more immediate relief[^2]
- Bankruptcy process acts as gatekeeping mechanism favoring the resourced[^2]

### 1.2 Competing Alternatives Analysis

| Competitor | Model | Strengths | Weaknesses | DigniFi Differentiation |
|------------|-------|-----------|------------|------------------------|
| **Upsolve** | Nonprofit; free Chapter 7 tool | $700M+ debt relieved; 17,000+ users; LSC-funded; legal aid partnerships | Chapter 7 only; limited trauma-informed design; English-only | Chapter 7 AND 13; trauma-informed UX; dignity-centered framing |
| **Attorney Representation** | Fee-for-service ($1,500-3,000) | 95%+ success rate; handles complexity | Cost-prohibitive for target users; capacity-limited | Free; accessible; guided self-service |
| **Bankruptcy Mills** | Low-cost attorneys ($500-1,000) | Lower than full-service fees | Often predatory; high dismissal rates; extractive | Mission-driven; user-first; transparent |
| **Legal Aid Clinics** | Free; attorney-supervised | Professional quality; no cost | Overwhelmed; limited capacity; geographic constraints | Scales beyond clinic capacity; 24/7 access |
| **DIY/Court Forms** | Self-service; free | No cost | 70%+ failure rate; no guidance; dismissal-prone | Guided; error-preventing; completion-focused |

**Key Insight:** Upsolve is the closest analog and has proven the model works. DigniFi differentiates through Chapter 13 support (where pro se failure is highest) and trauma-informed design philosophy.

### 1.3 Regulatory & Compliance Landscape

**Unauthorized Practice of Law (UPL) Boundaries:**[^5]

| Permitted (Legal Information) | Prohibited (Legal Advice) |
|------------------------------|--------------------------|
| Explaining what the law says | Recommending specific legal actions |
| Providing general process information | Interpreting law for specific situations |
| Auto-populating forms with user data | Advising whether to file |
| Showing eligibility criteria | Predicting case outcomes |
| Linking to official court resources | Representing users in proceedings |

**Compliance Strategies for Legal Tech:**[^5]
- Require users to agree software does not provide legal advice
- Conduct regular legal audits by UPL experts
- True technological automation provides defensible position against UPL claims
- Some jurisdictions creating regulatory sandboxes for AI-driven legal services

**State Bar Considerations:**
- UPL definitions vary by state
- Illinois (Northwestern's location) has specific UPL statutes
- [ASSUMPTION] Initial pilot should select district with favorable UPL case law

### 1.4 User Synthesis

**Primary User Persona: "Maria"**
- **Demographics:** Low-income (below 150% poverty line); working multiple jobs; single parent; limited legal literacy; smartphone-primary internet access
- **Jobs-to-be-Done:**
  1. Escape crushing debt burden that prevents basic stability
  2. Understand whether bankruptcy is right for her situation
  3. Complete filing without expensive attorney
  4. Avoid dismissal from paperwork errors
  5. Maintain dignity throughout process
- **Pains:**
  - Shame and stigma around bankruptcy
  - Confusion from legal jargon
  - Fear of making mistakes that worsen situation
  - Time poverty (can't take off work for court)
  - Prior negative experiences with systems designed to exclude
- **Gains:**
  - Fresh financial start
  - Relief from wage garnishment
  - Protection of essential assets
  - Restored sense of agency
  - Knowledge to help others in community

**Secondary Personas:**

| Persona | Description | Primary Need |
|---------|-------------|--------------|
| **Legal Aid Attorney** | Overworked; wants to help more people | Tool to 10x throughput (9-10 hours to 90 minutes)[^6] |
| **Court Staff** | Processes pro se filings; sees common errors | Reduced deficient filings |
| **Credit Counselor** | Required pre-filing certification provider | Seamless referral pathway |

### 1.5 Trauma-Informed Design Principles

Based on SAMHSA's six principles adapted for digital technology:[^7]

| Principle | DigniFi Application |
|-----------|---------------------|
| **Safety** | Secure data handling; no judgmental language; clear exit paths; progress saving |
| **Trustworthiness & Transparency** | Explicit about what platform can/cannot do; visible UPL disclaimers; source citations |
| **Peer Support** | Community features; success stories (with consent); optional human touchpoints |
| **Collaboration & Mutuality** | User controls pace; no forced paths; editable inputs; review before submission |
| **Empowerment, Voice & Choice** | Plain language; multiple chapter options explained; user makes final decisions |
| **Cultural, Historical & Gender Issues** | Acknowledgment of systemic racism in bankruptcy; multilingual support [future]; culturally responsive imagery |

### 1.6 Technical Feasibility Assessment

**Validated Technical Components:**
- PDF form manipulation: Mature libraries exist (PyPDF2, pdfrw, Adobe PDF Services API)
- Decision tree engines: Standard technology (Drools, OpenL Tablets, custom Python)
- PostgreSQL + object storage: Standard stack
- RAG/LLM for guidance: Emerging but viable (with guardrails)

**Technical Risks Requiring Validation:**
1. **District Variability:** 94 federal districts with differing local rules, exemption schedules, median income thresholds[^8]
2. **Form Version Drift:** Official forms change; requires monitoring Administrative Office updates
3. **Pro Se E-Filing Constraints:** Many courts limit e-filing for pro se litigants; may generate forms but not file directly[^9]

### 1.7 Opportunity Sizing

| Metric | Conservative | Moderate | Optimistic |
|--------|--------------|----------|------------|
| **Annual US Bankruptcy Filers** | 500,000 | 500,000 | 500,000 |
| **% Who Could Benefit from Free Tool** | 30% | 40% | 50% |
| **Addressable Users Annually** | 150,000 | 200,000 | 250,000 |
| **Realistic Year 1 Reach (Single District)** | 50 | 200 | 500 |
| **Debt Relief Per User (Avg)** | $30,000 | $40,000 | $50,000 |
| **Year 1 Debt Relief Impact** | $1.5M | $8M | $25M |

---

## 2. MITRE-Style Problem Framing Canvas

### 2.1 Alternative Problem Framings Considered

**Framing A: Technology Access Problem**
> "Low-income Americans lack access to legal technology that makes bankruptcy filing feasible without an attorney."

**Framing B: Legal Literacy Problem**
> "The bankruptcy system uses language and procedures that systematically exclude people without legal training."

**Framing C: Dignity & Systemic Exclusion Problem** [SELECTED]
> "The bankruptcy system strips dignity from those seeking relief through shame-inducing design, gatekeeping through complexity, and punitive dismissals that disproportionately harm marginalized communities."

### 2.2 Selection Rationale

| Criterion | Framing A | Framing B | Framing C |
|-----------|-----------|-----------|-----------|
| Aligns with founder's lived experience | Medium | Medium | **High** |
| Differentiates from Upsolve | Low | Medium | **High** |
| Addresses root cause | Low | Medium | **High** |
| Actionable via technology | **High** | **High** | **High** |
| Resonates with target users | Medium | Medium | **High** |
| Appeals to funders/partners | Medium | Medium | **High** |

**Why Framing C Wins:** Technology and literacy are necessary but insufficient. The dignity framing captures why the system fails and why DigniFi's trauma-informed approach is essential, not just nice-to-have. It also creates clear differentiation from Upsolve's more functional positioning.

**Why Framings A & B Were Rejected:**
- Framing A reduces the problem to a tool gap, missing the systemic critique
- Framing B focuses on symptoms (complexity) rather than intent (gatekeeping)
- Neither frames justify the trauma-informed UX investment

### 2.3 Final Problem Framing Canvas

| Dimension | Description |
|-----------|-------------|
| **Mission/Outcome** | Enable dignified, successful bankruptcy filings for low-income Americans without attorney representation |
| **Stakeholders** | Pro se filers (primary); legal aid organizations; bankruptcy courts; credit counselors; community advocates; regulators |
| **Scope/Boundaries** | IN: Chapter 7 & 13 consumer bankruptcy; single pilot district initially; web-based platform. OUT: Business bankruptcy; post-discharge litigation; attorney matching; e-filing on behalf of users |
| **Operational Context** | Users under financial stress; limited time; smartphone-primary; may have trauma history with institutions; need 24/7 access; court deadlines create urgency |
| **Constraints (Tech)** | Local server MVP; open-source tools; prize-funding budget; single developer initially |
| **Constraints (Budget)** | Prize-dependent; must demonstrate ROI before scaling; no paid advertising budget |
| **Constraints (Policy)** | UPL compliance non-negotiable; PII security requirements; district-specific rules; form version currency |
| **Risks/Ethics** | User reliance leads to failed filing; platform perceived as practicing law; data breach exposes vulnerable population; racial bias in algorithmic guidance |
| **Key Assumptions** | Users can complete intake with guidance; form auto-population reduces errors significantly; legal clinic partnership is achievable; single-district MVP can demonstrate efficacy |
| **Measures of Effectiveness (MOE)** | Discharge rate for DigniFi-assisted filings vs. baseline pro se rate; Fee waiver approval rate; Time to completion; User-reported dignity score |
| **Measures of Suitability (MOS)** | Task completion rate in platform; Error rate in generated forms; User satisfaction (NPS); Legal aid partner satisfaction |
| **Decision Criteria** | Does this feature maintain UPL compliance? Does this reduce dismissal risk? Does this preserve user dignity? Does this fit budget constraints? |

---

## 3. Opportunity Solution Tree

### 3.1 Business Outcome

**North Star Metric:** Number of successful bankruptcy discharges assisted by DigniFi

**Supporting Metrics:**
- Filing completion rate (started vs. submitted)
- Dismissal rate (DigniFi-assisted vs. baseline)
- Fee waiver approval rate
- User-reported dignity/autonomy score

### 3.2 Opportunity Identification & Scoring

| ID | Opportunity | Impact (1-5) | Confidence (1-5) | Effort (1-5) | Risk (1-5) | Weighted Score* |
|----|-------------|--------------|------------------|--------------|------------|-----------------|
| O1 | Reduce form errors causing dismissals | 5 | 4 | 3 | 2 | **4.0** |
| O2 | Simplify chapter selection decision | 4 | 4 | 2 | 3 | **3.5** |
| O3 | Increase fee waiver approval rates | 4 | 3 | 2 | 2 | **3.5** |
| O4 | Provide plain-language guidance | 4 | 4 | 3 | 2 | **3.5** |
| O5 | Track deadlines to prevent missed dates | 3 | 5 | 2 | 1 | **3.25** |
| O6 | Connect to credit counseling providers | 3 | 4 | 2 | 1 | **3.0** |
| O7 | Reduce shame/anxiety during process | 4 | 3 | 4 | 2 | **2.75** |
| O8 | Enable mobile-first completion | 3 | 4 | 4 | 2 | **2.5** |

*Weighted Score = (Impact x 0.35) + (Confidence x 0.25) + ((6-Effort) x 0.20) + ((6-Risk) x 0.20)*

### 3.3 Solution Mapping

```
                    NORTH STAR: Successful Bankruptcy Discharges
                                        |
            ┌───────────────────────────┼───────────────────────────┐
            |                           |                           |
    ┌───────▼───────┐          ┌────────▼────────┐         ┌───────▼───────┐
    │ REDUCE ERRORS │          │ SIMPLIFY        │         │ PRESERVE      │
    │ (O1, O5)      │          │ DECISIONS       │         │ DIGNITY       │
    │ Score: 4.0    │          │ (O2, O3, O4)    │         │ (O7, O8)      │
    └───────┬───────┘          │ Score: 3.5      │         │ Score: 2.6    │
            |                  └────────┬────────┘         └───────┬───────┘
            |                           |                          |
    ┌───────▼───────────┐      ┌────────▼────────────┐    ┌───────▼───────────┐
    │ SOLUTIONS:        │      │ SOLUTIONS:          │    │ SOLUTIONS:        │
    │                   │      │                     │    │                   │
    │ S1: Form auto-    │      │ S4: Means test      │    │ S7: Trauma-       │
    │     population    │      │     calculator      │    │     informed UX   │
    │     with          │      │                     │    │     patterns      │
    │     validation    │      │ S5: Chapter         │    │                   │
    │                   │      │     comparison      │    │ S8: Progress      │
    │ S2: Real-time     │      │     tool            │    │     saving &      │
    │     error         │      │                     │    │     resumption    │
    │     checking      │      │ S6: Fee waiver      │    │                   │
    │                   │      │     eligibility     │    │ S9: Plain-        │
    │ S3: Deadline      │      │     screener        │    │     language      │
    │     tracking &    │      │                     │    │     throughout    │
    │     reminders     │      │ S10: Contextual     │    │                   │
    │                   │      │      guidance       │    │ S11: Mobile-      │
    └───────────────────┘      │      (RAG/curated)  │    │      responsive   │
                               └─────────────────────┘    └───────────────────┘
```

### 3.4 Prioritized Solution Backlog (MVP)

| Priority | Solution | Opportunity | MVP Scope | Rationale |
|----------|----------|-------------|-----------|-----------|
| **P0** | S1: Form auto-population with validation | O1 | Core Forms 101-106, Schedules A-J | Highest impact on dismissal reduction |
| **P0** | S4: Means test calculator | O2 | Chapter 7 qualification only | Required for chapter recommendation |
| **P0** | S6: Fee waiver eligibility screener | O3 | 150% poverty line check | Critical for target population |
| **P1** | S10: Contextual guidance | O4 | Pre-written content, no LLM | UPL-safe; manageable scope |
| **P1** | S9: Plain language throughout | O7 | All user-facing copy | Foundational to brand promise |
| **P1** | S3: Deadline tracking | O5 | Basic calendar + email reminders | Prevents procedural dismissals |
| **P2** | S5: Chapter comparison tool | O2 | Informational only; user decides | Helpful but not blocking |
| **P2** | S7: Trauma-informed UX patterns | O7 | Core flows only | Differentiator; phased implementation |
| **P3** | S8: Progress saving | O7 | Session persistence | Quality of life; not critical path |
| **P3** | S11: Mobile-responsive | O8 | Responsive web, not native app | [ASSUMPTION] Web-first acceptable for MVP |

### 3.5 Rejected Solutions & Rationale

| Solution | Why Rejected |
|----------|--------------|
| **AI chatbot for Q&A** | UPL risk too high for MVP; requires extensive guardrails; budget constraint |
| **Direct e-filing integration** | Most courts restrict pro se e-filing; last-mile problem remains |
| **Attorney matching/referral** | Outside scope; potential conflict with free tool positioning |
| **Chapter 13 plan calculator** | Complexity too high for MVP; Chapter 7 focus first |
| **Multilingual support** | Important but deferred; budget constraint; single-district pilot |

---

## 4. Proof-of-Life Experiment Plan

### 4.1 Experiment Strategies Compared

| Strategy | Speed | Cost | Confidence | Risk |
|----------|-------|------|------------|------|
| **A: Paper Prototype Testing** | Fast (2 weeks) | Low ($0-500) | Medium | Low |
| **B: Legal Clinic Partnership Pilot** | Medium (3-6 months) | Medium ($2,000-5,000) | High | Medium |
| **C: Public Beta Launch** | Slow (6+ months) | High ($10,000+) | Highest | High |

**Selected Strategy: A then B (Sequential)**

**Rationale:**
- Paper prototype (A) validates UX assumptions with minimal cost before code
- Legal clinic pilot (B) provides supervised environment for real filings
- Public beta (C) deferred until clinic validation demonstrates efficacy
- This sequence matches prize-funding timeline and budget constraints

### 4.2 Experiment 1: Paper Prototype Usability

| Element | Specification |
|---------|---------------|
| **Hypothesis** | Low-income individuals can complete bankruptcy intake using DigniFi's proposed flow with <15% abandonment rate and >80% accuracy |
| **Metrics** | Task completion rate; Error rate; Time to complete; User-reported comprehension (1-5 scale); Emotional response (dignity survey) |
| **Success Threshold** | >85% task completion; <10% critical errors; Mean comprehension >3.5; Mean dignity score >3.5 |
| **Stop Rules** | <50% completion rate; >30% critical errors; Mean dignity score <2.5 |
| **Data Needed** | 10-15 participants matching target persona; Clickable prototype (Figma); Observation notes; Post-task survey |
| **Timeline** | 2-3 weeks |
| **Owner** | Founder + 1 volunteer UX researcher [ASSUMPTION] |

### 4.3 Experiment 2: Legal Clinic Controlled Pilot

| Element | Specification |
|---------|---------------|
| **Hypothesis** | DigniFi-assisted pro se filers achieve higher discharge rates and lower dismissal rates than unassisted pro se filers in the same district |
| **Metrics** | Discharge rate; Dismissal rate; Fee waiver approval rate; Time from start to filing; Clinic staff time per case; User satisfaction |
| **Success Threshold** | Discharge rate >50% (vs. ~30% baseline); Dismissal rate <30%; Fee waiver approval >70% of eligible; Clinic time <2 hours/case |
| **Stop Rules** | Discharge rate <30%; Any UPL complaint; Any data breach; Clinic partner withdraws |
| **Data Needed** | 20-50 filers over 6 months; Baseline data from clinic's historical pro se outcomes; Court disposition records; Time tracking |
| **Timeline** | 6 months (Q2-Q3 2026 per Strategic Communication Plan) |
| **Owner** | Founder + Legal clinic partner [TO BE ESTABLISHED] |

### 4.4 Experiment 3: Single-District Public Beta

| Element | Specification |
|---------|---------------|
| **Hypothesis** | DigniFi can maintain >50% discharge rate and <5% UPL incidents at scale (100+ users) in a single district |
| **Metrics** | All Experiment 2 metrics + support volume; edge case frequency; form rejection rate by court |
| **Success Threshold** | Discharge rate >50%; Zero UPL complaints; <10% support escalations; <5% court form rejections |
| **Stop Rules** | Any UPL complaint; Discharge rate <40%; Court feedback indicating systematic issues |
| **Data Needed** | 100+ filers; Automated analytics; Support ticket tracking; Court liaison feedback |
| **Timeline** | 6-12 months post-clinic validation |
| **Owner** | Founder + expanded team [CONTINGENT ON FUNDING] |

### 4.5 Pilot District Selection Criteria

| Criterion | Weight | Notes |
|-----------|--------|-------|
| Pro se filing volume | High | Need sufficient sample size |
| Local rule complexity | Medium | Simpler rules reduce MVP scope |
| E-filing availability for pro se | Medium | Affects last-mile friction |
| Existing legal aid partnerships | High | Accelerates clinic pilot |
| Geographic accessibility to founder | Medium | Enables in-person validation |
| Favorable UPL case law | High | Reduces regulatory risk |

**[ASSUMPTION] Target Districts for Evaluation:**
- Northern District of Illinois (Chicago) - Founder proximity; legal aid presence
- Northern District of California - Established pro se programs; tech-friendly
- Eastern District of Pennsylvania - Fee waiver pilot history[^4]

---

## 5. Product Requirements Document

### 5.1 Problem Statement

Low-income Americans who need bankruptcy relief face a system that:
- Obscures critical information behind legal jargon
- Charges prohibitive attorney fees ($1,500-3,000)
- Dismisses pro se filers over avoidable paperwork errors (70%+ failure rate)
- Strips dignity through shame-inducing design and punitive procedures
- Disproportionately harms Black, Brown, disabled, and under-resourced communities

This results in failed filings, continued debt burden, wage garnishment, and psychological harm that compounds financial distress.

### 5.2 Target Users

**Primary:** Low-income individuals (below 150% of federal poverty line) seeking Chapter 7 bankruptcy relief who cannot afford attorney representation and are willing to file pro se.

**Characteristics:**
- Annual household income: <$22,590 (single) to <$46,630 (family of 4) at 150% poverty
- Primary debt: Medical, credit card, personal loans
- Technology access: Smartphone primary; may have limited broadband
- Legal literacy: Low to medium; no prior bankruptcy experience
- Emotional state: Stressed, anxious, possibly ashamed; prior negative system experiences

**Secondary:** Legal aid attorneys and paralegals seeking to increase client throughput.

### 5.3 Goals & Success Metrics

**North Star Metric:**
> Number of successful bankruptcy discharges assisted by DigniFi

**Leading Indicators:**

| Metric | Target (MVP) | Measurement |
|--------|--------------|-------------|
| Intake completion rate | >85% | Analytics: started vs. completed |
| Form accuracy rate | >95% | Clinic review; court rejection rate |
| User comprehension score | >4.0/5.0 | Post-intake survey |
| User dignity score | >4.0/5.0 | Post-intake survey |
| Time to complete intake | <90 minutes | Session analytics |

**Lagging Indicators:**

| Metric | Target (Pilot) | Measurement |
|--------|----------------|-------------|
| Discharge rate | >50% | Court records |
| Dismissal rate | <30% | Court records |
| Fee waiver approval rate | >70% of eligible | Court records |
| User NPS | >50 | Post-discharge survey |

**Guardrail Metrics (Things That Must NOT Happen):**

| Guardrail | Threshold | Response |
|-----------|-----------|----------|
| UPL complaints | Zero | Immediate feature audit; legal counsel |
| Data breaches | Zero | Incident response; user notification |
| User harm reports | <1% | Case review; feature modification |
| Court rejection rate | <10% | Form template audit |

### 5.4 Scope & Constraints

**In Scope (MVP):**
- Chapter 7 consumer bankruptcy (individual filers)
- Single federal district (TBD based on pilot selection)
- Web-based platform (responsive for mobile)
- Core intake and form generation (Forms 101-106, Schedules A-J)
- Means test calculator (Chapter 7 eligibility)
- Fee waiver eligibility screening
- Deadline tracking and reminders
- Pre-written contextual guidance
- Document checklist and upload

**Out of Scope (MVP):**
- Chapter 13 (deferred to v1.1)
- Joint filings (deferred)
- Business bankruptcy
- Direct e-filing to courts
- AI-generated guidance (RAG/LLM)
- Attorney matching or referral
- Post-discharge credit rebuilding
- Multilingual support
- Native mobile apps

**Non-Goals:**
- Practicing law or providing legal advice
- Guaranteeing outcomes
- Replacing attorney representation for complex cases
- Serving non-consumer bankruptcies

**Compliance Requirements:**
- All guidance framed as legal information, not legal advice
- Clear UPL disclaimers at decision points
- No outcome predictions or case assessments
- Audit logging of all guidance provided
- PII encryption at rest and in transit
- GLBA-aligned data handling[^10]
- User consent and data deletion capabilities

### 5.5 Chosen Approach

**Architecture:** Monolithic web application with modular services

**Stack Selection:**

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Backend | Python/Django | Rapid development; strong PDF libraries; founder familiarity [ASSUMPTION] |
| Frontend | React (or Vue) | Component reusability; trauma-informed pattern library |
| Database | PostgreSQL | Robust; free; pgvector for future RAG |
| Document Storage | Local filesystem (MVP) / S3-compatible (scale) | Cost control |
| PDF Generation | PyPDF2 + ReportLab | Open-source; form field population |
| Hosting | Local server (MVP) | Per Strategic Communication Plan |
| Email/Notifications | Mailchimp (transactional) | Already in use per Comm Plan |

**Alternatives Considered & Rejected:**

| Alternative | Why Rejected |
|-------------|--------------|
| Cloud-native (AWS/GCP) from start | Budget constraint; premature optimization |
| No-code platform (Bubble, etc.) | Limited PDF manipulation; scaling concerns |
| Native mobile app | Development cost; web-responsive sufficient for MVP |
| Microservices architecture | Over-engineering for single-developer MVP |
| Commercial PDF tools (Adobe API) | Cost; open-source adequate |

### 5.6 User Flows

**Primary Flow: Chapter 7 Filing Intake**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CHAPTER 7 FILING INTAKE                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. WELCOME & CONSENT                                                    │
│    - Platform explanation (not legal advice)                            │
│    - UPL disclaimer acknowledgment                                      │
│    - Privacy policy consent                                             │
│    - [User clicks "I Understand, Let's Begin"]                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. INITIAL SCREENER (5 min)                                             │
│    - Household size                                                     │
│    - Gross income (last 6 months)                                       │
│    - Primary debt types                                                 │
│    - Prior bankruptcy history                                           │
│    - [System calculates: Means test likely pass/fail]                   │
│    - [System calculates: Fee waiver eligibility]                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │ LIKELY ELIGIBLE   │           │ LIKELY INELIGIBLE │
        │ Continue to full  │           │ Explain options:  │
        │ intake            │           │ - Chapter 13      │
        └─────────┬─────────┘           │ - Seek attorney   │
                  │                     │ - Resources       │
                  │                     └───────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. DOCUMENT CHECKLIST                                                   │
│    - Tax returns (2 years)                                              │
│    - Pay stubs (6 months)                                               │
│    - Bank statements (6 months)                                         │
│    - Debt statements                                                    │
│    - Property valuations                                                │
│    - [User can upload or skip to enter manually]                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. DETAILED INTAKE (45-60 min, can save & resume)                       │
│    Section A: Personal Information                                      │
│    Section B: Income & Employment                                       │
│    Section C: Expenses                                                  │
│    Section D: Assets & Property                                         │
│    Section E: Debts & Creditors                                         │
│    Section F: Prior Legal Actions                                       │
│    [Each section: Plain-language prompts + contextual help]             │
│    [Real-time validation + error highlighting]                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. REVIEW & CONFIRMATION                                                │
│    - Summary of all entered information                                 │
│    - Highlighted areas needing attention                                │
│    - Final means test calculation                                       │
│    - Fee waiver recommendation (if eligible)                            │
│    - [User confirms accuracy]                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. FORM GENERATION                                                      │
│    - Auto-populate all required forms                                   │
│    - Generate filing instructions                                       │
│    - Provide deadline calendar                                          │
│    - Credit counseling requirements explained                           │
│    - [User downloads PDF package]                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. POST-GENERATION SUPPORT                                              │
│    - Filing instructions for specific court                             │
│    - Deadline reminders (341 meeting, etc.)                             │
│    - Credit counseling provider links                                   │
│    - What to expect timeline                                            │
│    - [Optional: Legal aid clinic referral if available]                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.7 Edge Cases & Failure Modes

| Edge Case | Detection | Handling |
|-----------|-----------|----------|
| User income fluctuates significantly | Variance in 6-month income entries | Prompt for explanation; flag for review |
| User has prior bankruptcy within 8 years | Prior filing question | Block Chapter 7; explain waiting period; suggest alternatives |
| User has primarily non-consumer debt | Debt type classification | Warn that means test may not apply; suggest attorney consultation |
| User's assets exceed exemption limits | Asset valuation vs. state exemptions | Flag for review; explain exemption planning is legal advice |
| User has pending litigation | Legal action questions | Warn of automatic stay implications; suggest attorney consultation |
| User is married but filing individually | Marital status + filing type | Explain community property implications (state-dependent) |
| User's creditor list is incomplete | Creditor count vs. debt total plausibility | Prompt for review; explain consequences of omission |
| Session timeout during intake | Session duration monitoring | Auto-save; recovery flow; gentle notification |
| PDF generation fails | Error handling in generation pipeline | Retry; manual form links; support escalation |
| User abandons mid-intake | Funnel analytics | Follow-up email (if consented); exit survey |

### 5.8 Accessibility Considerations

| Requirement | Implementation |
|-------------|----------------|
| Screen reader compatibility | ARIA labels; semantic HTML; alt text for all images |
| Keyboard navigation | Full tab navigation; focus indicators; skip links |
| Color contrast | WCAG 2.1 AA minimum (4.5:1 for text) |
| Reading level | Target 6th-8th grade reading level; plain language throughout |
| Mobile accessibility | Touch targets >44px; responsive layout; no horizontal scroll |
| Cognitive load reduction | Progressive disclosure; chunked sections; clear progress indicators |
| Error communication | Clear error messages; suggested corrections; no blame language |
| Time accommodations | Generous timeouts; save progress; no auto-advance |

### 5.9 Acceptance Criteria (Gherkin Format)

**Feature: Initial Screener**

```gherkin
Scenario: User passes means test screening
  Given a user has entered household size of 3
  And user has entered gross income of $45,000 annually
  And the district median income for household of 3 is $70,000
  When the system calculates means test eligibility
  Then the user should see "You likely qualify for Chapter 7"
  And the user should see an option to continue to full intake
  And the system should NOT display this as legal advice

Scenario: User does not pass means test screening
  Given a user has entered household size of 2
  And user has entered gross income of $90,000 annually
  And the district median income for household of 2 is $65,000
  When the system calculates means test eligibility
  Then the user should see "Chapter 7 may not be available based on your income"
  And the user should see explanation of Chapter 13 option
  And the user should see recommendation to consult an attorney
  And the system should NOT block the user from continuing

Scenario: User qualifies for fee waiver
  Given a user has entered household size of 1
  And user has entered gross income of $18,000 annually
  And the poverty guideline for household of 1 is $15,060
  When the system calculates fee waiver eligibility
  Then the user should see "You may qualify for a filing fee waiver"
  And the system should display the fee waiver form in generated documents
```

**Feature: Form Generation**

```gherkin
Scenario: Successful form generation
  Given a user has completed all required intake sections
  And all required fields have valid entries
  When the user clicks "Generate My Forms"
  Then the system should generate Form 101 (Voluntary Petition)
  And the system should generate Form 106A/B (Schedules A/B)
  And the system should generate Form 106C (Schedule C)
  And the system should generate Form 106D (Schedule D)
  And the system should generate Form 106E/F (Schedules E/F)
  And the system should generate Form 106I (Schedule I)
  And the system should generate Form 106J (Schedule J)
  And the system should generate Form 122A-1 (Means Test)
  And all user data should be correctly mapped to form fields
  And the user should be able to download a single PDF package

Scenario: Form generation with missing required field
  Given a user has completed intake but left "Current employer name" blank
  When the user clicks "Generate My Forms"
  Then the system should NOT generate forms
  And the user should see an error highlighting the missing field
  And the error message should be in plain language
  And the user should be guided back to complete the missing field
```

**Feature: UPL Compliance**

```gherkin
Scenario: User asks if they should file bankruptcy
  Given the user is on any intake screen
  When the user encounters guidance text
  Then the guidance should NEVER say "you should" or "we recommend"
  And the guidance should always use phrases like "the law provides" or "you may be eligible"
  And a UPL disclaimer should be visible on every page

Scenario: User completes intake
  Given a user has completed all intake sections
  When the user views their summary
  Then the system should display "This tool provides legal information, not legal advice"
  And the system should display "Consider consulting an attorney if you have questions"
  And the system should NOT display any prediction of case outcome
```

### 5.10 Data & Instrumentation

**Events to Track:**

| Event | Properties | Purpose |
|-------|------------|---------|
| `screener_started` | user_id, timestamp, referral_source | Funnel analysis |
| `screener_completed` | user_id, means_test_result, fee_waiver_eligible, duration | Eligibility patterns |
| `screener_abandoned` | user_id, last_question, duration | Drop-off analysis |
| `intake_section_started` | user_id, section_name, timestamp | Progress tracking |
| `intake_section_completed` | user_id, section_name, duration, error_count | Section difficulty |
| `intake_abandoned` | user_id, last_section, total_duration | Drop-off analysis |
| `form_generated` | user_id, forms_generated, generation_time | Success tracking |
| `form_downloaded` | user_id, download_count | Completion tracking |
| `help_text_viewed` | user_id, help_topic, duration | Content effectiveness |
| `error_displayed` | user_id, error_type, field_name | Error patterns |

**Dashboard Metrics:**

| Metric | Visualization | Refresh |
|--------|---------------|---------|
| Funnel conversion (screener to download) | Funnel chart | Real-time |
| Means test eligibility distribution | Pie chart | Daily |
| Fee waiver eligibility distribution | Pie chart | Daily |
| Average completion time by section | Bar chart | Daily |
| Error frequency by field | Heat map | Daily |
| Abandonment points | Funnel chart | Daily |

**Evaluation Metrics (Post-Filing):**

| Metric | Data Source | Collection Method |
|--------|-------------|-------------------|
| Discharge rate | Court records (PACER) | Manual lookup + user self-report |
| Dismissal rate | Court records (PACER) | Manual lookup + user self-report |
| Fee waiver approval | Court records | User self-report |
| User satisfaction | Survey | Post-filing email survey |
| Dignity score | Survey | Pre/post intake survey |

### 5.11 AI/ML Notes

**MVP Approach: No Generative AI**

For the MVP, DigniFi will use pre-written, attorney-reviewed content for all guidance rather than generative AI. This decision is driven by:

1. **UPL Risk Mitigation:** LLMs can generate outputs that cross into legal advice territory
2. **Budget Constraints:** RAG infrastructure adds cost and complexity
3. **Validation Priority:** Prove core value prop before adding AI features

**Future AI Roadmap (Post-MVP):**

| Phase | AI Feature | Prerequisites |
|-------|------------|---------------|
| v1.1 | Semantic search over help content | Clinic pilot validation; additional funding |
| v1.2 | RAG-powered contextual explanations | UPL guardrails proven; legal review process |
| v2.0 | Intelligent form assistance | Extensive training data; bias auditing |

**AI Guardrails (When Implemented):**

- All AI outputs must be framed as informational, not advisory
- Confidence scores displayed when AI-generated
- Human-in-the-loop review for edge cases
- Regular bias auditing across demographic groups
- Clear fallback to static content when AI confidence is low
- Logging of all AI interactions for audit purposes

### 5.12 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **UPL complaint or investigation** | Medium | Critical | Conservative guidance framing; legal review of all content; clear disclaimers; audit logging |
| **Data breach exposing PII** | Low | Critical | Encryption at rest/transit; minimal data retention; access controls; breach response plan |
| **Form version becomes outdated** | Medium | High | Monitoring process for Administrative Office updates; version flagging; user notification |
| **District rules change** | Medium | Medium | Single-district MVP limits exposure; monitoring process; quick update capability |
| **User files incorrectly and is harmed** | Medium | High | Clear instructions; review prompts; error checking; disclaimer that filing is user's responsibility |
| **Legal clinic partnership falls through** | Medium | Medium | Identify backup clinics; paper prototype validates independently |
| **Prize funding not secured** | Medium | High | Lean MVP scope; alternative funding research; bootstrap capability |
| **Upsolve expands to Chapter 13** | Low | Medium | Differentiate on trauma-informed UX; community focus; founder story |
| **Technical complexity exceeds founder capacity** | Medium | Medium | Modular architecture; prioritized backlog; potential technical co-founder |

### 5.13 Release Plan

**Phase 0: Foundation (Current - Q1 2026)**
- Complete PRD and technical specification
- Secure prize funding
- Build paper prototype
- Conduct Experiment 1 (usability testing)
- Establish legal clinic partnership

**Phase 1: MVP Development (Q1-Q2 2026)**
- Core intake flow (Chapter 7 only)
- Form generation (single district)
- Basic means test calculator
- Fee waiver screening
- Pre-written guidance content
- Essential analytics

**Phase 2: Clinic Pilot (Q2-Q3 2026)**
- Deploy to clinic environment
- Conduct Experiment 2 (controlled pilot)
- Iterate based on clinic feedback
- Refine form accuracy
- Build support documentation

**Phase 3: Public Beta (Q4 2026 - contingent on Phase 2 success)**
- Public availability in pilot district
- Enhanced analytics and monitoring
- Support infrastructure
- Community building

**Phase 4: Scaling (2027+)**
- Additional districts
- Chapter 13 support
- AI-powered guidance
- Mobile optimization
- Partner API

### 5.14 Open Questions & Next Decisions

| Question | Owner | Decision Deadline | Dependencies |
|----------|-------|-------------------|--------------|
| Which district for MVP pilot? | Founder | Before prototype testing | Legal clinic interest; local rule analysis |
| Legal clinic partnership: which organization? | Founder | Q1 2026 | Outreach; relationship building |
| Technical co-founder needed? | Founder | Before MVP development | Skill assessment; funding level |
| What reading level for content? | Founder + Content | Before content creation | User testing feedback |
| How to handle incomplete credit counseling? | Founder + Legal Advisor | Before intake completion | Compliance review |
| Session persistence: cookies vs. accounts? | Technical | Before development | Privacy analysis; UX research |
| Form generation: fill existing PDFs or generate from scratch? | Technical | Before development | Technical spike |
| How to verify filing outcomes? | Founder | Before pilot launch | PACER access; user consent |

---

## 6. Simulated Gate Reviews

### 6.1 Team Kickoff Review

**Attendees (Simulated):** Founder, Technical Advisor, Legal Advisor, UX Advisor

**Feedback Incorporated:**

| Stakeholder | Concern | Resolution |
|-------------|---------|------------|
| **Technical Advisor** | "Single-district MVP is wise, but how will you handle district rule updates?" | Added monitoring process to risk mitigations; documented form versioning requirement |
| **Legal Advisor** | "The means test calculator output could be seen as legal advice. How do you frame it?" | Revised acceptance criteria to use "likely qualify" vs. "you qualify"; added mandatory disclaimer language |
| **UX Advisor** | "90-minute completion target is ambitious for this population. What's your fallback?" | Added session persistence as P1 feature; progressive save after each section |
| **Founder** | "The PRD doesn't mention community ambassadors mentioned in Comm Plan." | Added future consideration for peer support features; noted in Phase 4 roadmap |

### 6.2 Planning Review

**Attendees (Simulated):** Founder, Engineering Lead (future hire/contractor), Product Advisor

**Feedback Incorporated:**

| Stakeholder | Concern | Resolution |
|-------------|---------|------------|
| **Engineering Lead** | "Form generation is the riskiest technical component. Should we de-risk earlier?" | Added technical spike for form generation to Phase 0; specified PDF library evaluation |
| **Engineering Lead** | "Local server deployment limits testing options. Can we use staging environment?" | Added cloud staging environment to scope while keeping production local |
| **Product Advisor** | "Success metrics focus on completion, but what about user emotional state?" | Added dignity score survey to leading indicators; trauma-informed UX patterns elevated to P1 |

### 6.3 Cross-Functional Kickoff

**Attendees (Simulated):** Founder, Legal Clinic Partner (prospective), Court Liaison (hypothetical), Compliance Advisor

**Feedback Incorporated:**

| Stakeholder | Concern | Resolution |
|-------------|---------|------------|
| **Legal Clinic Partner** | "Our attorneys need to review forms before clients file. Does your system support that?" | Added clinic review workflow to pilot scope; attorney dashboard consideration for v1.1 |
| **Legal Clinic Partner** | "What happens if our funding changes and we can't continue the pilot?" | Documented partnership risk; identified backup clinic candidates; ensured system works standalone |
| **Court Liaison** | "Pro se filers often bring incomplete paperwork. How does this improve that?" | Emphasized validation features; added document checklist; highlighted error prevention focus |
| **Compliance Advisor** | "You'll need a clear data retention and deletion policy before handling PII." | Added data retention policy to Phase 1 deliverables; documented GLBA alignment |

### 6.4 Solution Review

**Attendees (Simulated):** Technical Advisor, Security Consultant, Accessibility Specialist

**Feedback Incorporated:**

| Stakeholder | Concern | Resolution |
|-------------|---------|------------|
| **Technical Advisor** | "The architecture diagram shows services but you mentioned monolith. Clarify." | Updated to clarify: monolith with logical separation; microservices for scale phase |
| **Security Consultant** | "Local server hosting increases breach risk. What's your security posture?" | Added security requirements: encryption, access controls, monitoring; documented future SOC 2 consideration |
| **Accessibility Specialist** | "6th-8th grade reading level may still be too high for some users. Test it." | Added reading level testing to paper prototype validation; noted potential for lower-level version |

### 6.5 Launch Readiness Review

**Attendees (Simulated):** Founder, Legal Advisor, Operations Lead, Support Lead

**Criteria for Clinic Pilot Launch:**
- [ ] All P0 features complete and tested
- [ ] Legal review of all user-facing content
- [ ] Clinic staff trained on system
- [ ] Support documentation complete
- [ ] Analytics implemented and verified
- [ ] Incident response plan documented
- [ ] User consent and privacy flows verified
- [ ] UPL disclaimer placement audited
- [ ] Form accuracy validated against court requirements

**Feedback Incorporated:**

| Stakeholder | Concern | Resolution |
|-------------|---------|------------|
| **Legal Advisor** | "You need a process for handling user questions that cross into legal advice territory." | Added escalation protocol: acknowledge limitation, provide legal aid resources, document interaction |
| **Operations Lead** | "Who handles support during pilot? Founder alone isn't sustainable." | Documented support model: clinic staff as first line, founder escalation, FAQ documentation |
| **Support Lead** | "What's the response time SLA for pilot users?" | Defined: 24-hour response for general questions, 4-hour for blocking issues during business hours |

### 6.6 Impact Review (Post-Pilot, Simulated)

**Success Criteria for Public Beta Approval:**
- Discharge rate >50% (vs. ~30% baseline)
- Zero UPL complaints
- Zero data breaches
- User dignity score >4.0/5.0
- Clinic partner endorsement
- <10% support escalation rate

---

## 7. Risks & Decisions Log

### 7.1 Major Decisions Made

| Decision | Alternatives Considered | Selection Rationale | Date |
|----------|------------------------|---------------------|------|
| **Single-district MVP** | Multi-district from start; National launch | Budget constraint; validation priority; local rule complexity | Jan 2026 |
| **Chapter 7 only for MVP** | Chapter 7 + 13; Chapter 13 first (higher need) | Chapter 7 simpler; faster time-to-validation; Chapter 13 adds significant complexity | Jan 2026 |
| **Web app (not native mobile)** | Native iOS/Android; Progressive Web App | Development speed; budget; responsive web adequate for MVP | Jan 2026 |
| **Pre-written guidance (not AI)** | RAG-powered; LLM chatbot | UPL risk; budget; prove core value first | Jan 2026 |
| **Local server hosting (MVP)** | Cloud-native; Hybrid | Per existing Strategic Comm Plan; cost control; simplicity | Jan 2026 |
| **Legal clinic pilot pathway** | Direct-to-consumer beta; Court partnership | Supervised environment; reduced risk; validation credibility | Jan 2026 |
| **Dignity/systemic framing** | Technology access framing; Legal literacy framing | Founder alignment; differentiation; root cause focus | Jan 2026 |
| **Python/Django stack** | Node.js; No-code platform | PDF library ecosystem; rapid development; founder skills [ASSUMPTION] | Jan 2026 |

### 7.2 Decisions Deferred

| Decision | Why Deferred | Decision Trigger |
|----------|--------------|------------------|
| Specific pilot district | Need legal clinic partnership first | Clinic interest confirmed |
| Chapter 13 feature scope | MVP validation required first | Phase 2 success |
| AI/RAG implementation details | Not in MVP; budget dependent | Post-pilot funding |
| Multilingual support languages | Budget and demand dependent | User demographic data from pilot |
| Pricing/sustainability model | Mission-driven; free for MVP | Post-pilot strategy |
| Organizational structure (nonprofit vs. B-corp) | Prize funding first; can decide later | Before scaling |

### 7.3 Assumptions Log

| ID | Assumption | Risk if Wrong | Validation Method |
|----|------------|---------------|-------------------|
| A1 | Users can complete intake with guidance in <90 minutes | Lower completion rates; frustration | Paper prototype testing |
| A2 | Form auto-population significantly reduces errors | Dismissal rates remain high | Clinic pilot comparison |
| A3 | Legal clinic partnership is achievable | Slower validation; higher risk pilot | Outreach conversations |
| A4 | Single-district MVP can demonstrate efficacy | Results not generalizable | Careful district selection |
| A5 | Founder can develop MVP with limited technical support | Delayed timeline; scope cuts | Technical spike; skill assessment |
| A6 | Web-first approach is acceptable for target users | Lower adoption; mobile-only users excluded | User research |
| A7 | Pre-written content is sufficient (no AI needed for MVP) | Users need more dynamic help | Pilot feedback |
| A8 | Courts will accept DigniFi-generated forms | Technical failure; user harm | Court liaison consultation |

---

## 8. Appendix

### 8.1 Research Citations

[^1]: [NOLO - Filing Bankruptcy Without Attorney: Pro Se Guide 2025](https://www.nolo.com/legal-encyclopedia/filing-bankruptcy-without-attorney.html) - Pro se Chapter 7 success rates approximately 30%; attorney-represented cases exceed 95%.

[^2]: DigniFi Brief (internal document) - 500,000+ annual bankruptcy filings; racial disparities in Chapter 13 steering; 90% Chapter 13 plan failure rate.

[^3]: [Legal Services Corporation - 2024 Innovations in Technology Conference](https://www.lsc.gov/events/2024-innovations-technology-conference) - 92% of civil legal issues among low-income Americans receive little to no assistance.

[^4]: [American Bankruptcy Institute - Impact of Fee-Waiver Provision](https://www.abi.org/abi-journal/the-impact-of-the-coming-fee-waiver-provision) - 29.7% of Chapter 7 debtors below 150% poverty line; fee waiver pilot program data.

[^5]: [Above the Law - UPL Risk Mitigation Strategies for Legal Tech](https://abovethelaw.com/2024/01/unauthorized-practice-of-law-risk-mitigation-strategies-for-legal-tech-entrepreneurs/) - Compliance strategies; legal information vs. legal advice distinction.

[^6]: [Legal Services Corporation - Upsolve for Legal Aid Organizations](https://www.lsc.gov/i-am-grantee/model-practices-innovations/technology/legal-aid-organizations-upsolve-offers-way-do-bankruptcies-10-times-faster-and-help-more-people) - Upsolve reduces bankruptcy assistance time from 9-10 hours to 90 minutes.

[^7]: [PMC - Trauma-Informed Care Principles in Design and Technology](https://pmc.ncbi.nlm.nih.gov/articles/PMC12304634/) - SAMHSA's six trauma-informed principles applied to digital design.

[^8]: [Cornell Law - Federal Rules of Bankruptcy Procedure Rule 9029](https://www.law.cornell.edu/rules/frbp/rule_9029) - District court authority to make local rules; variation across 94 districts.

[^9]: DigniFi Technical Architecture (internal document) - CM/ECF e-filing constraints for pro se litigants.

[^10]: [FTC - Gramm-Leach-Bliley Act Compliance](https://www.ftc.gov/business-guidance/resources/how-comply-privacy-consumer-financial-information-rule-gramm-leach-bliley-act) - PII protection requirements for financial information.

### 8.2 Glossary

| Term | Definition |
|------|------------|
| **Chapter 7** | Bankruptcy liquidation; debts discharged; assets may be sold |
| **Chapter 13** | Bankruptcy reorganization; 3-5 year repayment plan |
| **Discharge** | Court order releasing debtor from personal liability for debts |
| **Dismissal** | Case thrown out; no discharge; may refile with waiting period |
| **Fee Waiver** | Court waiver of $338 filing fee for those below 150% poverty |
| **IFP** | In Forma Pauperis; legal term for fee waiver eligibility |
| **Means Test** | Income test determining Chapter 7 eligibility |
| **Pro Se** | Self-represented; without attorney |
| **341 Meeting** | Meeting of creditors; debtor answers questions under oath |
| **UPL** | Unauthorized Practice of Law |
| **CM/ECF** | Case Management/Electronic Case Filing (court system) |
| **PACER** | Public Access to Court Electronic Records |
| **RAG** | Retrieval-Augmented Generation (AI technique) |

### 8.3 Form Reference

**Core Official Bankruptcy Forms (MVP Scope):**

| Form | Name | Purpose |
|------|------|---------|
| 101 | Voluntary Petition for Individuals Filing for Bankruptcy | Initial filing; basic debtor information |
| 106A/B | Schedule A/B: Property | Real and personal property listing |
| 106C | Schedule C: The Property You Claim as Exempt | Exemption claims |
| 106D | Schedule D: Creditors Who Hold Claims Secured by Property | Secured debts |
| 106E/F | Schedule E/F: Creditors Who Have Unsecured Claims | Priority and general unsecured debts |
| 106G | Schedule G: Executory Contracts and Unexpired Leases | Ongoing contracts |
| 106H | Schedule H: Your Codebtors | Co-signers |
| 106I | Schedule I: Your Income | Current income |
| 106J | Schedule J: Your Expenses | Current expenses |
| 106J-2 | Schedule J-2: Expenses for Separate Household | If applicable |
| 107 | Statement of Financial Affairs | Financial history |
| 108 | Statement of Intention | Plans for secured property |
| 119 | Bankruptcy Petition Preparer's Notice, Declaration, and Signature | If preparer used |
| 121 | Statement About Your Social Security Numbers | SSN verification |
| 122A-1 | Chapter 7 Statement of Your Current Monthly Income | Means test Part 1 |
| 122A-2 | Chapter 7 Means Test Calculation | Means test Part 2 (if required) |

### 8.4 District Selection Criteria Matrix

| District | Pro Se Volume | Rule Complexity | E-Filing Access | Legal Aid Partners | Founder Access | UPL Climate | Score |
|----------|---------------|-----------------|-----------------|-------------------|----------------|-------------|-------|
| N.D. Illinois | High | Medium | Limited | Multiple | High | Moderate | TBD |
| N.D. California | High | Medium | Good | Multiple | Low | Favorable | TBD |
| E.D. Pennsylvania | Medium | Medium | Limited | Strong | Low | Favorable | TBD |
| [To be completed with research] | | | | | | | |

### 8.5 Competitive Feature Matrix

| Feature | DigniFi (MVP) | Upsolve | DIY/Forms | Attorney |
|---------|---------------|---------|-----------|----------|
| Chapter 7 support | Yes | Yes | Yes | Yes |
| Chapter 13 support | No (v1.1) | No | Yes | Yes |
| Means test calculator | Yes | Yes | No | Yes |
| Fee waiver screening | Yes | Yes | No | Yes |
| Form auto-population | Yes | Yes | No | Yes |
| Plain-language guidance | Yes | Yes | No | Varies |
| Trauma-informed UX | Yes | Limited | No | Varies |
| Deadline tracking | Yes | Limited | No | Yes |
| Legal advice | No | No | No | Yes |
| E-filing | No | No | No | Yes |
| Cost | Free | Free | Free | $1,500-3,000 |
| Success rate (estimated) | TBD | ~30%+ | ~30% | ~95% |

---

## What to Validate Next

1. **[ ] Paper Prototype Usability Test** - Validate intake flow with 10-15 target users; measure completion, comprehension, and dignity scores

2. **[ ] Legal Clinic Partnership Outreach** - Initiate conversations with 3-5 legal aid organizations; assess pilot interest and requirements

3. **[ ] Pilot District Legal Analysis** - Research UPL case law and local rules for top 3 candidate districts; select primary and backup

4. **[ ] Technical Spike: Form Generation** - Build proof-of-concept PDF population for Form 101 using selected library; validate accuracy

5. **[ ] Content Reading Level Audit** - Test all draft guidance content against readability tools; iterate to 6th-8th grade level

---

## Final Question

**Ready to dive deeper into implementation details, or start building experiments?**

Options to explore next:
- **Technical Specification:** Detailed data models, API contracts, infrastructure setup
- **Experiment Design:** Detailed protocol for paper prototype testing
- **Content Strategy:** Plain-language guidance content for each intake section
- **Partnership Playbook:** Legal clinic outreach approach and pilot agreement template
- **Compliance Checklist:** Detailed UPL audit criteria and review process

---

*Document generated via PRD Discovery Process | January 3, 2026*
*DigniFi: Relief Without Shame. Dignity by Design.*
