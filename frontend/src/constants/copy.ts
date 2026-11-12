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

// ============================================================================
// Assets step (Schedule A/B)
// ============================================================================

export const NOTHING_TO_LIST_NOTE =
  "That's okay. Many Americans filing for bankruptcy don't have significant assets. It is not a failure. Answer No to each line that doesn't apply to you.";

// DRAFT: counsel C-14
export const LEASE_NOTE =
  'If you lease this vehicle, what it is worth is yours to say. Legal aid can help you decide.';

export const VALUE_UNKNOWN_BUTTON = "I don't know the value";

// DRAFT: counsel C-15
export const VALUE_UNKNOWN_NOTE =
  'You can come back and change this. Legal aid can help you find out.';

// The heading of Review's list of these rows
export const VALUE_UNKNOWN_HEADING = "You said you don't know the value of these";

export const REMOVE_ON_LINE = 'Remove {n} item(s) you listed on this line?';

export const REMOVE_UNDER_LINE = 'Remove {n} item(s) you listed under this line?';

export const REMOVE_THEM = 'Remove';

export const KEEP_THEM = 'Keep them';

export const ITEM_NUMBER = 'Item {n}';

// The Remove button's name for a screen reader: every row on a Part has one
export const REMOVE_ITEM_ON_LINE = 'Remove item {n} on line {key}';

export const PART_OF_PARTS = 'Part {n} of {total}';

export const ADD_ANOTHER_ITEM = 'Add another';

export const ADD_AN_ITEM = 'Add an item';

export const LINE_NEEDS_AN_ITEM = 'Add what you have, or change it to No.';

// The sentences Complete gives in apps/intake/asset_lines.py, shown after a Part's lines because
// Continue stops first. test_asset_gaps.py pins these to the server's words.
export const GATE_HAS_ONLY_NOS =
  'Line {key} says Yes, but every line under it says No. Change one of them.';

export const ASSET_GAP_NEEDS_AN_ANSWER = 'Line {key} on the Assets step needs a Yes or No.';

export const ASSET_GAP_YES_WITH_NO_ITEM =
  'Line {key} says Yes. Add what you have, or change it to No.';

export const ASSET_GAP_NO_STILL_LISTS =
  'Line {key} says No, but it still lists something. Remove it, or change the answer to Yes.';

export const ASSET_GAP_ROW_NEEDS_MORE = 'Line {key} needs more about "{name}" on the Assets step.';

export const ASSET_GAP_GATE_TAKES_NO_ITEMS = 'Line {key} takes no items. Remove what it lists.';

export const ASSET_GAP_UNDER_GATE =
  "Line {key} is under line {gate}, which isn't answered Yes. Remove what line {key} lists, or answer line {gate} Yes.";

// A row in those sentences before it has words of its own
export const ROW_WITH_NO_NAME = 'one item';

// The screen's words for the form's "Debtor 1 only" and "At least one of the debtors and another"
export const WHO_ONLY_YOU = 'Only you';

export const WHO_WITH_SOMEONE = 'You and someone else';

// Claim gaps (3c3 spec §7.5): the server's sentences, pinned by test_claim_gaps.py

export const NAMELESS_DEBT = 'one amount owed';

export const NAMELESS_CONTRACT = 'one contract';

export const NAMELESS_CODEBTOR = 'one codebtor';

export const CLAIM_GAP_KIND = 'Choose a kind for {name}.';

export const CLAIM_GAP_ADDRESS = 'Enter the street, city, two-letter state and ZIP for {name}.';

export const CLAIM_GAP_STREET_CITY = 'Enter the street and city for {name}.';

export const DEBT_GAP_NO_ANSWER = 'List each amount you owe, or press “I have no amounts owed.”';

export const DEBT_GAP_NONE_BUT_LISTED =
  'You said you have no amounts owed, but some are listed. Remove them, or change that answer.';

export const DEBT_GAP_NO_NAME = 'One amount owed has no creditor name. Enter who you owe.';

export const DEBT_GAP_AMOUNT = 'Enter the amount you owe {name}. It must be above $0.';

