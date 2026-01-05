# DigniFi UX/UI Research Document

**Document Version:** 1.0  
**Date:** January 4, 2026  
**Author:** UX Research Team  
**Status:** Comprehensive Analysis

---

## Executive Summary

This document presents comprehensive UX/UI research for DigniFi, a trauma-informed bankruptcy filing platform designed to enable low-income Americans to file Chapter 7 bankruptcy without an attorney. The research synthesizes product requirements, user population characteristics, accessibility needs, and design principles into actionable personas and design recommendations.

### Key Insights

1. **Target Population Demographics**: DigniFi serves users experiencing acute financial crisis—a population characterized by high stress, potential cognitive load impairment, and often limited digital literacy. Design must accommodate these constraints.

2. **Trauma-Informed Design is Non-Negotiable**: Users approach this platform in states of shame, fear, and overwhelm. Every UX decision must preserve dignity and reduce anxiety rather than compound it.

3. **Accessibility as Core Requirement**: 26% of U.S. adults have disabilities, with higher prevalence in low-income populations. The platform must exceed WCAG 2.1 AA standards.

4. **Trust Deficit**: Users have likely experienced failures from attorneys, courts, and financial systems. Building trust through transparency, clear communication, and consistent reliability is essential.

5. **Forced Attention Design Pattern**: The platform's unique value proposition—forcing review of BAPCPA special circumstances—must be implemented as a supportive experience, not a barrier.

---

## 1. Research Methodology

### 1.1 Data Sources Analyzed

| Source Type | Description | Confidence Level |
|-------------|-------------|------------------|
| **Product Documentation** | PRD v0.2, Technical Architecture, README | High |
| **Industry Research** | Bankruptcy outcome disparities, pro se success rates | High |
| **Demographic Data** | Census data, legal aid statistics, disability prevalence | High |
| **Comparable Product Analysis** | Upsolve, legal aid clinics, court self-help portals | Medium |
| **Existing Implementation** | Current React components, design system | High |
| **Inferred User Patterns** | Based on similar crisis-service applications | Medium-Low (requires validation) |

### 1.2 Research Limitations

- No direct user interviews conducted (recommended for validation)
- Limited quantitative data on current user behavior
- Assumptions about technology access based on demographic patterns
- Chapter 13 user patterns not yet researched (deferred to v1.1)

---

## 2. User Personas

### 2.1 Persona Summary Cards

| Persona | Age | Income | Key Goal | Primary Device | Tech Comfort |
|---------|-----|--------|----------|----------------|--------------|
| **Maria Santos** | 42 | $28,000/year | Discharge medical debt | Smartphone | ⭐⭐☆☆☆ (2/5) |
| **Darnell Washington** | 35 | $34,000/year | Fresh start after job loss | Desktop (library) | ⭐⭐⭐☆☆ (3/5) |
| **Linda Kowalski** | 58 | $22,000/year | Protect disability benefits | Tablet | ⭐⭐☆☆☆ (2/5) |
| **Carlos Mendoza** | 29 | $31,000/year | End creditor harassment | Smartphone | ⭐⭐⭐⭐☆ (4/5) |
| **Sarah Mitchell** | 47 | $41,000/year | File after divorce | Laptop | ⭐⭐⭐☆☆ (3/5) |

---

### 2.2 Detailed Persona Profiles

---

## PERSONA 1: Maria Santos

### Profile Overview

**Name:** Maria Santos  
**Age:** 42  
**Location:** Cicero, Illinois (Chicago suburb)  
**Occupation:** Home healthcare aide  
**Household:** Single mother, two children (ages 12 and 17)  
**Income:** $28,000/year (below 150% federal poverty level)  
**Education:** High school diploma, some community college  

**Background Narrative:**  
Maria immigrated to the U.S. at age 8 and has worked continuously since age 16. She was managing financially until her gallbladder surgery two years ago. Despite having insurance through her employer, the $18,000 in out-of-pocket costs—combined with lost wages during recovery—created a debt spiral she cannot escape. She's been avoiding phone calls from collectors, and the stress is affecting her sleep and her relationship with her teenagers. Her pastor mentioned that filing bankruptcy might help, but she's afraid of "failing" and worries about what it means for her kids' futures.

### Goals & Motivations

- **Primary Goal:** Discharge medical debt so collectors stop calling
- **Secondary Goal:** Protect her car (essential for work) and modest savings
- **Long-term Goal:** Rebuild credit to eventually buy a small condo
- **Emotional Goal:** Stop feeling shame about her financial situation

**What Success Looks Like:**  
Maria receives her discharge letter, collectors stop contacting her, and she can focus on her children and her work without the constant anxiety of debt.

### Pain Points & Frustrations

| Pain Point | Emotional Response | Current Workaround |
|------------|-------------------|-------------------|
| **Collector calls** | Anxiety, shame, avoidance | Doesn't answer unknown numbers; affecting work |
| **Confusion about bankruptcy** | Fear of "ruining" her life | Paralysis; delayed action for 18 months |
| **Attorney costs** | Hopelessness | Consulted one attorney, couldn't afford $1,500 fee |
| **Complex legal language** | Overwhelm, inadequacy | Stopped reading court documents she found online |
| **Technology barriers** | Frustration | Relies on daughter for help with forms |

