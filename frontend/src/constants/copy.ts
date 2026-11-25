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

import type { ScheduleITextKey, YesNo } from '../types/api';
import type { ClaimTextKey } from './claimTextLimits';

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

export const DASHBOARD_GATES_ONE =
  "1 answer is still missing. Your forms can't be prepared until it is given.";

export const DASHBOARD_GATES_MANY =
  "{count} answers are still missing. Your forms can't be prepared until each is given.";

export const DASHBOARD_GAPS_ONE = '1 answer is blank on your forms.';

export const DASHBOARD_GAPS_MANY = '{count} answers are blank on your forms.';

export const FILING_FEE_CHANGE_LINK = 'Change how you will pay the fee';

export const FILING_FEE_CHOOSE_LINK = 'Choose how you will pay the fee';

// ============================================================================
// Means Test Preview Copy
// ============================================================================

// DRAFT: counsel C-24
export const MEANS_TEST_PREVIEW_TITLE = 'Income test';

// DRAFT: counsel C-24
export const MEANS_TEST_UPDATING = 'Updating your result...';

// DRAFT: counsel C-24
export const MEANS_TEST_WAITING = "We'll show your result once you enter your income.";

// DRAFT: counsel C-24
export const MEANS_TEST_UNAVAILABLE =
  "DigniFi can't show your result right now. This is not an error with your information.";

export const MEANS_TEST_CALCULATING = 'Calculating...';

export const MEANS_TEST_INCOME_LABEL = 'Monthly income for the means test';

// DRAFT: counsel C-24
export const MEANS_OUTCOME_BELOW =
  "Your income is at or below the median for a household of {n} in Illinois. Form 122A-2 doesn't apply to you.";

// DRAFT: counsel C-24
export const MEANS_OUTCOME_ABOVE =
  'Your income is above the median for a household of {n}, so Form 122A-2 applies.';

// DRAFT: counsel C-24
export const MEANS_OUTCOME_REASSURANCE =
  "Being above the median doesn't mean a presumption of abuse applies.";

// DRAFT: counsel C-24
export const MEANS_OUTCOME_NO_PRESUMPTION =
  "The form's arithmetic gives: There is no presumption of abuse.";

// DRAFT: counsel C-24
export const MEANS_OUTCOME_PRESUMPTION =
  "The form's arithmetic gives: There is a presumption of abuse.";

// DRAFT: counsel C-39
export const MEANS_OUTCOME_NOT_CONSUMER =
  'You answered that your debts are not primarily consumer debts. Form 122A-1Supp says that a filer who answers this way checks box 1 on Form 122A-1, signs Part 3 and submits this supplement with it. Your packet follows the form.';

// DRAFT: counsel C-39
export const MEANS_OUTCOME_VETERAN =
  'You answered Yes to both questions on line 2 of Form 122A-1Supp. The form says that a filer who answers this way checks box 1 on Form 122A-1, signs Part 3 and submits this supplement with it. Your packet follows the form.';

// DRAFT: counsel C-39
export const MEANS_OUTCOME_MILITARY =
  "You chose one of the service categories on line 3 of Form 122A-1Supp. The form says that a filer who answers this way checks box 3 on Form 122A-1 and doesn't fill out the rest of that form during the exclusion period. The form counts back 540 days from the day you file; DigniFi doesn't check that. Your packet follows the form.";

// DRAFT: counsel C-24
export const MEANS_TABLE_MISSING =
  "DigniFi doesn't have the means test figures for today's date yet, so it can't work out Form 122A-2.";

// DRAFT: counsel C-24
export const MEANS_LINE_MISSING =
  "DigniFi can't work out every line of Form 122A-2, so it can't print that form. Form 122A-1 waits for it. File the two forms together.";

// DRAFT: counsel C-24
export const MEANS_PAIR_REFUSAL = 'File Form 122A-1 and Form 122A-2 together.';

// DRAFT: counsel C-39
export const MEANS_SUPP_PAIR_REFUSAL = 'File Form 122A-1 and Form 122A-1Supp together.';

// DRAFT: counsel C-39
export const MEANS_MILITARY_OPEN =
  'Answer each question about military service on the Amounts Owed step. Form 122A-2 waits for those answers.';

// DRAFT: counsel C-24
export const MEANS_PAIR_CONFIRM = 'These two forms go together. Mark both as filed?';

// DRAFT: counsel C-24
export const MEANS_PAIR_MARK_BOTH = 'Mark both as filed';

// DRAFT: counsel C-24
export const MEANS_PAIR_MARK_ALONE = 'Mark as filed';

// DRAFT: counsel C-24
export const MEANS_PAIR_CANCEL = 'Cancel';

// DRAFT: counsel C-24
export const MEANS_PAIR_NOTICE =
  'Form 122A-1 says your result is worked out on Form 122A-2. File them together.';

// DRAFT: counsel C-39
export const MEANS_SUPP_PAIR_NOTICE =
  'Form 122A-1Supp says to submit it with the signed Form 122A-1. File them together.';

// DRAFT: counsel C-24
export const MEANS_FILED_BEFORE_122A2 =
  'This copy was marked filed before DigniFi could fill in all of Form 122A-2. It shows what was stored then.';

// DRAFT: counsel C-24
export const MEANS_FILED_BEFORE_122A1 =
  'This copy was marked filed before DigniFi could fill in Form 122A-2, which this form points to. It shows what was stored then.';

// DRAFT: counsel C-24
export const MEANS_FILED_MISMATCH =
  "This copy doesn't say its result is worked out on Form 122A-2. Form 122A-2 now applies to you.";

// DRAFT: counsel C-39
export const MEANS_FILED_BOX_2_NOW_SUPP =
  'This filed copy has box 2 checked. With your current answers, your packet holds Form 122A-1Supp, and Form 122A-1 checks a different box.';

// The Form 122A-2 page (3h2)

// DRAFT: counsel C-24
export const MEANS_OUTCOME_ANSWER_SIDEBAR =
  "Its result can't be worked out until you answer the questions on the Form 122A-2 page, once you finish your intake.";

// DRAFT: counsel C-24
export const MEANS_OUTCOME_ANSWER_PAGE =
  "Its result can't be worked out until you answer the questions on the Form 122A-2 page.";

// DRAFT: counsel C-24
export const MEANS_PAGE_PHRASE = 'the Form 122A-2 page';

// DRAFT: counsel C-39
export const MEANS_OUTCOME_ANSWER_DEBTS =
  "Its result can't be worked out until you answer the questions on the Amounts Owed step.";

// DRAFT: counsel C-39
export const MEANS_DEBTS_STEP_PHRASE = 'the Amounts Owed step';

// DRAFT: counsel C-24
export const MEANS_LINE_43_LINK = 'Go to line 43, special circumstances';