export const DEBT_GAP_AMOUNT_NO_NAME =
  'Enter the amount you owe on the row with no creditor name. It must be above $0.';

export const DEBT_GAP_ADDRESS_NO_NAME =
  'Enter the street, city, two-letter state and ZIP on the row with no creditor name.';

export const DEBT_GAP_STREET_CITY_NO_NAME =
  'Enter the street and city on the row with no creditor name.';

export const DEBT_GAP_PROPERTY = 'Choose the property that secures {name}.';

export const DEBT_GAP_DESCRIBE = 'Describe the property that secures {name}.';

export const DEBT_GAP_LIEN = 'Check at least one kind of lien for {name}.';

export const DEBT_GAP_LIEN_OTHER = 'Say what the other kind of lien is, for {name}.';

export const DEBT_GAP_PAYMENT =
  'Enter the monthly payment for {name}. Enter 0 if you pay nothing on it.';

export const DEBT_GAP_HOME_LINE =
  'Say whether {name} is a first mortgage or an additional one, such as home equity.';

export const DEBT_GAP_WHO = 'Answer who owns the property that secures {name}.';

export const DEBT_GAP_STATUS =
  'Check any that fit {name}: contingent, unliquidated or disputed. Or choose None of these.';

export const DEBT_GAP_OFFSET = 'Answer whether {name} is subject to offset.';
export const DEBT_GAP_PRIORITY = 'Answer “Is this amount owed one of these kinds?” for {name}.';
export const DEBT_GAP_PRIORITY_OTHER = 'Fill in “Other. Specify” for {name}.';
export const DEBT_GAP_PAST_DUE =
  'Enter how much of what you owe {name} is past due. Enter 0 if none of it is.';

export const DEBT_GAP_NOTICE = 'Answer whether anyone else is contacting you about {name}.';

export const DEBT_GAP_NOTICE_PARTY =
  'Enter the name and full address of each person contacting you about {name}.';

export const CONTRACT_GAP_NO_ANSWER = 'Answer whether you have any contracts or leases.';

export const CONTRACT_GAP_YES_BUT_NONE =
  'You answered Yes. Add each contract or lease, or change the answer to No.';

export const CONTRACT_GAP_NO_BUT_LISTED =
  'You answered No, but contracts or leases are listed. Remove them, or change the answer to Yes.';

export const CONTRACT_GAP_NO_NAME = "One contract has no name. Enter the other party's name.";

export const CONTRACT_GAP_PURPOSE = 'Enter what the contract or lease is for, for {name}.';

export const CONTRACT_GAP_LEASE_KIND = 'Choose the kind of lease for {name}.';

export const CONTRACT_GAP_VEHICLE = 'Choose the vehicle you lease from {name}.';

export const CONTRACT_GAP_PAYMENT = 'Enter the monthly lease payment for {name}.';

// DRAFT: counsel C-9
export const CONTRACT_GAP_OWES_NOW = 'Answer “Do you owe money on this now?” for {name}.';

export const CONTRACT_GAP_OWED_DEBT =
  'Choose the amount owed that goes with {name}, or add it on the Amounts Owed step.';

export const CONTRACT_GAP_SAME_VEHICLE =
  'Your lease with {name} and your debt to {debt} are on the same vehicle, and each has a monthly payment above $0. Enter the monthly payment once, on either row, and $0 on the other.';

export const CONTRACT_GAP_VEHICLE_NO_NAME = 'Choose the vehicle you lease on the row with no name.';

export const CONTRACT_GAP_SAME_VEHICLE_NO_NAME =
  'Your lease on the row with no name and your debt to {debt} are on the same vehicle, and each has a monthly payment above $0. Enter the monthly payment once, on either row, and $0 on the other.';

export const CODEBTOR_GAP_NO_ANSWER = 'Answer whether you have any codebtors.';

export const CODEBTOR_GAP_YES_BUT_NONE =
  'You answered Yes. Add each codebtor, or change the answer to No.';

export const CODEBTOR_GAP_NO_BUT_LISTED =
  'You answered No, but codebtors are listed. Remove them, or change the answer to Yes.';

