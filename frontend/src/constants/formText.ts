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
import type {
  DeductionField,
  EntryKind,
  ExpenseField,
  ExpenseSpecifyField,
  MaritalStatus,
} from '../types/api';

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

// Schedule J (form_b106j.pdf pages 1-2), asked on the Expenses step. Apostrophes are written
// as ', not the template's typographic one. Each constant names its cut.

// No cut: line 3
export const LINE_3_QUESTION =
  'Do your expenses include expenses of people other than yourself and your dependents?';

// No cut: the heading over lines 4a-4d
export const LINE_4_GROUP_HEADING = 'If not included in line 4:';

// No cut: the heading over lines 15c-15d
export const LINE_15_GROUP_HEADING =
  'Insurance. Do not include insurance deducted from your pay or included in lines 4 or 20.';

// No cut: the heading over lines 20a-20e
export const LINE_20_GROUP_HEADING =
  'Other real property expenses not included in lines 4 or 5 of this form or on Schedule I: Your Income.';

// Cut: the template's trailing "(Official Form 106I.)"
export const NONCASH_EXPENSES_SENTENCE =
  'Include expenses paid for with non-cash government assistance if you know the value of such assistance and have included it on Schedule I.';

// The step's own heading over lines 4-21 (not on the form)
export const EXPENSES_HEADING = 'Your expenses';

export const EXPENSE_LINE_WORDS: Record<ExpenseField, string> = {
  // Line 4, no cut
  rent_or_mortgage:
    'The rental or home ownership expenses for your residence. Include first mortgage payments and any rent for the ground or lot.',
  // Line 4a, no cut
  real_estate_taxes: 'Real estate taxes',
  // Line 4b, no cut
  home_insurance: "Property, homeowner's, or renter's insurance",
  // Line 4c, no cut
  home_maintenance: 'Home maintenance, repair, and upkeep expenses',
  // Line 4d, no cut
  hoa_dues: "Homeowner's association or condominium dues",
  // Line 6's heading without its colon; the amount prints on 6d, "Utilities (combined)"
  utilities: 'Utilities',
  // Line 7, no cut
  food_and_groceries: 'Food and housekeeping supplies',
  // Line 8, no cut
  childcare: "Childcare and children's education costs",
  // Line 9, no cut
  clothing: 'Clothing, laundry, and dry cleaning',
  // Line 10, no cut
  personal_care: 'Personal care products and services',
  // Line 11, no cut
  medical_expenses: 'Medical and dental expenses',
  // Line 12, no cut
  vehicle_maintenance:
    'Transportation. Include gas, maintenance, bus or train fare. Do not include car payments.',
  // Line 13, no cut
  entertainment: 'Entertainment, clubs, recreation, newspapers, magazines, and books',
  // Line 14, no cut
  charitable_contributions: 'Charitable contributions and religious donations',
  // Line 15c, no cut
  vehicle_insurance: 'Vehicle insurance',
  // Line 15d, cut: ". Specify:" (the amount prints "Insurance (combined)")
  insurance_not_deducted: 'Other insurance',
  // Line 16, cut: the "Specify:" that follows, which EXPENSE_SPECIFY_WORDS carries
  taxes_not_deducted:
    'Taxes. Do not include taxes deducted from your pay or included in lines 4 or 20.',
  // Line 17a, no cut
  vehicle_payment: 'Car payments for Vehicle 1',
  // Line 18, no cut
  child_support_paid:
    'Your payments of alimony, maintenance, and support that you did not report as deducted from your pay on line 5, Schedule I, Your Income (Official Form 106I).',
  // Line 19, cut: "Specify:"
  support_others: 'Other payments you make to support others who do not live with you.',
  // Line 20a, no cut
  other_property_mortgages: 'Mortgages on other property',
  // Line 20b, no cut
  other_property_taxes: 'Real estate taxes',
  // Line 20c, no cut
  other_property_insurance: "Property, homeowner's, or renter's insurance",
  // Line 20d, no cut
  other_property_upkeep: 'Maintenance, repair, and upkeep expenses',
  // Line 20e, no cut
  other_property_hoa_dues: "Homeowner's association or condominium dues",
  // Line 21, cut: ". Specify:"
  other_expenses: 'Other',
};

// The field index's labels for the boxes `Other 16`, `Other 19` and `Other 21`
export const EXPENSE_SPECIFY_WORDS: Record<ExpenseSpecifyField, string> = {
  taxes_specify: 'Taxes. Specify:',
  support_others_specify:
    'Other payments you make to support others who do not live with you. Specify:',
  other_expenses_specify: 'Other. Specify:',
};
