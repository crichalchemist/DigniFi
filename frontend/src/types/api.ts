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
  // The six months the Income step's averages cover, worked out by the server (3e2 spec §4.4)
  income_window: IncomePeriod;

  // Related data (nested serializers)
  debtor_info?: DebtorInfo;
  income_info?: IncomeInfo;
  expense_info?: ExpenseInfo;
  assets?: AssetInfo[];
  debts?: DebtInfo[];
  household?: Household | null;
  spouse_income?: SpouseIncome | null;
  form_answers?: Record<string, unknown>;
  sofa_report?: Record<string, unknown>;
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
  phone: string;
  email: string;
}

/** A yes or no answer; null (unanswered) is kept apart from both */
export type YesNo = 'yes' | 'no';

export interface IncomeInfo {
  id: number;
  session: number;
  /** The six months the filer last confirmed by Continue on the Income step. Read-only. */
  answered_window?: IncomePeriod | null;
  data_source: 'manual' | 'bank_import' | 'tax_return';

  // The six-month total saved before income was stored by source. Read-only: the Income step
  // shows it while asking the filer to split it.
  monthly_income?: number[] | null;

  // The ten monthly amounts by source (INCOME_FIELDS). Empty (null) when the filer gave none.
  monthly_gross_wages?: number | null;
  monthly_overtime?: number | null;
  monthly_tips?: number | null;
  monthly_interest_and_dividends?: number | null;
  monthly_pension?: number | null;
  monthly_social_security?: number | null;
  monthly_unemployment?: number | null;
  monthly_child_support?: number | null;
  monthly_alimony?: number | null;
  monthly_other_income?: number | null;

  // The old rental figure. Read-only and unread by the step: rental income is a list entry now.
  readonly monthly_rental_income?: number | null;

  // The marriage answer, null until the filer gives one
  marital_status?: MaritalStatus | null;

  // The list of businesses and rental properties. null is unanswered; [] is none.
  business_and_rental?: IncomeEntry[] | null;

  // Whether the income is now different from the six-month average. null is unanswered.
  income_now_different?: YesNo | null;

  // The ten monthly amounts now, asked only under "yes" (CURRENT_INCOME_FIELDS)
  current_monthly_gross_wages?: number | null;
  current_monthly_overtime?: number | null;
  current_monthly_tips?: number | null;
  current_monthly_interest_and_dividends?: number | null;
  current_monthly_pension?: number | null;
  current_monthly_social_security?: number | null;
  current_monthly_unemployment?: number | null;
  current_monthly_child_support?: number | null;
  current_monthly_alimony?: number | null;
  current_monthly_other_income?: number | null;

  // Other government assistance (Schedule I line 8f): the answer, then cash and non-cash apart
  assistance_answer?: YesNo | null;
  cash_assistance_kind?: string;
  cash_assistance_amount?: number | null;
  noncash_assistance_kind?: string;
  noncash_assistance_value?: number | null;

  // Payroll deductions (Schedule I lines 5a-5h), asked on the Take-home pay step
  payroll_tax?: number | null;
  payroll_mandatory_retirement?: number | null;
  payroll_voluntary_retirement?: number | null;
  payroll_retirement_loan?: number | null;
  payroll_insurance?: number | null;
  payroll_support?: number | null;
  payroll_union_dues?: number | null;
  payroll_other?: number | null;
  payroll_other_specify?: string;

  // The last day of the six-month window the filer last confirmed. Read-only.
  readonly income_period_end?: string | null;

  // Calculated field: the ten added up, null when the filer gave none of them
  total_monthly_income: number | null;
}

/**
 * The ten monthly income amounts, under the names the backend stores and the court forms read.
 * DRF drops any other name without an error, so the step saves only these. The API sends each
 * as a decimal string or null.
 */
export const INCOME_FIELDS = [
  'monthly_gross_wages',
  'monthly_overtime',
  'monthly_tips',
  'monthly_interest_and_dividends',
  'monthly_pension',
  'monthly_social_security',
  'monthly_unemployment',
  'monthly_child_support',
  'monthly_alimony',
  'monthly_other_income',
] as const;

export type IncomeField = (typeof INCOME_FIELDS)[number];

