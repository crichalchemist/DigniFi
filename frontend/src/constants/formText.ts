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
  ClaimStatus,
  DeductionField,
  EntryKind,
  ExpenseField,
  ExpenseSpecifyField,
  LienKind,
  MaritalStatus,
  PaymentChoice,
  PriorityType,
  PropertyKind,
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
  // Line 18, no cut
  child_support_paid:
    'Your payments of alimony, maintenance, and support that you did not report as deducted from your pay on line 5, Schedule I, Your Income (Official Form 106I).',
  // Line 19, cut: "Specify:"
  support_others: 'Other payments you make to support others who do not live with you.',
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

// Form 101 line 8 (page 3) and Form 103B, on the filing-fee page

// No cut: the field index's label for `Check Box7`
export const LINE_8_LABEL = 'How you will pay the fee';

// The field index's option_text for `Check Box7`
export const PAYMENT_CHOICE_WORDS: Record<PaymentChoice, string> = {
  // Cut: "Please check with the clerk's office..." to the end
  pay_in_full: 'I will pay the entire fee when I file my petition.',
  // Cut: "If you choose this option, sign and attach..."
  installments: 'I need to pay the fee in installments.',
  // Cut: the parenthesis and "If you choose this option...". No period, as in the index.
  waiver: 'I request that my fee be waived',
};

// Cut: the parenthesis's first sentence and its brackets; a period added
export const FEE_LAW_SENTENCE =
  'By law, a judge may, but is not required to, waive your fee, and may do so only if your income is less than 150% of the official poverty line that applies to your family size and you are unable to pay the fee in installments.';

// Form 103B line 4, no cut
export const WAIVER_LINE_4_QUESTION =
  "Do you expect your family's average monthly net income to increase or decrease by more than 10% during the next 6 months?";

// Form 103B line 5, no cut
export const WAIVER_LINE_5_QUESTION =
  'Tell the court why you are unable to pay the filing fee in installments within 120 days. If you have some additional circumstances that cause you to not be able to pay your filing fee in installments, explain them.';

// Form 103B line 7, no cut
export const WAIVER_LINE_7_QUESTION =
  'Do these expenses cover anyone who is not included in your family as reported in line 1?';

// Form 103B line 9, no cut
export const WAIVER_LINE_9_QUESTION =
  'Do you expect your average monthly expenses to increase or decrease by more than 10% during the next 6 months?';

// Form 103B line 4, cut: "Yes."
export const WAIVER_LINE_4_EXPLAIN = 'Explain.';

// Form 103B line 9, cut: "Yes." Page 2 prints "Yes. Explain" with no period, unlike line 4.
export const WAIVER_LINE_9_EXPLAIN = 'Explain';

// Form 103B line 7, cut: "Yes."
export const WAIVER_IDENTIFY_WHO = 'Identify who';

// Schedule A/B (form_b106ab.pdf), asked on the Assets step. Never the field index's labels, which
// read "No" on lines 12-14 and 26-28. Apostrophes are written as ', not the template's typographic
// one. The dotted leaders after "Yes" and the line number's own period are dropped.

// Each Part's title, cut of its "Part n:" prefix, which the step says as "Part n of 7"
export const AB_PART_TITLES: Record<number, string> = {
  1: 'Describe Each Residence, Building, Land, or Other Real Estate You Own or Have an Interest In',
  2: 'Describe Your Vehicles',
  3: 'Describe Your Personal and Household Items',
  4: 'Describe Your Financial Assets',
  5: 'Describe Any Business-Related Property You Own or Have an Interest In. List any real estate in Part 1.',
  6: 'Describe Any Farm- and Commercial Fishing-Related Property You Own or Have an Interest In.',
  7: 'Describe All Property You Own or Have an Interest in That You Did Not List Above',
};

