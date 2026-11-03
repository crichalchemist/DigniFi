const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

/**
 * "2026-04-01" as "April 1, 2026", built from the ISO string's parts. Never `new Date(iso)`:
 * that is UTC midnight, which shows the day before in Chicago.
 */
export function formatIsoDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number);
  return `${MONTHS[month - 1]} ${day}, ${year}`;
}