// DRAFT: counsel C-24
export const MEANS_STALE_ANSWERS =
  "You answered the questions about your secured debts in {month}. If you've made payments since, check your answers on the Form 122A-2 page.";

// DRAFT: counsel C-24
export const MEANS_RESULT_CHANGED =
  'Your result has changed. It is at the top of the page. Press Continue again when you are ready.';

// DRAFT: counsel C-24
export const MEANS_PAGE_INTRO =
  "Form 122A-2 is the Chapter 7 means test calculation. Its questions use the form's own words, which can differ from the words on Schedules I and J. Beside some questions, DigniFi shows what you entered on those schedules, for you to compare. No answer is filled in for you.";

// DRAFT: counsel C-24
export const MEANS_PAGE_AGES =
  'Line 7 counts people under 65 and people 65 or older. DigniFi uses your date of birth and the ages on your household list, as you entered them.';

// DRAFT: counsel C-24
export const MEANS_PAGE_LOADING = 'Loading your answers...';

// DRAFT: counsel C-24
export const MEANS_PAGE_READ_FAILED =
  "We couldn't get your answers just now. Please try again in a moment.";

// DRAFT: counsel C-24
export const MEANS_PAGE_SAVE_FAILED = "We couldn't save your answers just now. Please try again.";

// DRAFT: counsel C-24
export const MEANS_PAGE_UPDATED =
  'Your intake changed after this page opened. The page now shows your latest answers. Check them, then press Continue again.';

// DRAFT: counsel C-24
export const MEANS_BESIDE_YOU = 'You entered {amount} on Schedule {form} line {line}.';

// DRAFT: counsel C-24
export const MEANS_BESIDE_SPOUSE =
  'You entered {amount} for your spouse on Schedule {form} line {line}.';

// DRAFT: counsel C-24
export const MEANS_LINE_7G = 'Your line 7 total is {amount}.';

// DRAFT: counsel C-24
export const MEANS_LINE_8 = 'Your line 8 amount is {amount}.';

// DRAFT: counsel C-24
export const MEANS_LINE_15_CAP =
  "The IRS amount for public transportation is {amount}. Line 15 can't be more than that.";

// DRAFT: counsel C-27
export const MEANS_LINE_27_NOTE =
  'The form says the court must keep the nature of these expenses confidential. DigniFi asks only for the amount.';

// DRAFT: counsel C-24
export const MEANS_LINE_29_NOTE = 'The form allows up to {amount} a month for each child.';

// DRAFT: counsel C-24
export const MEANS_LINE_30_CAP =
  "For {n} people, 5% of the IRS food and clothing amounts is {amount}. Line 30 can't be more than that.";

// DRAFT: counsel C-24
export const MEANS_LINE_30_CAP_ONE =
  "For 1 person, 5% of the IRS food and clothing amounts is {amount}. Line 30 can't be more than that.";

// DRAFT: counsel C-24
export const MEANS_LINE_35 =
  'Line 35 comes from what you entered as past due for priority debts on the Amounts Owed step: {amount}.';

// DRAFT: counsel C-24
export const MEANS_ADD_ROW = 'Add a row';

// DRAFT: counsel C-24
export const MEANS_REMOVE_ROW = 'Remove row {n}';

// DRAFT: counsel C-24
export const MEANS_ROW_LEGEND = 'Row {n}';

// DRAFT: counsel C-24
export const MEANS_DEBT_PROPERTY = 'Secured by {property}';

// DRAFT: counsel C-24
export const MEANS_DEBT_GOES_ON = 'On Form 122A-2, this debt goes on line {line}.';

// DRAFT: counsel C-24
export const MEANS_DEBT_WAITS = 'Its line depends on your answers about your vehicles above.';

// DRAFT: counsel C-24
export const MEANS_DEBT_PAYMENT =
  'You entered a monthly payment of {amount} on the Amounts Owed step.';

// DRAFT: counsel C-24
export const MEANS_PAYMENTS_LEFT = 'How many payments are left?';

// DRAFT: counsel C-24
export const MEANS_SIXTY_OR_MORE = '60 or more';

// DRAFT: counsel C-24
export const MEANS_PAYMENT_CHANGES = 'Will the payment change, or end with a larger payment?';

// DRAFT: counsel C-24
export const MEANS_SIXTY_MONTH_TOTAL = 'The total due in the 60 months after you file';

// DRAFT: counsel C-6
export const MEANS_LINE_36_LINK = 'Bankruptcy Basics, from the U.S. Courts';

// DRAFT: counsel C-6
export const MEANS_LINE_36_LIMITS =
  'Chapter 13 has debt limits (11 U.S.C. section 109(e)). For cases filed on or after {date}, the limits are {unsecured} in unsecured debts and {secured} in secured debts.';

// DRAFT: counsel C-6
export const MEANS_LINE_36_TOTALS =
  'You listed {ef} in unsecured debts on Schedule E/F. You listed {d} in secured debts on Schedule D.';

// DRAFT: counsel C-6
export const MEANS_LINE_36_OTHER_RULES =
  "Other rules also apply. DigniFi can't tell you whether you can file under chapter 13.";

// DRAFT: counsel C-6
export const MEANS_LINE_36_MULTIPLIER =
  "The U.S. Trustee's multiplier for the Northern District of Illinois is {m}%.";

// DRAFT: counsel C-6
export const MEANS_LINE_36_PRODUCT =
  'The average monthly administrative expense is {m}% of {payment}. That is {product}.';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_TITLE = "Your spouse's vehicles and loans";

// DRAFT: counsel C-34
export const MEANS_SPOUSE_INTRO =
  "These questions are about your spouse's vehicles and loans. Leave out a vehicle on your property list and a loan your Amounts Owed step lists as secured.";

// DRAFT: counsel C-34
export const MEANS_SPOUSE_VEHICLES_QUESTION =
  "Does your spouse have a vehicle that isn't on your property list?";

// DRAFT: counsel C-34
export const MEANS_SPOUSE_VEHICLE_DESCRIBE =
  'Describe the vehicle, such as its year, make and model.';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_VEHICLE_LEASED = 'Is this vehicle leased?';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_VEHICLE_LEGEND = "Your spouse's vehicle {n}";

// DRAFT: counsel C-34
export const MEANS_SPOUSE_ADD_VEHICLE = 'Add a vehicle';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_REMOVE_VEHICLE = "Remove your spouse's vehicle {n}";

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOANS_QUESTION =
  'Does your spouse owe a loan on your home, a vehicle or other property?';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOANS_HINT =
  'Leave out a loan your Amounts Owed step lists as secured. Count a loan you both owe on property only your spouse owns.';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOAN_LEGEND = "Your spouse's loan {n}";

