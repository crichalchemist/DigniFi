import { describe, it, expect } from 'vitest';
import { assembleExplanation } from '../meansDraft';
import {
  MEANS_LINE_43_LABEL_CHANGE,
  MEANS_LINE_43_LABEL_CHOICES,
  MEANS_LINE_43_LABEL_HAPPENED,
  MEANS_LINE_43_LABEL_PAPERS,
} from '../../../constants/copy';

const answers = {
  happened: 'Demo layoff in May.',
  change: 'Demo income fell by half.',
  choices: 'Demo overtime was cut too.',
  papers: 'Demo letter from the employer.',
};

describe("the line 43 aid's draft", () => {
  it("the assembled draft holds only the filer's words and the labels", () => {
    let rest = assembleExplanation(answers);
    for (const answer of Object.values(answers)) rest = rest.replace(answer, '');
    expect(rest).toBe(
      [
        MEANS_LINE_43_LABEL_HAPPENED,
        MEANS_LINE_43_LABEL_CHANGE,
        MEANS_LINE_43_LABEL_CHOICES,
        MEANS_LINE_43_LABEL_PAPERS,
      ]
        .map((label) => `${label} `)
        .join('\n')
    );
  });

  it('a blank answer leaves out its label', () => {
    const draft = assembleExplanation({ ...answers, change: '  \n ' });
    expect(draft).not.toContain(MEANS_LINE_43_LABEL_CHANGE);
    expect(draft.split('\n')).toHaveLength(3);
  });

  it('a line break inside an answer becomes a space', () => {
    const draft = assembleExplanation({ ...answers, happened: 'First part\nsecond part' });
    expect(draft.split('\n')[0]).toBe(`${MEANS_LINE_43_LABEL_HAPPENED} First part second part`);
  });

  it('the longest aid draft stays under 2,000 characters', () => {
    const long = 'x'.repeat(450);
    const draft = assembleExplanation({
      happened: long,
      change: long,
      choices: long,
      papers: long,
    });
    expect(draft.length).toBeLessThan(2000);
  });
});
