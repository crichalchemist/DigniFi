/**
 * UPL (Unauthorized Practice of Law) Disclaimer Constants
 *
 * Single source of truth for all legal disclaimer text.
 * Every user-facing compliance message lives here for easy legal review.
 *
 * Reading level target: 6th-8th grade Flesch-Kincaid.
 */

// ============================================================================
// Core Disclaimers
// ============================================================================

/** Shown at registration, landing page, and form generation */
export const UPL_GENERAL_DISCLAIMER =
  'DigniFi provides legal information and form-preparation tools, not legal advice. ' +
  'We cannot tell you whether to file for bankruptcy or which chapter is right for you. ' +
  'If you need legal advice, please speak with a licensed attorney.';

/** Inline disclaimer for wizard steps */
export const UPL_WIZARD_DISCLAIMER =
  'What you see here is general legal facts. ' +
  'It is not legal advice about your case.';

/** Shown alongside means test preview results */
export const UPL_MEANS_TEST_DISCLAIMER =
  'This is only an estimate based on what you entered. ' +
  'A court makes the final decision.';

/** Shown on form generation/download pages */
export const UPL_FORM_DISCLAIMER =
  'These forms use the facts you entered. ' +
  'DigniFi does not check your answers or tell you what to enter. ' +
  'Please review all forms before you file them with the court.';

/** Shown on asset/debt steps about exemptions */
export const UPL_EXEMPTION_DISCLAIMER =
  'Exemption rules vary by state. The information shown here is general guidance. ' +
  'We cannot advise you on which exemptions apply to your situation.';

/** Banner disclaimer before final submission on ReviewStep */
export const UPL_REVIEW_DISCLAIMER =
  'By finishing this intake, you agree that you know DigniFi only gives legal facts ' +
  'and helps you fill out forms. We are not your lawyer. ' +
  'If any part of this process is unclear, please talk to a lawyer or your local legal aid office.';

/** Confirmation text for modal before generating forms */
export const UPL_FORM_GENERATION_CONFIRMATION =
  'I know that DigniFi is a self-help tool. It gives legal facts, not legal advice. ' +
  'The forms use what I entered. I will review them before I file.';

// ============================================================================
// Variant Labels (for component display modes)
// ============================================================================

export type UPLDisclaimerVariant = 'inline' | 'banner' | 'modal' | 'checkbox';

/** Map of variant to default aria-label for screen readers */
export const UPL_ARIA_LABELS: Record<UPLDisclaimerVariant, string> = {
  inline: 'Legal information disclaimer',
  banner: 'Important legal disclaimer',
  modal: 'Legal acknowledgment required',
  checkbox: 'Legal disclaimer acknowledgment',
};
