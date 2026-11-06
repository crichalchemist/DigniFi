/**
 * Persona fixture data for E2E tests.
 *
 * Mirrors the backend seed_demo_data command but in TypeScript.
 * Each persona exercises a distinct eligibility path through ILND.
 */

// Unique per test run so registration never collides with a previous run's
// users when the database persists (local dev). CI databases are fresh.
const RUN_ID = Date.now().toString(36);

export interface PersonaDebtor {
  first_name: string;
  last_name: string;
  middle_name: string;
  ssn: string;
  date_of_birth: string; // YYYY-MM-DD for input fields
  phone: string;
  email: string;
  street_address: string;
  city: string;
  state: string;
  zip_code: string;
  // One of the 18 counties step 1 lists
  county: string;
}

/** The Income step's ten boxes, named as the backend stores them (INCOME_FIELDS in types/api.ts) */
export type IncomeSourceKey =
  | 'monthly_gross_wages'
  | 'monthly_overtime'
  | 'monthly_tips'
  | 'monthly_interest_and_dividends'
  | 'monthly_pension'
  | 'monthly_social_security'
  | 'monthly_unemployment'
  | 'monthly_child_support'
  | 'monthly_alimony'
  | 'monthly_other_income';

/** The four answers to Form 122A-1 line 1 on the Income step (MaritalStatus in types/api.ts) */
export type MaritalStatus =
  | 'not_married'
  | 'married_spouse_filing'
  | 'married_together'
  | 'married_separately';

/** One person on the Income step's household list, every question answered */
export interface PersonaMember {
  relationship: string;
  age: number;
  lives_with_you: boolean;
  claimed_or_supported: boolean;
  // On the spouse's row only
  spouse_is_dependent?: boolean;
}

export interface PersonaIncome {
  marital_status: MaritalStatus;
  // Everyone in the persona's home or supported by them; [] answers "No one else"
  members: PersonaMember[];
  // Each amount the persona types, in its own box. A source left out stays blank.
  sources: Partial<Record<IncomeSourceKey, number>>;
  // The spouse's ten, typed only by a persona living with their spouse
  spouse_sources?: Record<IncomeSourceKey, number>;
  // The persona's businesses and rental properties; [] presses "I have no business or rental income."
  business: PersonaEntry[];
  // The spouse's, typed only by a persona living with their spouse
  spouse_business?: PersonaEntry[];
  // "Is your income now different from that average?" Every persona answers no: none has current
  // figures to type.
  now_different: 'yes' | 'no';
  spouse_now_different?: 'yes' | 'no';
  // Schedule I line 8f, other government assistance
  assistance: PersonaAssistance;
  spouse_assistance?: PersonaAssistance;
}

/** One person's answer to Schedule I 8f, with cash and non-cash help kept apart */
export interface PersonaAssistance {
  answer: 'yes' | 'no';
  cash_kind?: string;
  cash_amount?: number;
  noncash_kind?: string;
  noncash_value?: number;
}

/** One business or rental property on the Income step's list, in six-month averages */
export interface PersonaEntry {
  kind: 'business' | 'rental';
  description: string;
  gross: number;
  expenses: number;
}

/** The boxes a Schedule A/B row can hold, named as the backend's `details` keys */
export interface PersonaAssetDetails {
  street?: string;
  city?: string;
  state?: string;
  zip?: string;
  county?: string;
  property_kinds?: string[];
  nature?: string;
  make?: string;
  model?: string;
  year?: string;
  mileage?: string;
  other_info?: string;
  who?: 'only_you' | 'with_someone';
  kind?: string;
  beneficiary?: string;
}

/** One Schedule A/B row, as seed_demo_data writes it: its line, its words and its figures */
export interface PersonaAsset {
  ab_line: string;
  /** The line's one text box, where it has one */
  description?: string;
  details?: PersonaAssetDetails;
  /** Typed as given: a $0 is typed as 0, never skipped */
  current_value: number;
  entire_value?: number;
}

/** A line 3 row, as seed_demo_data's `_car`: the two values, the make and model, and who */
function car(
  value: number,
  entire: number,
  make: string,
  model: string,
  year: string,
  mileage: string,
  more: PersonaAssetDetails = {}
): PersonaAsset {
  return {
    ab_line: '3',
    details: { make, model, year, mileage, who: 'only_you', ...more },
    current_value: value,
    entire_value: entire,
  };
}

