# Trauma-Informed Design Principles for DigniFi

**Document Version:** 1.0  
**Last Updated:** January 4, 2026  
**Purpose:** Guide compassionate, dignity-preserving design for bankruptcy filers

---

## I. Why Trauma-Informed Design Matters

### The Reality of Bankruptcy

Filing for bankruptcy is not a neutral administrative task. For most filers, it represents:

- **Financial collapse** after months or years of struggle
- **Shame** internalized from cultural narratives about debt and failure
- **Overwhelm** from creditor harassment, legal notices, and court complexity
- **Vulnerability** from disclosing intimate financial details to strangers
- **Previous trauma** (medical crisis, job loss, divorce, abuse, disability)

**DigniFi's users are in crisis.** Our design must acknowledge this reality and respond with compassion, not bureaucracy.

---

## II. Core Principles

### 1. Safety & Predictability

**Principle:** Users must feel safe exploring the platform without fear of judgment, consequences, or surprises.

**Implementation:**

- **Clear expectations at every step**
  - "This intake will take 45-60 minutes. You can save and return anytime."
  - "No information is shared with courts until you explicitly generate forms."
  
- **Progress indicators**
  - Show: "Step 3 of 8" with visual progress bar
  - Estimate time remaining: "About 15 minutes left"
  
- **Reversible actions**
  - "Edit" buttons on every completed section
  - "Are you sure?" confirmations before deleting data
  
- **No hidden requirements**
  - Upfront document checklist before intake begins
  - "You'll need: pay stubs, bank statements, creditor names"

**Anti-patterns to avoid:**
- ❌ Surprise requirements ("Actually, you need 3 more documents")
- ❌ Irreversible deletions without confirmation
- ❌ Vague next steps ("Submit forms to court")

---

### 2. Language of Dignity

**Principle:** Words matter. Debt is not moral failure. Bankruptcy is a legal right, not a shameful secret.

**Dignified Language:**

| Instead of | Use |
|------------|-----|
| "Debts" | "Amounts owed" (where possible) |
| "Failed to pay" | "Unable to pay" |
| "Defaulted" | "Fell behind on payments" |
| "Delinquent" | "Overdue" |
| "Creditors you owe" | "Companies you've done business with" |
| "Declare bankruptcy" | "File for bankruptcy protection" |
| "You're broke" | "Your income is below the threshold" |

**Explanatory Language (not condescending):**

- ✅ "Chapter 7 bankruptcy stops creditor calls and lawsuits. It's a legal protection available to you."
- ❌ "Chapter 7 is when you're so broke the court lets you off the hook."

**Affirmative Framing:**

- ✅ "You're taking a powerful step to protect yourself."
- ❌ "Bankruptcy is a last resort when you've tried everything else."

---

### 3. Emotional Regulation Support

**Principle:** Bankruptcy is emotionally overwhelming. Design must help users stay regulated, not trigger panic.

**Calming Design Elements:**

- **Color palette**: Soft blues, greens, neutrals (avoid red = alarm)
- **Whitespace**: Generous padding; don't crowd screens
- **Typography**: Sans-serif, 16px minimum, high contrast
- **Icons**: Friendly, rounded (not sharp, aggressive)

**Pacing & Breaks:**

- Offer breaks after intensive sections:
  ```
  ✓ Income section complete.
  
  Take a break if you need it. Your progress is saved.
  When you're ready, we'll move to expenses.
  ```

- Avoid time pressure:
  ```
  There's no rush. Many people complete this over 2-3 sessions.
  ```

**Celebration of Progress:**

- ✅ "Great work. You've completed 5 of 8 sections."
- ✅ "This was a big step. You're doing great."
- ❌ Silent progression to next screen (feels robotic)

---

### 4. Transparency Without Judgment

**Principle:** Users need honest information about their situation without shame or blame.

**Means Test Results (Above Median Example):**

❌ **Judgmental Version:**
```
You failed the means test. Your income is too high.
You don't qualify for Chapter 7.
```

✅ **Trauma-Informed Version:**
```
Based on the information provided, your income is above the median
for a household of your size in Illinois.

This doesn't mean you can't file Chapter 7. It means we need to look
at your expenses and any special circumstances (like recent job loss
or medical expenses).

Many people in your situation still qualify. Let's continue.
```

**Special Circumstances (Sensitive Topics):**

When asking about difficult circumstances (job loss, medical issues, domestic violence):

```
Have you experienced any of these circumstances in the past year?

☐ Job loss or reduced income
☐ Serious medical condition or injury
☐ Separation or divorce
☐ Care for family member with disability
☐ Domestic violence or abuse
☐ None of these

Your answer helps us understand your situation. You'll have a chance
to explain in your own words later.
```

**Why this works:**
- Multiple-choice reduces cognitive load
- "None of these" = no shame if circumstances don't apply
- "Explain in your own words later" = doesn't force disclosure now

