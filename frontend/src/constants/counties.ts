/**
 * The Northern District of Illinois's 18 counties (28 U.S.C. § 93(a)), as the server stores
 * them; `test_household_frontend_copy.py` pins this list.
 */
export const ILND_COUNTIES = [
  'Cook',
  'DuPage',
  'Grundy',
  'Kane',
  'Kendall',
  'Lake',
  'LaSalle',
  'Will',
  'Boone',
  'Carroll',
  'DeKalb',
  'Jo Daviess',
  'Lee',
  'McHenry',
  'Ogle',
  'Stephenson',
  'Whiteside',
  'Winnebago',
] as const;

/**
 * Each county's division (28 U.S.C. § 93(a)), which names the clerk's office in the public-record
 * notice and the division beside line 6 (4b-R6); `test_household_frontend_copy.py` pins it.
 */
export const COUNTY_DIVISION: Record<(typeof ILND_COUNTIES)[number], 'Eastern' | 'Western'> = {
  Cook: 'Eastern',
  DuPage: 'Eastern',
  Grundy: 'Eastern',
  Kane: 'Eastern',
  Kendall: 'Eastern',
  Lake: 'Eastern',
  LaSalle: 'Eastern',
  Will: 'Eastern',
  Boone: 'Western',
  Carroll: 'Western',
  DeKalb: 'Western',
  'Jo Daviess': 'Western',
  Lee: 'Western',
  McHenry: 'Western',
  Ogle: 'Western',
  Stephenson: 'Western',
  Whiteside: 'Western',
  Winnebago: 'Western',
};

/** A stored county's division; null before one is chosen, or for a spelling not on the list */
export function divisionOf(county: string | null): 'Eastern' | 'Western' | null {
  return county !== null && Object.hasOwn(COUNTY_DIVISION, county)
    ? COUNTY_DIVISION[county as keyof typeof COUNTY_DIVISION]
    : null;
}