/** The ten amounts now, asked only when the person's income is now different */
export const CURRENT_INCOME_FIELDS = [
  'current_monthly_gross_wages',
  'current_monthly_overtime',
  'current_monthly_tips',
  'current_monthly_interest_and_dividends',
  'current_monthly_pension',
  'current_monthly_social_security',
  'current_monthly_unemployment',
  'current_monthly_child_support',
  'current_monthly_alimony',
  'current_monthly_other_income',
] as const;

/** The two assistance amounts, which the API sends as decimal strings */
export const ASSISTANCE_AMOUNT_FIELDS = [
  'cash_assistance_amount',
  'noncash_assistance_value',
] as const;

/** The eight payroll deductions, Schedule I lines 5a-5h, which the API sends as decimal strings */
export const DEDUCTION_FIELDS = [
  'payroll_tax',
  'payroll_mandatory_retirement',
  'payroll_voluntary_retirement',
  'payroll_retirement_loan',
  'payroll_insurance',
  'payroll_support',
  'payroll_union_dues',
  'payroll_other',
] as const;

export type DeductionField = (typeof DEDUCTION_FIELDS)[number];

/** A business or a rental property on the Income step's list */
export type EntryKind = 'business' | 'rental';

/**
 * One business or property. A null is an unanswered box. The amounts are monthly averages;
 * the `current_` pair is asked only when the person's income is now different.
 */
export interface IncomeEntry {
  id?: number;
  kind: EntryKind | null;
  description: string | null;
  gross: number | null;
  expenses: number | null;
  current_gross: number | null;
  current_expenses: number | null;
}

/** The four amounts of an entry, which the API sends as decimal strings */
export const ENTRY_AMOUNT_KEYS = [
  'gross',
  'expenses',
  'current_gross',
  'current_expenses',
] as const;

/** A span of days, as ISO dates ("2026-04-01") */
export interface IncomePeriod {
  start: string;
  end: string;
}

/** The four answers to the marriage question on the Income step. */
export type MaritalStatus =
  | 'not_married'
  | 'married_spouse_filing'
  | 'married_together'
  | 'married_separately';

/** How a person on the household list is related to the filer. Never free text. */
export type Relationship =
  | 'spouse'
  | 'son'
  | 'daughter'
  | 'stepchild'
  | 'grandchild'
  | 'parent'
  | 'sibling'
  | 'other_relative'
  | 'unmarried_partner'
  | 'roommate'
  | 'other';

/** One person in the filer's home or supported by the filer. A null is an unanswered box. */
export interface HouseholdMember {
  id?: number;
  relationship: Relationship | null;
  age: number | null;
  lives_with_you: boolean | null;
  claimed_or_supported: boolean | null;
  // On the spouse's row only
  spouse_is_dependent?: boolean | null;
}

/**
 * The county (step 1) and the household list (Income step). A null `members` means the filer
 * never answered; an empty list means no one lives with them or depends on them.
 */
export interface Household {
  county: string | null;
  members: HouseholdMember[] | null;
  // Counted by the server
  readonly family_size?: number | null;
  readonly fee_waiver_household_size?: number | null;
}

/** A married filer's spouse's ten monthly income amounts, under the same names as the filer's. */
export type SpouseIncome = Partial<
  Omit<
    IncomeInfo,
    | 'id'
    | 'session'
    | 'data_source'
    | 'monthly_income'
    | 'marital_status'
    | 'income_period_end'
    | 'total_monthly_income'
  >
>;

export interface ExpenseInfo {
  id: number;
  session: number;
  data_source: 'manual' | 'bank_import';

  // The 26 Schedule J amounts, named in EXPENSE_FIELDS
  rent_or_mortgage: number;
  real_estate_taxes: number;
  home_insurance: number;
  home_maintenance: number;
  hoa_dues: number;
  utilities: number;
  food_and_groceries: number;
  childcare: number;
  clothing: number;
  personal_care: number;
  medical_expenses: number;
  vehicle_maintenance: number;
  entertainment: number;
  charitable_contributions: number;
  vehicle_insurance: number;
  insurance_not_deducted: number;
  taxes_not_deducted: number;
  vehicle_payment: number;
  child_support_paid: number;
  support_others: number;
  other_property_mortgages: number;
  other_property_taxes: number;
  other_property_insurance: number;
  other_property_upkeep: number;
  other_property_hoa_dues: number;
  other_expenses: number;