export interface PersonaDebt {
  creditor_name: string;
  debt_type: string;
  amount_owed: number;
  monthly_payment: number;
  is_in_collections: boolean;
  // Required by the Debts step when debt_type is secured (auto_loan, mortgage)
  collateral_description?: string;
}

/** The eight payroll deductions of Schedule I lines 5a-5h (DEDUCTION_FIELDS in types/api.ts) */
export type DeductionField =
  | 'payroll_tax'
  | 'payroll_mandatory_retirement'
  | 'payroll_voluntary_retirement'
  | 'payroll_retirement_loan'
  | 'payroll_insurance'
  | 'payroll_support'
  | 'payroll_union_dues'
  | 'payroll_other';

export interface PersonaData {
  username: string;
  password: string;
  debtor: PersonaDebtor;
  income: PersonaIncome;
  // The Take-home pay step: each deduction typed, a box left out stays blank
  deductions: Partial<Record<DeductionField, number>>;
  // The spouse's, typed only by a persona living with their spouse
  spouse_deductions?: Partial<Record<DeductionField, number>>;
  expenses: Record<string, number>;
  // Schedule J line 3, answered on the Expenses step
  expenses_include_others: 'yes' | 'no';
  // The Specify boxes beside lines 16, 19 and 21, typed only by a persona who has something to say
  expense_texts?: Partial<
    Record<'taxes_specify' | 'support_others_specify' | 'other_expenses_specify', string>
  >;
  assets: PersonaAsset[];
  /** Gate lines answered Yes: Part 5's lines show only under 37's Yes (Part 6's under 46's) */
  asset_gates?: string[];
  debts: PersonaDebt[];
  filing_fee: PersonaFilingFee;
  expected: { passes_means_test: boolean };
}

/** Form 101 line 8, answered on the filing-fee page */
export type PaymentChoice = 'pay_in_full' | 'installments' | 'waiver';

/** 103B lines 4, 5, 7 and 9, answered under the waiver. Every persona answers No to 4, 7 and 9. */
export interface PersonaWaiverAnswers {
  income_change_answer: 'no';
  installments_explanation: string;
  others_covered_answer: 'no';
  expense_change_answer: 'no';
}

/** What a persona answers on the filing-fee page (3f spec §10) */
export interface PersonaFilingFee {
  payment_choice: PaymentChoice;
  waiver?: PersonaWaiverAnswers;
}