// DRAFT: counsel C-34
export const MEANS_SPOUSE_ADD_LOAN = 'Add a loan';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_REMOVE_LOAN = "Remove your spouse's loan {n}";

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOAN_ON_AMOUNTS_OWED = 'Is this loan on your Amounts Owed step?';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOAN_WHICH = 'Which loan is it?';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOAN_WHICH_NOTE =
  "This list shows the loans on your Amounts Owed step that aren't listed as secured.";

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOAN_CREDITOR = 'Who does your spouse owe?';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOAN_SECURED_BY = 'What secures the loan?';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOAN_HOME = 'Your home';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOAN_OTHER = 'Other property';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOAN_PROPERTY = 'Describe the property.';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOAN_PAYMENT = 'The monthly payment';

// DRAFT: counsel C-34
export const MEANS_SPOUSE_LOAN_FROM = "Your spouse's loan from {name}";

// DRAFT: counsel C-31
export const MEANS_LINE_43_EXAMPLES =
  'The law gives two examples of special circumstances. One is a serious medical condition. The other is a call or order to active duty in the Armed Forces.';

// DRAFT: counsel C-30
export const MEANS_LINE_43_OWN_WORDS =
  'Line 43 is about your monthly expenses and income now. You can explain your situation in your own words.';

// DRAFT: counsel C-31
export const MEANS_LINE_43_NO_SUGGESTION =
  "DigniFi doesn't say which circumstances apply to you, or whether a court will allow them.";

// DRAFT: counsel C-31
export const MEANS_LINE_43_LAWYER = 'A lawyer can tell you how the law applies to your facts.';

// DRAFT: counsel C-31
export const MEANS_LINE_43_LEGEND = 'Circumstance {n}';

// DRAFT: counsel C-31
export const MEANS_LINE_43_ADD = 'Add a circumstance';

// DRAFT: counsel C-31
export const MEANS_LINE_43_REMOVE = 'Remove circumstance {n}';

// DRAFT: counsel C-31
export const MEANS_LINE_43_HAPPENED = 'What happened, and when?';

// DRAFT: counsel C-31
export const MEANS_LINE_43_HAPPENED_HINT = 'Use your own words.';

// DRAFT: counsel C-31
export const MEANS_LINE_43_CHANGE = 'How does it change your monthly expenses or income?';

// DRAFT: counsel C-31
export const MEANS_LINE_43_CHOICES =
  'What other choices did you look at, and why did they not work?';

// DRAFT: counsel C-31
export const MEANS_LINE_43_PAPERS = 'What papers will you give your case trustee to show this?';

// DRAFT: counsel C-31
export const MEANS_LINE_43_BOX_NOTE =
  'Write only what you want the court to read. This box prints with line 43 on Form 122A-2. Edit it until it says what you mean.';

// DRAFT: counsel C-31
export const MEANS_LINE_43_ASSEMBLE = 'Put my answers together';

// DRAFT: counsel C-31
export const MEANS_LINE_43_ASSEMBLE_NOTE =
  'This puts your answers in the box below, under short headings. Nothing else is added.';

// DRAFT: counsel C-31
export const MEANS_LINE_43_LABEL_HAPPENED = 'What happened:';

// DRAFT: counsel C-31
export const MEANS_LINE_43_LABEL_CHANGE = 'How it changes my monthly expenses or income:';

// DRAFT: counsel C-31
export const MEANS_LINE_43_LABEL_CHOICES = 'Other choices I looked at:';

// DRAFT: counsel C-31
export const MEANS_LINE_43_LABEL_PAPERS = 'Papers I will give my case trustee:';

// DRAFT: counsel C-31
export const MEANS_LINE_43_SKIPPED =
  "With your current answers, the form skips line 43, so this answer won't print.";

// DRAFT: counsel C-31
export const MEANS_LINE_43_POINTER = 'See line 43.{n} on the attached sheet.';

// DRAFT: counsel C-32
export const MEANS_REBUTTAL_NOW = 'Your line 39d is now {amount}.';

// DRAFT: counsel C-32
export const MEANS_REBUTTAL_IF =
  'If the court allowed the amounts on line 43, line 39d would be {amount}.';

// DRAFT: counsel C-32
export const MEANS_REBUTTAL_IF_BELOW =
  'If the court allowed the amounts on line 43, line 39d would be {amount} less than $0.';

// DRAFT: counsel C-32
export const MEANS_REBUTTAL_COURT = 'The court decides whether to allow them.';

// DRAFT: counsel C-24
export const MEANS_TOO_LONG = 'This is too long for the box on Form 122A-2. Shorten it.';
// DRAFT: counsel C-24
export const MEANS_LETTER = "This has a letter Form 122A-2 can't print. Change it.";

// DRAFT: counsel C-31
export const MEANS_EXPLANATION_TOO_LONG =
  'This explanation is too long to print with line 43. Shorten it.';

// DRAFT: counsel C-31
export const MEANS_EXPLANATION_LETTER =
  "This explanation has a letter Form 122A-2 can't print. Change it.";

// DRAFT: counsel C-33
export const MEANS_POLISH_NOTE =
  'An AI service can rewrite this explanation so it reads more clearly. You see the rewrite first, and your own words stay until you approve it.';

// DRAFT: counsel C-33
export const MEANS_POLISH_BUTTON = 'Rewrite this with an AI service';

// DRAFT: counsel C-33
export const MEANS_POLISH_CONSENT_HEADING = 'Before your words are sent';

// DRAFT: counsel C-33
export const MEANS_POLISH_CONSENT_WHAT =
  "DigniFi will send the words in the box you pick, with DigniFi's instructions for the rewrite, to Anthropic, an AI service. Nothing else from your answers goes with them.";

// DRAFT: counsel C-33
export const MEANS_POLISH_CONSENT_RETENTION =
  "DigniFi read Anthropic's terms on November 17, 2026. They say Anthropic doesn't keep what DigniFi sends.";

// DRAFT: counsel C-33
export const MEANS_POLISH_CONSENT_KEEP =
  'You can say no and keep your own words. You can also keep them after you see the rewrite.';

// DRAFT: counsel C-33
export const MEANS_POLISH_SEND = 'Send it and show me a rewrite';

// DRAFT: counsel C-33
export const MEANS_POLISH_DECLINE = 'No, keep my words';

// DRAFT: counsel C-33
export const MEANS_POLISH_WORKING = 'Getting a rewrite. This can take a few seconds.';

// DRAFT: counsel C-33
export const MEANS_POLISH_DISCLOSURE =
  'An AI service rewrote your explanation to make it clearer. Check that it says what you said, with nothing added and nothing left out, before you approve it.';

// DRAFT: counsel C-33
export const MEANS_POLISH_SENT_LABEL = 'What you sent';

// DRAFT: counsel C-33
export const MEANS_POLISH_REWRITE_LABEL = 'The rewrite';

// DRAFT: counsel C-33
export const MEANS_POLISH_APPROVE = 'Use this rewrite';

