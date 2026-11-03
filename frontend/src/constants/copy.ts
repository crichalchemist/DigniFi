/**
 * Centralized User-Facing Copy
 *
 * All user-visible strings live here for:
 * 1. Reading level validation (Flesch-Kincaid target: grade 6-8)
 * 2. Easy legal review of all user-facing language
 * 3. Future internationalization support
 *
 * UPL disclaimers live in ./upl.ts — this file covers non-legal copy.
 */

import type { YesNo } from '../types/api';

// ============================================================================
// Wizard Copy
// ============================================================================

export const WIZARD_TITLE = 'Bankruptcy Intake';

export const WIZARD_SUBTITLE =
  "We'll guide you through the information needed to understand your options.";

export const WIZARD_HELP_TEXT = 'Your progress is saved. You can come back anytime to finish.';

export const WIZARD_LOADING = 'Starting your intake session...';

export const WIZARD_ERROR_TITLE = 'We encountered an issue';

// ============================================================================
// Step Labels
// ============================================================================

export const STEP_LABELS = {
  debtor_info: 'Your Information',
  income_info: 'Income',
  expense_info: 'Expenses',
  assets: 'Assets',
  debts: 'Amounts Owed',
  review: 'Review & Results',
} as const;

// ============================================================================
// Landing Page Copy
// ============================================================================

export const LANDING_TITLE = 'Your Fresh Start Begins Here';

export const LANDING_SUBTITLE =
  'DigniFi helps you learn about bankruptcy and fill out your court forms. It is free, uses plain language, and treats you with respect.';

export const LANDING_CARD_FREE_TITLE = 'Free to Use';

export const LANDING_CARD_FREE_TEXT =
  "Filing for bankruptcy shouldn't cost money you don't have. DigniFi is completely free — no hidden fees, no premium tiers.";

export const LANDING_CARD_SECURE_TITLE = 'Private & Secure';

export const LANDING_CARD_SECURE_TEXT =
  'Your financial information is encrypted and never shared. We believe your story is yours to tell, on your terms.';

export const LANDING_CARD_INFO_TITLE = 'Legal Information';

export const LANDING_CARD_INFO_TEXT =
  'We explain what the law says in plain language so you can make informed decisions. This is information, not legal advice.';

export const LANDING_DISCLAIMER =
  'DigniFi gives you legal facts, not legal advice. Using this tool does not make us your lawyer. If you need legal advice, please talk to a lawyer in your area.';

// ============================================================================
// Form Dashboard Copy
// ============================================================================

export const DASHBOARD_TITLE = 'Your Court Forms';

export const DASHBOARD_UPL_TITLE = 'Legal Information Notice';

export const DASHBOARD_ERROR = 'Unable to load your forms. Please try again.';

export const DASHBOARD_EMPTY = 'No active intake session. Please complete the intake wizard first.';

export const FILING_FEE_CHANGE_LINK = 'Change how you will pay the fee';

export const FILING_FEE_CHOOSE_LINK = 'Choose how you will pay the fee';

// ============================================================================
// Means Test Preview Copy
// ============================================================================

export const MEANS_TEST_PREVIEW_TITLE = 'Eligibility Estimate';

export const MEANS_TEST_INCOMPLETE =
  'We need your income details first. Then we can show an estimate.';

export const MEANS_TEST_CALCULATING = 'Calculating...';

export const MEANS_TEST_INCOME_LABEL = 'Monthly income for the means test';

// DRAFT: counsel C-3
export const MEDIAN_FOR_HOUSEHOLD_OF = 'Median for Household of';

// ============================================================================
// Auth Copy
// ============================================================================

export const AUTH_LOGIN_TITLE = 'Welcome Back';

export const AUTH_LOGIN_SUBTITLE = 'Sign in to continue your bankruptcy intake.';

export const AUTH_REGISTER_TITLE = 'Create Your Account';

export const AUTH_REGISTER_SUBTITLE = 'Get started with your free bankruptcy intake in minutes.';

// ============================================================================
// Error Messages (Trauma-informed)
// ============================================================================

export const ERROR_NETWORK =
  "We're having trouble connecting. Please check your internet and try again.";

export const ERROR_GENERIC =
  'Something went wrong. Your information is safe — please try again in a moment.';