export const CODEBTOR_GAP_COMMUNITY =
  'Did you live in a community property state or territory in the last 8 years? Answer Yes or No.';

export const CODEBTOR_GAP_SPOUSE_LIVED =
  'Answer whether your spouse, former spouse or legal equivalent lived with you then.';

export const CODEBTOR_GAP_SPOUSE_DETAILS =
  'Enter the community property state, and that person’s name and full address.';

export const CODEBTOR_GAP_NO_NAME = "One codebtor has no name. Enter the person's name.";

export const CODEBTOR_GAP_NO_LINK =
  'Choose which amounts owed or contracts {name} shares with you.';

// Asked on a line 1 or line 4 row, since Schedule J lines 4, 5 and 20a read it (3c3 spec §8)
export const LIVES_HERE_QUESTION = 'Do you live here?';

export const AB_ADDRESS_LINE_2_LABEL = 'Address, second line';

// The name of a kind's box on lines 17, 22, 28 and 29, where the form prints none
export const AB_KIND_LABEL = 'Which one';

// The name of the text box on lines 47, 49 and 50, where the form prints only "Yes"
export const AB_TEXT_LABEL = 'What you have';

export const OUT_OF_RANGE_PERCENT = 'Please enter a number from 0 to 100, with up to 2 decimals.';

// Beside a box holding part of a number ("-"), whose earlier figure stays until a number replaces it
export const AMOUNT_NOT_A_NUMBER = 'Please enter a number.';

// Rows from before the step asked the form's lines (3b spec §9). Says why Continue waits.
export const OLD_ROWS_HEADING = 'Items you listed earlier';

export const OLD_ROWS_NOTE =
  'We now ask about what you own line by line, in the words of the form. Choose the line each of these goes on, or remove it. You can continue once each one has a line.';

export const OLD_ROW_LINE_LABEL = 'Which line does this go on?';

export const OLD_ROW_LINE_PLACEHOLDER = 'Choose a line';

// The blank first option of a select with no answer yet
export const CHOOSE_ONE = 'Choose one';

// What the step called a row's type before it asked the form's lines. Not the form's words, and
// never a suggestion of a line.
export const OLD_ASSET_TYPE_WORDS: Record<string, string> = {
  real_property: 'Real estate or home',
  vehicle: 'Vehicle',
  bank_account: 'Bank account',
  retirement_account: 'Retirement account',
  personal_property: 'Personal property',
  other: 'Other',
};

// The server's own name for a row with nothing to name it by (_row_name in asset_lines.py)
export const ONE_ITEM = 'One item';

export const REVIEW_VALUE_NOT_KNOWN = "You don't know";

export const REVIEW_ASSET_PART = 'Part {n}: {title}';

export const REVIEW_ASSET_ROW = 'Line {key}: {name}';

// A button's name for a screen reader, where the list repeats one button per row
export const GO_TO_STEP_FOR_ROW = 'Go to {step} for {row}';

// The Amounts Owed step (3c3 Task 8)

// DRAFT: counsel C-9
export const ADDRESS_HELP =
  'The court uses this address to send the creditor notice of your case. A bill, a letter from the creditor or a credit report may show it. Legal aid can help you find it.';

// DRAFT: counsel C-9
export const AMOUNT_HELP =
  'A recent bill, a letter from the creditor or a credit report may show the amount. Legal aid can help you find it.';

// Counsel's caution (spec §11 C2): keep "unliquidated" from implying the amount can be left
// blank, since the amount box above it is required above $0.
// DRAFT: counsel C-9
export const CLAIM_STATUS_HELP =
  'Contingent means it depends on something that has not happened yet. Unliquidated means the amount has not been set. Disputed means you or the creditor disagree about whether you owe it, or how much.';

// DRAFT: counsel C-9
export const OFFSET_HELP =
  'Offset means the creditor may take money it owes you, such as money in your account with it. It uses that money to pay part of this debt.';

// DRAFT: counsel C-2
export const PRIORITY_QUESTION = 'Is this amount owed one of these kinds?';