// DRAFT: counsel C-33
export const MEANS_POLISH_KEEP = 'Keep my words';

// DRAFT: counsel C-33
export const MEANS_POLISH_APPROVED =
  'Your explanation now holds the rewrite you approved. You can put your own words back at any time.';

// DRAFT: counsel C-33
export const MEANS_POLISH_KEPT = 'Your words are unchanged.';

// DRAFT: counsel C-33
export const MEANS_POLISH_HOLDS_REWRITE = 'This box holds a rewrite you approved.';

// DRAFT: counsel C-33
export const MEANS_POLISH_RESTORE = 'Put my own words back';

// DRAFT: counsel C-33
export const MEANS_POLISH_TOO_MANY =
  'You asked for rewrites too quickly. Wait a minute and try again.';

// DRAFT: counsel C-33
export const MEANS_POLISH_IDENTIFIER =
  'This explanation holds your name, login name, Social Security number, account number, phone number, email or address. Take it out first.';

// DRAFT: counsel C-33
export const MEANS_POLISH_PHRASE =
  "This explanation has a phrase DigniFi doesn't send to the AI service. Change it first.";

// DRAFT: counsel C-33
export const MEANS_POLISH_BLANK = 'Write your explanation first.';

// DRAFT: counsel C-33
export const MEANS_POLISH_NO_REWRITE =
  "The AI service didn't give a rewrite DigniFi can show. Your words are unchanged.";

// DRAFT: counsel C-33
export const MEANS_POLISH_UNAVAILABLE =
  "DigniFi couldn't reach the AI service. Your words are unchanged.";

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_3 = "Answer line 3, about your spouse's income.";

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_3_NO_ROW =
  "Add each use of your spouse's income on line 3, or change the answer to No.";

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_3_ROW =
  "Enter what your spouse's income was used for, and the amount, on each row of line 3.";

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_3_CAP =
  "Line 3 can't be more than {amount}, your spouse's income on Form 122A-1, Column B.";

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_VEHICLES =
  "Answer whether your spouse has a vehicle that isn't on your property list.";

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_VEHICLES_NO_ROW =
  "Add each of your spouse's vehicles, or change the answer to No.";

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_VEHICLE_DESCRIBE = "Describe each of your spouse's vehicles.";

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_VEHICLE_LEASED = 'Answer whether {name} is leased.';

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_LOANS =
  'Answer whether your spouse owes a loan on your home, a vehicle or other property.';

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_LOANS_NO_ROW =
  "Add each of your spouse's loans, or change the answer to No.";

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_LOAN_ON_AMOUNTS_OWED =
  "Answer whether each of your spouse's loans is on your Amounts Owed step.";

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_LOAN_WHICH =
  "For each of your spouse's loans that is on your Amounts Owed step, choose which one it is.";

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_LOAN_CREDITOR = 'Enter who your spouse owes on each of their loans.';

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_LOAN_SECURED_BY = "Say what secures your spouse's loan from {name}.";

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_LOAN_PROPERTY =
  "Describe the property that secures your spouse's loan from {name}.";

// DRAFT: counsel C-34
export const MEANS_GAP_SPOUSE_LOAN_PAYMENT =
  "Enter the monthly payment on your spouse's loan from {name}.";

// DRAFT: counsel C-24
export const MEANS_GAP_VEHICLE = 'Answer whether you claim an expense for {name}.';

// DRAFT: counsel C-24
export const MEANS_GAP_VEHICLE_CHOICE = 'Choose your Vehicle 1 and your Vehicle 2.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_15 = 'Answer the question on line 15.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_15_AMOUNT = 'Enter the amount for line 15.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_15_CAP =
  "Line 15 can't be more than {amount}, the IRS amount for public transportation.";

// DRAFT: counsel C-24
export const MEANS_GAP_AMOUNT = 'Enter the amount for line {n}. Enter 0 if you have none.';

// DRAFT: counsel C-24
export const MEANS_GAP_OPT_IN = 'Answer line {n}.';

// DRAFT: counsel C-24
export const MEANS_GAP_OPT_IN_AMOUNT = 'Enter the amount for line {n}.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_25_AMOUNTS = 'Enter the three amounts on line 25.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_25_SPENDS = 'Answer whether you actually spend the line 25 total.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_25_ACTUAL = 'Enter how much you actually spend, on line 25.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_30_CAP =
  "Line 30 can't be more than {amount}, which is 5% of the IRS food and clothing amounts for {n} people.";

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_30_CAP_ONE =
  "Line 30 can't be more than {amount}, which is 5% of the IRS food and clothing amounts for 1 person.";

// DRAFT: counsel C-24
export const MEANS_GAP_PAYMENTS_LEFT = 'Enter how many payments you have left to {name}.';

// DRAFT: counsel C-24
export const MEANS_GAP_PAYMENT_CHANGES = 'Answer whether your payment to {name} will change.';

// DRAFT: counsel C-24
export const MEANS_GAP_SIXTY_MONTH_TOTAL =
  'Enter the total you will owe {name} in the 60 months after you file.';

// DRAFT: counsel C-24
export const MEANS_GAP_TAXES = 'Say if the payment to {name} pays for taxes or insurance too.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_34 =
  'Answer line 34, about debts secured by property you need for support.';

// DRAFT: counsel C-24
export const MEANS_GAP_SUPPORT =
  'Say if your debt to {name} is secured by property you need for support.';

// DRAFT: counsel C-24
export const MEANS_GAP_CURE = 'Enter the cure amount for {name}. Enter 0 if there is none.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_36 = 'Answer line 36.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_36_PAYMENT = 'Enter the projected monthly plan payment on line 36.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_43 = 'Answer the question on line 43.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_43_NONE =
  'Add each special circumstance on line 43, or change the answer to No.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_43_EXPLANATION =
  'Give the explanation for circumstance {n} on line 43.';

// DRAFT: counsel C-24
export const MEANS_GAP_LINE_43_AMOUNT =
  'Enter the average monthly amount for circumstance {n} on line 43. Enter 0 if there is none.';

// DRAFT: counsel C-24
export const MEANS_NOT_A_COUNTED_DEBT = "This isn't one of your secured debts.";

// DRAFT: counsel C-24
export const MEANS_NOT_A_LINE_11_VEHICLE = "This isn't one of the vehicles on line 11.";

// DRAFT: counsel C-24
export const MEANS_NOT_AN_OPEN_DEBT =
  "This isn't one of the debts on your Amounts Owed step not listed as secured.";

// DRAFT: counsel C-24
export const TABLE_NOTICE_MEDIAN =
  'These forms use the median income figures the U.S. Trustee applies to cases filed on or after {date}.';

// DRAFT: counsel C-24
export const TABLE_NOTICE_STANDARDS =
  'These forms use the IRS expense standards the U.S. Trustee applies to cases filed on or after {date}.';

