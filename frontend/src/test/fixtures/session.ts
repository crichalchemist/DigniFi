/**
 * Reusable test fixtures for intake sessions and related data.
 *
 * Follows the factory pattern — call functions to get fresh copies
 * so mutations in one test don't pollute another.
 */

import type {
  IntakeSession,
  DebtorInfo,
  IncomeInfo,
  ExpenseInfo,
  AssetInfo,
  DebtInfo,
  MeansTestResult,
  UserProfile,
} from '../../types/api';

export const createMockUser = (overrides?: Partial<UserProfile>): UserProfile => ({
  id: 1,
  email: 'jane@example.com',
  username: 'janedoe',
  agreed_to_upl_disclaimer: true,
  upl_disclaimer_agreed_at: '2026-01-15T10:00:00Z',
  created_at: '2026-01-15T10:00:00Z',
  ...overrides,
});

export const createMockDebtorInfo = (overrides?: Partial<DebtorInfo>): DebtorInfo => ({
  id: 1,
  session: 1,
  first_name: 'Jane',
  middle_name: 'Marie',
  last_name: 'Doe',
  ssn: '***-**-6789',
  date_of_birth: '1990-01-15',
  street_address: '123 Main St',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60601',
  phone_number: '312-555-0100',
  email: 'jane@example.com',
  household_size: 1,
  filing_type: 'individual',
  co_debtor_first_name: '',
  co_debtor_middle_name: '',
  co_debtor_last_name: '',
  co_debtor_ssn: '',
  co_debtor_date_of_birth: '',
  ...overrides,
});

export const createMockIncomeInfo = (overrides?: Partial<IncomeInfo>): IncomeInfo => ({
  id: 1,
  session: 1,
  data_source: 'manual',
  monthly_income: [3500, 3500, 3500, 3500, 3500, 3500],
  total_monthly_income: 3500,
  ...overrides,
});

export const createMockExpenseInfo = (overrides?: Partial<ExpenseInfo>): ExpenseInfo => ({
  id: 1,
  session: 1,
  data_source: 'manual',
  rent_or_mortgage: 1200,
  utilities: 150,
  home_maintenance: 50,
  car_payment: 300,
  car_insurance: 100,
  gas_transportation: 80,
  food_groceries: 400,
  childcare: 0,
  medical_expenses: 50,
  insurance_not_deducted: 100,
  other_necessary_expenses: 70,
  total_monthly_expenses: 2500,
  ...overrides,
});

export const createMockAsset = (overrides?: Partial<AssetInfo>): AssetInfo => ({
  id: 1,
  session: 1,
  asset_type: 'vehicle',
  description: '2018 Honda Civic',
  current_value: 12000,
  amount_owed: 5000,
  account_number: '',
  equity: 7000,
  ...overrides,
});

export const createMockDebt = (overrides?: Partial<DebtInfo>): DebtInfo => ({
  id: 1,
  session: 1,
  debt_type: 'credit_card',
  creditor_name: 'Chase Bank',
  account_number: '****1234',
  amount_owed: 8500,
  monthly_payment: 200,
  is_secured: false,
  collateral_description: '',
  ...overrides,
});

export const createMockSession = (overrides?: Partial<IntakeSession>): IntakeSession => ({
  id: 1,
  user: 1,
  district: 1,
  current_step: 1,
  status: 'started',
  created_at: '2026-01-20T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
  completed_at: null,
  ...overrides,
});

export const createMockMeansTestResult = (
  overrides?: Partial<MeansTestResult>,
): MeansTestResult => ({
  passes_means_test: true,
  qualifies_for_fee_waiver: false,
  current_monthly_income: 3500,
  median_income_threshold: 71304,
  disposable_monthly_income: 500,
  message:
    'Based on the information you provided, your income is below the median income threshold for your household size in your district.',
  details: {
    household_size: 1,
    total_income: 3500,
    total_expenses: 3000,
    district_name: 'Northern District of Illinois',
  },
  ...overrides,
});