  // The three "Specify" texts beside lines 16, 19 and 21, up to 100 characters each
  taxes_specify: string;
  support_others_specify: string;
  other_expenses_specify: string;

  // Schedule J line 3; null is unanswered
  expenses_include_others: YesNo | null;

  // Calculated field, read-only: the server adds the amounts up
  total_monthly_expenses: number;
}

/**
 * The 26 monthly expense amounts, in Schedule J's order, under the names the backend stores
 * and the court forms read. DRF drops any other name without an error, so the step sums and
 * sends only these.
 */
export const EXPENSE_FIELDS = [
  'rent_or_mortgage',
  'real_estate_taxes',
  'home_insurance',
  'home_maintenance',
  'hoa_dues',
  'utilities',
  'food_and_groceries',
  'childcare',
  'clothing',
  'personal_care',
  'medical_expenses',
  'vehicle_maintenance',
  'entertainment',
  'charitable_contributions',
  'vehicle_insurance',
  'insurance_not_deducted',
  'taxes_not_deducted',
  'vehicle_payment',
  'child_support_paid',
  'support_others',
  'other_property_mortgages',
  'other_property_taxes',
  'other_property_insurance',
  'other_property_upkeep',
  'other_property_hoa_dues',
  'other_expenses',
] as const;

export type ExpenseField = (typeof EXPENSE_FIELDS)[number];

/** The three "Specify" texts, which sit beside lines 16, 19 and 21 */
export const EXPENSE_SPECIFY_FIELDS = [
  'taxes_specify',
  'support_others_specify',
  'other_expenses_specify',
] as const;

export type ExpenseSpecifyField = (typeof EXPENSE_SPECIFY_FIELDS)[number];

export interface AssetInfo {
  id: number;
  session: number;
  asset_type:
    | 'real_property'
    | 'vehicle'
    | 'bank_account'
    | 'retirement_account'
    | 'personal_property'
    | 'other';

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
  debt_type:
    | 'credit_card'
    | 'medical'
    | 'personal_loan'
    | 'student_loan'
    | 'auto_loan'
    | 'mortgage'
    | 'utility'
    | 'other';

  creditor_name: string;
  account_number: string; // Encrypted in backend
  amount_owed: number; // Encrypted in backend (trauma-informed: "amount owed" vs "debt")
  monthly_payment: number;

  // Classification
  is_secured: boolean;
  priority_classification?: 'unsecured' | 'secured' | 'priority';
  collateral_description: string;

  // Document scanning
  is_draft?: boolean;
  source_document?: number | null;
  source_document_name?: string | null;
}

/**
 * An asset or debt row as the wizard holds it. `_key` is the browser's own name for the row and
 * never reaches the server: a loaded row's id, or `new-<n>` from a counter for a new row. A save
 * writes the id the server gave each row into the row with that key (DIG-273).
 */
export type WizardRow<T> = Partial<T> & { _key: string };

/** A contract or lease (Schedule G), as the contracts list endpoint sends and saves it */
export interface ExecutoryContract {
  id?: number;
  counterparty_name: string;
  contract_type: 'lease' | 'contract' | 'other';
  description: string;
}

/** A codebtor (Schedule H), as the codebtors list endpoint sends and saves it */
export interface Codebtor {
  id?: number;
  name: string;
  street_address: string;
  city: string;
  state: string;
  zip_code: string;
  relationship: 'spouse' | 'former_spouse' | 'relative' | 'friend' | 'business_partner' | 'other';
}

// ============================================================================
// Means Test
// ============================================================================

// Mirrors MeansTestCalculator.calculate() — cmi is monthly, the median is
// annual, annualized_cmi (details) is what the § 707(b) comparison uses
export interface MeansTestResult {
  passes_means_test: boolean;
  qualifies_for_fee_waiver: boolean;
  cmi: number;
  median_income_threshold: number;
  family_size: number;
  message: string; // UPL-compliant message
  details: {
    cmi: number;
    annualized_cmi: number;
    median_income_threshold: number;
    family_size: number;
    [key: string]: unknown;
  };
  means_test_id: number;
}

// ============================================================================
// Filing fee
// ============================================================================