// DRAFT: counsel C-24
export const TABLE_NOTICE_SECTION_104 =
  "These forms use the Bankruptcy Code's dollar amounts for cases filed on or after {date}.";

// DRAFT: counsel C-24
export const TABLE_NOTICE_NEW_FIGURES =
  'New figures are expected after {date}. If you file after that date, download your forms again.';

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

// DRAFT: counsel C-24
export const REVIEW_INTRO =
  'Please review the information below carefully. DigniFi uses it to fill in your court forms.';

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
export const REVIEW_NOTHING_MISSING = 'Nothing is missing.';
export const REVIEW_GAPS_UNAVAILABLE =
  "We couldn't check what is still missing. Press Complete to try again.";

// ============================================================================
// The Frame: Section Intro, Public Record Notice, Definitions (forms step 4a)
// ============================================================================

export const SECTION_INTRO_TIME = 'This step takes about {n} minutes.';
export const SECTION_INTRO_PAUSE = 'You can stop at any time. What you have typed is saved.';

// The notice before a county is chosen, with no clerk's number (4b-R6)
// DRAFT: counsel C-40
export const PUBLIC_RECORD_NOTICE =
  "What you file with the court can be seen by the public. If an address raises a safety concern for you, the court's clerk can tell you what options exist.";
// The notice once a county is chosen: PublicRecordNotice adds its division's number and a period
// DRAFT: counsel C-40
export const PUBLIC_RECORD_NOTICE_WITH_CLERK =
  "What you file with the court can be seen by the public. If an address raises a safety concern for you, the court's clerk can tell you what options exist:";
// The clerk's office by division: https://www.ilnb.uscourts.gov/online-payments ("(312) 408-5000
// for (Chicago) or (815) 987-4350 for (Rockford)"), re-read 2026-11-21 (PF2-T8-8)
export const CLERK_PHONE_EASTERN = '(312) 408-5000';
export const CLERK_PHONE_WESTERN = '(815) 987-4350';

export const WHAT_DOES_THIS_MEAN = 'What does this mean?';

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

// DRAFT: counsel C-42
export const FEE_OTHER_LINES_NOTE =
  'DigniFi leaves Part 3 of Form 103B blank for now, and the details of lines 17 to 20. Form 103B also asks for a copy of your Schedule A/B.';

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

// DRAFT: counsel C-47
export const EXPENSES_LEGACY_UTILITIES =
  'Before this page asked about each utility, you gave one total. It is in the Other box. You can leave it there, or move it to the lines above.';

// DRAFT: counsel C-47
export const EXPENSES_LEGACY_INSURANCE =
  'Before this page asked about each kind of insurance, you gave one total. It is in the Other insurance box. You can leave it there, or move it to the lines above.';

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
  us_11_522_b3c:
    'Retirement funds in a tax-exempt account. The account is tax-exempt under one of the federal tax code sections this law names.',
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
  "The law you typed doesn't fit in its box on Schedule C. Type it with fewer letters. The form can't print some letters and symbols, such as emoji.";
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
export const EXEMPTIONS_CLAIM_NUMBER = 'Claim {n}';
export const EXEMPTIONS_REMOVE_CLAIM = 'Remove claim {n}';
export const EXEMPTIONS_TOTALS_HEADING = 'Totals by law';

// ============================================================================
// Your Information: Form 101's questions (forms step 4b)
// ============================================================================

// The gap sentences, each the server's own (apps/intake/petition.py, the name without
// `PETITION_`); test_petition_frontend_copy.py pins them both ways. Step 1 shows the first gate.
export const PETITION_GATE_OTHER_NAMES =
  'Say whether you have used another name in the last 8 years.';
// DRAFT: counsel C-44
export const PETITION_GATE_ITIN = 'Say whether you have an ITIN.';
// DRAFT: counsel C-44
export const PETITION_GATE_OTHER_SSN =
  'Say whether you have used any other Social Security number. Answer Yes or No.';
export const PETITION_GATE_MAILING =
  'Say whether your mailing address is different from where you live.';
export const PETITION_GATE_PRIOR_BANKRUPTCY =
  'Say whether you have filed for bankruptcy in the last 8 years.';
export const PETITION_GATE_PENDING_CASE =
  'Say whether a spouse, partner or affiliate has a bankruptcy case pending.';
export const PETITION_GATE_SOLE_PROPRIETOR = 'Say whether you are a sole proprietor of a business.';
export const PETITION_GATE_HAZARD =
  'Say whether any property you own poses a hazard or needs attention right away.';
export const PETITION_GATE_RENTS = 'Say whether you rent your residence.';
export const PETITION_GATE_EVICTION =
  'Say whether your landlord has an eviction judgment against you.';
// Amounts Owed's Form 101 line 16 and Form 122A-1Supp's military questions (4d, owner-approved
// 2026-11-23 as drafted)
// DRAFT: counsel C-39
export const PETITION_GATE_DEBT_NATURE =
  'Say whether your debts are primarily consumer debts, on the Amounts Owed step.';
// DRAFT: counsel C-39
export const PETITION_GATE_DISABLED_VETERAN = 'Say whether you are a disabled veteran.';
// DRAFT: counsel C-39
export const PETITION_GATE_RESERVIST =
  'Say whether you are or have been a Reservist or member of the National Guard.';
export const PETITION_DETAIL_VENUE = 'Choose why you are filing in this district.';
// DRAFT: counsel C-40
export const PETITION_DETAIL_VENUE_REASON = 'Explain your other reason for filing here.';
export const PETITION_DETAIL_OTHER_NAMES =
  'Add the other name you used, or change your answer to No.';
// DRAFT: counsel C-44
export const PETITION_DETAIL_ITIN = 'Type your 9-digit ITIN, or change your answer to No.';
// Nine digits whose first is not 9 (owner ruling Q7)
// DRAFT: counsel C-44
export const PETITION_DETAIL_ITIN_NINE =
  'An ITIN starts with 9. Check what you typed, or change your answer to No.';
// DRAFT: counsel C-44
export const PETITION_DETAIL_OTHER_SSN =
  'Type the other 9-digit Social Security number, or change your answer to No.';
export const PETITION_DETAIL_EIN = 'Your EIN has 9 digits. Check what you typed.';
export const PETITION_DETAIL_MAILING = 'Add your mailing address, or change your answer to No.';
export const PETITION_DETAIL_PRIOR_CASE =
  'Each earlier case needs its district and the date it was filed.';
export const PETITION_DETAIL_PRIOR_DATE =
  'A date is written as MM/DD/YYYY. Check the date of your earlier case.';
export const PETITION_DETAIL_PENDING_DATE =
  'A date is written as MM/DD/YYYY. Check the date of the pending case.';