export const ERROR_SESSION_EXPIRED =
  'Your session has ended. Please sign in again to continue where you left off.';

// ============================================================================
// Amount Box Messages (shown beside the box, see amountError)
// ============================================================================

export const AMOUNT_NEGATIVE = 'Amount cannot be negative';

export const AMOUNT_DECIMALS = 'Please enter dollars and cents, like 1250.50';

export const AMOUNT_TOO_LARGE = 'This amount is too large. Please check it';

// ============================================================================
// Review Step
// ============================================================================

// DRAFT: counsel C-3
export const REVIEW_HOUSEHOLD_COUNT = 'People in your home, counting you';

export const REVIEW_NOW_DIFFERENT = 'Is your income now different?';
export const REVIEW_SPOUSE_NOW_DIFFERENT = "Is your spouse's income now different?";
export const REVIEW_ASSISTANCE = 'Other help from the government';
export const REVIEW_SPOUSE_ASSISTANCE = "Your spouse's other help from the government";
export const REVIEW_ENTRIES = 'Your business or rental income';
export const REVIEW_SPOUSE_ENTRIES = "Your spouse's business or rental income";
export const REVIEW_LINE_3 = "Your expenses include anyone else's";
export const REVIEW_DEDUCTIONS = 'Taken out of your pay, a month';
export const REVIEW_SPOUSE_DEDUCTIONS = "Taken out of your spouse's pay, a month";
export const REVIEW_NO_ENTRIES = 'None';
export const REVIEW_YES_NO: Record<YesNo, string> = { yes: 'Yes', no: 'No' };

// ============================================================================
// Your Information Step
// ============================================================================

export const COUNTY_OUTSIDE_DISTRICT =
  'DigniFi prepares forms only for the Northern District of Illinois. Its 18 counties are the ones in this list.';

// ============================================================================
// Income Step
// ============================================================================

export const SPOUSE_FILING_INFO =
  "DigniFi prepares forms for one person filing alone. It can't prepare a case your spouse files with you.";

export const HOUSEHOLD_NO_NAMES =
  "List everyone who lives with you, and anyone you support who lives somewhere else. Don't include yourself. Don't type anyone's name.";

// DRAFT: counsel C-3
export const LIVES_WITH_YOU_HELP = 'Answer Yes if this person lives in your home with you.';

export const NO_ONE_ELSE = 'No one else lives with me or depends on me.';

export const SPOUSE_DEPENDENT_QUESTION = 'Is your spouse a dependent of yours?';

export const DEPENDENT_GLOSSARY_LEAD = "The court forms' instructions define a dependent as:";

export const AGE_OUT_OF_RANGE = 'Please enter an age from 0 to 120, in whole years';

export const NOT_ANSWERED_YET = 'Not answered yet';

export const BOTH_TOTALS_MONTHLY = 'Both totals are monthly, before taxes and deductions.';

export const SPOUSE_INCOME_HELP =
  "Enter your spouse's average monthly income before taxes. Leave a box blank if your spouse doesn't get that kind of income. If your spouse has no income at all, enter $0 in any box.";

// DRAFT: counsel C-10
export const INCOME_WINDOW_LEAD = 'Your average monthly income for';

// DRAFT: counsel C-10
export const SPOUSE_INCOME_WINDOW_LEAD = "Your spouse's average monthly income for";

// DRAFT: counsel C-10
export const WINDOW_NOTICE_ANSWERED_LEAD = 'Your income figures are your monthly average for';

// DRAFT: counsel C-10
export const WINDOW_NOTICE_NOW_LEAD = 'If you file now, the six months are';

// DRAFT: counsel C-10
export const WINDOW_NOTICE_CHECK = 'Check your income on the Income step.';

// DRAFT: counsel C-10
export const WINDOW_NOTICE_UNANSWERED_LEAD =
  'Check that your income figures are your monthly average for';

export const INCOME_AVERAGE_HEADING = 'Your income: the six-month average';

export const ENTRIES_HEADING = 'Businesses and rental property';

export const ADD_ENTRY = '+ Add a business or property';

export const SPOUSE_ADD_ENTRY = "+ Add your spouse's business or property";

export const NO_ENTRIES = 'I have no business or rental income.';

