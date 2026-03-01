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

// ============================================================================
// Wizard Copy
// ============================================================================

export const WIZARD_TITLE = 'Bankruptcy Intake';

export const WIZARD_SUBTITLE =
  "We'll guide you through the information needed to understand your options.";

export const WIZARD_HELP_TEXT =
  'Your progress is saved. You can come back anytime to finish.';

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

// ============================================================================
// Means Test Preview Copy
// ============================================================================

export const MEANS_TEST_PREVIEW_TITLE = 'Eligibility Estimate';

export const MEANS_TEST_INCOMPLETE =
  "We need your income details first. Then we can show an estimate.";

export const MEANS_TEST_CALCULATING = 'Calculating...';

// ============================================================================
// Auth Copy
// ============================================================================

export const AUTH_LOGIN_TITLE = 'Welcome Back';

export const AUTH_LOGIN_SUBTITLE = 'Sign in to continue your bankruptcy intake.';

export const AUTH_REGISTER_TITLE = 'Create Your Account';

export const AUTH_REGISTER_SUBTITLE =
  'Get started with your free bankruptcy intake in minutes.';

// ============================================================================
// Error Messages (Trauma-informed)
// ============================================================================

export const ERROR_NETWORK =
  "We're having trouble connecting. Please check your internet and try again.";

export const ERROR_GENERIC =
  'Something went wrong. Your information is safe — please try again in a moment.';

export const ERROR_SESSION_EXPIRED =
  'Your session has ended. Please sign in again to continue where you left off.';
