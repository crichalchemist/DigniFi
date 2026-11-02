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
import type { EntryKind, MaritalStatus } from '../types/api';

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