export const MARIA: PersonaData = {
  username: `e2e_maria_${RUN_ID}`,
  password: 'TestPass-2026!',
  debtor: {
    first_name: 'Maria',
    last_name: 'Torres',
    middle_name: '',
    ssn: '900-11-1001',
    date_of_birth: '1988-06-15',
    phone: '312-555-0101',
    email: `maria.e2e+${RUN_ID}@test.dignifi.org`,
    county: 'Cook',
    street_address: '2145 W Division St Apt 3',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60622',
  },
  income: {
    marital_status: 'not_married',
    members: [
      { relationship: 'son', age: 8, lives_with_you: true, claimed_or_supported: true },
      { relationship: 'daughter', age: 5, lives_with_you: true, claimed_or_supported: true },
    ],
    sources: { monthly_gross_wages: 3200, monthly_interest_and_dividends: 0 },
    business: [],
    now_different: 'no',
    assistance: { answer: 'yes', noncash_kind: 'SNAP (food stamps)', noncash_value: 350 },
  },
  deductions: {
    payroll_tax: 400,
    payroll_mandatory_retirement: 0,
    payroll_voluntary_retirement: 0,
    payroll_retirement_loan: 0,
    payroll_insurance: 0,
    payroll_support: 0,
    payroll_union_dues: 0,
    payroll_other: 0,
  },
  expenses_include_others: 'no',
  expenses: {
    rent_or_mortgage: 1100,
    utilities: 180,
    home_maintenance: 0,
    vehicle_payment: 0,
    vehicle_insurance: 85,
    vehicle_maintenance: 40,
    food_and_groceries: 450,
    clothing: 60,
    medical_expenses: 75,
    childcare: 400,
    child_support_paid: 0,
    insurance_not_deducted: 120,
    other_expenses: 50,
    personal_care: 40,
  },
  expense_texts: {
    other_expenses_specify: 'School supplies and fees',
  },
  assets: [
    car(6500, 6500, 'Honda', 'Civic', '2015', '120000'),
    { ab_line: '6', description: 'Beds, sofa, kitchen table, dishes', current_value: 600 },
    { ab_line: '7', description: 'Old laptop, cell phone, 32-inch TV', current_value: 200 },
    { ab_line: '11', description: 'Everyday clothes and shoes', current_value: 250 },
    { ab_line: '16', current_value: 40 },
    {
      ab_line: '17',
      description: 'JPMorgan Chase',
      details: { kind: 'checking' },
      current_value: 340,
    },
    // Her insurance policy has no cash value: typed 0, not skipped
    { ab_line: '31', description: 'Millbrook Mutual Life', current_value: 0 },
  ],
  debts: [
    {
      creditor_name: 'Brightwater Card Services',
      debt_type: 'credit_card',
      amount_owed: 4200,
      monthly_payment: 85,
      is_in_collections: true,
    },
    {
      creditor_name: 'Larkfield General Hospital',
      debt_type: 'medical',
      amount_owed: 12800,
      monthly_payment: 0,
      is_in_collections: true,
    },
    {
      creditor_name: 'Ironbridge Card Company',
      debt_type: 'personal_loan',
      amount_owed: 3500,
      monthly_payment: 120,
      is_in_collections: false,
    },
  ],
  filing_fee: {
    payment_choice: 'waiver',
    waiver: {
      income_change_answer: 'no',
      installments_explanation:
        "I support two children on what I earn. After rent, food, the car and the children's costs, there is not enough left each month to pay the fee, even in parts.",
      others_covered_answer: 'no',
      expense_change_answer: 'no',
    },
  },
  expected: { passes_means_test: true },
};

export const JAMES: PersonaData = {
  username: `e2e_james_${RUN_ID}`,
  password: 'TestPass-2026!',
  debtor: {
    first_name: 'James',
    last_name: 'Washington',
    middle_name: 'D',
    ssn: '900-22-2002',
    date_of_birth: '1975-03-22',
    phone: '312-555-0202',
    email: `james.e2e+${RUN_ID}@test.dignifi.org`,
    county: 'Cook',
    street_address: '850 N State St Apt 1204',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60610',
  },
  income: {
    marital_status: 'not_married',
    members: [],
    sources: { monthly_gross_wages: 5833, monthly_interest_and_dividends: 0 },
    business: [],
    now_different: 'no',
    assistance: { answer: 'no' },
  },
  deductions: { payroll_tax: 1288, payroll_union_dues: 45 },
  expenses_include_others: 'no',
  expenses: {
    rent_or_mortgage: 1650,
    utilities: 120,
    home_maintenance: 0,
    vehicle_payment: 350,
    vehicle_insurance: 110,
    vehicle_maintenance: 50,
    food_and_groceries: 400,
    clothing: 80,
    medical_expenses: 50,
    childcare: 0,
    child_support_paid: 0,
    insurance_not_deducted: 200,
    other_expenses: 100,
    home_insurance: 15,
    personal_care: 40,
    entertainment: 45,
  },
  expense_texts: {
    other_expenses_specify: 'Work boots and small tools for my job',
  },
  assets: [
    car(14000, 14000, 'Toyota', 'Camry', '2019', '78000'),
    {
      ab_line: '6',
      description: 'Bed, couch, table, kitchenware (secondhand)',
      current_value: 500,
    },
    { ab_line: '7', description: 'TV, laptop, cell phone', current_value: 400 },
    { ab_line: '11', description: 'Everyday clothes and work clothes', current_value: 300 },
    { ab_line: '16', current_value: 40 },
    {
      ab_line: '17',
      description: 'Bank of America',
      details: { kind: 'checking' },
      current_value: 1200,
    },
  ],
  debts: [
    {
      creditor_name: 'Meridale National Bank',
      debt_type: 'credit_card',
      amount_owed: 9800,
      monthly_payment: 200,
      is_in_collections: false,
    },
    {
      creditor_name: 'Crestway Auto Credit',
      debt_type: 'auto_loan',
      amount_owed: 8500,
      monthly_payment: 350,
      is_in_collections: false,
      collateral_description: '2019 Toyota Camry',
    },
  ],
  filing_fee: { payment_choice: 'pay_in_full' },
  expected: { passes_means_test: true },
};