// The sentence printed under a Part's title, no cut
export const AB_PART_LEADS: Partial<Record<number, string>> = {
  2: 'Do you own, lease, or have legal or equitable interest in any vehicles, whether they are registered or not? Include any vehicles you own that someone else drives. If you lease a vehicle, also report it on Schedule G: Executory Contracts and Unexpired Leases.',
  3: 'Do you own or have any legal or equitable interest in any of the following items?',
  4: 'Do you own or have any legal or equitable interest in any of the following?',
  6: 'If you own or have an interest in farmland, list it in Part 1.',
};

// No cut: the heading printed over lines 28-35 (page 7)
export const AB_OWED_TO_YOU_HEADING = 'Money or property owed to you?';

export interface AbLineWords {
  /** The line's words, without its number */
  words: string;
  /** What the form prints under the words, examples or a definition */
  examples?: string;
  /** The No and Yes answers, where the form says more than the word */
  no?: string;
  yes?: string;
  /** The name of the line's text box */
  textLabel?: string;
  /** The name of its value box, where the form doesn't call it the portion */
  valueLabel?: string;
}

const GIVE_SPECIFIC_ABOUT_THEM = 'Give specific information about them.';
const GIVE_SPECIFIC = 'Give specific information.';
const DESCRIBE = 'Describe.';
const DESCRIBE_EACH_CLAIM = 'Describe each claim.';
// The form's "Describe" with no period, on lines 38-41 (pages 8-9)
const DESCRIBE_NO_PERIOD = 'Describe';

