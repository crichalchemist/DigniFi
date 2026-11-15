import { describe, expect, it } from 'vitest';
import {
  MEANS_OUTCOME_ABOVE,
  MEANS_OUTCOME_ANSWER_PAGE,
  MEANS_OUTCOME_ANSWER_SIDEBAR,
  MEANS_OUTCOME_BELOW,
  MEANS_OUTCOME_NO_PRESUMPTION,
  MEANS_OUTCOME_PRESUMPTION,
  MEANS_OUTCOME_REASSURANCE,
  MEANS_TABLE_MISSING,
} from '../../constants/copy';
import { PRESUMPTION_INSTRUCTIONS } from '../../constants/formText';
import { UPL_MEANS_TEST_DISCLAIMER } from '../../constants/upl';
import { meansOutcomeSentences } from '../meansOutcome';

const forHousehold = (sentence: string, n: number) => sentence.replace('{n}', String(n));

describe('meansOutcomeSentences', () => {
  it('says the filer is at or below the median, with their household size', () => {
    expect(meansOutcomeSentences('at_or_below_median', 3, null, 'dashboard')).toEqual([
      forHousehold(MEANS_OUTCOME_BELOW, 3),
    ]);
  });

  it("names the Form 122A-2 page in the sidebar's words until the questions are answered", () => {
    expect(meansOutcomeSentences('cannot_work_out', 4, null, 'sidebar')).toEqual([
      forHousehold(MEANS_OUTCOME_ABOVE, 4),
      MEANS_OUTCOME_ANSWER_SIDEBAR,
      MEANS_OUTCOME_REASSURANCE,
    ]);
  });

  it.each(['dashboard', 'page'] as const)(
    'names the Form 122A-2 page in the page sentence outside the sidebar (%s)',
    (place) => {
      expect(meansOutcomeSentences('cannot_work_out', 4, null, place)).toEqual([
        forHousehold(MEANS_OUTCOME_ABOVE, 4),
        MEANS_OUTCOME_ANSWER_PAGE,
        MEANS_OUTCOME_REASSURANCE,
      ]);
    }
  );

  it.each(['sidebar', 'dashboard', 'page'] as const)(
    'names the missing table in place of the page sentence, the reassurance still last (%s)',
    (place) => {
      expect(meansOutcomeSentences('cannot_work_out', 4, 'IRS expense standards', place)).toEqual([
        forHousehold(MEANS_OUTCOME_ABOVE, 4),
        MEANS_TABLE_MISSING,
        MEANS_OUTCOME_REASSURANCE,
      ]);
    }
  );

  it('gives the form’s arithmetic for no presumption', () => {
    expect(meansOutcomeSentences('no_presumption', 2, null, 'dashboard')).toEqual([
      MEANS_OUTCOME_NO_PRESUMPTION,
    ]);
  });

  it('gives the form’s arithmetic for a presumption and ends with the form’s own instructions', () => {
    const sentences = meansOutcomeSentences('presumption', 2, null, 'dashboard');

    expect(sentences).toEqual([MEANS_OUTCOME_PRESUMPTION, PRESUMPTION_INSTRUCTIONS]);
    expect(sentences[sentences.length - 1]).toBe(PRESUMPTION_INSTRUCTIONS);
  });

  it('says nothing for a result that was never worked out', () => {
    expect(meansOutcomeSentences(null, 4, null, 'dashboard')).toEqual([]);
    expect(meansOutcomeSentences(null, null, 'Census median income', 'dashboard')).toEqual([]);
  });

  it.each(['at_or_below_median', 'cannot_work_out'] as const)(
    'never says "a household of null" for %s with no family size',
    (outcome) => {
      expect(meansOutcomeSentences(outcome, null, null, 'dashboard')).toEqual([]);
    }
  );

  it('replaces {n} everywhere it stands', () => {
    for (const outcome of ['at_or_below_median', 'cannot_work_out'] as const) {
      expect(meansOutcomeSentences(outcome, 7, null, 'dashboard').join(' ')).not.toContain('{n}');
    }
  });

  it.each(['at_or_below_median', 'cannot_work_out', 'no_presumption', 'presumption'] as const)(
    'leaves the closing sentence to the caller (%s)',
    (outcome) => {
      for (const sentence of meansOutcomeSentences(outcome, 4, null, 'dashboard')) {
        expect(sentence).not.toContain(UPL_MEANS_TEST_DISCLAIMER);
      }
    }
  );
});