> **Signature Quote:**  
> *"I've worked my whole life. I'm not lazy. I just got sick at the wrong time, and now I can't see a way out. I don't want my kids to think their mom is a failure."*

### Behaviors & Patterns

**How She Currently Solves Problems:**
- Asks family and church community for advice
- Uses Google Translate for English legal terms
- Prefers phone calls over email for important matters
- Pays bills in person or through her banking app

**Decision-Making Process:**
- Seeks social proof (who else has done this?)
- Needs reassurance that decisions are reversible or safe
- Values personal connection and empathy over efficiency
- Distrusts institutions that have failed her before

**Information Consumption:**
- Reads content in small chunks; long documents overwhelm her
- Prefers video explanations to text
- Often returns to the same content multiple times before acting

### Technology & Communication

| Dimension | Detail |
|-----------|--------|
| **Primary Device** | Samsung Galaxy A32 (3-year-old model, small screen) |
| **Secondary Device** | Rarely uses desktop; borrows daughter's laptop for forms |
| **Internet Access** | Mobile data (5GB/month); WiFi at work and church |
| **Digital Literacy** | Comfortable with WhatsApp, Facebook, banking app |
| **Challenges** | PDF forms don't work well on phone; small text hard to read |
| **Preferred Communication** | Text message reminders, phone calls for complex issues |

### Usage Scenarios

**Scenario 1: First Encounter**  
Maria finds DigniFi through a Google search at 11 PM after a particularly stressful collector call. She starts the intake process on her phone but stops after 10 minutes because she doesn't have her tax documents handy. She needs a way to save progress and return later.

**Scenario 2: Special Circumstances**  
When DigniFi prompts her about special circumstances (medical expenses), Maria realizes for the first time that her situation might qualify her for relief even with her income. She feels seen and understood—this is the moment she commits to completing the process.

**Scenario 3: Document Gathering**  
Maria needs to upload pay stubs but doesn't know how to download PDFs from her employer's portal. She takes photos with her phone. The system needs to accept and help her work with photo uploads.

### Design Implications

| Category | Recommendation |
|----------|----------------|
| **Reading Level** | All content at 6th-grade reading level or below |
| **Mobile Experience** | Mobile-first design is critical; responsive isn't enough |
| **Save/Resume** | Prominent save functionality with SMS confirmation |
| **Special Circumstances** | Emphasize this section; it's her path to relief |
| **Photo Upload** | Accept camera photos; provide cropping/enhancement tools |
| **Progress Visibility** | Clear indication of time remaining and completion status |
| **Error Messages** | Never shame; always offer clear next steps |
| **Language Support** | Spanish translation is priority for MVP+1 |

---

## PERSONA 2: Darnell Washington

### Profile Overview

**Name:** Darnell Washington  
**Age:** 35  
**Location:** South Side Chicago, Illinois  
**Occupation:** Unemployed (formerly warehouse supervisor)  
**Household:** Single, lives with elderly mother (caregiver)  
**Income:** $34,000/year (unemployment + gig work)  
**Education:** Associate degree in logistics  

**Background Narrative:**  
Darnell was laid off from his warehouse supervisor position eight months ago when his company automated operations. He's been piecing together income through DoorDash and helping at his cousin's moving company, but it's not enough. His credit card debt ($23,000) and car loan (now underwater) are crushing him. He tried working with a debt consolidation company that turned out to be predatory, taking $800 before he realized they weren't helping. He's skeptical of "free" services after that experience but knows he needs a real solution. He uses the public library's computers for most online tasks.

### Goals & Motivations

- **Primary Goal:** Get a clean slate to find stable employment without debt hanging over him
- **Secondary Goal:** Protect his car (needs it for gig work and to drive his mother to medical appointments)
- **Long-term Goal:** Return to logistics management once he has financial stability
- **Emotional Goal:** Prove to himself that he can recover from this setback

**What Success Looks Like:**  
Darnell completes his bankruptcy filing, gets his discharge, and can list his fresh start on job applications without the anxiety of debt affecting his credit checks.

### Pain Points & Frustrations

| Pain Point | Emotional Response | Current Workaround |
|------------|-------------------|-------------------|
| **Previous scam experience** | Deep distrust of "help" services | Verifies everything; slows decision-making |
| **Gig income variability** | Uncertainty, frustration | Tracks everything meticulously in spreadsheet |
| **Library computer limitations** | Embarrassment, inconvenience | Rushes through tasks; can't save locally |
| **Being steered to Chapter 13** | Skepticism (knows this is worse for him) | Researched online; wants to avoid |
| **Racial bias concerns** | Vigilance, exhaustion | Documents everything; assumes worst-case |