// DRAFT: counsel C-2
export const PRIORITY_DOMESTIC_SUPPORT_HELP =
  'Child support, or support for a spouse or former spouse. A court order, a divorce or separation agreement, or a government agency sets it.';

// DRAFT: counsel C-2
export const PRIORITY_TAXES_HELP =
  'Certain taxes, such as some income taxes, and certain other debts owed to the government. Not every debt owed to the government is one.';

// DRAFT: counsel C-2
export const PRIORITY_INTOXICATED_HELP =
  'Money owed for a death or injury caused by a car or other motor vehicle, or by a boat. It applies only if the person at the controls was intoxicated.';

// DRAFT: counsel C-2
export const PRIORITY_OTHER_HELP =
  'A few other kinds the law lists, such as wages owed to a worker. Legal aid can tell you whether yours is one.';

// DRAFT: counsel C-2
export const PRIORITY_NO = 'No, none of these';

// DRAFT: counsel C-2
export const PRIORITY_NOT_SURE = 'Not sure';

// DRAFT: counsel C-2
export const PRIORITY_NOT_SURE_NOTE =
  'If you are not sure, this amount goes in Part 2 of Schedule E/F, with your other amounts owed. You can change your answer later. Legal aid can help you find out which part fits.';

// DRAFT: counsel C-2
export const PRIORITY_SPLIT_HELP =
  "If the bill or notice shows a priority amount and a nonpriority amount, copy them here. Leave a box blank if it doesn't show them.";

// DRAFT: counsel C-2
export const PAST_DUE_LABEL = 'How much of this is past due as of the day you file?';

// DRAFT: counsel C-2
export const PAST_DUE_HELP =
  'Leave out amounts that are not due yet. Enter 0 if none of it is past due.';

export const REVIEW_PAST_DUE = 'Past due';

// DRAFT: counsel C-18
export const SECURED_QUESTION = 'Can the lender take back property if you do not pay?';

// DRAFT: counsel C-18
export const LIEN_HELP = 'A lien is a legal claim on property that backs up what you owe.';

// DRAFT: counsel C-1
export const CO_OWNED_NOTE = 'Which value applies is something legal aid can help you decide.';

// DRAFT: counsel C-17
export const NOTICE_QUESTION = 'Is anyone else contacting you about this amount owed?';

// DRAFT: counsel C-17
export const NOTICE_HELP =
  'List the creditor above. Here, list anyone else who contacts you about this amount, such as a collection agency or a law firm.';

export const NO_DEBTS_BUTTON = 'I have no amounts owed';

export const CLAIM_STATUS_NONE = 'None of these';

export const OUTSIDE_US_LABEL = 'This address is outside the United States';

export const OUTSIDE_US_HELP =
  'Type the whole address in the street and city boxes, with the country. Leave the state and ZIP boxes empty.';

export const SECURING_PROPERTY_LABEL = 'The property for this amount owed';

export const SECURING_PROPERTY_NONE =
  'Only property listed on the Assets step shows here. To choose other property, list it on the Assets step.';

export const LIEN_OTHER_LABEL = 'What kind of lien is it?';

export const HOME_LINE_QUESTION = 'Which kind of mortgage is this?';

export const PAYMENT_SECURED_HELP = 'Enter 0 if you pay nothing on it.';

export const DATE_INCURRED_HELP = 'Month and year, if you know them. You can leave this empty.';

export const ACCOUNT_SAVED = 'Saved. It ends in {last4}.';

export const NOTICE_PARTY_HEADING = 'Person or company {n}';

export const ADD_ANOTHER_PARTY = 'Add one more person or company';

export const REMOVE_PARTY = 'Remove person or company {n} on amount owed {debt}';

// DigniFi's words, not printed text: cut from Schedule J lines 4 and 5, which print "first
// mortgage payments" and "Additional mortgage payments for your residence, such as home equity
// loans", cut to the loan since the filer answers about the loan
export const HOME_LINE_FIRST = 'First mortgage';

export const HOME_LINE_ADDITIONAL = 'Additional mortgage, such as a home equity loan';

export const SECURED_PREFILLED_NOTE =
  'We filled this in from the kind of amount owed. Change it if it is wrong.';

