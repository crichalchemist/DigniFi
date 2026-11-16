import { MONTHS } from './formatIsoDate';

/**
 * "2026-10-16" as "October 2026", built from the ISO string's parts (never `new Date(iso)`, which
 * is UTC midnight and shows the day before in Chicago).
 */
export function formatMonthYear(iso: string): string {
  const [year, month] = iso.split('-').map(Number);
  return `${MONTHS[month - 1]} ${year}`;
}