> **Signature Quote:**  
> *"I did everything right—went to school, worked hard, took care of my mama—and I'm still here. I'm not trusting anybody who says they're 'here to help' unless I can verify it myself."*

### Behaviors & Patterns

**How He Currently Solves Problems:**
- Extensive research before making decisions
- Tracks finances obsessively in Google Sheets
- Asks specific, detailed questions when seeking help
- Prefers written documentation to verbal promises

**Decision-Making Process:**
- Analytical and methodical
- Needs to understand the "why" behind each step
- Values transparency about risks and limitations
- Will walk away at the first sign of manipulation

**Information Consumption:**
- Reads legal documents carefully
- Cross-references information across multiple sources
- Prefers text to video (faster to skim)
- Takes notes and screenshots

### Technology & Communication

| Dimension | Detail |
|-----------|--------|
| **Primary Device** | Library desktop computers |
| **Secondary Device** | Older iPhone (8 Plus) with limited storage |
| **Internet Access** | Library WiFi; mobile data is limited |
| **Digital Literacy** | Comfortable with spreadsheets, PDF forms, basic research |
| **Challenges** | Can't save files locally at library; 30-minute session limits |
| **Preferred Communication** | Email (checks daily at library) |

### Usage Scenarios

**Scenario 1: Trust Building**  
Darnell reads the UPL disclaimer carefully and notices the 501(c)(4) structure. He researches DigniFi before entering any information. He needs to see the founder's story and understand why this is free before proceeding.

**Scenario 2: Session Management**  
At the library, Darnell has 30 minutes per session. He needs to complete the income section in one session, then return tomorrow for expenses. The platform must save progress reliably and allow him to resume exactly where he left off.