export const DEBTS_STEP_WHY =
  'Your answers here fill in Schedules D and E/F, the court forms that list who you owe.';

export const LEASE_KIND_LABEL = 'Kind of lease';

export const VEHICLE_LEASE_LABEL = 'Vehicle you lease';

export const VEHICLE_LEASE_HELP =
  'The vehicles you listed on the Assets step are here. To add one, go back to that step.';

export const LEASE_PAYMENT_LABEL = 'Monthly lease payment';

// DRAFT: counsel C-9
export const OWES_NOW_QUESTION = 'Do you owe money on this now?';

// DRAFT: counsel C-9
export const OWES_NOW_PICK_LABEL = 'Which amount owed goes with this?';

// DRAFT: counsel C-9
export const OWES_NOW_ADD_HELP =
  'If it is not in this list, add it on the Amounts Owed step. Then come back and pick it.';

export const GO_TO_AMOUNTS_OWED = 'Go to Amounts Owed';

export const CONTRACTS_STEP_WHY =
  'Your answers here fill in Schedule G, the court form that lists your contracts and leases.';

// DRAFT: counsel C-9
export const CONTRACT_ADDRESS_HELP =
  'The court uses this address to send the other party notice of your case.';

export const CODEBTOR_LINKS_HELP =
  'Check each amount owed or contract this person is also responsible for.';

export const CODEBTOR_LINKS_DEBTS = 'Amounts owed';

export const CODEBTOR_LINKS_CONTRACTS = 'Contracts and leases';

export const CODEBTOR_LINKS_NONE =
  'You have not added any amounts owed or contracts yet. Add them on their steps, then come back.';

export const CODEBTORS_STEP_WHY =
  'Your answers here fill in Schedule H, the court form that lists people who owe a debt with you.';

// DRAFT: counsel C-9
export const CODEBTOR_ADDRESS_HELP =
  'The court uses this address to send this person notice of your case.';

export const REVIEW_NO_DEBTS = 'You said you have no amounts owed.';

export const REVIEW_RENT_OR_LOT_RENT = 'Rent or lot rent';

export const REVIEW_TYPED_TOTAL = 'Expenses you entered';

export const REVIEW_LINKED_PAYMENTS = 'Payments you linked on Amounts Owed and Contracts & Leases';

export const REVIEW_MONTHLY_TOTAL = 'Total monthly expenses';

export const REVIEW_NO_CONTRACTS = 'You said you have no contracts or leases.';

export const REVIEW_NO_CODEBTORS = 'You said you have no codebtors.';

export const REVIEW_UNNAMED_CONTRACT = 'Unnamed contract';

export const REVIEW_UNNAMED_CODEBTOR = 'Unnamed codebtor';

export const CLAIM_GAP_LEGACY_VEHICLE =
  'You told us you pay ${typed} a month for a car, and the payments you linked add up to ${linked}. Add the rest to the loan on Amounts Owed or the lease on Contracts & Leases, or remove this figure.';

export const CLAIM_GAP_LEGACY_OTHER =
  'You told us you pay ${typed} a month in mortgages on other property, and the payments you linked add up to ${linked}. Add the rest to the mortgage on Amounts Owed, or remove this figure.';

export const CLAIM_GAP_LINE_4 =
  'You entered ${typed} for rent or lot rent, and your first mortgage on Amounts Owed is ${linked} a month. Line 4 adds them. Do you pay both?';

export const LINE_4_HELP =
  'Rent, or rent for the lot your home sits on. A first mortgage you list on Amounts Owed is added to this line for you.';

export const EXPENSES_LINKED_NOTE =
  'Car and mortgage payments come from Amounts Owed and Contracts & Leases, so they are not in this total.';

export const LINE_4_PAY_BOTH = 'Yes, I pay both';

export const LINE_4_CLEAR = 'No, clear the ${typed}';

export const NOT_SAVED_TRY_AGAIN = 'That was not saved. Try again.';

export const LEGACY_REMOVE = 'Remove this figure';

// ============================================================================
// Exemptions page
// ============================================================================