---

### 5. User Control & Autonomy

**Principle:** Users are experts on their own lives. Platform facilitates; user decides.

**Preserve User Agency:**

- Never auto-submit forms without explicit user action
- Always show: "This is what will be filed. Review before submitting."
- Provide "Edit" and "Delete" options for all user input
- Respect session abandonment (don't shame: "Why did you leave?")

**Informed Consent:**

Before collecting sensitive data:
```
The next section asks about your income, bank accounts, and assets.

Why we ask: Bankruptcy courts require this information to determine
eligibility and protections.

Privacy: All data is encrypted. We never share information without
your permission.

[Continue] [Take a break]
```

**Anti-patterns:**
- ❌ Auto-populating fields from third-party data (feels invasive)
- ❌ Required fields with no explanation why
- ❌ Blocking progress without clear reason

---

### 6. Validation, Not Shame

**Principle:** Users are doing hard, brave work. Acknowledge it.

**Affirmations (Sparingly, Genuinely):**

After difficult sections:
```
✓ Special circumstances documented.

This strengthens your case. Many people don't know to include
this information. You're being thorough.
```

After means test:
```
You've completed the hardest part. The means test calculation
is complex, and you just worked through it.
```

**Error Messages (Compassionate):**

❌ **Harsh:**
```
ERROR: Invalid input. Try again.
```

✅ **Compassionate:**
```
It looks like this field needs a number (like 1500, not $1,500).
Could you check and reenter it?
```

---

## III. Specific Design Patterns

### Pattern 1: Intake Section Intros

**Structure:**
1. What we're asking about
2. Why it matters (legally)
3. How long it takes
4. Reminder: you can pause

**Example (Assets Section):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Assets & Property

We'll ask about property you own: home, car, bank accounts,
personal items, etc.

Why it matters: Bankruptcy law protects certain assets (called
exemptions). We need a complete list to determine what's protected.

This section takes about 10-15 minutes.

Your progress is automatically saved. You can pause anytime.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Begin Assets Section]
```

### Pattern 2: Help Text (Always Available)

**Inline help** for complex fields:

```
Monthly mortgage payment: $______

ℹ️ Include: principal + interest + property tax + insurance.
   Don't include: utilities, HOA fees (we'll ask about those later).
```

**Expandable definitions:**

```
Median income [?]

[Expanded:]
Median income is the middle income for a household of your size
in your state. Half of households earn more; half earn less.
If your income is below median, you typically qualify for Chapter 7.
```

### Pattern 3: Document Checklists (Reduce Anxiety)

**Before intake begins:**

```
Documents You'll Need

To complete this intake, gather these documents:
☐ Last 6 months of pay stubs
☐ Last 2 months of bank statements
☐ List of creditors (who you owe)
☐ Recent bills (mortgage, car, utilities)

Don't have everything? That's okay.
You can estimate and update later.