export const PETITION_DETAIL_PENDING_CASE =
  'Each pending case needs the name of the person who filed it.';
export const PETITION_DETAIL_BUSINESS = "Add your business's name, or change your answer to No.";
export const PETITION_DETAIL_HAZARD = 'Say what the hazard is, or change your answer to No.';
// Amounts Owed's details (4d): line 16c's words, then the Supp's follow-ups and dates
// DRAFT: counsel C-39
export const PETITION_DETAIL_DEBT_NATURE_TEXT = 'Say what type of debts you owe.';
// DRAFT: counsel C-39
export const PETITION_DETAIL_DEBTS_ON_DUTY =
  'Say whether most of your debts began while you were on active duty. Time doing a homeland defense activity counts too.';
// DRAFT: counsel C-39
export const PETITION_DETAIL_CALLED_TO_DUTY =
  'Say whether you were called to active duty. Doing a homeland defense activity counts too.';
// DRAFT: counsel C-39
export const PETITION_DETAIL_DUTY_CATEGORY = 'Choose a category, or say that none applies.';
// DRAFT: counsel C-39
export const PETITION_DETAIL_DUTY_RELEASED =
  'A date is written as MM/DD/YYYY. Type the date you were released from active duty.';
// DRAFT: counsel C-39
export const PETITION_DETAIL_DUTY_ENDED =
  'A date is written as MM/DD/YYYY. Type the date your homeland defense activity ended.';
// Templates the server fills in: {label} a box in plain words; {noun} and {n} a row (Q5);
// {forms} the forms whose box refuses it: Form 101, Form 103B or Forms 101 and 103B (Q10)
export const PETITION_DETAIL_TOO_LONG =
  'Your answer for {label} is too long for its box on Form 101.';
export const PETITION_DETAIL_TOO_LONG_ROW =
  'Your answer for {label}, in {noun} {n}, is too long to fit on {forms}.';
// Form 101A's landlord block (4b2, owner-approved 2026-11-22): the first mirrors
// DETAIL_LANDLORD, which is also Form 101A's refusal; the second is a {label} template.
// DRAFT: counsel C-46
export const PETITION_DETAIL_LANDLORD =
  "Form 101A asks for your landlord's name and address, on Contracts & Leases.";
// DRAFT: counsel C-46
export const PETITION_DETAIL_TOO_LONG_101A =
  'Your answer for {label} is too long for its box on Form 101A.';

// The questions step 1 asks in its own words, where the form prints no question (spec §6.1)
// DRAFT: counsel C-44
export const PETITION_ASKED_AS_ITIN = 'Do you have an ITIN?';
// DRAFT: counsel C-44
export const PETITION_ASKED_AS_OTHER_SSN =
  'Have you used any other Social Security number? Answer Yes or No.';
export const PETITION_ASKED_AS_MAILING = 'Is your mailing address different from where you live?';

// Why a gate that prints no box is asked (spec §5.7)
export const WHY_OTHER_NAMES =
  "Form 101 line 2 prints blank when you have used no other name; your No tells us that's so.";
// DRAFT: counsel C-44
export const WHY_ITIN =
  "Forms 101 and 121 print an ITIN only when you have one. Your No tells us you don't.";
// DRAFT: counsel C-44
export const WHY_OTHER_SSN =
  "Form 121 lists another Social Security number only when you have used one. Your No tells us you haven't.";
export const WHY_MAILING =
  "Form 101 line 5 prints a mailing address only when it is different from where you live. Your No tells us it isn't.";

// The one requirement the wizard can't meet for the filer, in step 1's intro (spec §6.1)
// DRAFT: counsel C-40
export const COUNSELING_REQUIREMENT_INTRO =
  'Before you file, the court requires a credit counseling briefing from an approved agency, taken within the 180 days before filing. The last step asks about it. The guide there says where the approved agencies are listed.';
// Line 6's information: the division follows the county (4b-R6, F-10)
// DRAFT: counsel C-40
export const VENUE_DIVISION_EASTERN = 'Your county is in the Eastern Division of this district.';
// DRAFT: counsel C-40
export const VENUE_DIVISION_WESTERN = 'Your county is in the Western Division of this district.';
export const LINE_12_FEEDS_107 =
  'Form 107 line 27 asks about this business again. Your answer here will show there.';

// Step 1's home ZIP box, five digits or nine (owner ruling Q7)
export const HOME_ZIP_ERROR = 'Enter a 5-digit or 9-digit ZIP code.';

// Answers kept under a No: they print nothing, and nothing reappears unannounced (spec §5.3)
export const HIDDEN_ROWS_ONE = '1 saved row is hidden. Show it or delete it.';
export const HIDDEN_ROWS_MANY = '{count} saved rows are hidden. Show them or delete them.';
export const HIDDEN_ANSWERS =
  'Your earlier answers here are saved but hidden. Show them or delete them.';
export const SHOW_HIDDEN = 'Show';
export const DELETE_HIDDEN = 'Delete';

// Amounts Owed's Form 101 line 16 and Form 122A-1Supp block (4d, owner approved 2026-11-23 as
// drafted). The list beside line 16 has no sum, no count and no comparison (spec §6.6).
// DRAFT: counsel C-39
export const DEBT_NATURE_LIST_HEADING = 'Your amounts owed, by the kind you chose for each';
// DRAFT: counsel C-39
export const DEBT_NATURE_LIST_NOTE =
  "The form asks you to say which kind your debts primarily are. It doesn't say how to measure that.";
// DRAFT: counsel C-39
export const DEBT_NATURE_LIST_EMPTY = "You haven't listed any amounts owed on this step.";
// DRAFT: counsel C-39
export const DEBT_NATURE_KIND_NOT_CHOSEN = 'Kind not chosen yet';
// DRAFT: counsel C-39
export const MILITARY_FRAMING =
  'Form 122A-1Supp asks two questions about military service. The form asks these of everyone whose debts are mostly consumer debts.';
// DRAFT: counsel C-39
export const MILITARY_540_DAYS =
  "The form counts back 540 days from the day you file. DigniFi doesn't know that day and doesn't check it; your tick is your statement.";
// The fifth duty_category answer, "none" (D9): DigniFi's words, not the form's
// DRAFT: counsel C-39
export const DUTY_CATEGORY_NONE = 'None of these categories applies to me';
// The two definitions' names, each the visible words of its summary (4d-R21, Ruling M)
// DRAFT: counsel C-39
export const WHAT_DOES_DISABLED_VETERAN_MEAN = 'What does “disabled veteran” mean?';
// The owner's words of 2026-11-24, replacing the four-word label
// DRAFT: counsel C-39
export const WHAT_DOES_HOMELAND_DEFENSE_MEAN =
  'What does “homeland defense activity” mean on this form?';