// DRAFT: counsel C-8
export const EXEMPTION_LAW_SUMMARIES: Record<string, string> = {
  il_40_5_4_135: "A firefighter's pension, and the fund that pays it.",
  il_215_5_238:
    'Money from life insurance and annuities. It covers money paid to a spouse, child, parent or other dependent of the insured.',
  il_305_5_11_3: 'Public aid, and certain child care payments, under the Illinois Public Aid Code.',
  il_735_5_12_901:
    'A home that a person owns or holds by lease and lives in, such as a house, a condo or a co-op, up to the limit.',
  il_735_5_12_1001_a:
    'Things in a home and things a person owns, such as furniture, clothes, pets, phones and computers.',
  il_735_5_12_1001_b:
    'The equity in any other property, up to the limit. Equity is what the property is worth, less what is owed on it.',
  il_735_5_12_1001_c: 'One motor vehicle, up to the limit.',
  il_735_5_12_1001_d: "Tools, books and equipment for a person's trade or profession.",
  il_735_5_12_1001_e: 'Health aids that a professional prescribed for a person or a dependent.',
  il_735_5_12_1001_f:
    'Life insurance money and cash value. It covers money paid to a spouse, child, parent or other dependent of the insured.',
  il_735_5_12_1001_g1:
    'The right to get certain benefits. These are social security, unemployment pay and public aid.',
  il_735_5_12_1001_g2: "The right to get a veteran's benefit.",
  il_735_5_12_1001_g3:
    'The right to get a benefit for a disability or an illness, or for being out of work.',
  il_735_5_12_1001_g4: 'The right to get alimony or support. It also covers separate maintenance.',
  il_735_5_12_1001_h1:
    'An award under a law for crime victims. This covers the right to get it and property that came from it.',
  il_735_5_12_1001_h2:
    'A wrongful death payment for someone the person depended on. This covers the right to get it and property that came from it.',
  il_735_5_12_1001_h3:
    'A life insurance payment on someone the person depended on. This covers the right to get it and property that came from it.',
  il_735_5_12_1001_h4:
    'A payment for a bodily injury. This covers the right to get it and property that came from it.',
  il_735_5_12_1001_h5:
    'Restitution under the federal Civil Liberties Act of 1988. This covers the right to get it and property that came from it.',
  il_735_5_12_1001_i: "The right to get a crime victims' award under Illinois law.",
  il_735_5_12_1006: 'Retirement plans, such as a pension plan or an IRA.',
  il_820_305_21: "Money from workers' compensation, and claims and awards for it.",
  us_11_522_b3c: 'Retirement funds in an account that is exempt from federal income tax.',
  us_38_5301: "Veterans' benefits.",
  us_42_407: 'Social Security benefits.',
};

export const EXEMPTION_GAP_LINE_1 = 'Choose which set of exemptions you are claiming.';
export const EXEMPTION_GAP_NO_CLAIMS =
  "Add the property you claim as exempt, or press “I'm not claiming any property as exempt.”";
export const EXEMPTION_GAP_NO_ITEMS = "Press “I'm not claiming any property as exempt.”";
export const EXEMPTION_GAP_ITEM_GONE =
  'One claim is for property that is no longer on your property list. Remove it or choose the property again.';
export const EXEMPTION_GAP_LAW = 'Choose the law for {name}.';
export const EXEMPTION_GAP_LAW_CHANGED =
  'The list of laws has changed since you chose a law for {name}. Choose a law again.';
export const EXEMPTION_GAP_AMOUNT_KIND =
  'Choose a dollar amount or 100% of fair market value for {name}.';
export const EXEMPTION_GAP_AMOUNT = 'Enter the dollar amount you claim for {name}.';
export const EXEMPTION_GAP_DESCRIPTION = 'Type a shorter description of {name} for Schedule C.';
export const EXEMPTION_GAP_LINE_3 = 'Answer line 3, the homestead question.';
export const EXEMPTION_GAP_LINE_3_1 = 'Answer the second part of line 3.';