export const PRIYA: PersonaData = {
  username: `e2e_priya_${RUN_ID}`,
  password: 'TestPass-2026!',
  debtor: {
    first_name: 'Priya',
    last_name: 'Sharma',
    middle_name: '',
    ssn: '900-33-3003',
    date_of_birth: '1982-11-08',
    phone: '312-555-0303',
    email: `priya.e2e+${RUN_ID}@test.dignifi.org`,
    county: 'Cook',
    street_address: '456 W Fullerton Pkwy',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60614',
  },
  income: {
    marital_status: 'married_together',
    members: [
      {
        relationship: 'spouse',
        age: 45,
        lives_with_you: true,
        claimed_or_supported: true,
        spouse_is_dependent: false,
      },
      { relationship: 'daughter', age: 10, lives_with_you: true, claimed_or_supported: true },
      { relationship: 'son', age: 7, lives_with_you: true, claimed_or_supported: true },
    ],
    // $12,000 plus the spouse's $1,800 is $13,800 a month, $165,600 a year — above the
    // $137,902 HH4 median, so the annualized § 707(b) comparison fails as the persona intends.
    sources: { monthly_gross_wages: 12000, monthly_interest_and_dividends: 0 },
    business: [],
    now_different: 'no',
    assistance: { answer: 'no' },
    spouse_sources: {
      monthly_gross_wages: 1800,
      monthly_overtime: 0,
      monthly_tips: 0,
      monthly_interest_and_dividends: 0,
      monthly_pension: 0,
      monthly_social_security: 0,
      monthly_unemployment: 0,
      monthly_child_support: 0,
      monthly_alimony: 0,
      monthly_other_income: 0,
    },
    spouse_business: [],
    spouse_now_different: 'no',
    spouse_assistance: { answer: 'no' },
  },
  deductions: { payroll_tax: 2450, payroll_voluntary_retirement: 600, payroll_insurance: 620 },
  spouse_deductions: { payroll_tax: 250 },
  expenses_include_others: 'yes',
  expenses: {
    rent_or_mortgage: 2800,
    utilities: 250,
    home_maintenance: 100,
    vehicle_payment: 450,
    vehicle_insurance: 180,
    vehicle_maintenance: 60,
    food_and_groceries: 800,
    clothing: 150,
    medical_expenses: 100,
    childcare: 1200,
    child_support_paid: 0,
    insurance_not_deducted: 350,
    other_expenses: 200,
    home_insurance: 20,
    personal_care: 60,
    entertainment: 80,
    charitable_contributions: 50,
    taxes_not_deducted: 200,
  },
  expense_texts: {
    taxes_specify: 'IRS installment agreement, 2025 tax',
    other_expenses_specify: "Children's after-school activities",
  },
  assets: [
    car(20500, 20500, 'Honda', 'CR-V EX', '2021', '41000'),
    { ab_line: '6', description: 'Household goods and furniture', current_value: 2500 },
    { ab_line: '7', description: 'Family laptop, two phones, TV', current_value: 1500 },
    { ab_line: '11', description: 'Clothes', current_value: 800 },
    { ab_line: '12', description: 'Wedding and engagement rings', current_value: 1200 },
    // Both joint accounts: the whole balance is her portion
    {
      ab_line: '17',
      description: 'JPMorgan Chase',
      details: { kind: 'checking' },
      current_value: 1900,
    },
    {
      ab_line: '17',
      description: 'JPMorgan Chase',
      details: { kind: 'savings' },
      current_value: 8500,
    },
    {
      ab_line: '21',
      description: 'Vanguard',
      details: { kind: '401k' },
      current_value: 31000,
    },
    // Line 31's text box is the form's "Company name": two companies, both typed 0
    {
      ab_line: '31',
      description: 'Wrenfield Life',
      details: { beneficiary: 'Spouse' },
      current_value: 0,
    },
    { ab_line: '31', description: 'Alderbrook Assurance', current_value: 0 },
  ],
  debts: [
    {
      creditor_name: 'Silverpine Card Services',
      debt_type: 'credit_card',
      amount_owed: 22000,
      monthly_payment: 500,
      is_in_collections: false,
    },
    {
      creditor_name: 'Westhaven University Medical Center',
      debt_type: 'medical',
      amount_owed: 35000,
      monthly_payment: 0,
      is_in_collections: true,
    },
  ],
  filing_fee: { payment_choice: 'pay_in_full' },
  expected: { passes_means_test: false },
};

