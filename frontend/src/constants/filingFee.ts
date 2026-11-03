/**
 * The longest text each of the filing-fee page's boxes takes: what its box on Form 103B can
 * print (3f spec §6.4). The server measures them once, on `FilingFee.TEXT_LIMITS`, and
 * `test_filing_fee_frontend_copy.py` pins this copy to it.
 */
export const FILING_FEE_TEXT_LIMITS: Record<
  | 'income_change_explanation'
  | 'installments_explanation'
  | 'others_covered_who'
  | 'expense_change_explanation',
  number
> = {
  income_change_explanation: 520,
  installments_explanation: 520,
  others_covered_who: 420,
  expense_change_explanation: 420,
};