// Form 101 line 8, "How you will pay the fee"
export type PaymentChoice = 'pay_in_full' | 'installments' | 'waiver';

// What the page shows beside the question (3f spec §6.2): amounts as decimal strings
export interface FilingFeeInformation {
  family_size: number;
  limit_monthly: string;
  guideline: { year: number; effective_date: string; source_url: string };
  family_income_monthly: string;
}

// The session's filing-fee record, as GET and PUT .../filing-fee/ return it. Null is unanswered.
export interface FilingFee {
  payment_choice: PaymentChoice | null;
  income_change_answer: YesNo | null;
  income_change_explanation: string;
  installments_explanation: string;
  others_covered_answer: YesNo | null;
  others_covered_who: string;
  expense_change_answer: YesNo | null;
  expense_change_explanation: string;
  information: FilingFeeInformation | null;
  information_gap: 'income' | 'no_table' | null;
}

// ============================================================================
// Form Generation
// ============================================================================

/** All 17 form types registered in the backend form registry */
export type FormType =
  | 'form_101' // Voluntary Petition
  | 'form_103b' // Fee Waiver Application
  | 'form_106dec' // Declaration
  | 'form_106sum' // Summary of Assets/Liabilities
  | 'form_107' // Statement of Financial Affairs
  | 'form_121' // SSN Statement
  | 'form_122a1' // Means Test
  | 'form_122a1_supp' // Means Test Supplement
  | 'form_122a2' // Means Test Expense Calculation
  | 'schedule_a_b' // Property
  | 'schedule_c' // Exemptions
  | 'schedule_d' // Secured Creditors
  | 'schedule_e_f' // Unsecured Creditors
  | 'schedule_g' // Executory Contracts & Unexpired Leases
  | 'schedule_h' // Codebtors
  | 'schedule_i' // Income
  | 'schedule_j'; // Expenses

export type FormStatus = 'generated' | 'downloaded' | 'filed';

export interface GeneratedForm {
  id: number;
  session: number;
  form_type: FormType;
  form_type_display: string;
  status: FormStatus;
  status_display: string;
  pdf_file_path: string | null;
  upl_disclaimer?: string;
  generated_by: number;
  generated_at: string;
  updated_at: string;
}

/** Display metadata for each form type (frontend-only, for the dashboard) */
export const FORM_TYPE_METADATA: Record<
  FormType,
  { label: string; description: string; order: number }
> = {
  form_101: {
    label: 'Form 101 - Voluntary Petition',
    description: 'Your official petition to file for bankruptcy',
    order: 1,
  },
  form_103b: {
    label: 'Form 103B - Fee Waiver Application',
    description: 'Request to waive the filing fee',
    order: 2,
  },
  form_106dec: {
    label: 'Form 106Dec - Declaration',
    description: 'Declaration about the accuracy of your forms',
    order: 3,
  },
  form_106sum: {
    label: 'Form 106Sum - Summary',
    description: 'Summary of your assets and liabilities',
    order: 4,
  },
  form_107: {
    label: 'Form 107 - Financial Affairs',
    description: 'Statement of your financial affairs',
    order: 5,
  },
  form_121: {
    label: 'Form 121 - SSN Statement',
    description: 'Social Security number verification',
    order: 6,
  },
  form_122a1: {
    label: 'Form 122A-1 - Means Test',
    description: 'Chapter 7 means test calculation',
    order: 7,
  },
  form_122a1_supp: {
    label: 'Form 122A-1 Supp - Means Test Supplement',
    description: 'Supplement to the Chapter 7 means test',
    order: 8,
  },
  form_122a2: {
    label: 'Form 122A-2 - Means Test Expenses',
    description: 'Chapter 7 means test expense calculation',
    order: 9,
  },
  schedule_a_b: {
    label: 'Schedule A/B - Property',
    description: 'List of all your property',
    order: 11,
  },
  schedule_c: {
    label: 'Schedule C - Exemptions',
    description: 'Property you claim as exempt',
    order: 12,
  },
  schedule_d: {
    label: 'Schedule D - Secured Creditors',
    description: 'Creditors with collateral claims',
    order: 13,
  },
  schedule_e_f: {
    label: 'Schedule E/F - Unsecured Creditors',
    description: 'Creditors without collateral',
    order: 14,
  },
  schedule_g: {
    label: 'Schedule G - Executory Contracts',
    description: 'Executory contracts and unexpired leases',
    order: 15,
  },
  schedule_h: {
    label: 'Schedule H - Codebtors',
    description: 'People who are also liable for your debts',
    order: 16,
  },
  schedule_i: { label: 'Schedule I - Income', description: 'Your current income', order: 17 },
  schedule_j: { label: 'Schedule J - Expenses', description: 'Your current expenses', order: 18 },
};