export const DESHAWN: PersonaData = {
  username: `e2e_deshawn_${RUN_ID}`,
  password: 'TestPass-2026!',
  debtor: {
    first_name: 'DeShawn',
    last_name: 'Mitchell',
    middle_name: 'R',
    ssn: '900-44-4004',
    date_of_birth: '1980-09-03',
    phone: '312-555-0404',
    email: `deshawn.e2e+${RUN_ID}@test.dignifi.org`,
    county: 'Cook',
    street_address: '7823 S Sangamon St',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60620',
  },
  income: {
    marital_status: 'married_together',
    members: [
      {
        relationship: 'spouse',
        age: 44,
        lives_with_you: true,
        claimed_or_supported: true,
        spouse_is_dependent: false,
      },
    ],
    sources: { monthly_gross_wages: 3500, monthly_interest_and_dividends: 0 },
    business: [],
    now_different: 'no',
    assistance: { answer: 'no' },
    spouse_sources: {
      monthly_gross_wages: 1000,
      monthly_overtime: 0,
      monthly_tips: 0,
      monthly_interest_and_dividends: 0,
      monthly_pension: 0,
      monthly_social_security: 0,
      monthly_unemployment: 0,
      monthly_child_support: 0,
      monthly_alimony: 0,
      monthly_other_income: 0,
    },
    spouse_business: [],
    spouse_now_different: 'no',
    spouse_assistance: { answer: 'no' },
  },
  deductions: { payroll_tax: 450 },
  spouse_deductions: { payroll_tax: 115 },
  expenses_include_others: 'yes',
  expenses: {
    rent_or_mortgage: 1200,
    utilities: 200,
    home_maintenance: 100,
    vehicle_payment: 0,
    vehicle_insurance: 95,
    vehicle_maintenance: 50,
    food_and_groceries: 350,
    clothing: 50,
    medical_expenses: 60,
    childcare: 0,
    child_support_paid: 0,
    insurance_not_deducted: 150,
    other_expenses: 40,
    personal_care: 40,
    entertainment: 25,
    charitable_contributions: 50,
  },
  expense_texts: {
    other_expenses_specify: 'Printer ink, paper and postage',
  },
  assets: [
    {
      ab_line: '1',
      details: {
        street: '7823 S Sangamon St',
        city: 'Chicago',
        state: 'IL',
        zip: '60620',
        county: 'Cook',
        property_kinds: ['single_family'],
        who: 'only_you',
        nature: 'Fee simple',
      },
      current_value: 180000,
      entire_value: 180000,
    },
    car(8000, 8000, 'Ford', 'F-150', '2012', '168000'),
    { ab_line: '6', description: 'Furniture, appliances and beds', current_value: 1500 },
    { ab_line: '7', description: 'TV, laptop and phone', current_value: 400 },
    { ab_line: '11', description: 'Everyday clothes and work boots', current_value: 300 },
    { ab_line: '12', description: 'Wedding band and watch', current_value: 600 },
    { ab_line: '16', current_value: 60 },
    {
      ab_line: '17',
      description: 'PNC Bank',
      details: { kind: 'checking' },
      current_value: 640,
    },
    {
      ab_line: '21',
      description: 'Fidelity',
      details: { kind: '401k' },
      current_value: 12000,
    },
  ],
  debts: [
    {
      creditor_name: 'Harrowgate Home Loans',
      debt_type: 'mortgage',
      amount_owed: 160000,
      monthly_payment: 1200,
      is_in_collections: false,
      collateral_description: 'Single-family home, 7823 S Sangamon St',
    },
    {
      creditor_name: 'Tallgrass Credit Management',
      debt_type: 'credit_card',
      amount_owed: 6700,
      monthly_payment: 0,
      is_in_collections: true,
    },
    {
      creditor_name: 'Lakeline Electric',
      debt_type: 'utility',
      amount_owed: 800,
      monthly_payment: 0,
      is_in_collections: true,
    },
    {
      creditor_name: 'Southmoor Health',
      debt_type: 'medical',
      amount_owed: 4200,
      monthly_payment: 0,
      is_in_collections: true,
    },
  ],
  filing_fee: { payment_choice: 'installments' },
  expected: { passes_means_test: true },
};

