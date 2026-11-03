import { formatIsoDate } from '../formatIsoDate';

describe('formatIsoDate', () => {
  // Built from the ISO parts, never new Date(iso), which shows the day before in Chicago (§4.4)
  it('dates read whole, with the year, from the ISO parts', () => {
    expect(formatIsoDate('2026-04-01')).toBe('April 1, 2026');
    expect(formatIsoDate('2027-02-28')).toBe('February 28, 2027');
    expect(formatIsoDate('2028-02-29')).toBe('February 29, 2028');
    expect(formatIsoDate('2026-09-30')).toBe('September 30, 2026');
  });
});