export const AB_LINE_WORDS: Record<string, AbLineWords> = {
  '1': {
    words:
      'Do you own or have any legal or equitable interest in any residence, building, land, or similar property?',
    no: 'No. Go to Part 2.',
    yes: 'Yes. Where is the property?',
  },
  '3': { words: 'Cars, vans, trucks, tractors, sport utility vehicles, motorcycles' },
  '4': {
    words:
      'Watercraft, aircraft, motor homes, ATVs and other recreational vehicles, other vehicles, and accessories',
    examples:
      'Examples: Boats, trailers, motors, personal watercraft, fishing vessels, snowmobiles, motorcycle accessories',
  },
  '6': {
    words: 'Household goods and furnishings',
    examples: 'Examples: Major appliances, furniture, linens, china, kitchenware',
    textLabel: DESCRIBE,
  },
  '7': {
    words: 'Electronics',
    examples:
      'Examples: Televisions and radios; audio, video, stereo, and digital equipment; computers, printers, scanners; music collections; electronic devices including cell phones, cameras, media players, games',
    textLabel: DESCRIBE,
  },
  '8': {
    words: 'Collectibles of value',
    examples:
      'Examples: Antiques and figurines; paintings, prints, or other artwork; books, pictures, or other art objects; stamp, coin, or baseball card collections; other collections, memorabilia, collectibles',
    textLabel: DESCRIBE,
  },
  '9': {
    words: 'Equipment for sports and hobbies',
    examples:
      'Examples: Sports, photographic, exercise, and other hobby equipment; bicycles, pool tables, golf clubs, skis; canoes and kayaks; carpentry tools; musical instruments',
    textLabel: DESCRIBE,
  },
  '10': {
    words: 'Firearms',
    examples: 'Examples: Pistols, rifles, shotguns, ammunition, and related equipment',
    textLabel: DESCRIBE,
  },
  '11': {
    words: 'Clothes',
    examples: 'Examples: Everyday clothes, furs, leather coats, designer wear, shoes, accessories',
    textLabel: DESCRIBE,
  },
  '12': {
    words: 'Jewelry',
    examples:
      'Examples: Everyday jewelry, costume jewelry, engagement rings, wedding rings, heirloom jewelry, watches, gems, gold, silver',
    textLabel: DESCRIBE,
  },
  '13': {
    words: 'Non-farm animals',
    examples: 'Examples: Dogs, cats, birds, horses',
    textLabel: DESCRIBE,
  },
  '14': {
    words:
      'Any other personal and household items you did not already list, including any health aids you did not list',
    textLabel: GIVE_SPECIFIC,
  },
  '16': {
    words: 'Cash',
    examples:
      'Examples: Money you have in your wallet, in your home, in a safe deposit box, and on hand when you file your petition',
    valueLabel: 'Cash:',
  },
  '17': {
    words: 'Deposits of money',
    examples:
      'Examples: Checking, savings, or other financial accounts; certificates of deposit; shares in credit unions, brokerage houses, and other similar institutions. If you have multiple accounts with the same institution, list each.',
    textLabel: 'Institution name:',
  },
  '18': {
    words: 'Bonds, mutual funds, or publicly traded stocks',
    examples:
      'Examples: Bond funds, investment accounts with brokerage firms, money market accounts',
    textLabel: 'Institution or issuer name:',
  },
  '19': {
    words:
      'Non-publicly traded stock and interests in incorporated and unincorporated businesses, including an interest in an LLC, partnership, and joint venture',
    textLabel: 'Name of entity:',
  },
  '20': {
    words: 'Government and corporate bonds and other negotiable and non-negotiable instruments',
    examples:
      "Negotiable instruments include personal checks, cashiers' checks, promissory notes, and money orders. Non-negotiable instruments are those you cannot transfer to someone by signing or delivering them.",
    textLabel: 'Issuer name:',
  },
  '21': {
    words: 'Retirement or pension accounts',
    examples:
      'Examples: Interests in IRA, ERISA, Keogh, 401(k), 403(b), thrift savings accounts, or other pension or profit-sharing plans',
    textLabel: 'Institution name:',
  },
  '22': {
    words: 'Security deposits and prepayments',
    examples:
      'Your share of all unused deposits you have made so that you may continue service or use from a company. Examples: Agreements with landlords, prepaid rent, public utilities (electric, gas, water), telecommunications companies, or others',
    textLabel: 'Institution name or individual:',
  },
  '23': {
    words:
      'Annuities (A contract for a periodic payment of money to you, either for life or for a number of years)',
    textLabel: 'Issuer name and description:',
  },
  '24': {
    words:
      'Interests in an education IRA, in an account in a qualified ABLE program, or under a qualified state tuition program.',
    examples: '26 U.S.C. §§ 530(b)(1), 529A(b), and 529(b)(1).',
    textLabel:
      'Institution name and description. Separately file the records of any interests. 11 U.S.C. § 521(c):',
  },
  '25': {
    words:
      'Trusts, equitable or future interests in property (other than anything listed in line 1), and rights or powers exercisable for your benefit',
    textLabel: GIVE_SPECIFIC_ABOUT_THEM,
  },
  '26': {
    words: 'Patents, copyrights, trademarks, trade secrets, and other intellectual property',
    examples:
      'Examples: Internet domain names, websites, proceeds from royalties and licensing agreements',
    textLabel: GIVE_SPECIFIC_ABOUT_THEM,
  },
  '27': {
    words: 'Licenses, franchises, and other general intangibles',
    examples:
      'Examples: Building permits, exclusive licenses, cooperative association holdings, liquor licenses, professional licenses',
    textLabel: GIVE_SPECIFIC_ABOUT_THEM,
  },
  '28': {
    words: 'Tax refunds owed to you',
    textLabel:
      'Give specific information about them, including whether you already filed the returns and the tax years.',
  },
  '29': {
    words: 'Family support',
    examples:
      'Examples: Past due or lump sum alimony, spousal support, child support, maintenance, divorce settlement, property settlement',
    textLabel: GIVE_SPECIFIC,
  },
  '30': {
    words: 'Other amounts someone owes you',
    examples:
      "Examples: Unpaid wages, disability insurance payments, disability benefits, sick pay, vacation pay, workers' compensation, Social Security benefits; unpaid loans you made to someone else",
    textLabel: GIVE_SPECIFIC,
  },
  '31': {
    words: 'Interests in insurance policies',
    examples:
      "Examples: Health, disability, or life insurance; health savings account (HSA); credit, homeowner's, or renter's insurance",
    textLabel: 'Company name:',
    valueLabel: 'Surrender or refund value:',
  },
  '32': {
    words: 'Any interest in property that is due you from someone who has died',
    examples:
      'If you are the beneficiary of a living trust, expect proceeds from a life insurance policy, or are currently entitled to receive property because someone has died.',
    textLabel: GIVE_SPECIFIC,
  },
  '33': {
    words:
      'Claims against third parties, whether or not you have filed a lawsuit or made a demand for payment',
    examples: 'Examples: Accidents, employment disputes, insurance claims, or rights to sue',
    textLabel: DESCRIBE_EACH_CLAIM,
  },
  '34': {
    words:
      'Other contingent and unliquidated claims of every nature, including counterclaims of the debtor and rights to set off claims',
    textLabel: DESCRIBE_EACH_CLAIM,
  },
  '35': { words: 'Any financial assets you did not already list', textLabel: GIVE_SPECIFIC },
  '37': {
    words: 'Do you own or have any legal or equitable interest in any business-related property?',
    no: 'No. Go to Part 6.',
    yes: 'Yes. Go to line 38.',
  },
  '38': {
    words: 'Accounts receivable or commissions you already earned',
    textLabel: DESCRIBE_NO_PERIOD,
  },
  '39': {
    words: 'Office equipment, furnishings, and supplies',
    examples:
      'Examples: Business-related computers, software, modems, printers, copiers, fax machines, rugs, telephones, desks, chairs, electronic devices',
    textLabel: DESCRIBE_NO_PERIOD,
  },
  '40': {
    words: 'Machinery, fixtures, equipment, supplies you use in business, and tools of your trade',
    textLabel: DESCRIBE_NO_PERIOD,
  },
  '41': { words: 'Inventory', textLabel: DESCRIBE_NO_PERIOD },
  '42': { words: 'Interests in partnerships or joint ventures', textLabel: 'Name of entity:' },
  '43': { words: 'Customer lists, mailing lists, or other compilations', textLabel: DESCRIBE },
  '44': {
    words: 'Any business-related property you did not already list',
    textLabel: 'Give specific information',
  },
  '46': {
    words:
      'Do you own or have any legal or equitable interest in any farm- or commercial fishing-related property?',
    no: 'No. Go to Part 7.',
    yes: 'Yes. Go to line 47.',
  },
  '47': { words: 'Farm animals', examples: 'Examples: Livestock, poultry, farm-raised fish' },
  '48': { words: 'Crops—either growing or harvested', textLabel: GIVE_SPECIFIC },
  '49': {
    words: 'Farm and fishing equipment, implements, machinery, fixtures, and tools of trade',
  },
  '50': { words: 'Farm and fishing supplies, chemicals, and feed' },
  '51': {
    words: 'Any farm- and commercial fishing-related property you did not already list',
    textLabel: GIVE_SPECIFIC,
  },
  '53': {
    words: 'Do you have other property of any kind you did not already list?',
    examples: 'Examples: Season tickets, country club membership',
    textLabel: GIVE_SPECIFIC,
  },
};

