/**
 * The shapes step 1's number and date boxes keep as the filer types or pastes (spec §5.7: the
 * browser masks the SSN, ITIN, ZIP and date boxes). Each keeps digits only, at most as many as the
 * shape holds, and shows them with the dashes or slashes the form prints, so no stray space or
 * other character reaches the server. Nothing is added until a digit follows it, so Backspace
 * never meets a dash it can't remove.
 */

function digits(value: string, most: number): string {
  return value.replace(/\D/g, '').slice(0, most);
}

/** A ZIP code: digits only, at most nine (owner ruling Q1; a pasted "60201-1234" is "602011234") */
export function zipDigits(value: string): string {
  return digits(value, 9);
}

/** A Social Security number or ITIN as XXX-XX-XXXX */
export function nineDigitNumber(value: string): string {
  const d = digits(value, 9);
  if (d.length <= 3) return d;
  if (d.length <= 5) return `${d.slice(0, 3)}-${d.slice(3)}`;
  return `${d.slice(0, 3)}-${d.slice(3, 5)}-${d.slice(5)}`;
}

/** An EIN as XX-XXXXXXX, the 2 + 7 the form's boxes print */
export function einNumber(value: string): string {
  const d = digits(value, 9);
  return d.length <= 2 ? d : `${d.slice(0, 2)}-${d.slice(2)}`;
}

/** A date as MM/DD/YYYY, the shape the server judges (`is_mm_dd_yyyy`) */
export function mmDdYyyy(value: string): string {
  const d = digits(value, 8);
  if (d.length <= 2) return d;
  if (d.length <= 4) return `${d.slice(0, 2)}/${d.slice(2)}`;
  return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`;
}
