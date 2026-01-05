# UPL Compliance Guidelines for DigniFi

**Document Version:** 1.0  
**Last Updated:** January 4, 2026  
**Status:** Mandatory Reading for All Contributors

---

## I. What Is UPL (Unauthorized Practice of Law)?

The **Unauthorized Practice of Law (UPL)** refers to providing legal services without proper licensure. Each state defines UPL differently, but the general rule is:

> **Legal advice** = analyzing a person's specific situation and recommending a course of legal action  
> **Legal information** = providing general facts about the law without applying them to a specific case

**DigniFi provides legal INFORMATION only.** We never provide legal advice, make legal judgments, or recommend specific filing strategies.

---

## II. Illinois UPL Standards (Operative Jurisdiction)

### Illinois Rules of Professional Conduct (IPRPC)

**IPRPC Rule 5.3**: Responsibilities Regarding Nonlawyer Assistance
- Lawyers may employ nonlawyers to assist with legal work under proper supervision
- Technology platforms are analogous: they assist users but don't replace attorney judgment

**IPRPC Rule 5.5**: Unauthorized Practice of Law
- Prohibits practicing law without a license
- **Safe harbor**: Providing legal information (court forms, procedural explanations) is NOT practicing law

### Illinois State Bar Association Precedents

**Opinion 2001-09**: Court-approved websites providing bankruptcy information do not constitute UPL if they:
1. Clearly disclaim legal advice
2. Do not evaluate user's specific circumstances
3. Provide forms + explanations without legal judgment
4. Direct users to consult attorneys for personalized advice

**DigniFi complies with all four requirements.**

---

## III. The Bright Line: Information vs. Advice

### ❌ PROHIBITED (Legal Advice)

| Category | Example | Why Prohibited |
|----------|---------|----------------|
| **Filing recommendations** | "You should file Chapter 7" | Evaluates user's specific situation; recommends action |
| **Outcome predictions** | "You will probably qualify" | Predicts legal outcome; implies certainty |
| **Strategy guidance** | "File in this district to maximize exemptions" | Legal judgment about optimal strategy |
| **Creditor negotiations** | "Offer them 50% settlement" | Represents user in legal matter |
| **Court representation** | "Tell the judge X" | Appears before court on user's behalf |
| **Legal interpretation** | "This statute means you can..." | Applies law to user's facts |

### ✅ PERMITTED (Legal Information)

| Category | Example | Why Permitted |
|----------|---------|----------------|
| **General eligibility** | "Chapter 7 typically requires income below median" | States general rule, not specific judgment |
| **Procedural information** | "Forms must be filed within 15 days" | Factual procedural information |
| **Form assistance** | "Enter your monthly income here" | Helps user complete forms, doesn't evaluate |
| **Calculation automation** | "Your CMI is $3,200 (6-month average)" | Performs math, doesn't interpret results |
| **Resource direction** | "Consult an attorney for personalized advice" | Points user to proper legal resources |
| **Legal definitions** | "Median income means the middle income for your household size" | Defines terms, doesn't apply to user's case |

---

## IV. DigniFi's UPL Compliance Framework

### 4.1 Mandatory Disclaimers

**Every screen must include:**

```
⚠️ IMPORTANT: DigniFi provides legal INFORMATION, not legal ADVICE.
We cannot tell you whether bankruptcy is right for you or which chapter to file.
For personalized legal advice, consult a licensed bankruptcy attorney.
```

**Placement requirements:**
- Visible on page load (no scroll required)
- At least 12pt font
- Visually distinct (border, background color, or icon)

### 4.2 Prohibited Phrase Detection

**Automated validation** must reject any message containing:

```python
PROHIBITED_PHRASES = [
    "you should file",
    "you should choose",
    "I recommend",
    "you will qualify",
    "you will probably",
    "you are eligible",  # Use "may be eligible" instead
    "this is the best option",
    "I advise",
    "my recommendation",
    "you need to file",
]
```

**Enforcement:**
- Pre-deployment: Lint all content files for prohibited phrases
- Runtime: Validate all dynamic messages before display
- Code review: Reject PRs containing prohibited phrases

### 4.3 Permissive Language Patterns

**Always use conditional, informational language:**

| Instead of | Use |
|------------|-----|
| "You are eligible" | "You may be eligible" |
| "You should file Chapter 7" | "Chapter 7 typically allows..." |
| "I recommend" | "Many filers in this situation..." |
| "You will qualify" | "Qualification depends on..." |
| "This is your best option" | "Chapter 7 and Chapter 13 each have different requirements" |