// Schedule I lines 1, 11 and 13 and Schedule J line 24 (4c, words owner-approved 2026-11-22). The
// gap sentences mirror apps/intake/schedule_i.py word for word; test_schedule_i_frontend_copy.py
// pins them. {label} is a box in plain words (SCHEDULE_I_TEXT_LABELS) and {form} the form whose
// box refuses it, "Schedule I" or "Schedule J"; the server fills both in.
// DRAFT: counsel C-42
export const SCHEDULE_I_LINE_11_QUESTION =
  'Does anyone else pay part of your Schedule J expenses on a regular basis?';
// DRAFT: counsel C-42
export const SCHEDULE_I_LINE_11_AMOUNT_LABEL = 'How much they pay each month';
// DRAFT: counsel C-42
export const SCHEDULE_I_ONE_EMPLOYER =
  'DigniFi prints one employer on Schedule I. The form asks you to attach a separate page for any other job.';
// {name} is the employer's name the pay stub gave
// DRAFT: counsel C-42
export const PAYSTUB_EMPLOYER_HINT = 'Your pay stub says: {name}';
// DRAFT: counsel C-42
export const PAYSTUB_UPLOAD_HELP =
  "Recent pay stubs from your job. The Income step shows the employer's name from your stub so you can check it.";
// DRAFT: counsel C-42
export const SCHEDULE_I_GATE_LINE_11 =
  'Say if anyone else pays part of your Schedule J expenses on a regular basis.';
// DRAFT: counsel C-42
export const SCHEDULE_I_GATE_LINE_13 =
  'Say whether you expect your income to go up or down in the year after you file.';
// DRAFT: counsel C-42
export const SCHEDULE_I_GATE_J24 =
  'Say whether you expect your expenses to go up or down in the year after you file.';
// DRAFT: counsel C-42
export const SCHEDULE_I_DETAIL_EMPLOYMENT = 'Choose Employed or Not employed.';
// DRAFT: counsel C-42
export const SCHEDULE_I_DETAIL_SPOUSE_EMPLOYMENT =
  'Choose Employed or Not employed for your spouse.';
// DRAFT: counsel C-42
export const SCHEDULE_I_DETAIL_EMPLOYER =
  "Add your employer's name, or change your answer to Not employed.";
// DRAFT: counsel C-42
export const SCHEDULE_I_DETAIL_SPOUSE_EMPLOYER =
  "Add your spouse's employer's name, or change their answer to Not employed.";
// DRAFT: counsel C-42
export const SCHEDULE_I_DETAIL_LINE_11_AMOUNT =
  'Add how much others pay each month, or change your answer to No.';
// DRAFT: counsel C-42
export const SCHEDULE_I_DETAIL_LINE_13 =
  'Explain the change you expect in your income, or change your answer to No.';
// DRAFT: counsel C-42
export const SCHEDULE_I_DETAIL_J24 =
  'Explain the change you expect in your expenses, or change your answer to No.';
// DRAFT: counsel C-42
export const SCHEDULE_I_DETAIL_TOO_LONG =
  'Your answer for {label} is too long for its box on {form}.';
// The {label} of each text, schedule_i.limits.json's `labels` (owner W18)
// DRAFT: counsel C-42
export const SCHEDULE_I_TEXT_LABELS: Record<ScheduleITextKey, string> = {
  occupation: 'Occupation',
  employer_name: "Employer's name",
  employer_street: "Employer's address",
  employer_street_2: "Employer's address, line 2",
  employer_city: "Employer's city",
  employer_state: "Employer's state",
  employer_zip: "Employer's ZIP Code",
  time_employed: 'How long employed there',
  spouse_occupation: "Your spouse's occupation",
  spouse_employer_name: "Your spouse's employer's name",
  spouse_employer_street: "Your spouse's employer's address",
  spouse_employer_street_2: "Your spouse's employer's address, line 2",
  spouse_employer_city: "Your spouse's employer's city",
  spouse_employer_state: "Your spouse's employer's state",
  spouse_employer_zip: "Your spouse's employer's ZIP Code",
  spouse_time_employed: 'How long your spouse has been employed there',
  line_11_text: 'Line 11, Specify',
  line_13_text: 'Line 13, Explain',
  schedule_j_line_24_text: 'Line 24, Explain',
};

// Your Plans: a Form 108 row left open, in the server's words (apps/intake/intentions.py, pinned
// by test_intention_frontend_copy.py). {name} is the creditor's or lessor's name, or "one amount
// owed" / "one contract"
// DRAFT: counsel C-37
export const INTENTION_GAP_NONE =
  "Choose what you plan to do with the property for {name}. Or say you haven't decided.";
// DRAFT: counsel C-37
export const INTENTION_GAP_UNDECIDED =
  'Your choice for {name} is open, so Form 108 shows no choice for it.';
// DRAFT: counsel C-37
export const INTENTION_GAP_EXPLAIN = 'Type your words for {name}, or choose another answer.';
// DRAFT: counsel C-37
export const LEASE_GAP_NONE =
  "Say if the lease with {name} will be assumed. Or say you haven't decided yet.";
// DRAFT: counsel C-37
export const LEASE_GAP_UNDECIDED =
  'Your answer for the lease with {name} is open, so Form 108 shows no answer for it.';

// Your Plans, Form 108's step (forms step 4e; owner-approved 2026-11-24 as drafted, E7, with E8's
// words). Nothing here chooses for the filer: the choices are the form's own (formText.ts)
// DRAFT: counsel C-37
export const PLANS_TITLE = 'Your plans for what you owe on';
// DRAFT: counsel C-37
export const PLANS_INTRO =
  "These questions are for Form 108. It lists each debt secured by your property and each lease of personal property. For each one, you choose what the form says. DigniFi doesn't choose for you.";
// DRAFT: counsel C-37
export const PLANS_NOT_APPLICABLE =
  "DigniFi isn't preparing Form 108. You listed no debt secured by your property and no lease of personal property. If that isn't right, go back to Amounts Owed or Contracts & Leases.";
// The app's own fifth answer, after the form's choices (E7)
// DRAFT: counsel C-37
export const PLANS_UNDECIDED = "I haven't decided yet.";
// DRAFT: counsel C-37
export const PLANS_UNDECIDED_INFO =
  'You can leave a choice open and come back to it. While it is open, no choice is ticked for that row on Form 108.';
// The label of the box under "Retain the property and [explain]:"
// DRAFT: counsel C-37
export const PLANS_EXPLAIN_LABEL = 'Your words for the form';
// Each row's exempt box, from the exemptions page's answers (R-EXEMPT, 4e-R6)
// DRAFT: counsel C-37
export const PLANS_EXEMPT_LISTED = 'Your Schedule C lists this property.';
// DRAFT: counsel C-37
export const PLANS_EXEMPT_NOT_CLAIMING = "Your Schedule C doesn't list this property.";
// DRAFT: counsel C-37
export const PLANS_EXEMPT_LATER =
  'You answer Schedule C after you finish these steps. This box follows your answers there.';
