/**
 * UPL check on the Assets step's sentences (3b spec §12)
 *
 * DigniFi gives legal information, never advice. A filer reading the Assets step must never be told
 * what will happen to what they own, or what a thing is worth: which value to swear to is theirs.
 * The list is PROHIBITED_PHRASES in docs/UPL_COMPLIANCE.md §4.2, plus the wording that predicts an
 * outcome or suggests a value. A new sentence on the step goes in ASSET_SENTENCES.
 */

import { describe, expect, it } from 'vitest';
import * as copy from '../constants/copy';

const ADVICE: RegExp[] = [
  /\bshould\b/i,
  /\brecommend/i,
  /\bwe suggest\b/i,
  /\byou must\b/i,
  /\badvise/i,
  /\bwill be discharged\b/i,
  /\byou will keep\b/i,
  /\byou qualify\b/i,
  /\$\s?\d/,
  // PROHIBITED_PHRASES that the words above don't already catch
  /\byou will qualify\b/i,
  /\byou will probably\b/i,
  /\byou are eligible\b/i,
  /\bthis is the best option\b/i,
  /\byou need to file\b/i,
];

const ASSET_SENTENCES = {
  NOTHING_TO_LIST_NOTE: copy.NOTHING_TO_LIST_NOTE,
  LEASE_NOTE: copy.LEASE_NOTE,
  VALUE_UNKNOWN_BUTTON: copy.VALUE_UNKNOWN_BUTTON,
  VALUE_UNKNOWN_NOTE: copy.VALUE_UNKNOWN_NOTE,
  VALUE_UNKNOWN_HEADING: copy.VALUE_UNKNOWN_HEADING,
  REMOVE_ON_LINE: copy.REMOVE_ON_LINE,
  REMOVE_UNDER_LINE: copy.REMOVE_UNDER_LINE,
  LINE_NEEDS_AN_ITEM: copy.LINE_NEEDS_AN_ITEM,
  GATE_HAS_ONLY_NOS: copy.GATE_HAS_ONLY_NOS,
  ASSET_GAP_NEEDS_AN_ANSWER: copy.ASSET_GAP_NEEDS_AN_ANSWER,
  ASSET_GAP_YES_WITH_NO_ITEM: copy.ASSET_GAP_YES_WITH_NO_ITEM,
  ASSET_GAP_NO_STILL_LISTS: copy.ASSET_GAP_NO_STILL_LISTS,
  ASSET_GAP_ROW_NEEDS_MORE: copy.ASSET_GAP_ROW_NEEDS_MORE,
  ASSET_GAP_GATE_TAKES_NO_ITEMS: copy.ASSET_GAP_GATE_TAKES_NO_ITEMS,
  ASSET_GAP_UNDER_GATE: copy.ASSET_GAP_UNDER_GATE,
  OLD_ROWS_NOTE: copy.OLD_ROWS_NOTE,
  OLD_ROW_LINE_LABEL: copy.OLD_ROW_LINE_LABEL,
  REVIEW_VALUE_NOT_KNOWN: copy.REVIEW_VALUE_NOT_KNOWN,
};

function adviceIn(sentence: string) {
  return ADVICE.filter((pattern) => pattern.test(sentence)).map(String);
}

describe('the Assets step gives information, never advice', () => {
  it.each(Object.entries(ASSET_SENTENCES))(
    '%s predicts no outcome and suggests no value',
    (_name, sentence) => {
      expect(adviceIn(sentence)).toEqual([]);
    }
  );

  // So a list that stopped matching can't pass by saying nothing
  it.each([
    'You should list this at $0.',
    'We recommend leaving it blank.',
    'We suggest a low value.',
    'You must list your car.',
    'We advise you to wait.',
    'This debt will be discharged.',
    'You will keep your home.',
    'You qualify for this exemption.',
    'Put $500 here.',
    'You are eligible for this.',
  ])('finds the advice in "%s"', (sentence) => {
    expect(adviceIn(sentence)).not.toEqual([]);
  });

  it('leaves the words that only sound like it alone', () => {
    expect(adviceIn('Put the shoulder bag on line 14.')).toEqual([]);
  });
});
