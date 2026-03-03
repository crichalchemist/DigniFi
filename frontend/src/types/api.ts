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

  // Backend expects this
  monthly_income?: number[];

  // Frontend form fields (not in backend model, but useful for state)
  monthly_gross_wages?: number;
  monthly_overtime?: number;
  monthly_tips?: number;
  monthly_rental_income?: number;
  monthly_pension?: number;
  monthly_social_security?: number;
  monthly_unemployment?: number;
  monthly_child_support?: number;
  monthly_alimony?: number;
  monthly_other_income?: number;

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

/** All 13 form types registered in the backend form registry */
export type FormType =
  | 'form_101'      // Voluntary Petition
  | 'form_103b'     // Fee Waiver Application
  | 'form_106dec'   // Declaration
  | 'form_106sum'   // Summary of Assets/Liabilities
  | 'form_107'      // Statement of Financial Affairs
  | 'form_121'      // SSN Statement
  | 'form_122a1'    // Means Test
  | 'schedule_a_b'  // Property
  | 'schedule_c'    // Exemptions
  | 'schedule_d'    // Secured Creditors
  | 'schedule_e_f'  // Unsecured Creditors
  | 'schedule_i'    // Income
  | 'schedule_j';   // Expenses

export type FormStatus = 'generated' | 'downloaded' | 'filed';

export interface GeneratedForm {
  id: number;
  session: number;
  form_type: FormType;
  form_type_display: string;
  status: FormStatus;
  status_display: string;
  form_data: Record<string, unknown>;
  pdf_file_path: string | null;
  upl_disclaimer?: string;
  generated_by: number;
  generated_at: string;
  updated_at: string;
}

/** Display metadata for each form type (frontend-only, for the dashboard) */
export const FORM_TYPE_METADATA: Record<FormType, { label: string; description: string; order: number }> = {
  form_101:     { label: 'Form 101 - Voluntary Petition', description: 'Your official petition to file for bankruptcy', order: 1 },
  form_103b:    { label: 'Form 103B - Fee Waiver Application', description: 'Request to waive the filing fee', order: 2 },
  form_106dec:  { label: 'Form 106Dec - Declaration', description: 'Declaration about the accuracy of your forms', order: 3 },
  form_106sum:  { label: 'Form 106Sum - Summary', description: 'Summary of your assets and liabilities', order: 4 },
  form_107:     { label: 'Form 107 - Financial Affairs', description: 'Statement of your financial affairs', order: 5 },
  form_121:     { label: 'Form 121 - SSN Statement', description: 'Social Security number verification', order: 6 },
  form_122a1:   { label: 'Form 122A-1 - Means Test', description: 'Chapter 7 means test calculation', order: 7 },
  schedule_a_b: { label: 'Schedule A/B - Property', description: 'List of all your property', order: 8 },
  schedule_c:   { label: 'Schedule C - Exemptions', description: 'Property you claim as exempt', order: 9 },
  schedule_d:   { label: 'Schedule D - Secured Creditors', description: 'Creditors with collateral claims', order: 10 },
  schedule_e_f: { label: 'Schedule E/F - Unsecured Creditors', description: 'Creditors without collateral', order: 11 },
  schedule_i:   { label: 'Schedule I - Income', description: 'Your current income', order: 12 },
  schedule_j:   { label: 'Schedule J - Expenses', description: 'Your current expenses', order: 13 },
};

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

export interface GenerateFormRequest {
  session_id: number;
  form_type?: FormType;
}

export interface GenerateFormResponse {
  form: GeneratedForm;
  message: string;
}

/** @deprecated Use GenerateFormRequest */
export type GenerateForm101Request = GenerateFormRequest;
/** @deprecated Use GenerateFormResponse */
export type GenerateForm101Response = GenerateFormResponse;

export interface GenerateAllFormsResponse {
  generated: GeneratedForm[];
  errors: Array<{ form_type: string; error: string }>;
  total_generated: number;
  total_errors: number;
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
// Authentication
// ============================================================================

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  agreed_to_upl_disclaimer: boolean;
  agreed_to_terms: boolean;
}

export interface RegisterResponse {
  id: number;
  email: string;
  username: string;
}

export interface UserProfile {
  id: number;
  email: string;
  username: string;
  agreed_to_upl_disclaimer: boolean;
  upl_disclaimer_agreed_at: string | null;
  created_at: string;
}

// ============================================================================
// API Error Response
// ============================================================================

export interface APIError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}