// DRAFT: counsel C-37
export const PLANS_EXEMPT_NOT_NAMED =
  "Your Schedule C answers don't name this property, so this box prints blank.";
// DRAFT: counsel C-37
export const PLANS_EXEMPT_NO_PROPERTY =
  "This debt isn't linked to property on your Assets step, so this box prints blank.";
// The definitions' names, each the visible words of its summary (E2, Ruling M)
// DRAFT: counsel C-37
export const WHAT_DOES_SURRENDER_MEAN = 'What does “surrender” mean on this form?';
// DRAFT: counsel C-37
export const WHAT_DOES_REDEEM_MEAN = 'What does “redeem” mean on this form?';
// DRAFT: counsel C-37
export const WHAT_DOES_REAFFIRM_MEAN = 'What is a “Reaffirmation Agreement” on this form?';
// The retain-and-explain panel's name (E8)
// DRAFT: counsel C-37
export const WHAT_DOES_EXPLAIN_MEAN = 'What does “retain” mean on this form?';
// DRAFT: counsel C-37
export const WHAT_DOES_ASSUME_MEAN = 'What does it mean for a lease to be “assumed”?';
// Each definition's closing sentence (E1). The number is the court's pro se help desk, not a
// clerk's office by division (4b-R6)
// DRAFT: counsel C-37
export const PLANS_EFFECTS_HELP =
  "A licensed attorney can answer questions about your own case. The court's pro se help desk takes calls at (312) 229-6344.";
// The {label} of each claims text in SCHEDULE_I_DETAIL_TOO_LONG, form_108.limits.json's `labels`
// (E4, E8), pinned by test_intention_frontend_copy.py
// DRAFT: counsel C-37
export const CLAIM_TEXT_LABELS: Record<ClaimTextKey, string> = {
  creditor_name: "the creditor's name",
  collateral_description: 'the description of the property',
  counterparty_name: "the lessor's name",
  description: 'the description of the leased property',
  explain: 'the explanation of your plan',
};
// Where each row comes from
// DRAFT: counsel C-37
export const PLANS_FROM_DEBTS = 'From your Amounts Owed step';
// DRAFT: counsel C-37
export const PLANS_FROM_CONTRACTS = 'From your Contracts & Leases step';
// The lead before Form 108's deadline sentence (E6)
// DRAFT: counsel C-37
export const PLANS_DEADLINE_LABEL = 'Form 108 says:';

// The write-only numbers: the server says only whether one is saved (F-3, owner ruling Q3)
export const SSN_SAVED = 'Your Social Security number is saved. You can replace it.';
// DRAFT: counsel C-44
export const ITIN_SAVED = 'An ITIN is saved.';
// DRAFT: counsel C-44
export const OTHER_SSN_SAVED = 'Another Social Security number is saved. You can replace it.';
export const REPLACE_SAVED = 'Replace it';

// The row lists' controls; {n} is the row's place, counted from 1
export const PETITION_ADD_OTHER_NAME = 'Add another name';
export const PETITION_ADD_BUSINESS_NAME = 'Add a business name';
export const PETITION_ADD_PRIOR_CASE = 'Add an earlier case';
export const PETITION_ADD_PENDING_CASE = 'Add a pending case';
export const PETITION_OTHER_NAME_ROW = 'Other name {n}';
export const PETITION_BUSINESS_NAME_ROW = 'Business name {n}';
export const PETITION_PRIOR_CASE_ROW = 'Earlier case {n}';
export const PETITION_PENDING_CASE_ROW = 'Pending case {n}';
export const PETITION_REMOVE_OTHER_NAME = 'Remove other name {n}';
export const PETITION_REMOVE_BUSINESS_NAME = 'Remove business name {n}';
export const PETITION_REMOVE_PRIOR_CASE = 'Remove earlier case {n}';
export const PETITION_REMOVE_PENDING_CASE = 'Remove pending case {n}';

// Contracts & Leases, under Form 101 line 11's two Yes answers: the lead before line 11's own
// sentence (owner ruling Q8), the lead before each sentence quoted from Form 101A (formText.ts),
// and DigniFi's own sentences and links (PF2-T9-4)
// DRAFT: counsel C-40
export const FORM_101_LINE_11_LEAD = 'Form 101 line 11 says:';
// DRAFT: counsel C-40
export const FORM_101A_SAYS = 'Form 101A says:';
// DRAFT: counsel C-40
export const FORM_101A_LINK = 'Get Form 101A and its instructions from the U.S. Courts website';
// The court's Form 101A page, read 2026-11-21 (the page without "-individuals" is a 404)
// DRAFT: counsel C-40
export const COURT_FORM_101A_URL =
  'https://www.uscourts.gov/forms-rules/forms/initial-statement-about-eviction-judgment-against-you-individuals';
// DRAFT: counsel C-40
export const FORM_101B_NOT_PREPARED = "DigniFi doesn't prepare Form 101B.";
// Form 101A's certification boxes stay blank (owner-approved 2026-11-22, spec §6.7 item 2, B58).
// DEPOSIT_WITH_CLERK ends in a colon: the step adds the division's number (CLERK_PHONE_*, 4b-R6)
// DRAFT: counsel C-46
export const FORM_101A_BOXES_BLANK =
  'DigniFi leaves these two boxes blank. They are sworn statements about the law that applies to your eviction judgment and about a rent deposit given to the clerk when you file.';
// DRAFT: counsel C-46
export const FORM_101A_DEPOSIT = "The clerk's office can tell you how the deposit is made.";
// DRAFT: counsel C-46
export const FORM_101A_DEPOSIT_WITH_CLERK =
  "The clerk's office can tell you how the deposit is made:";
// The landlord's pick from a lease listed on the same step (4b2-R7)
// DRAFT: counsel C-46
export const LANDLORD_PICK_LABEL = 'Copy a name and address from a lease you listed on this step';
// DRAFT: counsel C-46
export const LANDLORD_PICK_PLACEHOLDER = 'Choose a lease';
// DRAFT: counsel C-46
export const LANDLORD_PICK_HINT = 'You can change what is copied.';
// Signing guide, Form 101A bullet (spec §16.3): rendered from 4i
// DRAFT: counsel C-46
export const GUIDE_FORM_101A_BOXES_BLANK =
  'On Form 101A, DigniFi leaves both boxes of the sworn statement blank.';
// DRAFT: counsel C-40
export const FORM_101B_LINK = 'Get Form 101B from the U.S. Courts website';
// The court's Form 101B page, read 2026-11-21
// DRAFT: counsel C-40
export const COURT_FORM_101B_URL =
  'https://www.uscourts.gov/forms-rules/forms/statement-about-payment-eviction-judgment-against-you-individuals';