export const SARAH: PersonaData = {
  username: `e2e_sarah_${RUN_ID}`,
  password: 'TestPass-2026!',
  debtor: {
    first_name: 'Sarah',
    last_name: 'Chen',
    middle_name: '',
    ssn: '900-55-5005',
    date_of_birth: '1995-01-20',
    phone: '312-555-0505',
    email: `sarah.e2e+${RUN_ID}@test.dignifi.org`,
    county: 'Cook',
    street_address: '1520 N Damen Ave Apt 2F',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60622',
  },
  income: {
    marital_status: 'not_married',
    members: [
      { relationship: 'roommate', age: 29, lives_with_you: true, claimed_or_supported: false },
    ],
    sources: { monthly_gross_wages: 2000, monthly_interest_and_dividends: 0 },
    business: [],
    now_different: 'no',
    assistance: { answer: 'no' },
  },
  deductions: { payroll_tax: 250 },
  expenses_include_others: 'no',
  expenses: {
    rent_or_mortgage: 850,
    utilities: 80,
    home_maintenance: 0,
    vehicle_payment: 0,
    vehicle_insurance: 0,
    vehicle_maintenance: 0,
    food_and_groceries: 250,
    clothing: 30,
    medical_expenses: 20,
    childcare: 0,
    child_support_paid: 0,
    insurance_not_deducted: 0,
    other_expenses: 0,
    personal_care: 30,
    entertainment: 20,
  },
  assets: [],
  debts: [
    {
      creditor_name: 'Keelson Loan Servicing',
      debt_type: 'student_loan',
      amount_owed: 28000,
      monthly_payment: 0,
      is_in_collections: false,
    },
    {
      creditor_name: 'Lakemont University Hospital',
      debt_type: 'medical',
      amount_owed: 3400,
      monthly_payment: 0,
      is_in_collections: true,
    },
  ],
  filing_fee: {
    payment_choice: 'waiver',
    waiver: {
      income_change_answer: 'no',
      installments_explanation:
        'I have no savings. My pay covers rent, food and my bus pass, and what is left each month goes to bills I already owe.',
      others_covered_answer: 'no',
      expense_change_answer: 'no',
    },
  },
  expected: { passes_means_test: true },
};

