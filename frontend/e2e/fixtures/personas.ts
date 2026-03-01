/**
 * Persona fixture data for E2E tests.
 *
 * Mirrors the backend seed_demo_data command but in TypeScript.
 * Each persona exercises a distinct eligibility path through ILND.
 */

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
}

export interface PersonaIncome {
  marital_status: string;
  number_of_dependents: number;
  total_monthly_income: number;
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

export const MARIA: PersonaData = {
  username: 'e2e_maria',
  password: 'TestPass-2026!',
  debtor: {
    first_name: 'Maria',
    last_name: 'Torres',
    middle_name: '',
    ssn: '900-11-1001',
    date_of_birth: '1988-06-15',
    phone: '312-555-0101',
    email: 'maria.e2e@test.dignifi.org',
    street_address: '2145 W Division St Apt 3',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60622',
  },
  income: {
    marital_status: 'single',
    number_of_dependents: 2,
    total_monthly_income: 3200,
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
    { asset_type: 'bank_account', description: 'Chase checking', current_value: 340, amount_owed: 0, financial_institution: 'JPMorgan Chase' },
  ],
  debts: [
    { creditor_name: 'Capital One', debt_type: 'credit_card', amount_owed: 4200, monthly_payment: 85, is_in_collections: true },
    { creditor_name: 'Northwestern Memorial Hospital', debt_type: 'medical', amount_owed: 12800, monthly_payment: 0, is_in_collections: true },
    { creditor_name: 'Discover Financial', debt_type: 'personal_loan', amount_owed: 3500, monthly_payment: 120, is_in_collections: false },
  ],
  expected: { passes_means_test: true, fee_waiver_eligible: true },
};

export const JAMES: PersonaData = {
  username: 'e2e_james',
  password: 'TestPass-2026!',
  debtor: {
    first_name: 'James',
    last_name: 'Washington',
    middle_name: 'D',
    ssn: '900-22-2002',
    date_of_birth: '1975-03-22',
    phone: '312-555-0202',
    email: 'james.e2e@test.dignifi.org',
    street_address: '850 N State St Apt 1204',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60610',
  },
  income: {
    marital_status: 'single',
    number_of_dependents: 0,
    total_monthly_income: 5833,
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
    { asset_type: 'vehicle', description: '2019 Toyota Camry', current_value: 14000, amount_owed: 8500 },
    { asset_type: 'bank_account', description: 'Bank of America checking', current_value: 1200, amount_owed: 0, financial_institution: 'Bank of America' },
  ],
  debts: [
    { creditor_name: 'Citibank', debt_type: 'credit_card', amount_owed: 9800, monthly_payment: 200, is_in_collections: false },
    { creditor_name: 'Toyota Financial Services', debt_type: 'auto_loan', amount_owed: 8500, monthly_payment: 350, is_in_collections: false },
  ],
  expected: { passes_means_test: true, fee_waiver_eligible: false },
};

export const PRIYA: PersonaData = {
  username: 'e2e_priya',
  password: 'TestPass-2026!',
  debtor: {
    first_name: 'Priya',
    last_name: 'Sharma',
    middle_name: '',
    ssn: '900-33-3003',
    date_of_birth: '1982-11-08',
    phone: '312-555-0303',
    email: 'priya.e2e@test.dignifi.org',
    street_address: '456 W Fullerton Pkwy',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60614',
  },
  income: {
    marital_status: 'married_joint',
    number_of_dependents: 2,
    total_monthly_income: 10000,
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
    { asset_type: 'bank_account', description: 'Joint savings', current_value: 8500, amount_owed: 0, financial_institution: 'Chase' },
  ],
  debts: [
    { creditor_name: 'American Express', debt_type: 'credit_card', amount_owed: 22000, monthly_payment: 500, is_in_collections: false },
    { creditor_name: 'Rush University Medical Center', debt_type: 'medical', amount_owed: 35000, monthly_payment: 0, is_in_collections: true },
  ],
  expected: { passes_means_test: false, fee_waiver_eligible: false },
};

export const DESHAWN: PersonaData = {
  username: 'e2e_deshawn',
  password: 'TestPass-2026!',
  debtor: {
    first_name: 'DeShawn',
    last_name: 'Mitchell',
    middle_name: 'R',
    ssn: '900-44-4004',
    date_of_birth: '1980-09-03',
    phone: '312-555-0404',
    email: 'deshawn.e2e@test.dignifi.org',
    street_address: '7823 S Sangamon St',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60620',
  },
  income: {
    marital_status: 'married_joint',
    number_of_dependents: 0,
    total_monthly_income: 3500,
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
    { asset_type: 'real_property', description: 'Single-family home, 7823 S Sangamon', current_value: 180000, amount_owed: 160000 },
    { asset_type: 'vehicle', description: '2012 Ford F-150', current_value: 8000, amount_owed: 0 },
    { asset_type: 'retirement_account', description: '401(k) through employer', current_value: 12000, amount_owed: 0, financial_institution: 'Fidelity' },
  ],
  debts: [
    { creditor_name: 'Wells Fargo Home Mortgage', debt_type: 'mortgage', amount_owed: 160000, monthly_payment: 1200, is_in_collections: false },
    { creditor_name: 'Midland Credit Management', debt_type: 'credit_card', amount_owed: 6700, monthly_payment: 0, is_in_collections: true },
    { creditor_name: 'ComEd', debt_type: 'utility', amount_owed: 800, monthly_payment: 0, is_in_collections: true },
    { creditor_name: 'Advocate Health', debt_type: 'medical', amount_owed: 4200, monthly_payment: 0, is_in_collections: true },
  ],
  expected: { passes_means_test: true, fee_waiver_eligible: false },
};

export const SARAH: PersonaData = {
  username: 'e2e_sarah',
  password: 'TestPass-2026!',
  debtor: {
    first_name: 'Sarah',
    last_name: 'Chen',
    middle_name: '',
    ssn: '900-55-5005',
    date_of_birth: '1995-01-20',
    phone: '312-555-0505',
    email: 'sarah.e2e@test.dignifi.org',
    street_address: '1520 N Damen Ave Apt 2F',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60622',
  },
  income: {
    marital_status: 'single',
    number_of_dependents: 0,
    total_monthly_income: 2000,
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
    { creditor_name: 'Navient', debt_type: 'student_loan', amount_owed: 28000, monthly_payment: 0, is_in_collections: false },
    { creditor_name: 'University of Illinois Hospital', debt_type: 'medical', amount_owed: 3400, monthly_payment: 0, is_in_collections: true },
  ],
  expected: { passes_means_test: true, fee_waiver_eligible: true },
};
