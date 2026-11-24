import { describe, expect, it } from 'vitest';
import {
  MEANS_OUTCOME_ABOVE,
  MEANS_OUTCOME_ANSWER_DEBTS,
  MEANS_OUTCOME_ANSWER_PAGE,
  MEANS_OUTCOME_ANSWER_SIDEBAR,
  MEANS_OUTCOME_BELOW,
  MEANS_OUTCOME_MILITARY,
  MEANS_OUTCOME_NOT_CONSUMER,
  MEANS_OUTCOME_NO_PRESUMPTION,
  MEANS_OUTCOME_PRESUMPTION,
  MEANS_OUTCOME_REASSURANCE,
  MEANS_OUTCOME_VETERAN,
  MEANS_TABLE_MISSING,
} from '../../constants/copy';
import { FORM_122A1SUPP_AMENDED, PRESUMPTION_INSTRUCTIONS } from '../../constants/formText';
import { UPL_MEANS_TEST_DISCLAIMER } from '../../constants/upl';
import { meansOutcomeSentences } from '../meansOutcome';

const forHousehold = (sentence: string, n: number) => sentence.replace('{n}', String(n));

describe('meansOutcomeSentences', () => {
  it('says the filer is at or below the median, with their household size', () => {
    expect(meansOutcomeSentences('at_or_below_median', 3, null, null, 'dashboard')).toEqual([
      forHousehold(MEANS_OUTCOME_BELOW, 3),
    ]);
  });

  it("names the Form 122A-2 page in the sidebar's words until the questions are answered", () => {
    expect(meansOutcomeSentences('cannot_work_out', 4, null, null, 'sidebar')).toEqual([
      forHousehold(MEANS_OUTCOME_ABOVE, 4),
      MEANS_OUTCOME_ANSWER_SIDEBAR,
      MEANS_OUTCOME_REASSURANCE,
    ]);
  });

  it.each(['dashboard', 'page'] as const)(
    'names the Form 122A-2 page in the page sentence outside the sidebar (%s)',
    (place) => {
      expect(meansOutcomeSentences('cannot_work_out', 4, null, null, place)).toEqual([
        forHousehold(MEANS_OUTCOME_ABOVE, 4),
        MEANS_OUTCOME_ANSWER_PAGE,
        MEANS_OUTCOME_REASSURANCE,
      ]);
    }
  );

  it.each(['sidebar', 'dashboard', 'page'] as const)(
    'names the missing table in place of the page sentence, the reassurance still last (%s)',
    (place) => {
      expect(
        meansOutcomeSentences('cannot_work_out', 4, 'IRS expense standards', null, place)
      ).toEqual([
        forHousehold(MEANS_OUTCOME_ABOVE, 4),
        MEANS_TABLE_MISSING,
        MEANS_OUTCOME_REASSURANCE,
      ]);
    }
  );

  // 4d-R27: above the median, an open answer on Amounts Owed holds the result, and the page and the
  // dashboard name that step; the sidebar keeps O4's words (4d-R14, B34)
  it.each(['dashboard', 'page'] as const)(
    'names the Amounts Owed step while the result waits on it (%s)',
    (place) => {
      expect(meansOutcomeSentences('cannot_work_out', 4, null, 'debts', place)).toEqual([
        forHousehold(MEANS_OUTCOME_ABOVE, 4),
        MEANS_OUTCOME_ANSWER_DEBTS,
        MEANS_OUTCOME_REASSURANCE,
      ]);
    }
  );

  it('keeps the Form 122A-2 page sentence in the sidebar while the result waits on Amounts Owed', () => {
    expect(meansOutcomeSentences('cannot_work_out', 4, null, 'debts', 'sidebar')).toEqual([
      forHousehold(MEANS_OUTCOME_ABOVE, 4),
      MEANS_OUTCOME_ANSWER_SIDEBAR,
      MEANS_OUTCOME_REASSURANCE,
    ]);
  });

  it.each(['sidebar', 'dashboard', 'page'] as const)(
    'names a missing table even while an Amounts Owed answer is open (%s)',
    (place) => {
      expect(
        meansOutcomeSentences('cannot_work_out', 4, 'IRS expense standards', 'debts', place)
      ).toEqual([
        forHousehold(MEANS_OUTCOME_ABOVE, 4),
        MEANS_TABLE_MISSING,
        MEANS_OUTCOME_REASSURANCE,
      ]);
    }
  );

  // D1: the three routes Form 122A-1Supp gives, in the form's words, wherever they show
  it.each(['sidebar', 'dashboard', 'page'] as const)(
    'says a not-consumer filer checks box 1 and files the Supp (%s)',
    (place) => {
      expect(meansOutcomeSentences('not_consumer', 4, null, null, place)).toEqual([
        MEANS_OUTCOME_NOT_CONSUMER,
      ]);
    }
  );

  it.each(['sidebar', 'dashboard', 'page'] as const)(
    'says a disabled veteran with debts from active duty checks box 1 (%s)',
    (place) => {
      expect(meansOutcomeSentences('veteran_exemption', 4, null, null, place)).toEqual([
        MEANS_OUTCOME_VETERAN,
      ]);
    }
  );

  it.each(['sidebar', 'dashboard', 'page'] as const)(
    'says a service category checks box 3, then the form’s amended-form sentence (%s)',
    (place) => {
      expect(meansOutcomeSentences('military_exclusion', 4, null, null, place)).toEqual([
        MEANS_OUTCOME_MILITARY,
        FORM_122A1SUPP_AMENDED,
      ]);
    }
  );

  it.each(['not_consumer', 'veteran_exemption', 'military_exclusion'] as const)(
    'needs no household size for %s',
    (outcome) => {
      expect(meansOutcomeSentences(outcome, null, null, null, 'dashboard')).not.toEqual([]);
    }
  );

  it('gives the form’s arithmetic for no presumption', () => {
    expect(meansOutcomeSentences('no_presumption', 2, null, null, 'dashboard')).toEqual([
      MEANS_OUTCOME_NO_PRESUMPTION,
    ]);
  });

  it('gives the form’s arithmetic for a presumption and ends with the form’s own instructions', () => {
    const sentences = meansOutcomeSentences('presumption', 2, null, null, 'dashboard');

    expect(sentences).toEqual([MEANS_OUTCOME_PRESUMPTION, PRESUMPTION_INSTRUCTIONS]);
    expect(sentences[sentences.length - 1]).toBe(PRESUMPTION_INSTRUCTIONS);
  });

  it('says nothing for a result that was never worked out', () => {
    expect(meansOutcomeSentences(null, 4, null, null, 'dashboard')).toEqual([]);
    expect(meansOutcomeSentences(null, null, 'Census median income', null, 'dashboard')).toEqual(
      []
    );
  });

  it.each(['at_or_below_median', 'cannot_work_out'] as const)(
    'never says "a household of null" for %s with no family size',
    (outcome) => {
      expect(meansOutcomeSentences(outcome, null, null, null, 'dashboard')).toEqual([]);
    }
  );

  it('replaces {n} everywhere it stands', () => {
    for (const outcome of ['at_or_below_median', 'cannot_work_out'] as const) {
      expect(meansOutcomeSentences(outcome, 7, null, null, 'dashboard').join(' ')).not.toContain(
        '{n}'
      );
    }
  });

  it.each([
    'at_or_below_median',
    'cannot_work_out',
    'no_presumption',
    'presumption',
    'not_consumer',
    'veteran_exemption',
    'military_exclusion',
  ] as const)('leaves the closing sentence to the caller (%s)', (outcome) => {
    for (const sentence of meansOutcomeSentences(outcome, 4, null, null, 'dashboard')) {
      expect(sentence).not.toContain(UPL_MEANS_TEST_DISCLAIMER);
    }
  });
});
