/**
 * Where each of Form 101's text boxes stops: the character caps build_form_101.py measures from
 * the boxes at 6 pt (form_101.limits.json's `limits`), and build_form_101a.py the five landlord
 * keys (form_101a.limits.json's `limits`). test_petition_frontend_copy.py pins this copy to the
 * union of both files and the row-cell ceiling to the server's.
 */
export const PETITION_TEXT_LIMITS: Record<string, number> = {
  name_suffix: 30,
  mailing_street: 42,
  mailing_po_box: 55,
  mailing_city: 35,
  mailing_state: 4,
  mailing_zip: 9,
  venue_reason: 104,
  business_name: 100,
  business_street: 88,
  business_city: 53,
  business_state: 4,
  business_zip: 29,
  hazard_what: 82,
  hazard_why: 53,
  hazard_street: 66,
  hazard_city: 45,
  hazard_state: 4,
  hazard_zip: 22,
  debt_nature_text: 82,
  preparer_name: 79,
  // Form 101A's landlord boxes (form_101a.limits.json)
  landlord_name: 65,
  landlord_street: 65,
  landlord_city: 35,
  landlord_state: 2,
  landlord_zip: 13,
};

// A row cell has no cap of its own: it is measured where it prints (PF2-10), and stops where the
// server stops storing text (`PetitionAnswers.TEXT_CEILING`)
export const PETITION_ROW_CELL_MAX_LENGTH = 500;
