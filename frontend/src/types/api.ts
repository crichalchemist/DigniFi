/**
 * TypeScript types for DigniFi backend API
 *
 * These interfaces match the Django REST Framework serializers.
 * Generated from backend/apps/intake/serializers.py and backend/apps/forms/serializers.py
 */

// ============================================================================
// District & Reference Data
// ============================================================================

export interface District {
  id: number;
  name: string;
  code: string;
  state: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Intake Session
// ============================================================================

export interface IntakeSession {
  id: number;
  user: number;
  district: number;
  current_step: number;
  status: 'started' | 'in_progress' | 'completed' | 'abandoned';
  created_at: string;
  updated_at: string;
  completed_at: string | null;

  // Related data (nested serializers)
  debtor_info?: DebtorInfo;
  income_info?: IncomeInfo;
  expense_info?: ExpenseInfo;
  assets?: AssetInfo[];
  debts?: DebtInfo[];
}

export interface DebtorInfo {
  id: number;
  session: number;

  // Personal information
  first_name: string;
  middle_name: string;
  last_name: string;
  ssn: string; // Encrypted in backend
  date_of_birth: string;

  // Contact information
  street_address: string;
  city: string;
  state: string;
  zip_code: string;
  phone_number: string;
  email: string;

  // Household information
  household_size: number;
  filing_type: 'individual' | 'joint';

  // Co-debtor information (for joint filings)
  co_debtor_first_name: string;
  co_debtor_middle_name: string;
  co_debtor_last_name: string;
  co_debtor_ssn: string;
  co_debtor_date_of_birth: string;
}

export interface IncomeInfo {
  id: number;
  session: number;
  data_source: 'manual' | 'bank_import' | 'tax_return';

  // Employment income
  monthly_gross_wages: number;
  monthly_overtime: number;
  monthly_tips: number;

  // Other income
  monthly_rental_income: number;
  monthly_pension: number;
  monthly_social_security: number;
  monthly_unemployment: number;
  monthly_child_support: number;
  monthly_alimony: number;
  monthly_other_income: number;

  // Calculated field
  total_monthly_income: number;
}

export interface ExpenseInfo {
  id: number;
  session: number;
  data_source: 'manual' | 'bank_import';

  // Housing expenses
  rent_or_mortgage: number;
  utilities: number;
  home_maintenance: number;

  // Transportation
  car_payment: number;
  car_insurance: number;
  gas_transportation: number;

  // Living expenses
  food_groceries: number;
  childcare: number;
  medical_expenses: number;
  insurance_not_deducted: number;
  other_necessary_expenses: number;

  // Calculated field
  total_monthly_expenses: number;
}

export interface AssetInfo {
  id: number;
  session: number;
  asset_type: 'real_estate' | 'vehicle' | 'bank_account' | 'retirement_account' | 'personal_property' | 'other';

  description: string;
  current_value: number; // Encrypted in backend
  amount_owed: number; // Encrypted in backend
  account_number: string; // Encrypted in backend

  // Calculated field
  equity: number;
}

export interface DebtInfo {
  id: number;
  session: number;
  debt_type: 'secured' | 'unsecured' | 'priority';

  creditor_name: string;
  account_number: string; // Encrypted in backend
  amount_owed: number; // Encrypted in backend (trauma-informed: "amount owed" vs "debt")
  monthly_payment: number;

  // Classification
  is_secured: boolean;
  collateral_description: string;
}

// ============================================================================
// Means Test
// ============================================================================

export interface MeansTestResult {
  passes_means_test: boolean;
  qualifies_for_fee_waiver: boolean;
  current_monthly_income: number;
  median_income_threshold: number;
  disposable_monthly_income: number;
  message: string; // UPL-compliant message
  details: {
    household_size: number;
    total_income: number;
    total_expenses: number;
    district_name: string;
  };
}

// ============================================================================
// Form Generation
// ============================================================================

export interface GeneratedForm {
  id: number;
  session: number;
  form_type: 'form_101' | 'form_106' | 'form_107';
  form_type_display: string;
  status: 'generated' | 'downloaded' | 'filed';
  status_display: string;
  form_data: Record<string, any>;
  pdf_file_path: string | null;
  generated_by: number;
  generated_at: string;
  updated_at: string;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface CreateSessionRequest {
  district: number;
  current_step: number;
}

export interface CreateSessionResponse {
  session: IntakeSession;
  message: string;
}

export interface UpdateStepRequest {
  current_step: number;
  data?: Partial<IntakeSession>;
}

export interface UpdateStepResponse {
  session: IntakeSession;
  message: string;
}

export interface CalculateMeansTestResponse {
  means_test_result: MeansTestResult;
  session_id: number;
}

export interface GenerateForm101Request {
  session_id: number;
}

export interface GenerateForm101Response {
  form: GeneratedForm;
  message: string;
}

export interface SessionSummaryResponse {
  session: IntakeSession;
  progress: {
    current_step: number;
    status: string;
    completion_percentage: number;
  };
  means_test?: {
    passes: boolean;
    qualifies_fee_waiver: boolean;
  };
  forms: {
    generated_count: number;
    forms: Array<{ form_type: string; status: string }>;
  };
}

// ============================================================================
// API Error Response
// ============================================================================

export interface APIError {
  error: string;
  message: string;
  details?: Record<string, any>;
}