// ============================================================================
// Document scanning
// ============================================================================

export type OCRStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'validated';

/** Why a failed scan failed. Blank on every other status, and on rows from before 0006. */
export type OCRFailureReason = 'nothing_found' | 'processing_error';

export interface OCRResult {
  status: OCRStatus;
  failure_reason: OCRFailureReason | '';
  confidence_scores: Record<string, number>;
  overall_confidence: number;
  user_validated: boolean;
}

export interface UploadedDocument {
  id: number;
  document_type: string;
  original_filename: string;
  uploaded_at: string;
  ocr_result: OCRResult | null;
}

export interface DocumentUploadResponse {
  id: number;
  status: 'processing';
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
  /** Each form refused, with the wizard step (a `WIZARD_STEPS` key) or page that fixes it, if any */
  errors: Array<{ form_type: string; error: string; step?: string; page?: string }>;
  total_generated: number;
  total_errors: number;
}

/** A dated reference table the forms were filled from (forms step 3a1 spec §3.6) */
export interface DatedTableUsed {
  name: string;
  /** ISO date, YYYY-MM-DD */
  effective_date: string;
  /** ISO date; null when no newer table is expected */
  valid_through: string | null;
  source_url: string;
}

/** The six months the filer last confirmed, and the six months in force now */
export interface IncomePeriodNotice {
  answered_for: IncomePeriod | null;
  now: IncomePeriod;
}

/** What GET /api/forms/packet/ returns: the forms that apply to this filer, in filing order */
export interface FormPacketResponse {
  session: number;
  form_types: FormType[];
  tables: DatedTableUsed[];
  income_period?: IncomePeriodNotice;
  /** Form 101 line 8: the filer's answer, null until they choose (forms step 3f §7) */
  payment_choice?: PaymentChoice | null;
}

/** What `api.forms.packet` returns */
export interface Packet {
  form_types: FormType[];
  tables: DatedTableUsed[];
  income_period: IncomePeriodNotice | null;
  payment_choice: PaymentChoice | null;
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

export interface DemoLoginResponse extends LoginResponse {
  session_id?: number;
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

// ============================================================================
// SOFA Report (Form 107 Financial Affairs) API
// ============================================================================

export interface SOFAPriorIncome {
  id: number;
  year: number;
  source: string;
  gross_amount: string;
}

export interface SOFACreditorPayment {
  id: number;
  creditor_name: string;
  total_paid: string;
  dates_of_payments: string;
}

export interface SOFAReport {
  id: number;
  session: number;
  has_prior_income: boolean;
  has_creditor_payments: boolean;
  has_business: boolean;
  prior_income: SOFAPriorIncome[];
  creditor_payments: SOFACreditorPayment[];
}

/** One thing Complete found missing, with the wizard step (a `WIZARD_STEPS` key) that fixes it */
export interface CompletionError {
  step: string;
  message: string;
}

export interface APIError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
  /** Complete's refusal: each thing missing, in wizard order */
  errors?: CompletionError[];
  /** The wizard step key that fixes a refusal, when one does */
  step?: string;
  /** The page (a route) that fixes a refusal, when one does */
  page?: string;
}

// ============================================================================
// SP4: Ask-Modules UI Spec
// ============================================================================

export interface UIFieldSpec {
  binding: string;
  prompt: string;
  widget: string;
  help_text?: string | null;
  conditional_on?: string | null;
  repeat?: string | null;
  repeat_capacity?: number | null;
  fields?: UIFieldSpec[];
  options?: Array<{ label: string; value: string }> | null;
}

export interface UIStep {
  title: string;
  fields: UIFieldSpec[];
}

export interface FormUISpec {
  form_type: string;
  steps: UIStep[];
}

export interface AnswerPayload {
  form_type: string;
  binding: string;
  value: string;
}
