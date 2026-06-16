/**
 * Format a phone number as the user types into US 3-3-4 form: XXX-XXX-XXXX.
 *
 * Strips non-digits, caps at 10 digits, and inserts dashes progressively so a
 * partial entry still reads cleanly ("312", "312-555", "312-555-1234"). Pasting
 * an already-formatted or +1-prefixed number normalizes to the same 10 digits.
 */
export function formatPhone(value: string): string {
  const raw = value.replace(/\D/g, '');
  // Strip a leading "1" country code so a pasted +1 number (11 digits) keeps its
  // last 10 local digits instead of silently dropping the final one.
  const local = raw.length === 11 && raw[0] === '1' ? raw.slice(1) : raw;
  const digits = local.slice(0, 10);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
  return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`;
}