**Scenario 3: Means Test Verification**  
Darnell's income is above median due to last year's employment (even though he's now unemployed). He needs to understand how special circumstances (job loss) affect his eligibility and verify this independently before trusting the platform's calculation.

### Design Implications

| Category | Recommendation |
|----------|----------------|
| **Transparency** | Prominent "Why is this free?" section; visible founder story |
| **UPL Clarity** | Explain the legal information vs. advice distinction clearly |
| **Session Management** | Auto-save every field; clear session timeout warnings |
| **Means Test Explanation** | Show calculation breakdown; explain special circumstances |
| **Time Estimates** | Accurate per-section time estimates for library users |
| **PDF Downloads** | Allow form preview/download at any stage for offline review |
| **Data Export** | Provide downloadable summary of all entered information |
| **Email Reminders** | Robust email-based resume links (his primary touchpoint) |

---

## PERSONA 3: Linda Kowalski

### Profile Overview

**Name:** Linda Kowalski  
**Age:** 58  
**Location:** Rockford, Illinois  
**Occupation:** Disabled (formerly factory worker, now on SSDI)  
**Household:** Widowed, lives alone with cat  
**Income:** $22,000/year (SSDI + small survivor's pension)  
**Education:** GED  

**Background Narrative:**  
Linda worked in manufacturing for 28 years before a repetitive strain injury made work impossible. She's been on SSDI for six years. Her husband passed away three years ago, leaving her with his medical debts (she didn't realize she was a co-signer). The debt collectors are aggressive, even though most of her income is protected from garnishment. She doesn't fully understand her rights and fears that filing bankruptcy might affect her SSDI. She has arthritis in her hands and moderate vision impairment, making standard web forms challenging.

### Goals & Motivations

- **Primary Goal:** Stop harassment from collectors about her late husband's medical debts
- **Secondary Goal:** Confirm that her SSDI and pension are protected
- **Long-term Goal:** Live peacefully without financial stress in her remaining years
- **Emotional Goal:** Honor her husband's memory without being crushed by his debts

**What Success Looks Like:**  
Linda receives confirmation that her SSDI is protected, files her bankruptcy without complications, and can focus on her health and her memories without collector calls.

### Pain Points & Frustrations

| Pain Point | Emotional Response | Current Workaround |
|------------|-------------------|-------------------|
| **Vision impairment** | Frustration, fatigue | Uses tablet's accessibility features; magnification |
| **Hand arthritis** | Physical pain during long forms | Takes frequent breaks; avoids typing when possible |
| **Fear about SSDI** | Anxiety, protectiveness | Called Social Security (no clear answer); still worried |
| **Aggressive collectors** | Fear, grief | Keeps phone unplugged some days |
| **Technology overwhelm** | Shame about needing help | Asks neighbor's teenager for help |

> **Signature Quote:**  
> *"My husband was sick for two years before he passed. We did everything we could. I shouldn't have to spend the rest of my life paying for the privilege of watching him die."*

### Behaviors & Patterns

**How She Currently Solves Problems:**
- Calls helplines rather than using websites
- Asks community members (church, neighbors) for referrals
- Takes physical notes in a notebook
- Needs to re-read instructions multiple times

**Decision-Making Process:**
- Cautious and slow-moving
- Needs explicit reassurance about safety
- Values personal connection over efficiency
- Will abandon process if it feels risky to her benefits

**Information Consumption:**
- Prefers large text and high contrast
- Can't read PDFs without zooming significantly
- Watches videos only if they have captions
- Needs summaries—can't process dense information

### Technology & Communication

| Dimension | Detail |
|-----------|--------|
| **Primary Device** | iPad (used with accessibility features) |
| **Secondary Device** | Landline phone |
| **Internet Access** | Home WiFi (basic plan, reliable) |
| **Digital Literacy** | Limited; uses email and Facebook with difficulty |
| **Challenges** | Small touch targets; vision impairment; hand pain |
| **Preferred Communication** | Phone call (prefers human voice); voicemail okay |

### Usage Scenarios

**Scenario 1: Accessibility Check**  
Linda opens DigniFi on her iPad with magnification enabled. If text doesn't scale properly or buttons are too close together, she'll abandon the platform immediately and try to find a phone number to call instead.

**Scenario 2: Benefit Protection Anxiety**  
When asked about income sources, Linda needs explicit reassurance that SSDI is protected in bankruptcy. Without this, she'll stop mid-form to research elsewhere, likely losing her progress and trust.

**Scenario 3: Document Upload Challenge**  
Linda has her Social Security statements as PDFs in her email. She doesn't know how to download them to her iPad and then upload them to DigniFi. She needs step-by-step guidance or the ability to forward documents via email.

### Design Implications

| Category | Recommendation |
|----------|----------------|
| **Accessibility** | WCAG 2.1 AAA for contrast; 200% zoom support; large touch targets (44x44px minimum) |
| **Text Size** | Base font 18px minimum; user-adjustable |
| **Form Design** | Voice input option; larger fields; autocomplete where possible |
| **SSDI Reassurance** | Dedicated explainer: "Your disability benefits are protected" |
| **Progress Saving** | Automatic; never lose data due to timeout or navigation |
| **Document Alternatives** | Email-to-upload option; phone-based document submission pathway |
| **Phone Support** | Clearly visible phone number for questions (even if voicemail) |
| **Session Duration** | No time limits; accommodate slow, careful completion |

---

## PERSONA 4: Carlos Mendoza

### Profile Overview

**Name:** Carlos Mendoza  
**Age:** 29  
**Location:** Logan Square, Chicago  
**Occupation:** Restaurant line cook  
**Household:** Lives with roommate  
**Income:** $31,000/year (hourly wages, variable hours)  
**Education:** Some college (dropped out sophomore year)  

**Background Narrative:**  
Carlos dropped out of college after his father was deported. He's been working in restaurants ever since, cobbling together hours at two different establishments. His credit card debt ($15,000) accumulated during his attempts to help with immigration lawyer fees and family expenses in Mexico. He's now being sued by a creditor, and he received a wage garnishment notice. He's angry at a system that made his family's situation impossible and is motivated to fight back. He's technologically savvy but deeply skeptical of institutions.

### Goals & Motivations

- **Primary Goal:** Stop wage garnishment before it starts
- **Secondary Goal:** Eliminate credit card debt so he can help his family financially
- **Long-term Goal:** Save enough to either finish his degree or start a business
- **Emotional Goal:** Regain control over his financial life after years of crisis response

**What Success Looks Like:**  
Carlos files quickly, stops the garnishment, gets his discharge, and can start saving money for the first time in years.

### Pain Points & Frustrations

| Pain Point | Emotional Response | Current Workaround |
|------------|-------------------|-------------------|
| **Wage garnishment threat** | Urgency, anger | Researching options frantically |
| **Variable income** | Difficulty documenting | Keeps all pay stubs; calculates averages |
| **Two-job schedule** | Time scarcity | Does everything on phone during breaks/commute |
| **Immigration-related trauma** | Distrust of government systems | Hesitant to enter personal information |
| **Lawsuit stress** | Overwhelm | Ignored it initially; now scrambling |

> **Signature Quote:**  
> *"They want to take 25% of my paycheck? For debt I got into trying to keep my family together? This system is broken, and I'm not just going to accept it."*

### Behaviors & Patterns

**How He Currently Solves Problems:**
- Researches online extensively
- Asks friends in similar situations for advice
- Uses apps for most tasks (banking, communication, scheduling)
- Prefers self-service over phone calls

**Decision-Making Process:**
- Quick once convinced; research precedes action
- Values efficiency and clarity
- Distrusts institutions but will engage if treated fairly
- Responds to urgency (deadline-driven)

**Information Consumption:**
- Skims content for key points
- Prefers bullet points over paragraphs
- Uses search functions to find specific answers
- Will read terms if genuinely concerned about implications

### Technology & Communication

| Dimension | Detail |
|-----------|--------|
| **Primary Device** | iPhone 13 (employer-discounted) |
| **Secondary Device** | Rarely uses desktop |
| **Internet Access** | Unlimited mobile data; WiFi at apartments |
| **Digital Literacy** | High; uses multiple productivity apps |
| **Challenges** | Completing long forms on phone during short breaks |
| **Preferred Communication** | Text/push notifications; checks email rarely |

### Usage Scenarios

**Scenario 1: Urgent Timeline**  
Carlos has 10 days before wage garnishment begins. He needs to understand immediately whether bankruptcy can stop it (automatic stay) and how fast he can file.

**Scenario 2: Mobile-First Completion**  
Carlos fills out intake during his 30-minute lunch break and 15-minute afternoon break. He needs to complete meaningful chunks in short sessions without losing progress.

**Scenario 3: Variable Income Documentation**  
With inconsistent hours, Carlos's income varies from $400-$700 per week. He needs to understand how to average this properly for the means test and whether his bad months or good months matter more.

### Design Implications

| Category | Recommendation |
|----------|----------------|
| **Urgency Addressing** | Clear timeline explanation: "Bankruptcy stops garnishment immediately through automatic stay" |
| **Mobile Optimization** | Every form must be completable on iPhone; no desktop-required features |
| **Session Chunking** | Design for 10-15 minute completion bursts; clear stopping points |
| **Variable Income Support** | Calculator for averaging; explanation of which months count |
| **Progress Indicators** | Real-time: "5 more questions in this section" |
| **Push Notifications** | Deadline reminders; session resume prompts |
| **Fast Path Options** | If straightforward, surface time-to-completion estimates prominently |
| **Political Framing** | He resonates with DigniFi's political mission; visible but not required |

---

## PERSONA 5: Sarah Mitchell

### Profile Overview

**Name:** Sarah Mitchell  
**Age:** 47  
**Location:** Evanston, Illinois  
**Occupation:** Part-time administrative assistant  
**Household:** Recently divorced, two teenagers (shared custody)  
**Income:** $41,000/year (salary + child support)  
**Education:** Bachelor's degree in communications  

**Background Narrative:**  
Sarah's 20-year marriage ended in a contentious divorce. She discovered that her ex-husband had accumulated $45,000 in credit card debt in her name (she was an authorized user) and that the IRS was owed $12,000 from a side business she didn't know existed. Her divorce attorney failed to properly address these debts in the settlement, and now she's responsible for them. She's humiliated—she was a stay-at-home mom for 15 years and is now navigating financial systems she never had to understand. She has decent computer skills from her administrative work but is new to legal and financial complexity.

### Goals & Motivations

- **Primary Goal:** Discharge the debts she unfairly inherited from her marriage
- **Secondary Goal:** Protect her ability to provide for her children
- **Long-term Goal:** Establish independent financial identity and stability
- **Emotional Goal:** Move on from the shame and anger of her divorce situation

**What Success Looks Like:**  
Sarah receives her discharge, can focus on her career growth, and demonstrates to her children that setbacks can be overcome with resourcefulness.

### Pain Points & Frustrations

| Pain Point | Emotional Response | Current Workaround |
|------------|-------------------|-------------------|
| **Unfair debt burden** | Anger, betrayal | Researching whether she can contest assignment |
| **Prior attorney failure** | Deep distrust of legal professionals | Doing everything herself if possible |
| **Shame about situation** | Embarrassment | Hasn't told friends or family |
| **Tax complexity** | Confusion | Doesn't know if IRS debt is dischargeable |
| **Income classification** | Uncertainty | Child support affects means test? |

> **Signature Quote:**  
> *"I trusted everyone—my husband, my lawyer—and I ended up with nothing but debt that isn't even mine. I'm done trusting. I'm going to figure this out myself."*

### Behaviors & Patterns

**How She Currently Solves Problems:**
- Methodical research; creates spreadsheets
- Joins online forums and Facebook groups for divorced parents
- Takes notes extensively; prints documents
- Prefers to understand everything before taking action

**Decision-Making Process:**
- Careful and deliberate
- Seeks control over situations (reaction to past loss of control)
- Values competence and clarity
- Will ask detailed questions when uncertain

**Information Consumption:**
- Reads thoroughly when stakes are high
- Prefers organized, scannable content
- Uses bookmarks and note-taking
- Researches providers before engaging

### Technology & Communication

| Dimension | Detail |
|-----------|--------|
| **Primary Device** | MacBook Air (work laptop, personal use allowed) |
| **Secondary Device** | iPhone 14 |
| **Internet Access** | Home WiFi (stable); work WiFi |
| **Digital Literacy** | Moderate-high; comfortable with standard office applications |
| **Challenges** | Not familiar with legal terminology; financial forms |
| **Preferred Communication** | Email for records; text for reminders |

### Usage Scenarios

**Scenario 1: Tax Debt Uncertainty**  
Sarah knows bankruptcy doesn't always discharge tax debt. She needs clear explanation of what categories of IRS debt can be discharged and whether her situation qualifies.

**Scenario 2: Child Support Income**  
She's unsure whether child support counts as income for the means test. She needs explicit guidance, with references to official sources she can verify.

**Scenario 3: Prior Attorney Failure as Special Circumstance**  
Her current financial situation exists partly because her divorce attorney failed to address debts properly. She wonders if this qualifies as "special circumstances" and needs to understand how to document it.

### Design Implications

| Category | Recommendation |
|----------|----------------|
| **Tax Debt Explainer** | Dedicated section on IRS debt dischargeability criteria |
| **Child Support Clarity** | Explicit means test treatment of child support/alimony |
| **Documentation Emphasis** | Help her build evidence for any contested claims |
| **Special Circumstances** | Include divorce-related expenses in prompted categories |
| **Control Features** | Print/export at every stage; full visibility into all data |
| **Attorney Reference** | Explain where professional help might still be needed |
| **Verification Links** | Link to official sources (IRS, USCIS) for verification |
| **Desktop-First** | Optimize for laptop experience (her primary device) |

---

## 3. Cross-Persona Insights

### 3.1 Universal Needs

| Need | Frequency | Design Response |
|------|-----------|-----------------|
| **Trust & Transparency** | All personas | Visible mission, founder story, clear UPL disclaimer |
| **Dignity Preservation** | All personas | Trauma-informed language throughout |
| **Save/Resume Capability** | All personas | Auto-save; multiple resume pathways (email, login, code) |
| **Progress Visibility** | All personas | Clear step indicators; time estimates |
| **Plain Language** | All personas | 6th-8th grade reading level; glossary on hover |
| **Error Recovery** | All personas | Non-judgmental errors; clear correction paths |

### 3.2 Segmented Needs

| Need | Personas | Design Response |
|------|----------|-----------------|
| **Mobile-First** | Maria, Carlos | All forms functional on 320px screens |
| **Desktop/Library Optimization** | Darnell, Sarah | Session timeout warnings; offline export |
| **Accessibility Features** | Linda | AAA contrast; zoom support; voice input |
| **Speed/Urgency** | Carlos, Darnell | Fast-track options; timeline clarity |
| **Special Circumstances Emphasis** | Maria, Sarah | Prominent, supportive presentation |
| **Spanish Language** | Maria | MVP+1 priority |

### 3.3 Trust-Building Requirements

Users arrive with varying trust deficits:

| Persona | Trust Barrier | Trust Signal Needed |
|---------|---------------|---------------------|
| **Maria** | Fear of institutional shame | Warmth; personal story; community proof |
| **Darnell** | Prior scam experience | Transparency; verifiable credentials; no tricks |
| **Linda** | Confusion, dependency fear | Explicit benefit protection; phone access option |
| **Carlos** | Institutional distrust | Political alignment; efficiency; respect |
| **Sarah** | Attorney failure | Self-service control; verifiable information |

---

## 4. Design Principles

Based on persona research, DigniFi's UX must embody these principles:

### 4.1 Core Principles

1. **Dignity First**  
   Every interaction should make users feel respected, not judged. Language matters: "amounts you owe" not "your debts"; "your situation" not "your problem."

2. **Radical Transparency**  
   Explain what the platform can and cannot do. Show the calculation behind every result. Never hide information that affects user decisions.

3. **Trauma-Aware Pacing**  
   Allow users to go slowly. Provide frequent saves. Never create artificial urgency. Acknowledge that this process is difficult.

4. **Accessible by Default**  
   Design for the most constrained user. If Linda (vision impaired, arthritic hands, limited tech literacy) can use it, everyone can.

5. **Mobile Parity**  
   Every feature works on a smartphone. No degraded experience for users without desktops.

6. **Progressive Disclosure**  
   Show only what's needed at each step. Provide "learn more" for those who want depth without overwhelming those who don't.

### 4.2 Language Guidelines

| Instead of... | Use... |
|---------------|--------|
| Your debts | Amounts you owe |
| Failed to | Not yet completed |
| You must | You'll need to |
| Error | Let's fix this |
| Invalid | Needs attention |
| Submit | Continue |
| Bankruptcy | Fresh start / bankruptcy relief |
| Discharged | Cleared / forgiven |

### 4.3 Error Message Framework

All error messages should follow this pattern:

1. **What happened** (neutral, factual)
2. **Why it matters** (brief, if necessary)
3. **What to do** (clear, actionable)
4. **Reassurance** (if appropriate)

**Example:**
> "This date doesn't look right. The format should be MM/DD/YYYY. You can type it again or use the calendar."

**Not:**
> "Error: Invalid date format"

---

## 5. Critical UX Recommendations

### 5.1 Special Circumstances Flow (Highest Priority)

The forced review of BAPCPA special circumstances is DigniFi's differentiating feature. It must be implemented as:

**✓ Supportive, Not Punitive**
- Frame as "finding all the relief you're entitled to"
- Not as "additional requirements to complete"

**✓ Guided, Not Demanding**
- Use checkboxes with examples
- Provide templates for written explanations
- Offer sentence starters: "My income decreased because..."

**✓ Validating**
- "Many people qualify for these—let's make sure you get the benefit"
- Highlight that attorneys often miss this step

**Recommended Implementation:**
```
┌──────────────────────────────────────────────────────────────────┐
│ ★ Special Circumstances Review                                   │
├──────────────────────────────────────────────────────────────────┤
│ The law provides additional relief for people in difficult       │
│ situations. Many filers—and even some attorneys—miss this.       │
│                                                                  │
│ Let's make sure you get every benefit you're entitled to.        │
│                                                                  │
│ Does any of the following apply to you?                          │
│                                                                  │
│ ☐ Job loss or reduced income in the past 6 months               │
│     Example: "I was laid off from my warehouse job in August"    │
│                                                                  │
│ ☐ Medical expenses for yourself or family                        │
│     Example: "My surgery cost $12,000 out of pocket"             │
│                                                                  │
│ [More options with examples...]                                  │
│                                                                  │
│ ℹ️ What you enter here will appear on Form 122A-2, Line 44.     │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Onboarding Experience

**First 30 Seconds: Trust Establishment**
1. Clear statement: "This is a free tool. Here's why." (Link to founder story)
2. Visual: Human face/name of founder (builds connection)
3. Promise: "We provide legal information—you make the decisions"
4. Time estimate: "Most people complete this in 45-60 minutes, saved as you go"

**First 2 Minutes: Safety Confirmation**
1. Explain data privacy (where it's stored, who sees it)
2. Confirm: "Your disability benefits / wages / [relevant asset] are protected"
3. Acknowledge: "This is hard. We'll guide you through it."

### 5.3 Save/Resume System

Given user constraints (library computers, short sessions, technology limitations), the save/resume system must be robust:

**Save Triggers:**
- Every field change (autosave with visual confirmation)
- Every page navigation
- On window blur/close (with warning)

**Resume Pathways:**
- Email link (primary for Darnell, Linda)
- SMS link (primary for Maria, Carlos)
- Login (for users who create accounts)
- Resume code (8-character, case-insensitive, works from any device)

**Visual Confirmation:**
- Constant "Saved ✓" indicator
- Timestamp of last save
- On resume: "Welcome back! You were on [step name]"

### 5.4 Mobile Form Optimization

For Maria and Carlos (smartphone-primary users):

| Pattern | Implementation |
|---------|----------------|
| **Single-column layouts** | No side-by-side fields on mobile |
| **Large touch targets** | Minimum 48x48px (exceeds WCAG's 44px) |
| **Sticky navigation** | Progress and action buttons always visible |
| **Input type specificity** | `type="tel"` for phone; `type="email"` for email; `inputmode="numeric"` for SSN |
| **Camera integration** | Document upload via camera with auto-enhancement |
| **Keyboard avoidance** | Forms scroll so active field is always visible |

### 5.5 Accessibility Requirements

Beyond WCAG 2.1 AA compliance (already in existing CSS):

| Requirement | Implementation Status | Recommendation |
|-------------|----------------------|----------------|
| **Color contrast** | 4.5:1 for body text ✓ | Increase to 7:1 for critical content |
| **Text scaling** | 200% zoom supported | Test at 400% for low-vision users |
| **Screen reader** | ARIA labels present ✓ | Add live regions for dynamic updates |
| **Keyboard navigation** | Focus indicators ✓ | Add skip links; logical tab order |
| **Motion** | No auto-animations | Add `prefers-reduced-motion` support |
| **Voice input** | Not implemented | Add speech-to-text for long text fields |
| **Touch targets** | 44px minimum | Increase to 48px for form fields |

---

## 6. Information Architecture

### 6.1 Recommended Wizard Flow

Based on user needs and cognitive load research:

```
1. Welcome & Trust Building (2 min)
   ├── What DigniFi is
   ├── Why it's free
   └── What to expect

2. Quick Screener (5 min)
   ├── Household size
   ├── Income estimate
   ├── Primary debt types
   └── [Preliminary feedback: "You likely qualify"]

3. Document Checklist (Pause point)
   ├── What you'll need
   ├── Download checklist as PDF
   └── [Option to save and return with documents]

4. Your Information (10 min)
   ├── Personal details
   ├── Address
   └── Contact information

5. Income Details (15 min)
   ├── Employment income
   ├── Other income
   ├── [MEANS TEST CALCULATION: Show current status]
   └── [If above median: Introduce special circumstances possibility]

6. Special Circumstances Review (5-15 min) ★ CRITICAL
   ├── Guided checklist with examples
   ├── Written explanation (with templates)
   ├── Document upload (optional but encouraged)
   └── [MEANS TEST UPDATE: Show impact]

7. Expenses (15 min)
   ├── Allowed expenses (IRS standards shown)
   ├── Actual expenses
   └── [MEANS TEST FINAL: Pass/fail with explanation]

8. Assets (10 min)
   ├── Property
   ├── Vehicles
   ├── Financial accounts
   └── [EXEMPTION CALCULATION: What's protected]

9. Amounts Owed (10 min)
   ├── Secured debts
   ├── Unsecured debts
   ├── Priority debts (taxes, support)
   └── [What will be discharged]

10. Review & Confirm (5 min)
    ├── Summary of all information
    ├── Key findings highlighted
    └── Form generation

11. Filing Guidance
    ├── District-specific instructions
    ├── Timeline and deadlines
    └── What happens next
```

### 6.2 Content Hierarchy Principles

**Primary:** What the user needs to do (actions)
**Secondary:** Why it matters (context)
**Tertiary:** Legal details (expandable)

**Example:**
```
PRIMARY: "Enter your monthly income from all jobs"
SECONDARY: "We use this to calculate whether you qualify for Chapter 7"
TERTIARY: [Expand] "The law looks at your average income over the past 6 months..."
```

---

## 7. Emotional Design Guidelines

### 7.1 Key Emotional Moments

| Moment | User Feeling | Design Response |
|--------|--------------|-----------------|
| **First landing** | Skeptical, hopeful, scared | Warmth, clarity, safety signals |
| **Entering SSN** | Vulnerable, distrustful | Privacy reassurance, encryption note |
| **Failing means test** | Panic, discouragement | Immediate pivot to special circumstances |
| **Completing special circumstances** | Seen, validated | Celebration, affirmation |
| **Final review** | Anxiety, accomplishment | Clear summary, confidence building |
| **Form download** | Relief, uncertainty | Next steps clarity, ongoing support |

### 7.2 Celebration Points

Build in moments of positive reinforcement:

- "You're 25% done—great progress!"
- "You've completed the hardest part (income). The rest is faster."
- "Special circumstances documented. This strengthens your case."
- "Your forms are ready. You did it."

### 7.3 Stress Mitigation

- Never use red except for critical errors
- Avoid countdowns or timers
- Provide "I need a break" option (saves and returns to home with encouragement)
- Include breathing/grounding prompts before stressful sections (optional, accessible)

---

## 8. Research Validation Plan

### 8.1 Recommended User Research

To validate and refine these personas, conduct:

| Research Method | Sample Size | Timing | Focus |
|-----------------|-------------|--------|-------|
| **User Interviews** | 8-12 participants | Before MVP launch | Validate persona assumptions; discover missing needs |
| **Usability Testing** | 5-8 participants | Prototype stage | Test special circumstances flow; mobile experience |
| **Accessibility Testing** | 3-5 with disabilities | Before launch | Screen reader; zoom; keyboard-only navigation |
| **A/B Testing** | 100+ users | Post-launch | Optimize trust-building; conversion points |
| **Diary Studies** | 5-8 participants | During pilot | Real-world usage patterns; barriers encountered |

### 8.2 Metrics to Track

**Engagement Metrics:**
- Session completion rate by step
- Save/resume rate
- Drop-off points
- Time per section

**Outcome Metrics:**
- Special circumstances documentation rate
- Form generation completion rate
- Filing confirmation rate (self-reported)

**Experience Metrics:**
- CSAT/NPS after form generation
- Accessibility issue reports
- Mobile vs. desktop completion rates

### 8.3 Assumption Risk Log

| Assumption | Confidence | Validation Method |
|------------|------------|-------------------|
| Users will trust platform with SSN | Medium | A/B test privacy messaging |
| Mobile completion is viable | Medium-High | Usability testing on smartphones |
| Special circumstances prompts don't overwhelm | Medium | User interviews; A/B test |
| 45-60 minute completion time is acceptable | Medium | Session time tracking |
| Spanish translation is highest-priority language | Low | User demographic survey |

---

## 9. Appendix

### 9.1 Competitive UX Analysis

| Platform | Strength | Weakness | DigniFi Opportunity |
|----------|----------|----------|---------------------|
| **Upsolve** | Clean, simple; strong mobile | Chapter 7 only; screens out complexity | Handle harder cases with special circumstances |
| **LegalZoom** | Professional trust signals | Expensive; not specialized | Free alternative with better guidance |
| **Court Self-Help** | Official; authoritative | Confusing; no guidance | Plain-language translation of official forms |
| **NerdWallet Guides** | Good explanatory content | No action capability | Integrated guidance + form generation |

### 9.2 Accessibility Testing Checklist

- [ ] Screen reader (VoiceOver, NVDA, JAWS) complete workflow
- [ ] Keyboard-only navigation through entire flow
- [ ] 200% zoom usability
- [ ] 400% zoom usability (low vision)
- [ ] High contrast mode
- [ ] Reduced motion preference respected
- [ ] Color-blind modes (protanopia, deuteranopia)
- [ ] Cognitive accessibility (reading level, complexity)

### 9.3 Trauma-Informed Design Resources

1. **SAMHSA's Trauma-Informed Care Framework** – Guidance on trauma-sensitive service delivery
2. **The Legal Design Lab (Stanford)** – Legal service design patterns
3. **The Beeck Center's Trauma-Informed Design Guide** – Digital service considerations
4. **18F Content Guide** – Plain language writing for government/legal services

---

## Document Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | January 4, 2026 | UX Research Team | Initial comprehensive research document |

---

*DigniFi: Relief Without Shame. Dignity by Design.*
