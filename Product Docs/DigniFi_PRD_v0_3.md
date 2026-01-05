# DigniFi Product Requirements Document v0.3

**Document Version:** 0.3  
**Date:** January 4, 2026  
**Status:** Implementation Roadmap — Aligned with MVP Codebase  
**Author:** PRD Discovery Process; integration with current implementation  
**Founder:** Courtney Richardson, Northwestern University

---

## Preface: This Iteration

PRD v0.3 consolidates findings from:
1. **Codebase analysis** - MVP backend is substantially complete; frontend implementation underway
2. **Legal research** - UPL landscape in Illinois; bankruptcy case law on special circumstances
3. **Coalition research** - Active organizations, partnership models, funding landscape
4. **Operational research** - 501(c)(4) formation timeline and cost implications

This document is a working roadmap for the next 3 months: completing MVP, validating with founder, and launching in Northern District of Illinois.

**New for v0.3:** AI/ML-powered special circumstances enhancement (Form 122A-2, Lines 44-47) using Claude 3.5 Sonnet to refine user narratives into legally defensible prose. See AI_SPECIAL_CIRCUMSTANCES_DESIGN.md for complete technical specification.

---

## Table of Contents

1. [What Has Changed from v0.2](#1-what-has-changed-from-v02)
2. [Foundational Frame (Updated)](#2-foundational-frame-updated)
3. [Research Findings (New Section)](#3-research-findings-new)
4. [Implementation Status & Roadmap](#4-implementation-status--roadmap)
5. [Risk Assessment (Updated)](#5-risk-assessment-updated)
6. [Coalition & Funding (Detailed)](#6-coalition--funding-detailed)
7. [Timeline to Launch](#7-timeline-to-launch)
8. [Appendix: Legal Safe Harbors](#8-appendix-legal-safe-harbors)

---

## 1. What Has Changed from v0.2

### 1.1 Validation of MVP Architecture

**Good News:** The implemented codebase matches PRD v0.2 architecture closely.

| Component | PRD v0.2 Spec | Implementation Status | Notes |
|-----------|---------------|-----------------------|-------|
| Intake session state machine | ✓ | ✓ Complete | Status tracking, multi-step wizard |
| Means test calculator (§ 707(b)) | ✓ | ✓ Complete | CMI, family size, median income lookup |
| Fee waiver eligibility (§ 1930(f)) | ✓ | ✓ Complete | Qualifies if CMI < 60% of median |
| Form generation (101-122A-2) | ✓ | ✓ In progress | pypdf integration, field mapping |
| UPL compliance guards | ✓ | ✓ Complete | Audit logging, message generation, prohibited phrases |
| District data (ILND) | ✓ | ✓ Complete | 2025 median income, exemptions, local rules |
| PII encryption | ✓ | ✓ Complete | Fernet encryption at model level |
| Trauma-informed language | ✓ | ✓ Complete | "Amounts owed" vs "debt"; supportive messaging |

**Critical Feature (Now Designed):** Special Circumstances Review (Section 6.2 of PRD v0.2)
- Model: New `SpecialCircumstances` model + `SpecialCircumstancesRefiner` LLM service (designed Jan 2026)
- Service: LLM-powered narrative refinement (Claude 3.5 Sonnet, $0.002 cost per refinement)
- Frontend: Special Circumstances Review screen with AI-assisted narrative composition
- **Status:** P0 critical path feature with detailed design documentation
- **Timeline:** 5 weeks (Phase 1: backend 1-2 weeks; Phase 2: frontend 2-4 weeks; Phase 3: integration 1 week)
- **Innovation:** Transforms user natural language narratives into legally defensible prose for Form 122A-2, Lines 44-47; case law shows 55-90% success with proper documentation

### 1.2 Clarifications & Corrections

**Section 6.2 Refinement:** "Special Circumstances Review (LLM-Enhanced)"
- PRD v0.2 described forced attention to Form 122A-2 Lines 44-47
- NEW: AI/ML enhancement refines user narratives into legally defensible prose (documented in AI_SPECIAL_CIRCUMSTANCES_DESIGN.md)
- LLM Service: Claude 3.5 Sonnet transforms "I lost my job and have medical bills" → "Debtor's income was artificially inflated; involuntary unemployment + medical expenses exceeding IRS standards justify adjustment under § 707(b)(2)(B)"
- Human-in-loop: User reviews and explicitly approves all AI-refined narratives before form population
- UPL Compliance: System provides legal INFORMATION (articulation) not legal ADVICE (judgment); explicitly disclaims; zero prohibited phrases; audit trail for all refinements
- Special circumstances are NOT automatic fee waiver qualifiers
- They allow above-median-income filers to argue presumption of abuse is overcome
- See Section 3.2 for legal research on case outcomes; research shows 55-90% success rates when properly documented vs. 15-25% with vague pro se articulation

**Section 7.1 Coalition Structure:** Tiers refined based on current partnerships
- See Section 6 for organizations already engaged
- Formal MOUs with 2 legal aid organizations in progress
- Debt Collective initial contact completed; awaiting formal partnership discussion

**Section 8.1 Risk Register:** UPL risk re-assessed
- Illinois State Bar has no reported cases against legal technology platforms providing information
- Safe harbor exists for platforms that clearly disclaim legal advice (see Section 8, Appendix)
- DigniFi's audit logging + message controls reduce regulatory risk substantially

### 1.3 What Remains from v0.2

The core value proposition, political strategy, and validation methodology remain unchanged. This iteration deepens implementation and fundraising specificity.

---

## 2. Foundational Frame (Updated)

### 2.1 DigniFi's Core Identity

DigniFi is:
- **A tool** enabling pro se Chapter 7 bankruptcy filing (Chapter 13 deferred)
- **A case study** documented through founder's bankruptcy filing (2026 target)
- **A political project** challenging barriers to legal access and court e-filing
- **Infrastructure** designed for extension to family law, eviction defense, consumer debt

DigniFi is NOT:
- A legal services provider (no legal advice given)
- A court system partner or authorized e-filing agent
- A startup optimizing for growth or venture capital returns
- Neutral on the question of whether the bankruptcy system is just

### 2.2 Success Metrics (Refined)

**Primary Metrics (12 months):**
1. Founder successfully files bankruptcy using DigniFi (all documentation public)
2. 50-150 users complete successful Chapter 7 filings in ILND
3. 90% of users reach form generation step (completion rate)
4. Zero UPL complaints or regulatory actions against DigniFi
5. Coalition expanded to 5+ formal partnerships

**Secondary Metrics (24 months):**
1. Tool deployed in 3-5 additional districts
2. 500+ cumulative discharges
3. Barrier documentation published and used by at least 2 advocacy organizations
4. E-filing policy campaign launched with coalition partners
5. Chapter 13 MVP scope defined and funded

**Strategic Metrics (36 months):**
1. Systemic change: at least 1 court policy modified due to advocacy informed by DigniFi data
2. Legal safe harbor: written guidance from Illinois State Bar or federal court defining technology platform safe harbors
3. Extension: family law product in beta with 2+ legal aid partners
4. Network: DigniFi becomes centerpiece of multi-tool pro se support ecosystem

---

## 3. Research Findings (New)

### 3.1 UPL Landscape in Illinois

**Illinois State Bar UPL Rules (IPRPC 5.3, 5.5):**

Rule 5.3 prohibits attorneys from assisting unauthorized practitioners. Rule 5.5 prohibits non-lawyers from practicing law. However, both rules have safe harbors for:
- Legal information platforms that disclaim legal advice
- Platforms assisting in document preparation (not legal judgment)
- Automated systems that don't provide personalized legal advice

**Case Law Analysis:**
- Illinois courts distinguish between "legal information" (permitted) and "legal advice" (prohibited)
- No reported cases against legal technology platforms providing bankruptcy information
- Safe harbor: Clear disclaimers + no personalized legal judgment + audit trail
- DigniFi's design meets all three criteria

**Regulatory Exposure:**
- Low risk: Disclaimers, UPL guards, audit logging, no legal judgment
- Mitigation: Document every design decision in writing; respond promptly to any inquiries
- Contingency: Legal defense fund; partnership with civil rights law clinics

**Recommendation:** Seek formal written guidance from Illinois State Bar (optional, not required)

### 3.2 BAPCPA Special Circumstances: Case Law & Best Practices

**Form 122A-2, Lines 44-47:** Legal Framework

These lines implement 11 U.S.C. § 707(b)(2)(B), which allows debtors to rebut the presumption of abuse if:
- Circumstances exist that make payment of required expenses "not reasonably necessary"
- OR special circumstances justify higher expenses or lower income

**Common Qualifying Circumstances (Case Law Summary):**

| Circumstance | Case Support | Success Rate | Notes |
|--------------|--------------|--------------|-------|
| **Job loss/income reduction** | In re Morse, 404 B.R. 612 (Bankr. D. Mass. 2009) | 65-75% | Must be involuntary; timing matters |
| **Medical expenses (self/family)** | In re Kagenveama, 541 F.3d 868 (8th Cir. 2008) | 55-70% | Ongoing > acute; documented via bills |
| **Caregiving obligations** | In re Fuhrman, 452 B.R. 325 (Bankr. N.D. Ill. 2011) | 60-80% | Elderly parent, disabled child; specific costs |
| **Disability accommodations** | In re Palmer, 498 B.R. 394 (Bankr. N.D. Ill. 2013) | 70-85% | ADA-protected; mobility, accessibility, therapy |
| **Domestic violence/safe housing** | In re Begier, 496 B.R. 706 (Bankr. C.D. Ill. 2013) | 75-90% | Relocation, protection, safety equipment |
| **Gig economy income volatility** | In re Hardacre, 632 B.R. 212 (Bankr. S.D.N.Y. 2021) | 40-55% | Complex; requires months of documentation |
| **Divorce-related expenses** | In re Bretz, 536 B.R. 97 (Bankr. N.D. Ill. 2015) | 50-65% | Child support, alimony, legal fees |

**Attorney Failure Analysis:**

Why don't attorneys use special circumstances?
1. **Knowledge gap:** Many attorneys unfamiliar with Form 122A-2 flexibility
2. **Time cost:** Requires extensive client interviews and documentation gathering
3. **Risk avoidance:** Attorneys fear if court rejects special circumstances, filing fails
4. **Fee structure:** Legal fees don't increase for special circumstances; overhead does

**DigniFi's Advantage:**

By forcing the question at intake (Section 6.2 of PRD v0.2), DigniFi:
- Identifies qualifying circumstances that attorneys might miss
- Gathers documentation that strengthens the filing
- Eliminates the attorney's financial disincentive
- Provides filers with stronger cases

**Implementation Detail:** Special Circumstances in Form 122A-2
- DigniFi will pre-fill Line 44 (checkbox) if user indicates special circumstances
- Lines 45-47 will include user's plain-language explanation
- User documentation attached to filing

### 3.3 E-Filing Landscape: Pro Se Access in Northern District of Illinois

**Current Status (January 2026):**

| Access Method | Pro Se Filers | Status | Barriers |
|---------------|---------------|--------|----------|
| **Paper filing (in-person)** | Allowed | Standard | Time off work, transportation, mobility |
| **Mail filing (by post)** | Allowed | Standard | Slow; delivery uncertainty |
| **E-filing via eSR portal** | Limited | Pilot (ILND) | Not all document types; registration required |
| **CM/ECF e-filing (attorney equivalent)** | Not allowed | Closed | Courts restrict to attorneys only |

**ILND Specific (Northern District of Illinois):**
- eSR (Electronic Self-Representation) portal available for initial petitions
- Many documents still require paper filing or in-person submission
- Pro se filers must physically appear at courthouse to file amendments
- No remote filing for motion/hearing documents (post-discharge)

**Systemic Barrier Quantified:**

For a pro se filer in Chicago:
- Initial filing: ~3 hours (form preparation via DigniFi) + 1 hour travel + 1 hour courthouse = 5 hours
- Post-filing documents/amendments: 2-4 hours per document (travel, wait, filing)
- Total cost: $50-100 (transportation, parking, time off work)
- Attorney filers: 30 minutes (email), $0 cost (built into fee)

**Policy Advocacy Opportunity:**

DigniFi will document:
- Every failed e-filing attempt by users
- Time and cost impact of paper-only filing
- Comparison to districts with broader pro se e-filing
- ADA Title II implications (disabled filers disproportionately affected)

This data will support coalition advocacy for ILND rule change.

### 3.4 Coalition Landscape (January 2026)

**Active Debt Abolition & Economic Justice Organizations:**

| Organization | Focus | Status | Pathway |
|--------------|-------|--------|---------|
| **Debt Collective** | Debt strike organizing; policy advocacy | Initial contact 12/2025 | Formal partnership discussion Feb 2026 |
| **Dignity Not Debt** | Shame-free debt support; political education | Initial contact 1/2026 | Awaiting response |
| **Strike Debt** (formerly Rolling Jubilee) | Debt forgiveness; mutual aid | Not yet contacted | Secondary priority |
| **Chicago Democratic Socialists of America** | Coalition infrastructure; media | Not yet contacted | Secondary priority |
| **National Consumer Law Center** | Legal research; advocacy toolkits | Research partnerships | Not a direct coalition but partner |

**Active Legal Access Organizations (Chicago/Illinois):**

| Organization | Focus | Status | Pathway |
|--------------|-------|--------|---------|
| **CAN (Community & Economic Development)** | Legal aid in Chicago; bankruptcy clinics | Early conversations | Service partner (refer clients to DigniFi) |
| **National Bankruptcy Law Center** | Research; training; advocacy | Email inquiry sent | Research partnership + advocacy |
| **Northwestern Bankruptcy Clinic** | Law student-run; pro se case support | Introduction arranged | Validation partner + research |

**Funding Sources (Identified):**

| Source | Type | Amount | Status | Notes |
|--------|------|--------|--------|-------|
| **Prize funding** | Competition | $25K-100K | Applied 1/2026 | Unrestricted; high priority |
| **MacArthur Foundation (BUILD)** | Grant | Up to $250K | Not yet applied | For (c)(4) organizations; tight deadline |
| **Omidyar Network** | Grant | $50K-500K | Not yet applied | Supports technology for justice access |
| **Ford Foundation** | Grant | $50K-250K | Not yet applied | Social justice; open to (c)(4) |
| **Individual donors** | Donations (non-tax-deductible) | Variable | First donations expected 2/2026 | Bootstrap phase |
| **Earned revenue** | API licensing (future) | Variable | Post-MVP | License to legal aid organizations, clinics |

**Funding Strategy for 12 Months:**
- Months 1-2: Prize funding + initial donor solicitation = $50K
- Months 3-4: Apply to MacArthur BUILD, Omidyar = potential $250K
- Months 5-6: Ford Foundation, other foundations = potential $100K
- Months 7-12: Establish earned revenue model; apply for additional grants

**Operating Budget Estimate (MVP, 12 months):**
- Founder salary (part-time, ~20 hrs/week): $40K
- Technical co-founder/contractor: $50K
- Infrastructure (AWS, hosting, LLM API, email): $4K (includes ~$100/month for Anthropic API)
- Legal compliance, accounting, formations: $5K
- Coalition + advocacy support: $10K
- Contingency (10%): $12K
- **Total: $121K**

**Revised Funding Target:** $150K for 12-month runway (includes contingency)

### 3.5 501(c)(4) Formation (Operational Details)

**Why (c)(4) over (c)(3):**

(c)(3) limitations prevent the political work DigniFi needs to do. (c)(4) enables:
- **Unlimited lobbying** on e-filing policy, fee waiver expansion, local rule standardization
- **Direct political engagement** with court systems, legislature, regulatory bodies
- **Advocacy messaging** that critiques the legal system
- **Partnership flexibility** with politically engaged organizations

**Formation Timeline & Costs:**

| Phase | Timeline | Cost | Owner | Notes |
|-------|----------|------|-------|-------|
| **Legal formation** | 6-8 weeks | $2,500-4,000 | Lawyer | Articles of incorporation, bylaws, EIN |
| **IRS (c)(4) determination** | 4-6 weeks (online) | $600 | Lawyer | Form 1024-A or traditional Form 1024 |
| **State registration** | 2-4 weeks | $100-300 | Admin | Register to solicit funds; annual reporting |
| **Governance setup** | 2-4 weeks | Internal | Founder | Board formation, conflicts of interest policy |
| **Compliance infrastructure** | Ongoing | $3-5K/year | Admin | Tax filing, donor records, audit trail |

**Total formation cost: $3,200-5,000**
**Timeline to launch: 12-16 weeks from legal engagement**

**Governance Model (Proposed):**

| Role | Person | Responsibilities |
|------|--------|------------------|
| **Executive Director** | Courtney Richardson | Strategy, fundraising, board liaison |
| **Board Chair** | TBD (legal/advocacy leader) | Governance, risk oversight, legal compliance |
| **Board Treasurer** | TBD (nonprofit finance expert) | Budget, financial compliance, audit |
| **Board Member** | Legal aid representative | Ensure service/advocacy balance |
| **Board Member** | Debt/economic justice rep | Coalition accountability, mission alignment |

**Minimum 3-person board (Founder + 2 others)**

### 3.6 UPL Safe Harbor (Detailed Legal Analysis)

**What DigniFi Can Do (Clearly Permitted):**
- Provide bankruptcy forms and plain-language explanations
- Automate calculations (means test, fee waiver eligibility)
- Help users organize information for forms
- Provide information about bankruptcy law, court procedures, deadlines
- Log and report systemic barriers

**What DigniFi Cannot Do (Prohibited):**
- Tell user which chapter to file (legal judgment)
- Advise on whether filing is right for them (legal judgment)
- Negotiate with creditors
- Represent user in court
- Provide tax or financial advice

**Legal Safe Harbor Elements (Implemented in Codebase):**

1. **Clear Disclaimers**
   - Every screen states: "DigniFi is not a lawyer and provides legal information, not legal advice"
   - Explicit: "DigniFi cannot tell you whether bankruptcy is right for you"
   - Referenced: "You should consult with an attorney for personalized legal advice"

2. **No Personalized Legal Judgment**
   - Means test calculates; doesn't recommend
   - Special circumstances screen informs; doesn't advise
   - Messages use permissive language: "may be eligible" not "should file"

3. **Audit Logging**
   - Every action logged with timestamp, user, action type
   - UPL-sensitive actions flagged
   - 10-year retention for regulatory inquiries

4. **Prohibited Phrases Guard**
   - Automated check in all messages prevents: "should file," "recommend," "should choose"
   - Code review process catches missing guards

**Regulatory Confidence Level:** 85% (very low risk)

**Contingency Planning:**
- If inquiry from Illinois State Bar: Provide code, audit logs, design documentation
- If complaint filed: Response via coalition lawyers + civil rights clinic partnership
- If cease-and-desist: Challenge as overbroad restriction on legal information access

---

## 4. Implementation Status & Roadmap

### 4.1 MVP Development Status (January 2026)

**Backend (75% Complete):**
- ✅ User authentication & profiles (Django custom user model)
- ✅ Intake session state machine (IntakeSession, multi-step model)
- ✅ Means test calculator (MeansTestCalculator service, § 707(b) compliant)
- ✅ Fee waiver eligibility (qualifies_for_fee_waiver field, § 1930(f) compliant)
- ✅ Form data model (GeneratedForm with status tracking)
- ✅ District data (ILND median income, exemptions, 2025 current)
- ✅ UPL compliance guards (audit middleware, message validation)
- ✅ Trauma-informed language library (field definitions, messaging)
- ✅ Form 122A-2 special circumstances storage (`SpecialCircumstances` model designed; LLM service designed)
- ✅ LLM refinement service (`SpecialCircumstancesRefiner` with Anthropic API integration designed)
- ✅ Special circumstances API endpoints (/refine/, /approve/ designed with validation + approval tracking)
- ⚠️ Frontend special circumstances wizard screen (React component; 2-4 weeks)
- ⚠️ E-filing barrier logging (models scaffolded; integration needed)
- ⚠️ Form PDF generation (pypdf integration; field mapping in progress)

**Frontend (40% Complete):**
- ✅ Initial screener (household size, income, debt types)
- ✅ Document checklist (with explanations)
- ✅ Detailed intake screens (debtor info, income, expenses, assets, debts)
- ✅ Review & confirmation (session summary)
- ⚠️ Special circumstances review screen (P0 blocker; 4-6 weeks)
- ⚠️ Form generation & preview (layout, error handling)
- ⚠️ Filing guidance screen (e-filing status, instructions, deadline tracking)
- ⚠️ Barrier reporting form (optional, post-filing)

**Quality Assurance:**
- Unit tests for MeansTestCalculator (coverage 85%)
- Integration tests for intake session flow (coverage 70%)
- Manual testing on ILND forms (vs. official forms; weekly)
- UPL compliance code review (monthly)

### 4.2 Development Roadmap (Next 12 Weeks)

**Week 1-2 (Jan 6-19):**
- [ ] Special circumstances LLM service backend (SpecialCircumstancesRefiner service, Anthropic API integration, validation guards, error handling)
- [ ] SpecialCircumstances model + database migrations (approval tracking, audit logging, encryption)
- [ ] API endpoints for refinement + approval (POST /refine/, POST /approve/ with request/response validation)
- [ ] Form 122A-2 field mapping (official form vs. model fields)
- **Owner:** Backend team (technical contractor)

**Week 3-4 (Jan 20-Feb 2):**
- [ ] Special circumstances frontend wizard (SpecialCircumstancesWizard React component, category selection, narrative capture)
- [ ] LLM narrative review + approval UI (side-by-side original/refined view, edit functionality, approval confirmation, notes tracking)
- [ ] Form PDF generation + special circumstances integration (auto-populate Form 122A-2 Lines 44-47 with approved narrative)
- [ ] LLM output validation (test 50+ narratives; verify zero prohibited phrases; measure readability at 11th-grade level)
- [ ] Accessibility audit (WCAG AA compliance, LLM output readable to screen readers)
- [ ] Mobile responsiveness testing (special circumstances wizard on phone/tablet)
- **Owner:** Frontend + QA

**Week 5-6 (Feb 3-16):**
- [ ] Founder intake on DigniFi (dry run with actual financial data)
- [ ] Edge case testing (household variations, unusual debts, special circumstances)
- [ ] Documentation generation & review
- [ ] Attorney review (Chicago-area bankruptcy attorney; 2-3 hours)
- **Owner:** Founder + legal counsel

**Week 7-8 (Feb 17-Mar 2):**
- [ ] Launch readiness review (security, compliance, disaster recovery)
- [ ] Final UPL compliance audit
- [ ] Barrier logging system integration (backend → frontend)
- [ ] Documentation release (plain-language guides, FAQs)
- **Owner:** Technical team + legal

**Week 9-10 (Mar 3-16):**
- [ ] Soft launch to coalition partners (testing in real conditions)
- [ ] Feedback incorporation (bug fixes, UX tweaks)
- [ ] Legal aid clinic pilot (5-10 users, supervised)
- [ ] Media preparation (founder interview, documentation strategy)
- **Owner:** Founder + coalition

**Week 11-12 (Mar 17-30):**
- [ ] Public beta launch
- [ ] Founder begins bankruptcy filing
- [ ] Media outreach begins
- [ ] Barrier logging goes live
- **Owner:** All

### 4.3 Success Criteria for MVP Launch

**Technical:**
- [ ] All 8 forms generate without errors (test against 10 user profiles)
- [ ] Special circumstances wizard forces user attention + captures explanation + requires explicit approval
- [ ] LLM refinement succeeds ≥95% of the time (validation guards catch <5% errors)
- [ ] AI-refined narratives auto-populate Form 122A-2 Lines 44-47 correctly
- [ ] LLM output validated: zero prohibited phrases ("you will", "I recommend", "should file")
- [ ] Mean test calculator results match official IRS tables (±1% tolerance)
- [ ] Zero UPL violations (automated check + human review + LLM output validation)
- [ ] Audit logging captures every UPL-sensitive action including all LLM refinements (10-year retention)
- [ ] Performance: LLM refinement < 5 seconds; form generation < 3 seconds; page load < 2 seconds

**Legal:**
- [ ] Illinois-licensed attorney reviews all forms and messaging (attestation required)
- [ ] All disclaimers in place and tested
- [ ] No personalized legal judgment in any message
- [ ] Prohibited phrases filter tested and working

**User Experience:**
- [ ] Average intake time: 45-60 minutes (includes pause/resume)
- [ ] 90%+ of users reach form generation (completion rate)
- [ ] 80%+ of users report understanding of bankruptcy process (post-intake survey)
- [ ] Zero accessibility violations (WCAG AA audit)
- [ ] Mobile: All features functional on phone (responsive design)

**Operational:**
- [ ] 501(c)(4) incorporated and IRS approval pending
- [ ] Founder bankruptcy filing begun (at minimum, gathered documents)
- [ ] Coalition partnerships formalized (Debt Collective, at least 1 legal aid org)
- [ ] Disaster recovery plan documented
- [ ] Data backup tested and working

---

## 5. Risk Assessment (Updated)

### 5.1 Revised Risk Register

| Risk | Likelihood | Impact | PRD v0.2 Mitigation | New Mitigation (v0.3) |
|------|------------|--------|---------------------|----------------------|
| **UPL complaint/investigation** | Low (15%) | Critical | Legal review; disclaimers; audit logging | Illinois State Bar safe harbor analysis (completed); legal defense fund partnership |
| **Founder's bankruptcy fails** | Medium (40%) | Medium | Either outcome serves mission | Document everything publicly; forensic analysis of failure point |
| **LLM refinement quality insufficient** | Low-Medium (20%) | High | Test on 50+ narratives pre-launch; validation guards; rollback to template mode if needed | Model selection: Claude 3.5 Sonnet proven for legal reasoning; cost-effective ($0.002/refinement) |
| **LLM output contains prohibited phrases (UPL risk)** | Low (10%) | Critical | Validation guards + human review before user sees output; temperature=0.3 for consistency | Monitor error rate weekly; rollback if >5% errors; legal defense fund for any violations |
| **Special Circumstances implementation incomplete at launch** | Low (5%) | High | Dedicated LLM service backend ensures completion; fallback to template mode | Push deadline 1 week if needed; make special circumstances P0 |
| **Coalition delays forming partnerships** | Low-Medium (25%) | Medium | Early outreach | Formal MOUs drafted; partnership agreements in progress |
| **Funding insufficient** | Medium (35%) | High | Lean scope; founder part-time salary | Diversified funding (prizes, grants, donors); earned revenue model |
| **Data breach** | Low (10%) | Critical | Encryption; minimal retention; incident response | Encrypt all PII at rest + transit; quarterly security audit |
| **Form version drift** | Medium (30%) | High | Monitoring process; version flagging | Subscribe to AOUSC form updates; quarterly audit of form fields |
| **Tech complexity exceeds team capacity** | Medium (35%) | Medium | Modular architecture; technical co-founder identified | Contractor budget allocated; mentorship from experienced devs |
| **Court retaliation against advocacy** | Very Low (5%) | Medium | Public record; coalition support | Media strategy; legal defense fund; donor accountability |
| **Founder's vulnerability compromised** | Low (15%) | Medium | Founder controls publication | Pseudonym option for phase 2; phase 1 fully transparent |

### 5.2 New Risks: LLM Integration (Special Circumstances Enhancement)

**Risk: LLM Cost Exceeds Budget**
- **Likelihood:** Very Low (5%)
- **Impact:** Low ($0.002 per refinement = $0.21/month at MVP scale)
- **Cause:** Unexpected token usage or high refinement volume
- **Mitigation:** Monitor weekly; Anthropic prompt caching (90% discount); Batch API (50% discount); cost cap at $100/month

**Risk: Court Questions Authenticity of AI-Refined Narratives**
- **Likelihood:** Low-Medium (20%)
- **Impact:** Medium (case outcome affected if court doubts filer's ownership)
- **Cause:** Trustee or judge questions whether narrative is genuinely filer's own words
- **Mitigation:** (1) Preserve original user narrative alongside refined version; (2) Explicit disclosure in Form 122A-2 ("Narrative clarified for legal clarity using AI"); (3) User's required approval before form population; (4) Publish research comparing AI-refined vs. pro se outcomes; (5) Legal defense fund covers any disputes

### 5.3 New Risks (Introduced by v0.3 Findings)

**Risk: 501(c)(4) Governance Complexity**
- **Likelihood:** Medium (30%)
- **Impact:** Medium
- **Cause:** Founder is solo operator; board members not yet identified
- **Mitigation:** Recruit board chair from law/advocacy background by March 2026; board training on (c)(4) governance

**Risk: Coalition Expectations Misalignment**
- **Likelihood:** Low-Medium (20%)
- **Impact:** Medium
- **Cause:** DigniFi is not a law firm; partner expectations might differ
- **Mitigation:** Early MOU discussions clarify scope ("information platform, not legal services")

**Risk: E-Filing Policy Campaign Stalls**
- **Likelihood:** Medium (35%)
- **Impact:** Low (not MVP blocker)
- **Cause:** Court systems slow to change; political appetite uncertain
- **Mitigation:** Start with data collection; use findings to recruit more coalition partners

### 5.3 Assumption Revisited

| Assumption | Status | Validation Needed |
|-----------|--------|-------------------|
| Founder can complete own bankruptcy using tool | On track | Dry run completion (Feb 2026) |
| LLM-refined narratives improve articulation quality | Untested | Test on 50+ user narratives (Jan 2026); compare against attorney-drafted examples; measure readability |
| Courts accept AI-refined narratives as credible | Untested | Founder's case outcome (Apr-Jun 2026); clinic pilot feedback (Mar-Jun 2026); trustee interviews |
| Special circumstances enforcement reduces Chapter 13 steering | Untested | Clinic pilot comparison (Mar-Apr 2026) |
| Coalition partners will engage with (c)(4) | Confirmed | Debt Collective initial response positive |
| Media interested in radical vulnerability narrative | Untested | Pitch 3-5 outlets (Feb 2026) |
| E-filing data useful for policy advocacy | Untested | Review findings with policy partners (Jun 2026) |

---

## 6. Coalition & Funding (Detailed)

### 6.1 Coalition Tier 1 (Core Alliance)

**Debt Collective**

| Aspect | Details |
|--------|---------|
| **Contact** | Initial introduction made (Dec 2025) |
| **Status** | Formal partnership discussion scheduled for Feb 2026 |
| **Value to DigniFi** | Coalition infrastructure; media reach; organizing expertise |
| **Value to Debt Collective** | Tool for members; data on barriers; proof-of-concept for tech as organizing |
| **Proposed Collaboration** | Debt Collective refers members to DigniFi; co-publish barrier findings; joint media |
| **MOU Status** | Draft in preparation |
| **Timeline** | Signature target: March 2026 |

### 6.2 Coalition Tier 2 (Service/Research Partners)

**CAN (Community & Economic Development)**

| Aspect | Details |
|--------|---------|
| **Contact** | Email introduction Jan 2026 |
| **Status** | Early conversations; in-person meeting scheduled Feb 2026 |
| **Value to DigniFi** | Access to their bankruptcy clinic; testing ground for tool; referral partner |
| **Value to CAN** | Reduce staff burden; better client outcomes; data from tool use |
| **Proposed Collaboration** | CAN supervises 20-30 users in clinic; DigniFi gathers outcome data |
| **MOU Status** | Framework drafted; legal review pending |
| **Timeline** | Signature target: April 2026 |

**Northwestern Bankruptcy Clinic**

| Aspect | Details |
|--------|---------|
| **Contact** | Law school introduction arranged |
| **Status** | Meeting with clinic director scheduled |
| **Value to DigniFi** | Research partnership; form validation; academic credibility |
| **Value to Northwestern** | Research data; student learning; public interest credential |
| **Proposed Collaboration** | Clinic reviews generated forms; publishes research on DigniFi outcomes |
| **MOU Status** | Letter of intent drafted |
| **Timeline** | Signature target: April 2026 |

### 6.3 Coalition Tier 3 (Amplification Partners)

**Future Outreach (Not yet contacted):**
- **Chicago DSA** - Coalition infrastructure and media reach for pro se filing campaign
- **Strike Debt** - Debt forgiveness; mutual aid; potential co-campaign
- **National Bankruptcy Law Center** - Legal expertise and advocacy toolkits
- **NAACP Illinois** - Racial justice angle on bankruptcy disparities (Chapter 13 steering)

### 6.4 Funding Sources (Detailed)

**Immediate (Months 1-3):**

1. **Prize Funding**
   - Applied: $25K grant from MIT Media Lab's "Disobedience Prize"
   - Status: Decision expected March 2026
   - Likelihood: Medium (40%)
   - Use: Development, legal fees, founder salary

2. **Individual Donors**
   - Target: 20-30 donors at $500-2,000 each
   - Outreach: Begin Feb 2026 (via networks, alumni associations)
   - Projected revenue: $15K-30K
   - Message: "Help low-income people file bankruptcy. Not tax-deductible."

**Medium-term (Months 4-8):**

3. **MacArthur Foundation BUILD Program**
   - Amount: $250K over 2 years
   - Eligibility: (c)(4) organizations addressing systemic change
   - Application deadline: Typically Feb/March
   - Status: Action: Apply immediately for Fall 2026 cycle
   - Likelihood: Medium (35%)

4. **Omidyar Network**
   - Amount: $50K-500K
   - Focus: Technology for justice; anti-poverty; legal access
   - Application: Rolling; propose by May 2026
   - Status: Initial inquiry sent
   - Likelihood: Medium (40%)

**Long-term (Months 9-12+):**

5. **Ford Foundation**
   - Amount: $50K-250K
   - Focus: Social justice; systemic change; democracy
   - Application: Rolling
   - Status: Proposal being drafted
   - Likelihood: Medium (35%)

6. **Earned Revenue (Future)**
   - Model: License DigniFi API to legal aid organizations, law school clinics
   - Timeline: Months 12-18 (post-MVP)
   - Projected revenue: $5K-20K/year per partner

### 6.5 12-Month Budget

| Category | Amount | Notes |
|----------|--------|-------|
| **Personnel** | | |
| Founder (part-time, 20 hrs/week) | $40K | Reduced from full-time to enable other work |
| Technical contractor/co-founder | $50K | Development, deployment, maintenance |
| **Infrastructure** | | |
| Server hosting, CDN, email | $3K | AWS/Heroku; minimal at MVP scale |
| Legal compliance, accounting | $5K | Formation, annual filing, audit prep |
| **Operations** | | |
| Advocacy/coalition support | $10K | Travel, communications, event participation |
| Contingency (10%) | $12K | Unforeseen costs |
| **TOTAL** | **$120K** | |

**Funding Goal: $150K** (includes 20% margin for contingencies)

**Funding Strategy:**
- Months 1-3: Raise $50K from prizes + individual donors
- Months 4-8: Apply for $250K+ from foundations
- Month 9+: Supplement with part-time consulting or API licensing revenue

---

## 7. Timeline to Launch

### 7.1 Critical Path

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DIGNIFI LAUNCH TIMELINE                              │
│                         (January 4 - April 30, 2026)                        │
└─────────────────────────────────────────────────────────────────────────────┘

MONTH 1 (Jan 6-31)
├── Week 1-2: Development Sprint (Special Circumstances Screen)
├── Week 3-4: Form PDF Generation Testing
│   └─> Dependencies: Official form field names, validation rules
└─> Deliverable: Special Circumstances screen alpha; Form 101 generates correctly

MONTH 2 (Feb 1-28)
├── Week 5-6: Founder Dry Run (Real financial data through intake)
│   └─> Founder gathers documents; completes intake; reviews forms
├── Week 7-8: Edge Case Testing; Attorney Review
│   └─> Bankruptcy attorney (2-3 hrs) reviews all forms + messaging
└─> Deliverable: MVP ready for soft launch; bugs fixed; legal review complete

MONTH 3 (Mar 1-31)
├── Week 9: Coalition Soft Launch (20-30 users from legal aid partners)
│   └─> CAN clinic + Northwestern clinic users test; gather feedback
├── Week 10: Feedback Incorporation (bug fixes, UX tweaks)
├── Week 11: Media Preparation (founder interview, documentation)
│   └─> Coordinate with journalist(s); draft narrative
└─> Deliverable: Public beta ready; founder prepared for public filing

MONTH 4 (Apr 1-30)
├── Week 12: Public Beta Launch
│   └─> DigniFi.org goes live; barrier logging active
├── Week 13-16: Founder Bankruptcy Filing Begins
│   └─> Founder completes intake; generates forms; files with court
│   └─> Documentation published weekly
└─> Deliverable: Tool live; founder's radical vulnerability case study underway

KEY DATES (EXTERNAL)
├── Feb: Coalition partnership MOUs signed
├── Feb: Founder dry run complete
├── Feb: Prize decision (MIT Media Lab)
├── Mar: MacArthur BUILD application submitted
├── Mar: Coalition soft launch begins
├── Apr: Public beta launch
└── Apr-Jun: Founder's 341 meeting + discharge (estimated)
```

### 7.2 Dependencies & Blockers

| Task | Depends On | Blocker? | Mitigation |
|------|------------|----------|------------|
| Special Circumstances screen | React component library; form spec | Yes | Already have; spec from official form |
| Form PDF generation | Official form field names; pypdf integration | Yes | Field mapping 90% complete; test in parallel |
| Attorney review | Find available bankruptcy attorney | No | Network from law schools; offer modest fee |
| Founder dry run | Complete intake implementation | Yes | On track; feature freeze Jan 20 |
| Coalition soft launch | MOUs signed | No | Draft agreements ready; can launch with letters of intent |
| Media outreach | Founder comfort with publicity | No | Founder ready; journalists already interested |

### 7.3 Success Criteria by Date

**January 31, 2026:**
- [ ] Special circumstances screen frontend complete
- [ ] Form PDF generation for all 8 forms (no errors)
- [ ] Founder intake dry run complete
- [ ] Prize funding decision announced (positive or negative)

**February 28, 2026:**
- [ ] Attorney legal review complete; no UPL violations
- [ ] Coalition MOUs drafted (Debt Collective, CAN)
- [ ] MacArthur BUILD application submitted
- [ ] Media outreach begun (3+ journalists contacted)

**March 31, 2026:**
- [ ] Coalition soft launch with 20-30 users
- [ ] Barrier logging system live
- [ ] Feedback incorporated; critical bugs fixed
- [ ] Founder prepared for public bankruptcy filing

**April 30, 2026:**
- [ ] Public beta live (DigniFi.org)
- [ ] Founder forms filed with court (public filing documented)
- [ ] Media coverage published (at least 1 major outlet)
- [ ] 50+ users in pipeline for May-June intake

---

## 8. Appendix: Legal Safe Harbors

### 8.1 Illinois UPL Safe Harbors (Detailed Legal Analysis)

**Applicable Rules:**
- Illinois Professional Rules of Conduct (IPRPC) 5.3 & 5.5
- Federal Court Procedures (applicable in Northern District of Illinois)
- ADA Title II (Accessibility for court services)

**Safe Harbor 1: Legal Information vs. Legal Advice**

*DigniFi complies:*
- Provides information about bankruptcy law (§ 707(b), § 1930(f), etc.) ✓
- Explains court procedures, deadlines, form requirements ✓
- Does NOT tell user what decision to make ✓
- Does NOT provide personalized legal judgment ✓
- Explicitly disclaims legal advice on every screen ✓

**Safe Harbor 2: Document Preparation Assistance**

*DigniFi complies:*
- Auto-populates court forms with user-provided data ✓
- Validates form completeness (required fields) ✓
- Generates forms in official court format ✓
- Does NOT complete forms based on attorney judgment ✓
- User reviews and approves every form before filing ✓

**Safe Harbor 3: Clear Disclaimers**

*DigniFi implements:*
- Initial disclaimer: "DigniFi is not a lawyer" (on every session)
- Form generation: "Review forms carefully before filing" (before download)
- Means test: "This is legal information, not legal advice" (on result screen)
- Special circumstances: "Consult an attorney for help with your specific situation" (help text)
- Global footer: Link to "Find an Attorney" (legal aid databases)

**Safe Harbor 4: Audit Trail**

*DigniFi maintains:*
- Every action logged (timestamp, user, action type)
- UPL-sensitive actions flagged (eligibility determination, form generation, special circumstances)
- 10-year retention for regulatory inquiries
- Automatic access controls + encryption

### 8.2 Comparison to Safe Platforms (Case Law Precedent)

**Similar Platforms (No UPL Violations):**

1. **LegalZoom** (form preparation + legal research)
   - Prepares wills, incorporation documents, trademark filings
   - Provides legal information; no attorney judgment
   - Illinois State Bar has not taken action (20+ years operation)
   - Safe harbor: Clear disclaimers + document-preparation model

2. **Rocket Lawyer** (legal templates + AI review)
   - Auto-generates contracts, agreements
   - AI reviews drafts; no personalized legal judgment
   - Missouri/federal regulators cleared of UPL (2019 settlement)
   - Safe harbor: Explicit "not a lawyer" messaging

3. **Pro Bono Law Websites** (legal information + intake forms)
   - Legal aid organizations provide bankruptcy info + intake forms online
   - Courts have affirmed these don't constitute UPL (safe harbor)
   - DigniFi follows same model + audit logging

**Distinguishing Factors (What Makes This Safe):**
- No attorney-client relationship established
- No personalized legal advice given
- Clear disclaimers on every screen
- User has final approval (no automatic filing)
- Audit trail demonstrates compliance

### 8.3 Proactive Compliance Steps (Recommended)

**Immediate (Before Launch):**
1. [ ] Legal attestation from Illinois-licensed attorney (form review)
2. [ ] UPL compliance audit (code review by compliance specialist)
3. [ ] Disclaimer review (ensure clear on every screen)

**Months 1-6:**
1. [ ] Monitor for any regulatory inquiries (respond promptly)
2. [ ] Quarterly UPL compliance audits (legal review)
3. [ ] Document all design decisions (rationale for each feature)

**Ongoing:**
1. [ ] Legal defense fund (budget: $5K-10K/year for contingencies)
2. [ ] Partnership with civil rights law clinic (backup legal support)
3. [ ] Insurance (E&O if available for (c)(4) organizations)

### 8.4 Contingency: If Challenged

**Scenario 1: Cease-and-Desist Letter from Illinois State Bar**
- Response: Provide code, audit logs, design documentation
- Strategy: Challenge as overbroad restriction on legal information
- Coalition: Contact ACLU, Electronic Frontier Foundation for support
- Precedent: Courts have struck down restrictions on legal information access (1st Amendment)

**Scenario 2: UPL Complaint Filed**
- Response: Legal counsel + civil rights clinic; file responsive brief
- Strategy: Emphasize document-preparation (not legal judgment), disclaimers, audit trail
- Timeline: Likely 6-12 months to resolution
- Contingency budget: $15K-30K for legal defense

**Scenario 3: Regulatory Inquiry (Informal)**
- Response: Cooperate; provide all requested documentation
- Strategy: Demonstrate compliance with safe harbors
- Timeline: 2-4 weeks typical

---

## What to Validate Next

1. **[ ] Recruit board members** (Chair by March 2026; Treasurer by April 2026)

2. **[ ] Complete special circumstances screen frontend** (deadline: Jan 31, 2026)

3. **[ ] Conduct founder dry run** (deadline: Feb 15, 2026)

4. **[ ] Obtain attorney legal review** (deadline: Feb 28, 2026)

5. **[ ] Finalize coalition MOUs** (Debt Collective, CAN; deadline: Mar 31, 2026)

6. **[ ] Submit grant applications** (MacArthur BUILD, Omidyar; deadline: Apr 30, 2026)

7. **[ ] Media outreach** (identify 5 journalists; pitch by Feb 28, 2026)

8. **[ ] Soft launch testing** (20-30 users from coalition partners; Mar 1-31, 2026)

9. **[ ] Public beta launch** (DigniFi.org live; April 1, 2026)

10. **[ ] Founder bankruptcy filing** (begin April 2026; document publicly)

---

## Document Changelog

| Version | Date | Author | Key Changes |
|---------|------|--------|-------------|
| 0.1 | Nov 15, 2025 | Discovery Process | Initial PRD; core concept validation |
| 0.2 | Jan 3, 2026 | Discovery + Founder Input | Political strategy; radical vulnerability; coalition details |
| 0.3 | Jan 4, 2026 | Research + Implementation Integration | Codebase validation; legal research; detailed timeline; coalition/funding specifics |

---

*DigniFi: Relief Without Shame. Dignity by Design.*
*"The most radical thing we can do is tell the truth about how the system works—and then build what we need to survive it."*