export const SPOUSE_NO_ENTRIES = 'My spouse has no business or rental income.';

export const ENTRY_DESCRIPTION_HELP =
  "What it is, such as rideshare driving or the property's address";

export const ENTRY_NET_LABEL = 'Net a month';

// DRAFT: counsel C-12
export const FLOOR_AVERAGE_BUSINESS =
  'For your business income, your operating expenses are more than your gross receipts. DigniFi counts this net as $0.00 on Form 122A-1, and on Schedule I unless your income is now different.';

// DRAFT: counsel C-12
export const FLOOR_AVERAGE_RENTAL =
  'For your rental income, your operating expenses are more than your gross receipts. DigniFi counts this net as $0.00 on Form 122A-1, and on Schedule I unless your income is now different.';

// DRAFT: counsel C-12
export const SPOUSE_FLOOR_AVERAGE_BUSINESS =
  "For your spouse's business income, the operating expenses are more than the gross receipts. DigniFi counts this net as $0.00 on Form 122A-1, and on Schedule I unless your spouse's income is now different.";

// DRAFT: counsel C-12
export const SPOUSE_FLOOR_AVERAGE_RENTAL =
  "For your spouse's rental income, the operating expenses are more than the gross receipts. DigniFi counts this net as $0.00 on Form 122A-1, and on Schedule I unless your spouse's income is now different.";

// DRAFT: counsel C-13
export const DOUBLE_COUNT_INCOME_NOTE =
  'If one cost is both for this work and for your home, count each dollar once, in one place only: here or on the Expenses step. How you split it is your choice. Legal aid can help.';

// DRAFT: counsel C-10
export const NOW_DIFFERENT_QUESTION = 'Is your income now different from that average?';

// DRAFT: counsel C-10
export const SPOUSE_NOW_DIFFERENT_QUESTION =
  "Is your spouse's income now different from that average?";

export const INCOME_NOW_HEADING = 'Your income now (a month)';

export const SPOUSE_INCOME_NOW_HEADING = "Your spouse's income now (a month)";

export const START_FROM_AVERAGES = 'Start from my average figures';

export const SPOUSE_START_FROM_AVERAGES = "Start from my spouse's average figures";

// DRAFT: counsel C-12
export const FLOOR_CURRENT_BUSINESS =
  'For your business income now, your operating expenses are more than your gross receipts. DigniFi counts this net as $0.00 on Schedule I.';

// DRAFT: counsel C-12
export const FLOOR_CURRENT_RENTAL =
  'For your rental income now, your operating expenses are more than your gross receipts. DigniFi counts this net as $0.00 on Schedule I.';

// DRAFT: counsel C-12
export const SPOUSE_FLOOR_CURRENT_BUSINESS =
  "For your spouse's business income now, the operating expenses are more than the gross receipts. DigniFi counts this net as $0.00 on Schedule I.";

// DRAFT: counsel C-12
export const SPOUSE_FLOOR_CURRENT_RENTAL =
  "For your spouse's rental income now, the operating expenses are more than the gross receipts. DigniFi counts this net as $0.00 on Schedule I.";

// DRAFT: counsel C-11
export const ASSISTANCE_OWN_BOXES_NOTE =
  'Unemployment and Social Security have their own boxes. They are above.';

export const ASSISTANCE_HEADING = 'Government assistance';

export const SPOUSE_ASSISTANCE_HEADING = "Your spouse's government assistance";

export const CASH_KIND_LABEL = 'Cash assistance: what kind?';

export const CASH_AMOUNT_LABEL = 'How much a month?';

export const NONCASH_KIND_LABEL = 'Non-cash assistance: what kind?';

export const NONCASH_VALUE_LABEL = 'Its value a month, if you know it';

// Plan draft for the owner: 8f's words about the spouse, with no sentence that speaks to the filer
export const SPOUSE_ASSISTANCE_QUESTION =
  'Other government assistance that your spouse regularly receives. Include cash assistance. Include the value of non-cash assistance, if known. Food stamps and housing subsidies are examples.';

export const SPOUSE_CASH_KIND_LABEL = "Spouse's cash assistance: what kind?";

export const SPOUSE_CASH_AMOUNT_LABEL = "Spouse's cash assistance a month";

export const SPOUSE_NONCASH_KIND_LABEL = "Spouse's non-cash assistance: what kind?";

