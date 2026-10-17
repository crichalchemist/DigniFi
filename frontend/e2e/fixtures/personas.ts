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
  // Household & filing info (required on the DebtorInfo step).
  // household_size mirrors seed_demo_data: dependents + 1 (+1 if married).
  household_size: number;
  filing_type: 'individual' | 'joint';
}

/** The Income step's ten boxes, named as the backend stores them (INCOME_FIELDS in types/api.ts) */
export type IncomeSourceKey =
  | 'monthly_gross_wages'
  | 'monthly_overtime'
  | 'monthly_tips'
  | 'monthly_rental_income'
  | 'monthly_pension'
  | 'monthly_social_security'
  | 'monthly_unemployment'
  | 'monthly_child_support'
  | 'monthly_alimony'
  | 'monthly_other_income';

export interface PersonaIncome {
  marital_status: string;
  number_of_dependents: number;
  // Each amount the persona types, in its own box. A source left out stays blank.
  sources: Partial<Record<IncomeSourceKey, number>>;
}

export interface PersonaAsset {
  asset_type: string;
  description: string;
  current_value: number;
  amount_owed: number;
  financial_institution?: string;
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

export interface PersonaData {
  username: string;
  password: string;
  debtor: PersonaDebtor;
  income: PersonaIncome;
  expenses: Record<string, number>;
  assets: PersonaAsset[];
  debts: PersonaDebt[];
  expected: {
    passes_means_test: boolean;
    fee_waiver_eligible: boolean;
  };
}

/** What a persona answers on the fee-waiver page (Form 103B lines 2 and 3) */
export interface PersonaFeeWaiver {
  take_home_pay: number;
  // The "What kind?" answer, or null for a persona who gets no non-cash help
  noncash_assistance: string | null;
}

/** A persona the means test sends to the fee-waiver page */
export interface WaiverPersonaData extends PersonaData {
  fee_waiver: PersonaFeeWaiver;
}

export const MARIA: WaiverPersonaData = {
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
    household_size: 3,
    filing_type: 'individual',
    street_address: '2145 W Division St Apt 3',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60622',
  },
  income: {
    marital_status: 'single',
    number_of_dependents: 2,
    sources: { monthly_gross_wages: 3200 },
  },
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
  },
  assets: [
    { asset_type: 'vehicle', description: '2015 Honda Civic', current_value: 6500, amount_owed: 0 },
    {
      asset_type: 'bank_account',
      description: 'Chase checking',
      current_value: 340,
      amount_owed: 0,
      financial_institution: 'JPMorgan Chase',
    },
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
  fee_waiver: { take_home_pay: 2800, noncash_assistance: 'SNAP (food stamps)' },
  expected: { passes_means_test: true, fee_waiver_eligible: true },
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
    household_size: 1,
    filing_type: 'individual',
    street_address: '850 N State St Apt 1204',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60610',
  },
  income: {
    marital_status: 'single',
    number_of_dependents: 0,
    sources: { monthly_gross_wages: 5833 },
  },
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
  },
  assets: [
    {
      asset_type: 'vehicle',
      description: '2019 Toyota Camry',
      current_value: 14000,
      amount_owed: 8500,
    },
    {
      asset_type: 'bank_account',
      description: 'Bank of America checking',
      current_value: 1200,
      amount_owed: 0,
      financial_institution: 'Bank of America',
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
  expected: { passes_means_test: true, fee_waiver_eligible: false },
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
    household_size: 4,
    filing_type: 'individual',
    street_address: '456 W Fullerton Pkwy',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60614',
  },
  income: {
    marital_status: 'married_joint',
    number_of_dependents: 2,
    // $12,000/month = $144,000/year — above the $137,902 HH4 median, so the
    // annualized § 707(b) comparison fails as the persona intends.
    sources: { monthly_gross_wages: 12000 },
  },
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
  },
  assets: [
    {
      asset_type: 'bank_account',
      description: 'Joint savings',
      current_value: 8500,
      amount_owed: 0,
      financial_institution: 'Chase',
    },
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
  expected: { passes_means_test: false, fee_waiver_eligible: false },
};

export const DESHAWN: WaiverPersonaData = {
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
    household_size: 2,
    filing_type: 'individual',
    street_address: '7823 S Sangamon St',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60620',
  },
  income: {
    marital_status: 'married_joint',
    number_of_dependents: 0,
    sources: { monthly_gross_wages: 3500 },
  },
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
  },
  assets: [
    {
      asset_type: 'real_property',
      description: 'Single-family home, 7823 S Sangamon',
      current_value: 180000,
      amount_owed: 160000,
    },
    { asset_type: 'vehicle', description: '2012 Ford F-150', current_value: 8000, amount_owed: 0 },
    {
      asset_type: 'retirement_account',
      description: '401(k) through employer',
      current_value: 12000,
      amount_owed: 0,
      financial_institution: 'Fidelity',
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
  fee_waiver: { take_home_pay: 3050, noncash_assistance: null },
  // $3,500/month = $42,000/year — below 60% of the HH2 median ($56,360.40),
  // so DeShawn qualifies for the fee waiver as well as Chapter 7.
  expected: { passes_means_test: true, fee_waiver_eligible: true },
};

export const SARAH: WaiverPersonaData = {
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
    household_size: 1,
    filing_type: 'individual',
    street_address: '1520 N Damen Ave Apt 2F',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60622',
  },
  income: {
    marital_status: 'single',
    number_of_dependents: 0,
    sources: { monthly_gross_wages: 2000 },
  },
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
    other_expenses: 50,
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
  fee_waiver: { take_home_pay: 1750, noncash_assistance: null },
  expected: { passes_means_test: true, fee_waiver_eligible: true },
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
    household_size: 2,
    filing_type: 'individual',
    street_address: '1418 Marquette Ave Apt 2',
    city: 'Aurora',
    state: 'IL',
    zip_code: '60505',
  },
  income: {
    marital_status: 'single',
    number_of_dependents: 1,
    // What he keeps from driving ($4,200 from the apps less $830 of driving costs) is other
    // income until the Income step asks for business income (3a1.Q1). Every other box is $0.
    sources: {
      monthly_gross_wages: 0,
      monthly_overtime: 0,
      monthly_tips: 0,
      monthly_rental_income: 0,
      monthly_pension: 0,
      monthly_social_security: 0,
      monthly_unemployment: 0,
      monthly_child_support: 0,
      monthly_alimony: 0,
      monthly_other_income: 3370,
    },
  },
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
  },
  assets: [
    // His half of a car titled to him and his brother
    {
      asset_type: 'vehicle',
      description: '2017 Honda Fit',
      current_value: 4300,
      amount_owed: 7800,
    },
    {
      asset_type: 'personal_property',
      description: 'Household goods, electronics and clothing',
      current_value: 1900,
      amount_owed: 0,
    },
    {
      asset_type: 'bank_account',
      description: 'Harborline Bank checking',
      current_value: 412,
      amount_owed: 0,
      financial_institution: 'Harborline Bank',
    },
    {
      asset_type: 'bank_account',
      description: 'Prairie Line Credit Union share savings',
      current_value: 85,
      amount_owed: 0,
      financial_institution: 'Prairie Line Credit Union',
    },
  ],
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
  // Today's flag (income under 60% of the median) qualifies him for a fee waiver, but he pays
  // in installments and files no application (3a1.Q2), so he has no fee_waiver answers.
  expected: { passes_means_test: true, fee_waiver_eligible: true },
};
