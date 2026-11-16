/**
 * The information beside each line of the Form 122A-2 page (R6). Business intent: a filer sees what
 * they entered on Schedules I and J, labelled with where it came from, so they can compare it with
 * the form's own words; nothing is suggested, and a spouse's figure shows only for a joint filing.
 */
import { besideLine } from '../beside';
import { meansPage } from '../../../test/fixtures/meansPage';
import type { MeansInformation } from '../../../types/api';

function information(over: Partial<MeansInformation> = {}): MeansInformation {
  const base = meansPage().information as MeansInformation;
  return {
    ...base,
    schedule_i: {
      you: {
        '5a': '2300.00',
        '5b': '0.00',
        '5d': '10.00',
        '5e': '30.00',
        '5f': '0.00',
        '5g': '5.00',
      },
      spouse: { '5a': '300.00', '5e': '12.00' },
    },
    schedule_j: {
      '7': '40.00',
      '8': '1200.00',
      '9': '60.00',
      '11': '25.00',
      '14': '15.00',
      '15c': '80.00',
      '15d': '20.00',
      '16': '500.00',
      '18': '75.00',
    },
    ...over,
  };
}

describe('besideLine', () => {
  it('names the schedule and line of each figure beside line 16, the spouse after the filer', () => {
    expect(besideLine('16', information(), true)).toEqual([
      'You entered $2,300.00 on Schedule I line 5a.',
      'You entered $300.00 for your spouse on Schedule I line 5a.',
      'You entered $500.00 on Schedule J line 16.',
    ]);
  });

  it('shows the spouse only for a married couple filing together', () => {
    expect(besideLine('16', information(), false)).toEqual([
      'You entered $2,300.00 on Schedule I line 5a.',
      'You entered $500.00 on Schedule J line 16.',
    ]);
  });

  it('shows the three Schedule I deductions beside line 17 and leaves out one the filer never entered', () => {
    const info = information({
      schedule_i: { you: { '5b': '0.00', '5g': '5.00' }, spouse: null },
    });
    expect(besideLine('17', info, true)).toEqual([
      'You entered $0.00 on Schedule I line 5b.',
      'You entered $5.00 on Schedule I line 5g.',
    ]);
  });

  it('shows life insurance and health insurance figures beside lines 18 and 25', () => {
    const insurance = [
      'You entered $30.00 on Schedule I line 5e.',
      'You entered $12.00 for your spouse on Schedule I line 5e.',
      'You entered $80.00 on Schedule J line 15c.',
      'You entered $20.00 on Schedule J line 15d.',
    ];
    expect(besideLine('18', information(), true)).toEqual(insurance);
    expect(besideLine('25', information(), true)).toEqual(insurance);
  });

  it('shows Schedule J figures beside lines 19, 21, 22 and 31', () => {
    expect(besideLine('19', information(), true)).toEqual([
      'You entered $0.00 on Schedule I line 5f.',
      'You entered $75.00 on Schedule J line 18.',
    ]);
    expect(besideLine('21', information(), true)).toEqual([
      'You entered $1,200.00 on Schedule J line 8.',
    ]);
    expect(besideLine('31', information(), true)).toEqual([
      'You entered $15.00 on Schedule J line 14.',
    ]);
  });

  it('adds the line 7 total beside line 22 only when there is one, and only under Yes', () => {
    expect(besideLine('22', information({ line_7g: '310.00' }), true, 'yes')).toEqual([
      'You entered $25.00 on Schedule J line 11.',
      'Your line 7 total is $310.00.',
    ]);
    expect(besideLine('22', information({ line_7g: null }), true, 'yes')).toEqual([
      'You entered $25.00 on Schedule J line 11.',
    ]);
    for (const answer of ['no', null] as const) {
      expect(besideLine('22', information({ line_7g: '310.00' }), true, answer)).toEqual([
        'You entered $25.00 on Schedule J line 11.',
      ]);
    }
  });

  it('shows the public transportation cap beside line 15 only under Yes', () => {
    expect(besideLine('15', information(), true, 'yes')).toEqual([
      "The IRS amount for public transportation is $250.00. Line 15 can't be more than that.",
    ]);
    expect(besideLine('15', information(), true, 'no')).toEqual([]);
    expect(besideLine('15', information(), true)).toEqual([]);
  });

  it('shows the line 8 amount beside line 28 and the per-child amount beside line 29', () => {
    expect(besideLine('28', information({ line_8: '900.00' }), true)).toEqual([
      'Your line 8 amount is $900.00.',
    ]);
    expect(besideLine('28', information({ line_8: null }), true)).toEqual([]);
    expect(besideLine('29', information(), true)).toEqual([
      'The form allows up to $1,000.00 a month for each child.',
    ]);
  });

  it('shows the line 30 cap for the household, and reads 1 person for a household of one', () => {
    expect(besideLine('30', information(), true)).toEqual([
      'You entered $40.00 on Schedule J line 7.',
      'You entered $60.00 on Schedule J line 9.',
      "For 4 people, 5% of the IRS food and clothing amounts is $76.00. Line 30 can't be more than that.",
    ]);
    const one = besideLine(
      '30',
      information({ line_30_people: 1, line_30_cap: '30.00' }),
      true
    ).join(' ');
    expect(one).toContain(
      "For 1 person, 5% of the IRS food and clothing amounts is $30.00. Line 30 can't be more than that."
    );
    expect(one).not.toContain('1 people');
  });

  it('reads 2 people and the two-person cap for a household of two', () => {
    expect(
      besideLine('30', information({ line_30_people: 2, line_30_cap: '53.00' }), true)
    ).toContain(
      "For 2 people, 5% of the IRS food and clothing amounts is $53.00. Line 30 can't be more than that."
    );
  });

  it('shows nothing when the means test figures are missing', () => {
    for (const line of ['15', '16', '21', '22', '28', '29', '30'] as const) {
      expect(besideLine(line, null, true)).toEqual([]);
    }
  });

  it('shows nothing beside a line that has no source', () => {
    expect(besideLine('20', information(), true)).toEqual([]);
    expect(besideLine('23', information(), true)).toEqual([]);
  });
});