// The words the form prints beside each kind's box or amount, cut of their colons
export const AB_KIND_WORDS: Record<string, Record<string, string>> = {
  '17': {
    checking: 'Checking account',
    savings: 'Savings account',
    cd: 'Certificates of deposit',
    other: 'Other financial account',
  },
  '21': {
    '401k': '401(k) or similar plan',
    pension: 'Pension plan',
    ira: 'IRA',
    retirement: 'Retirement account',
    keogh: 'Keogh',
    additional: 'Additional account',
  },
  '22': {
    electric: 'Electric',
    gas: 'Gas',
    heating_oil: 'Heating oil',
    security_deposit: 'Security deposit on rental unit',
    prepaid_rent: 'Prepaid rent',
    telephone: 'Telephone',
    water: 'Water',
    rented_furniture: 'Rented furniture',
    other: 'Other',
  },
  '28': { federal: 'Federal', state: 'State', local: 'Local' },
  '29': {
    alimony: 'Alimony',
    maintenance: 'Maintenance',
    support: 'Support',
    divorce_settlement: 'Divorce settlement',
    property_settlement: 'Property settlement',
  },
};

// Line 21's name for its kinds (page 6), no cut
export const AB_ACCOUNT_TYPE_LABEL = 'Type of account:';

// Lines 1, 3 and 4, no cut
export const AB_ENTIRE_LABEL = 'Current value of the entire property?';
export const AB_PORTION_LABEL = 'Current value of the portion you own?';
export const AB_WHO_QUESTION = 'Who has an interest in the property? Check one.';
export const AB_COMMUNITY = 'Check if this is community property (see instructions)';
export const AB_DO_NOT_DEDUCT_SCHEDULE_D =
  'Do not deduct secured claims or exemptions. Put the amount of any secured claims on Schedule D: Creditors Who Have Claims Secured by Property.';