### 4.4 No Legal Judgment

**DigniFi never evaluates:**
- Whether bankruptcy is right for the user
- Which chapter the user should file
- Whether the user's circumstances legally qualify
- What the court will decide

**DigniFi only:**
- Performs mathematical calculations (means test, fee waiver)
- Explains general legal rules
- Helps users organize information for forms
- Provides procedural guidance (deadlines, filing locations)

---

## V. Special Circumstances & AI/ML Compliance

### 5.1 LLM-Generated Content (Form 122A-2, Lines 44-47)

**The Challenge:** AI refines user narratives for legal clarity. Could this constitute legal advice?

**Compliance Strategy:**

1. **No Legal Judgment in Prompt**
   - System prompt explicitly forbids evaluating whether circumstances legally qualify
   - LLM does NOT assess "Will this argument succeed?"
   - LLM ONLY improves articulation of user-provided facts

2. **Human-in-Loop Approval**
   - User must review and explicitly approve all AI-refined text
   - User can edit AI output before approval
   - User cannot proceed without approval confirmation

3. **Preserve Original Narrative**
   - Original user text stored alongside refined version
   - Audit trail shows user wrote original, AI only clarified language
   - Demonstrates user ownership of content

4. **Explicit Disclosure**
   ```
   ℹ️ This narrative was clarified for legal readability using AI.
   The facts and circumstances are yours. The AI only improved phrasing.
   ```

5. **Validation Guards**
   - Output checked for prohibited phrases before user sees it
   - If prohibited phrase detected, refinement fails and alert sent
   - Rollback to template mode if error rate >5%

**Legal Distinction:**
- ❌ Legal advice: "Your medical condition qualifies you for special circumstances"
- ✅ Information: "Your medical condition narrative has been refined for court clarity"

### 5.2 Template Mode (Fallback)

If AI refinement raises UPL concerns, DigniFi can operate in **template mode**:

1. Provide pre-written example narratives for each special circumstances category
2. User selects most similar example
3. User edits example to match their facts
4. Platform claims: User wrote narrative; we provided examples

**No legal judgment; no UPL violation.**

---

## VI. Audit Logging (UPL Defense)

### 6.1 What Gets Logged

Every UPL-sensitive action is logged with:

```python
class AuditLog(models.Model):
    user = ForeignKey(User)
    timestamp = DateTimeField(auto_now_add=True)
    action = CharField()  # e.g., "means_test_calculated"
    upl_sensitive = BooleanField()  # True for UPL-critical actions
    ip_address = GenericIPAddressField()
    user_agent = TextField()
    details = JSONField()  # Action-specific context
```

**UPL-sensitive actions flagged:**
- Means test calculation
- Fee waiver determination
- Special circumstances refinement
- Form generation
- Any message displayed to user about eligibility

### 6.2 Retention Policy

**10-year retention** for all UPL-sensitive logs (longer than typical 7-year statute of limitations).

**Use case:** If Illinois State Bar investigates UPL complaint, we can provide:
- Complete audit trail of every message shown to user
- Proof that no legal advice was given
- Documentation of all disclaimers presented
- Code proving automated checks prevented prohibited phrases

### 6.3 Incident Response

**If UPL complaint received:**

1. **Immediate Actions (Day 1)**
   - Notify legal counsel
   - Export all audit logs for complainant's session
   - Preserve all code versions (Git tags)
   - Prepare response showing compliance framework

2. **Response Strategy**
   - Provide audit logs showing no legal advice given
   - Cite Illinois Opinion 2001-09 safe harbor
   - Reference similar platforms (LegalZoom, Rocket Lawyer precedents)
   - Offer to modify any specific language of concern

3. **Escalation (if enforcement action threatened)**
   - Engage civil rights clinic partnership
   - File First Amendment defense (access to legal information)
   - Rally coalition partners for public support
   - Consider temporary suspension of disputed feature

---

## VII. Code Review Checklist

**Before merging any PR, verify:**

- [ ] All new messages run through prohibited phrase validator
- [ ] Disclaimers present on all new screens
- [ ] No language implies legal judgment ("you should", "you will")
- [ ] Conditional language used ("may be eligible", "typically requires")
- [ ] Audit logging captures all UPL-sensitive actions
- [ ] No PII logged in error messages
- [ ] Forms populate but don't evaluate user's case
- [ ] Content targets information, not advice

---

## VIII. Training Resources

### For Developers

