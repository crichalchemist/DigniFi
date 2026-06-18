# Adversary Complaint Template Generator — Design Spec

> **Status:** Ready for Implementation
> **Scope:** Student loan discharge complaint under 11 U.S.C. § 523(a)(8)

---

## Context

The adversary complaint for student loan discharge is a narrative legal document, not a fillable PDF. It alleges undue hardship under the Brunner test. DigniFi generates this from structured data captured in `AdversaryProceeding` and `IntakeSession`.

---

## What the Generator Produces

A **formatted text document** (not a PDF) that the user reviews, edits, and files with the court. The complaint follows ILND local formatting rules.

---

## Input Data

From `AdversaryProceeding` model:

- `lender_name` — loan holder (defendant)
- `loan_amount` — original loan balance
- `loan_type` — federal/private
- `hardship_narrative` — user's description of hardship
- `income_insufficient`, `persistence_likely`, `good_faith_efforts` — Brunner test factors

From `IntakeSession`:

- Debtor name, address, district
- Income, expenses, household size
- Other debts and assets

---

## Complaint Structure

```
UNITED STATES BANKRUPTCY COURT
NORTHERN DISTRICT OF ILLINOIS

In Re: [Debtor Name], Case No. [____]

ADVERSARY PROCEEDING

[Debtor Name],
    Plaintiff,

v.

[Lender Name],
    Defendant.

________________________________________

COMPLAINT FOR DETERMINATION OF
DISCHARGEABILITY OF STUDENT LOAN
UNDER 11 U.S.C. § 523(a)(8)

________________________________________

I. INTRODUCTION

This adversary proceeding is filed pursuant to 11 U.S.C. § 523(a)(8)
to determine whether [lender_name]'s student loan claim in the amount
of $[loan_amount] is dischargeable based on undue hardship.

II. PARTIES

Plaintiff [Debtor Name] is an individual who filed for Chapter 7
bankruptcy on [filing_date] in Case No. [case_number].

Defendant [lender_name] is the holder of a student loan obligation
incurred by Plaintiff.

III. JURISDICTION AND VENUE

This Court has jurisdiction under 28 U.S.C. § 1334(b) and 11 U.S.C.
§ 157(b)(2)(K). Venue is proper under 28 U.S.C. § 1409(a).

IV. UNDUE HARDSHIP — BRUNNER TEST

Plaintiff alleges that repayment of the student loan would impose an
undue hardship on Plaintiff and Plaintiff's dependents under the
three-prong Brunner test:

A. PRONG ONE — MINIMAL STANDARD OF LIVING

[based on income_insufficient + hardship_narrative]

[User's narrative, refined into legal prose]

B. PRONG TWO — LIKELIHOOD OF PERSISTENCE

[based on persistence_likely + additional circumstances]

[User's narrative about why financial situation will persist]

C. PRONG THREE — GOOD FAITH EFFORTS

[based on good_faith_efforts]

[User's description of repayment efforts]

V. PRAYER FOR RELIEF

WHEREFORE, Plaintiff respectfully requests that this Court:

1. Determine that Defendant's student loan claim in the amount of
   $[loan_amount] is dischargeable pursuant to 11 U.S.C. § 523(a)(8);
2. Grant such other relief as the Court deems just and proper.

Dated: _______________

Respectfully submitted,

_____________________________
[Debtor Name], Pro Se
[Address]
[Phone]
```

---

## Implementation

**Generator class:** `backend/apps/forms/services/adversary_complaint_generator.py`

```python
class AdversaryComplaintGenerator:
    def __init__(self, proceeding: AdversaryProceeding):
        self.proceeding = proceeding
        self.session = proceeding.session

    def generate(self) -> str:
        """Generate formatted complaint text."""
        data = self._gather_data()
        return COMPLAINT_TEMPLATE.format(**data)

    def _gather_data(self) -> dict:
        """Collect all data for template substitution."""
        return {
            "debtor_name": self._get_debtor_name(),
            "lender_name": self.proceeding.lender_name,
            "loan_amount": self._fmt_money(self.proceeding.loan_amount),
            "filing_date": self.session.created_at.strftime("%B %d, %Y"),
            "case_number": "",  # Assigned by court
            "district": self.session.district.name,
            "income_insufficient": self._format_prong_one(),
            "persistence_likely": self._format_prong_two(),
            "good_faith_efforts": self._format_prong_three(),
        }
```

---

## Output

- **Text file** (.txt) — user downloads, reviews, edits, files with court
- **Future:** PDF rendering via weasyprint or similar (post-MVP)
- **Not a fillable PDF** — the complaint is narrative, not form-based

---

## UPL Compliance

- Generator produces template text with placeholders
- User reviews and edits all content before filing
- No legal conclusions — just structural framing
- Disclaimer: "This document is a template. You should review it for accuracy before filing."