// The column heading's second sentence on Parts 3 to 6
export const AB_DO_NOT_DEDUCT = 'Do not deduct secured claims or exemptions.';

// Line 1's boxes
export const AB_STREET_LABEL = 'Street address, if available, or other description';
export const AB_CITY_LABEL = 'City';
export const AB_STATE_LABEL = 'State';
export const AB_ZIP_LABEL = 'ZIP Code';
export const AB_COUNTY_LABEL = 'County';
export const AB_PROPERTY_KIND_QUESTION = 'What is the property? Check all that apply.';
export const AB_NATURE_LABEL =
  'Describe the nature of your ownership interest (such as fee simple, tenancy by the entireties, or a life estate), if known.';
export const AB_PLACE_OTHER_INFO_LABEL =
  'Other information you wish to add about this item, such as local property identification number:';

// Keyed as the backend's PROPERTY_KIND_WORDS, which a sheet prints; the same words
export const AB_PROPERTY_KIND_WORDS: Record<PropertyKind, string> = {
  single_family: 'Single-family home',
  duplex: 'Duplex or multi-unit building',
  condo: 'Condominium or cooperative',
  manufactured: 'Manufactured or mobile home',
  land: 'Land',
  investment: 'Investment property',
  timeshare: 'Timeshare',
  other: 'Other',
};

// Lines 3 and 4's boxes
export const AB_MAKE_LABEL = 'Make:';
export const AB_MODEL_LABEL = 'Model:';
export const AB_YEAR_LABEL = 'Year:';
export const AB_MILEAGE_LABEL = 'Approximate mileage:';
export const AB_VEHICLE_OTHER_INFO_LABEL = 'Other information:';

// Lines 19 and 42's and line 31's other boxes
export const AB_PERCENT_LABEL = '% of ownership:';
export const AB_BENEFICIARY_LABEL = 'Beneficiary:';

// Line 43's question, after its "Yes."
export const AB_PERSONAL_INFO_QUESTION =
  'Do your lists include personally identifiable information (as defined in 11 U.S.C. § 101(41A))?';

// The words beside the form's two boxes, where a line prints nothing longer
export const AB_NO = 'No';

export const AB_YES = 'Yes';

// Schedule D and E/F, the claim rows (form_b106d.pdf pages 1 and 3, form_b106ef.pdf pages 1 and 3)

// D prints "Number" and "Street" as two captions under one line
export const CLAIM_STREET_LABEL = 'Number Street';
export const D_DESCRIBE_PROPERTY_LABEL = 'Describe the property that secures the claim:';
export const CLAIM_STATUS_QUESTION = 'As of the date you file, the claim is: Check all that apply.';

export const CLAIM_STATUS_WORDS: Record<ClaimStatus, string> = {
  contingent: 'Contingent',
  unliquidated: 'Unliquidated',
  disputed: 'Disputed',
};

export const LIEN_QUESTION = 'Nature of lien. Check all that apply.';