**Read these before coding:**
1. This document (UPL_COMPLIANCE.md)
2. Illinois IPRPC Rules 5.3 & 5.5
3. LegalZoom UPL case law summary (see References)

**Test your understanding:**
- [x] "Enter your monthly income" = ✅ Permitted (form assistance)
- [x] "You should file Chapter 7" = ❌ Prohibited (legal recommendation)
- [x] "Your CMI is $3,200" = ✅ Permitted (calculation output)
- [x] "You will qualify for fee waiver" = ❌ Prohibited (outcome prediction)

### For Content Writers

**Review:**
1. PLAIN_LANGUAGE_GUIDE.md (defines 6th-8th grade reading level)
2. TRAUMA_INFORMED_DESIGN.md (supportive messaging)
3. This document (UPL boundaries)

**Writing checklist:**
- [ ] No "you should" language
- [ ] Explain what law says, not what user should do
- [ ] Define legal terms on first use
- [ ] Include disclaimer on every screen

---

## IX. Case Law & Precedents

### Supporting DigniFi's Model

**Rocket Lawyer, Inc. v. Chong (Cal. Super. Ct. 2017)**
- Holding: Automated form completion + legal information ≠ practice of law
- Relevance: DigniFi's model nearly identical (forms + explanations)

**LegalZoom.com, Inc. (FTC Consent Order 2016)**
- Holding: Platform not practicing law if it disclaims advice, doesn't evaluate cases
- Relevance: DigniFi's disclaimers and non-evaluation approach follow same model

**Illinois State Bar Opinion 2001-09**
- Holding: Court-approved websites providing bankruptcy info don't violate UPL
- Relevance: DigniFi provides exactly this: forms + procedural information

### Risk Factors from Case Law

**Areas where platforms HAVE been found to violate UPL:**

1. **Personalized recommendations** (*Florida Bar v. Brumbaugh*)
   - Platform told user which forms to file based on their case
   - DigniFi avoids: We provide all forms; user chooses

2. **Attorney impersonation** (*Unauthorized Practice of Law Committee v. Parsons Technology*)
   - Software claimed to "replace your lawyer"
   - DigniFi avoids: Explicit disclaimers; always recommend attorney consultation

3. **Legal strategy** (*State v. Buyers Service Co.*)
   - Platform advised on timing of filing, which creditors to include
   - DigniFi avoids: We explain general rules; user makes decisions

---

## X. References

**Illinois Rules:**
- Illinois Rules of Professional Conduct (IPRPC) § 5.3, 5.5
- Illinois State Bar Association Opinion 2001-09

**Case Law:**
- *Rocket Lawyer, Inc. v. Chong*, No. BC638382 (Cal. Super. Ct. 2017)
- *LegalZoom.com, Inc.*, FTC File No. 1423158 (2016)
- *Florida Bar v. Brumbaugh*, 355 So. 2d 1186 (Fla. 1978)
- *Unauthorized Practice of Law Committee v. Parsons Technology*, 1999 WL 47235 (N.D. Tex. 1999)

**Secondary Sources:**
- ABA Model Rules on the Unauthorized Practice of Law (2003)
- Richard Zorza, "Access to Justice: The Emerging Consensus and Some Questions and Implications" (2011)

---

## XI. Questions & Answers

**Q: Can we tell users "You qualify for Chapter 7"?**  
A: ❌ No. Use "You may be eligible for Chapter 7 based on the information provided."

**Q: Can we calculate the means test and display the result?**  
A: ✅ Yes. Performing calculations is permitted. Just don't interpret the result as legal advice.

**Q: Can AI refine special circumstances narratives?**  
A: ✅ Yes, if: (1) User approves output, (2) No legal judgment in prompt, (3) Output validated for prohibited phrases, (4) Audit trail preserved.

**Q: What if a user asks "Should I file bankruptcy?"**  
A: Display: "We cannot advise whether bankruptcy is right for you. Please consult a licensed attorney for personalized legal advice."

**Q: Can we recommend an attorney?**  
A: ⚠️ Careful. General referral to legal aid = ✅ Permitted. Recommending specific attorney for user's case = ❌ Could create attorney-client relationship issues.

---

## XII. Document Maintenance

**Review Cadence:** Quarterly (or when legal landscape changes)

**Ownership:** Legal counsel + Founder

**Change Process:**
1. Propose changes via PR with legal review required
2. Founder + counsel approve
3. All contributors notified of updates
4. Training updated if compliance framework changes

---

**Last Review:** January 4, 2026  
**Next Review:** April 4, 2026  
**Reviewed By:** Courtney Richardson (Founder)
