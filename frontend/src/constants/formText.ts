/**
 * Text quoted from the court forms, kept in their words (3e1 spec §8.5). It lives outside
 * copy.ts, where the reading-level test would score it, because the forms' words are not
 * DigniFi's to simplify.
 *
 * Form 122A-1 line 1 (b_122a-1.pdf page 1) is asked on the Income step. The step has no
 * columns, so it drops each answer's column instruction, and the answers drop the period the
 * cut leaves at their end. Each constant names its cut. Nothing marks a cut on screen (rulings
 * P2).
 */
import type { DeductionField, EntryKind, MaritalStatus } from '../types/api';

// No cut: the question as printed
export const LINE_1_QUESTION = 'What is your marital and filing status? Check one only.';

// No cut: the third answer, under which the last two sit. It has no stored value of its own.
export const MARRIED_NOT_FILING =
  'Married and your spouse is NOT filing with you. You and your spouse are:';

export const MARRIAGE_ANSWER_WORDS: Record<MaritalStatus, string> = {
  // Cut: ". Fill out Column A, lines 2-11."
  not_married: 'Not married',
  // Cut: ". Fill out both Columns A and B, lines 2-11."
  married_spouse_filing: 'Married and your spouse is filing with you',
  // Cut: ". Fill out both Columns A and B, lines 2-11."
  married_together: 'Living in the same household and are not legally separated',
  // Cut: ". Fill out Column A, lines 2-11; do not fill out Column B."
  married_separately: 'Living separately or are legally separated',
};

// The rest of the fourth answer, whole, after its cut
export const LIVING_SEPARATELY_DECLARATION =
  'By checking this box, you declare under penalty of perjury that you and your spouse are legally separated under nonbankruptcy law that applies or that you and your spouse are living apart for reasons that do not include evading the Means Test requirements. 11 U.S.C. § 707(b)(7)(B).';

// The forms' instructions define a dependent this way; shown whole, as a quotation
export const DEPENDENT_GLOSSARY =
  'A person who is economically dependent on you regardless of whether the person can be claimed as a dependent on your federal tax return.';

// The averaging sentence beside the six-month boxes, whole (b_122a-1.pdf page 1)
export const AVERAGING_SENTENCE =
  'If the amount of your monthly income varied during the 6 months, add the income for all 6 months and divide the total by 6.';

// The sentence about counting an amount once, whole (b_122a-1.pdf page 1)
export const ONE_COLUMN_ONLY =
  'Do not include any income amount more than once. For example, if both spouses own the same rental property, put the income from that property in one column only.';

// Lines 5 and 6's names for the two kinds (b_122a-1.pdf page 1)
export const ENTRY_KIND_WORDS: Record<EntryKind, string> = {
  business: 'A business, profession, or farm, or self-employment',
  rental: 'Rental or other real property',
};

// Line 7's name (b_122a-1.pdf page 1)
export const INTEREST_LABEL = 'Interest, dividends, and royalties';

// Lines 5 and 6, box A (b_122a-1.pdf page 1)
export const GROSS_RECEIPTS_LABEL = 'Gross receipts (before all deductions)';

// Lines 5 and 6, box B (b_122a-1.pdf page 1)
export const OPERATING_EXPENSES_LABEL = 'Ordinary and necessary operating expenses';

// Schedule I line 8f, whole but for its last word, "Specify:" (form_b106i.pdf 8f)
export const ASSISTANCE_QUESTION =
  'Other government assistance that you regularly receive. Include cash assistance and the value (if known) of any non-cash assistance that you receive, such as food stamps (benefits under the Supplemental Nutrition Assistance Program) or housing subsidies.';

// Schedule I lines 5a-5h (form_b106i.pdf)
export const DEDUCTION_WORDS: Record<DeductionField, string> = {
  payroll_tax: '5a. Tax, Medicare, and Social Security deductions',
  payroll_mandatory_retirement: '5b. Mandatory contributions for retirement plans',
  payroll_voluntary_retirement: '5c. Voluntary contributions for retirement plans',
  payroll_retirement_loan: '5d. Required repayments of retirement fund loans',
  payroll_insurance: '5e. Insurance',
  payroll_support: '5f. Domestic support obligations',
  payroll_union_dues: '5g. Union dues',
  payroll_other: '5h. Other deductions. Specify:',
};

// Schedule I line 4 (form_b106i.pdf), cut of ". Add line 2 + line 3."
export const SCHEDULE_I_LINE_4 = '4. Calculate gross income';

// Schedule I line 6 (form_b106i.pdf), cut of ". Add lines 5a + … + 5h."
export const SCHEDULE_I_LINE_6 = '6. Add the payroll deductions';

// Schedule I line 7 (form_b106i.pdf), cut of ". Subtract line 6 from line 4."
export const SCHEDULE_I_LINE_7 = '7. Calculate total monthly take-home pay';