[I'm ready] [I need more time]
```

### Pattern 4: Review & Confirm (Transparency)

**Before form generation:**

```
Review Your Information

Before we generate your bankruptcy forms, please review this summary.
You can edit any section.

Personal Information    [Edit]
Income Information     [Edit]
Expenses               [Edit]
Assets & Property      [Edit]
Special Circumstances  [Edit]

When you're satisfied, we'll generate your official forms.

[Generate Forms]
```

---

## IV. Sensitive Topics: Special Handling

### Medical Information

**Principle:** Medical debt often comes with trauma (diagnosis, treatment, lost work).

**Approach:**
- Don't require diagnosis disclosure unless user volunteers
- Frame as "medical expenses" not "illness"
- Normalize: "Medical expenses are the #1 cause of bankruptcy filings."

**Example:**

```
Do you have medical expenses?

☐ Yes, from a recent illness or injury
☐ Yes, from ongoing treatment or medication
☐ No

If yes, you'll enter the monthly cost. You don't need to describe
your medical condition unless you want to.
```

### Domestic Violence

**Principle:** DV survivors may fear creditor contact revealing their location.

**Approach:**
- Include DV-specific privacy guidance
- Offer contact preference options
- Validate without requiring disclosure

**Example:**

```
Contact Preferences

How should we contact you about your case?

☐ Email
☐ Phone
☐ Mail to the address you provided

If you have safety concerns about creditor contact or mail,
check this resource: [Link to DV safety planning]
```

### Job Loss

**Principle:** Job loss = identity threat + financial crisis.

**Approach:**
- Frame as involuntary, not personal failure
- Normalize: "Job loss affects millions of Americans each year."

**Example:**

```
Employment Status

Are you currently employed?

☐ Yes, full-time
☐ Yes, part-time
☐ No, recently lost job
☐ No, unable to work due to disability
☐ No, retired

If you've lost a job in the past year, this may qualify as a
"special circumstance" that strengthens your bankruptcy case.
We'll ask about this later.
```

---

## V. Visual Design Standards

### Color Palette

**Primary:**
- DigniFi Blue: `#2C5F8D` (trustworthy, calm)
- Success Green: `#2D7A3E` (affirmation)
- Neutral Gray: `#4A5568` (body text)

**Avoid:**
- Red (alarm, danger) except critical errors
- Bright yellow (anxiety)
- Black (harsh)

### Typography

**Body text:**
- Font: Inter, SF Pro, or system sans-serif
- Size: 16px minimum (18px for long-form content)
- Line height: 1.6 (generous spacing)
- Paragraph width: Max 65 characters (readable)

**Headings:**
- Clear hierarchy (h1 > h2 > h3)
- Not all caps (harder to read)
- Bold or size, not both (avoid visual overwhelm)

### Iconography

**Use:**
- Rounded, friendly icons
- Outline style (less aggressive than solid)
- Meaningful, not decorative

**Examples:**
- ✓ Checkmark (progress)
- ℹ️ Info circle (help available)
- 📄 Document (forms)
- 🔒 Lock (privacy/security)

**Avoid:**
- ❌ X marks (feels punitive)
- ⚠️ Warning triangles (anxiety)
- 🚫 Prohibition symbols (restrictive)

---

## VI. Content Voice & Tone

### Voice (Consistent Across Platform)

DigniFi's voice is:
- **Knowledgeable** (not condescending)
- **Supportive** (not patronizing)
- **Clear** (not oversimplified)
- **Respectful** (not formal to the point of coldness)

### Tone (Varies by Context)

**Intake screens:** Calm, matter-of-fact
> "Let's gather information about your income."

**Difficult topics:** Validating, gentle
> "This section asks about recent hardships. Take your time."

**Successes:** Warm, encouraging
> "Great work. You've completed the income section."

**Errors:** Helpful, non-judgmental
> "It looks like this date format needs to be MM/DD/YYYY. Could you try again?"

**Legal information:** Authoritative, but plain
> "Chapter 7 bankruptcy stops creditor lawsuits. This is called the 'automatic stay.'"

---

## VII. Testing for Trauma-Informed Design

### User Testing Protocol

**Recruit participants who:**
- Are currently considering bankruptcy
- Have filed for bankruptcy in past 2 years
- Represent diverse backgrounds (race, age, disability, geography)

**Test for:**
1. **Emotional response**: Do users report feeling supported or judged?
2. **Cognitive load**: Can users complete intake without overwhelm?
3. **Language comprehension**: Do terms make sense? Anything confusing?
4. **Trust**: Do users feel safe entering sensitive information?

**Red flags:**
- User expresses shame or self-blame during test
- User abandons intake due to stress (not technical issues)
- User misunderstands legal terms despite explanations
- User feels rushed or pressured

### Post-Launch Monitoring

**Collect feedback:**
- Post-intake survey: "How did you feel during this process?" (1-5 scale + open text)
- Abandonment analysis: Which screens have highest drop-off?
- Support requests: Are users confused or distressed by specific sections?

**Iterate:**
- Quarterly review of feedback
- Update language, pacing, or design based on patterns
- A/B test new approaches for high-stress sections

---

## VIII. Case Study: Special Circumstances Wizard

**Context:** Users must disclose difficult circumstances (job loss, medical crisis, DV) for Form 122A-2.

**Trauma-Informed Approach:**

1. **Multi-screen pacing** (not single overwhelming form)
   - Screen 1: Category checkboxes (low cognitive load)
   - Screen 2: Explanation in user's words (controlled disclosure)
   - Screen 3: AI refinement review (user retains control)

2. **Language of validation**
   ```
   Many filers don't realize these circumstances matter legally.
   You're being thorough by documenting them.
   ```

3. **User control**
   - User can edit AI-refined narrative before approval
   - User can skip special circumstances (though we encourage completion)
   - User sees both original and refined versions side-by-side

4. **Privacy affirmation**
   ```
   This information is encrypted and only included in your
   bankruptcy petition if you choose to file.
   ```

**Outcome:** Users disclose sensitive information without feeling exploited or judged.

---

## IX. Resources & Further Reading

**Trauma-Informed Design:**
- "Trauma-Informed Design: Building Systems That Support Survivors" (Center for Health Care Strategies, 2018)
- "Design Justice" by Sasha Costanza-Chock (MIT Press, 2020)

**Plain Language & Accessibility:**
- plainlanguage.gov (Federal Plain Language Guidelines)
- WCAG 2.1 AA Standards (Web Content Accessibility Guidelines)

**Financial Trauma Research:**
- "The Psychological Impact of Debt" (Money and Mental Health Policy Institute, 2019)
- "Shame, Stigma, and Bankruptcy" (American Bankruptcy Institute Journal, 2015)

---

## X. Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | January 4, 2026 | Initial draft | Courtney Richardson |

**Next Review:** March 4, 2026