// Data from docs/testing/persona-briefs/andres-kettleby.md, with an SSN of the journey's own:
// the seed's demo_andres has 900-66-0006.
export const ANDRES: PersonaData = {
  username: `e2e_andres_${RUN_ID}`,
  password: 'TestPass-2026!',
  debtor: {
    first_name: 'Andrés',
    last_name: 'Kettleby',
    middle_name: 'J',
    ssn: '900-66-6006',
    date_of_birth: '1988-04-12',
    phone: '630-555-0161',
    email: `andres.e2e+${RUN_ID}@test.dignifi.org`,
    county: 'Kane',
    street_address: '1418 Marquette Ave Apt 2',
    city: 'Aurora',
    state: 'IL',
    zip_code: '60505',
  },
  income: {
    marital_status: 'not_married',
    members: [
      { relationship: 'daughter', age: 9, lives_with_you: true, claimed_or_supported: true },
    ],
    // His driving ($4,200 from the apps less $830 of driving costs) is a business entry.
    // Every box is $0.
    sources: {
      monthly_gross_wages: 0,
      monthly_overtime: 0,
      monthly_tips: 0,
      monthly_interest_and_dividends: 0,
      monthly_pension: 0,
      monthly_social_security: 0,
      monthly_unemployment: 0,
      monthly_child_support: 0,
      monthly_alimony: 0,
      monthly_other_income: 0,
    },
    business: [
      {
        kind: 'business',
        description: 'Rideshare and delivery driving',
        gross: 4200,
        expenses: 830,
      },
    ],
    now_different: 'no',
    assistance: { answer: 'no' },
  },
  deductions: {},
  expenses_include_others: 'no',
  expenses: {
    rent_or_mortgage: 1150,
    utilities: 210,
    home_maintenance: 0,
    // The Corolla lease, his only car
    vehicle_payment: 389,
    vehicle_insurance: 165,
    vehicle_maintenance: 60,
    food_and_groceries: 520,
    clothing: 60,
    medical_expenses: 45,
    childcare: 180,
    child_support_paid: 0,
    insurance_not_deducted: 0,
    other_expenses: 0,
    home_insurance: 15,
    personal_care: 40,
    entertainment: 30,
    charitable_contributions: 20,
    taxes_not_deducted: 150,
  },
  expense_texts: {
    taxes_specify: '2026 estimated income tax',
  },
  assets: [
    // Leased, so 0 and 0 (the lease is on Schedule G)
    car(0, 0, 'Toyota', 'Corolla Hybrid', '2024', '61000', { other_info: 'Leased' }),
    // His half of a car titled to him and his brother
    car(4300, 8600, 'Honda', 'Fit', '2017', '96000', { who: 'with_someone' }),
    { ab_line: '6', description: 'Beds, couch, table, kitchen things', current_value: 1200 },
    { ab_line: '7', description: 'Phone, TV', current_value: 400 },
    { ab_line: '11', description: 'Clothes', current_value: 300 },
    { ab_line: '16', current_value: 60 },
    {
      ab_line: '17',
      description: 'Harborline Bank',
      details: { kind: 'checking' },
      current_value: 412,
    },
    {
      ab_line: '17',
      description: 'Prairie Line Credit Union',
      details: { kind: 'savings' },
      current_value: 85,
    },
    // Part 5: driving is his business, so line 37 is Yes
    {
      ab_line: '38',
      description: 'Driving payouts already earned, not yet paid by the apps',
      current_value: 310,
    },
    {
      ab_line: '40',
      description: 'Insulated delivery bags, phone mount, dash camera',
      current_value: 150,
    },
  ],
  asset_gates: ['37'],
  debts: [
    {
      creditor_name: 'Copperline Auto Finance',
      debt_type: 'auto_loan',
      amount_owed: 7800,
      // His brother drives the car and pays the loan he co-signed
      monthly_payment: 0,
      is_in_collections: false,
      collateral_description: '2017 Honda Fit, co-owned with my brother',
    },
    {
      creditor_name: 'Bright Signal Wireless',
      debt_type: 'utility',
      amount_owed: 640,
      monthly_payment: 0,
      is_in_collections: false,
    },
    {
      creditor_name: 'Calumet Ridge Medical Center',
      debt_type: 'medical',
      amount_owed: 3850,
      monthly_payment: 0,
      is_in_collections: true,
    },
    {
      creditor_name: 'Driveline Tire & Auto',
      debt_type: 'credit_card',
      amount_owed: 1180,
      monthly_payment: 0,
      is_in_collections: false,
    },
    {
      creditor_name: 'Illinois State Toll Highway Authority',
      debt_type: 'other',
      amount_owed: 380,
      monthly_payment: 0,
      is_in_collections: false,
    },
    {
      creditor_name: 'Tallowfield Lending Co.',
      debt_type: 'personal_loan',
      amount_owed: 4100,
      monthly_payment: 0,
      is_in_collections: false,
    },
    {
      creditor_name: 'Northgate Card Services',
      debt_type: 'credit_card',
      amount_owed: 6420,
      monthly_payment: 0,
      is_in_collections: false,
    },
    {
      creditor_name: 'Prairie Line Credit Union',
      debt_type: 'credit_card',
      amount_owed: 1760,
      monthly_payment: 0,
      is_in_collections: false,
    },
    {
      creditor_name: 'Hollowmere Residential LLC',
      debt_type: 'other',
      amount_owed: 1850,
      monthly_payment: 0,
      is_in_collections: false,
    },
    {
      creditor_name: 'Sablewood Bank',
      debt_type: 'credit_card',
      amount_owed: 2980,
      monthly_payment: 0,
      is_in_collections: false,
    },
  ],
  filing_fee: { payment_choice: 'installments' },
  expected: { passes_means_test: true },
};