export const EXEMPTIONS_TITLE = 'The property you claim as exempt';
// DRAFT: counsel C-8
export const EXEMPTIONS_INTRO =
  'On Schedule C, you list the property you claim as exempt. For each claim, you choose the law and the amount. The limits shown here come from the laws themselves.';
// DRAFT: counsel C-8
export const EXEMPTIONS_NOTE_12_1201 =
  'The Illinois law 735 ILCS 5/12-1201 says residents of Illinois are prohibited from using the federal exemptions in 11 U.S.C. § 522(d), except as Illinois law otherwise permits.';
// DRAFT: counsel C-8
export const EXEMPTIONS_NOTE_DOMICILE =
  "Which state's laws apply depends on where you have lived. The rule, in 11 U.S.C. § 522(b)(3)(A), looks at where your legal home was for the 730 days before you file. If it was not in one state that whole time, the rule looks at where it was for most of the 180 days before that. If that rule leaves a person with no exemptions at all, the person may use the list in 11 U.S.C. § 522(d) instead. Legal aid can help you find out which set is yours.";
// Page only: a new claim row with no property yet (P20). The server never sees one.
export const EXEMPTION_GAP_CHOOSE_ITEM = 'Choose the property for each new claim.';
export const EXEMPTIONS_NOT_CLAIMING_BUTTON = "I'm not claiming any property as exempt";
export const EXEMPTIONS_NO_TABLE =
  "DigniFi doesn't have the exemption laws for today's date yet, so it can't prepare Schedule C.";
export const EXEMPTIONS_READ_FAILED =
  "We couldn't get your answers just now. Please try again in a moment.";
export const EXEMPTIONS_SAVE_FAILED = "We couldn't save your answers just now. Please try again.";
export const EXEMPTIONS_DESCRIPTION_DOESNT_FIT =
  "This description doesn't fit in its box on Schedule C. Type a shorter one. The form can't print some letters and symbols, such as emoji.";
export const EXEMPTIONS_OTHER_LAW_DOESNT_FIT =
  "This law doesn't fit in its box on Schedule C. Type a shorter one. The form can't print some letters and symbols, such as emoji.";
// DRAFT: counsel C-8
export const EXEMPTION_NO_LIMIT = 'This law names no dollar limit.';
// DRAFT: counsel C-8
export const EXEMPTION_TOTAL_DOLLARS = 'Amounts entered under this law: {amount}';
// DRAFT: counsel C-8
export const EXEMPTION_TOTAL_FAIR_MARKET =
  '{n} more claimed at 100% of fair market value, up to any limit the law sets.';
export const EXEMPTION_DESCRIPTION_TOO_LONG =
  'This description is too long for the box on Schedule C. Type a shorter one for this form.';
export const EXEMPTION_ITEM_GONE =
  'This claim was for property that is no longer on your property list. Its law and amount are still here. Remove the claim, or choose the property again.';
export const EXEMPTIONS_NO_ITEMS =
  'No property is listed on the Assets step yet, so there is nothing to claim here.';
export const EXEMPTIONS_LAWS_HEADING = 'The list of laws';
export const EXEMPTIONS_ILLINOIS_LAWS = 'Illinois laws';
export const EXEMPTIONS_FEDERAL_LAWS = 'Federal laws';
export const EXEMPTIONS_CLAIMS_HEADING = 'Your claims';
export const EXEMPTIONS_ADD_CLAIM = 'Add a claim';
export const EXEMPTIONS_PROPERTY_LABEL = 'Property';
export const EXEMPTIONS_LAW_LABEL = 'Law';
export const EXEMPTIONS_ANOTHER_LAW = 'Another law';
export const EXEMPTIONS_CHOOSE_ONE = 'Choose one';
export const EXEMPTIONS_AMOUNT_LABEL = 'Amount you claim';
export const EXEMPTIONS_DOLLAR_AMOUNT = 'A dollar amount';
export const EXEMPTIONS_SHORT_LABEL = 'A shorter description for Schedule C';
export const EXEMPTIONS_REMOVE_CLAIM = 'Remove this claim';
export const EXEMPTIONS_TOTALS_HEADING = 'Totals by law';
