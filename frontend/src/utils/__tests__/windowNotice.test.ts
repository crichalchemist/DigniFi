import { describe, it, expect } from 'vitest';
import { windowNotice } from '../windowNotice';

const NOW = { start: '2026-05-01', end: '2026-10-31' };

describe('windowNotice', () => {
  it('names both windows in words when the six months have moved', () => {
    expect(windowNotice({ start: '2026-04-01', end: '2026-09-30' }, NOW)).toBe(
      'Your income figures are your monthly average for April 1, 2026 through September 30, 2026. If you file now, the six months are May 1, 2026 through October 31, 2026. Check your income on the Income step.'
    );
  });

  it('asks the filer to check a window never confirmed', () => {
    expect(windowNotice(null, NOW)).toBe(
      'Check that your income figures are your monthly average for May 1, 2026 through October 31, 2026.'
    );
  });

  it('says nothing when the two windows match', () => {
    expect(windowNotice(NOW, NOW)).toBeNull();
  });

  it('writes a window across a year end with each year', () => {
    expect(
      windowNotice(
        { start: '2026-09-01', end: '2027-02-28' },
        { start: '2026-10-01', end: '2027-03-31' }
      )
    ).toMatch(
      /^Your income figures are your monthly average for September 1, 2026 through February 28, 2027\./
    );
  });
});
