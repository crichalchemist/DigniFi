// The sentences shown beside a line of Form 122A-2's page (R6): what the filer entered on Schedules
// I and J, labelled with where it came from. Information only: never compared with the answer.
import {
  MEANS_BESIDE_SPOUSE,
  MEANS_BESIDE_YOU,
  MEANS_LINE_15_CAP,
  MEANS_LINE_29_NOTE,
  MEANS_LINE_30_CAP,
  MEANS_LINE_30_CAP_ONE,
  MEANS_LINE_7G,
  MEANS_LINE_8,
} from '../../constants/copy';
import type { MeansAskedLine } from '../../constants/formText';
import type { MeansInformation, YesNo } from '../../types/api';
import { dollars } from './money';

// Each line's Schedule I and Schedule J line labels, in the order the sentences are shown
const SCHEDULE_I: Partial<Record<MeansAskedLine, string[]>> = {
  '16': ['5a'],
  '17': ['5b', '5d', '5g'],
  '18': ['5e'],
  '19': ['5f'],
  '25': ['5e'],
};

const SCHEDULE_J: Partial<Record<MeansAskedLine, string[]>> = {
  '16': ['16'],
  '18': ['15c', '15d'],
  '19': ['18'],
  '21': ['8'],
  '22': ['11'],
  '25': ['15c', '15d'],
  '30': ['7', '9'],
  '31': ['14'],
};

// split/join, not replace: replace reads $& in a figure as a pattern
const fill = (sentence: string, values: Record<string, string | number>) =>
  Object.entries(values).reduce(
    (text, [key, value]) => text.split(`{${key}}`).join(String(value)),
    sentence
  );

/**
 * The sentences beside `line`. Line 15's IRS amount and line 22's line 7 total go with the amount
 * the form asks under Yes (spec 8.2 items 4 and 6), so they show only while `answer` is Yes.
 */
export function besideLine(
  line: MeansAskedLine,
  information: MeansInformation | null,
  marriedTogether: boolean,
  answer: YesNo | null = null
): string[] {
  if (information === null) return [];
  const sentences: string[] = [];
  const spouse = marriedTogether ? information.schedule_i.spouse : null;
  for (const label of SCHEDULE_I[line] ?? []) {
    const you = information.schedule_i.you[label];
    if (you !== undefined) {
      sentences.push(fill(MEANS_BESIDE_YOU, { amount: dollars(you), form: 'I', line: label }));
    }
    const theirs = spouse?.[label];
    if (theirs !== undefined) {
      sentences.push(
        fill(MEANS_BESIDE_SPOUSE, { amount: dollars(theirs), form: 'I', line: label })
      );
    }
  }
  for (const label of SCHEDULE_J[line] ?? []) {
    const amount = information.schedule_j[label];
    if (amount !== undefined) {
      sentences.push(fill(MEANS_BESIDE_YOU, { amount: dollars(amount), form: 'J', line: label }));
    }
  }
  if (line === '22' && answer === 'yes' && information.line_7g !== null) {
    sentences.push(fill(MEANS_LINE_7G, { amount: dollars(information.line_7g) }));
  }
  if (line === '15' && answer === 'yes') {
    sentences.push(fill(MEANS_LINE_15_CAP, { amount: dollars(information.line_15_cap) }));
  }
  if (line === '28' && information.line_8 !== null) {
    sentences.push(fill(MEANS_LINE_8, { amount: dollars(information.line_8) }));
  }
  if (line === '29') {
    sentences.push(fill(MEANS_LINE_29_NOTE, { amount: dollars(information.line_29_per_child) }));
  }
  if (line === '30' && information.line_30_cap !== null && information.line_30_people !== null) {
    const people = information.line_30_people;
    const cap = dollars(information.line_30_cap);
    sentences.push(
      people === 1
        ? fill(MEANS_LINE_30_CAP_ONE, { amount: cap })
        : fill(MEANS_LINE_30_CAP, { amount: cap, n: people })
    );
  }
  return sentences;
}