// Cut: the printed blank after "Other (including a right to offset)", and the first answer's
// second line is joined to its first
export const LIEN_KIND_WORDS: Record<LienKind, string> = {
  agreement: 'An agreement you made (such as mortgage or secured car loan)',
  statutory: 'Statutory lien (such as tax lien, mechanic’s lien)',
  judgment: 'Judgment lien from a lawsuit',
  other: 'Other (including a right to offset)',
};

export const D_COMMUNITY_LABEL = 'Check if this claim relates to a community debt';
export const EF_COMMUNITY_LABEL = 'Check if this claim is for a community debt';
export const D_DATE_LABEL = 'Date debt was incurred';
export const EF_DATE_LABEL = 'When was the debt incurred?';
export const CLAIM_OFFSET_QUESTION = 'Is the claim subject to offset?';

// Schedule E/F Part 1, row 2.1 (form_b106ef.pdf page 1), and 122A-2 line 35 (b_122a-2_0425-form.pdf
// page 7). Cut: line 35's ", such as those you listed in line 19".
export const PRIORITY_TYPE_WORDS: Record<PriorityType, string> = {
  domestic_support: 'Domestic support obligations',
  taxes: 'Taxes and certain other debts you owe the government',
  intoxicated: 'Claims for death or personal injury while you were intoxicated',
  other: 'Other. Specify',
};
export const PRIORITY_AMOUNT_LABEL = 'Priority amount';
export const NONPRIORITY_AMOUNT_LABEL = 'Nonpriority amount';
export const PRIORITY_OTHER_LABEL = 'Other. Specify';
export const PAST_DUE_NOTE = 'Do not include current or ongoing priority claims.';

export const CLAIM_LAST_4_LABEL = 'Last 4 digits of account number';

// Schedule D Part 2
export const CLAIM_NOTICE_NAME_LABEL = 'Name';

// Schedule G line 1. The answers are asked as "No" and "Yes". Cut from No: ". Check this box and
// file this form with the court with your other schedules. You have nothing else to report on
// this form." Cut from Yes: ". Fill in all of the information below even if the contracts or
// leases are listed on Schedule A/B: Property (Official Form 106A/B)." Both are instructions to a
// person holding the paper form.
export const SCHEDULE_G_LINE_1_QUESTION =
  'Do you have any executory contracts or unexpired leases?';
export const SCHEDULE_G_NAME_LABEL = 'Person or company with whom you have the contract or lease';
export const SCHEDULE_G_PURPOSE_LABEL = 'State what the contract or lease is for';

// Schedule H. The answers are asked as "No" and "Yes", and the line numbers "1.", "2." and "3."
// are dropped. Line 2's "No. Go to line 3." and "Yes." lose their instructions ("Go to line 3."
// and the question that follows each), which the step asks as its own question.
export const SCHEDULE_H_LINE_1_QUESTION =
  'Do you have any codebtors? (If you are filing a joint case, do not list either spouse as a codebtor.)';
export const SCHEDULE_H_LINE_2_QUESTION =
  'Within the last 8 years, have you lived in a community property state or territory? (Community property states and territories include Arizona, California, Idaho, Louisiana, Nevada, New Mexico, Puerto Rico, Texas, Washington, and Wisconsin.)';
export const SCHEDULE_H_LINE_2_SPOUSE_QUESTION =
  'Did your spouse, former spouse, or legal equivalent live with you at the time?';
export const SCHEDULE_H_LINE_2_STATE_LABEL = 'In which community state or territory did you live?';
export const SCHEDULE_H_LINE_2_PERSON_LEAD = 'Fill in the name and current address of that person.';
export const SCHEDULE_H_LINE_2_NAME_LABEL =
  'Name of your spouse, former spouse, or legal equivalent';
// Cut: the "Column 2: " that leads it. It is the legend of a row's links.
export const SCHEDULE_H_COLUMN_2 = 'The creditor to whom you owe the debt';