export const SPOUSE_NONCASH_VALUE_LABEL = "Spouse's non-cash assistance value a month, if known";

// Schedule I lines 5a-5h, on the Take-home pay step. §4.5's retirement sentence scored 14.93.
export const PAY_PERIOD_HELP =
  "Paid every two weeks? Multiply one paycheck's amount by 26, then divide by 12. Paid twice a month? Multiply by 2. Paid every week? Multiply by 52, then divide by 12.";

export const RETIREMENT_HELP =
  "Your pay stub, or your employer's benefits office, can tell you this. Mandatory means your job requires it. Voluntary means you chose it.";

export const TAKE_HOME_PAY_INTRO =
  'Enter what is taken out of your pay each month. Leave a box blank if nothing of that kind is taken out. If nothing is taken out at all, enter $0 in one box.';

export const DEDUCTIONS_HEADING = 'Your deductions';

export const SPOUSE_DEDUCTIONS_HEADING = "Your spouse's deductions";

export const OTHER_DEDUCTIONS_SPECIFY_LABEL = 'What are the other deductions?';

export const SPOUSE_OTHER_DEDUCTIONS_SPECIFY_LABEL = "What are your spouse's other deductions?";

export const SPOUSE_DEDUCTION_LABEL_PREFIX = "Spouse's";

// ============================================================================
// Expenses Step
// ============================================================================

// DRAFT: counsel C-13
export const LINE_3_INFO =
  "Line 3 asks about the expenses of anyone other than you and your dependents. One example is a spouse who isn't your dependent.";

// DRAFT: counsel C-13
export const DOUBLE_COUNT_EXPENSES_NOTE =
  'If one cost is both for your home and for a business or rental property, count each dollar once, in one place only: here or as an operating expense on the Income step. How you split it is your choice. Legal aid can help.';

export const EXPENSE_HELP_HOME_MAINTENANCE = 'Repairs and yard work';

export const EXPENSE_HELP_OTHER = 'Costs that fit none of the lines above';

// ============================================================================
// Filing fee page
// ============================================================================

export const FILING_FEE_TITLE = 'How you will pay the filing fee';

// DRAFT: counsel C-7
export const FEE_LIMIT_LEAD = '150% of the official poverty line for a family of';

// DRAFT: counsel C-7
export const FEE_GUIDELINE_LEAD = 'This comes from the HHS poverty guidelines for';

// DRAFT: counsel C-7
export const FEE_FIGURE_LEAD = "Your family's income, as Form 103B counts it from your answers:";

// DRAFT: counsel C-7
export const FEE_COURT_DECIDES =
  'The court decides. The judge also looks at whether you can pay the fee in installments.';

// DRAFT: counsel C-7
export const FEE_INCOME_GAP =
  "Your family size and income can't be shown until your Income step is finished.";

// DRAFT: counsel C-7
export const FEE_NO_TABLE =
  "DigniFi doesn't have the current poverty figures, so it can't show the limit right now.";

// DRAFT: counsel C-7
export const FEE_LINE_5_NOTE =
  'The court decides whether you can pay in installments, from what you write here and the rest of the form.';

export const FEE_OTHER_LINES_NOTE =
  'DigniFi leaves line 8 and Part 3 of Form 103B blank for now, and the details of lines 17 to 20. Form 103B also asks for a copy of your Schedule A/B.';

// Form 103A's title is printed plain: one string can't carry italics
export const INSTALLMENTS_NOTICE =
  "To pay in installments, you also file Form 103A, Application for Individuals to Pay the Filing Fee in Installments. DigniFi doesn't prepare Form 103A yet. You can get it from the court.";

export const FORM_103A_LINK = 'Get Form 103A from the U.S. Courts website';

// The current Official Form 103A page. The URL without "-0" is the superseded Form 3A.
export const FORM_103A_URL =
  'https://www.uscourts.gov/forms-rules/forms/application-individuals-pay-filing-fee-installments-0';

export const FEE_CHOICE_MISSING = 'Choose how you will pay the filing fee.';

export const FEE_READ_FAILED =
  "We couldn't get your answers just now. Please try again in a moment.";

export const FEE_SAVE_FAILED = "We couldn't save your answer just now. Please try again.";
