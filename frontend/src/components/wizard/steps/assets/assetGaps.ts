/**
 * What the Assets step still lacks, for its Continue button and the sentence that says why it
 * waits. A copy of asset_step_gaps in the backend's apps/intake/asset_lines.py, line for line and
 * in its words (test_asset_gaps.py pins them), so Continue and Complete agree.
 */

import { AB_PARTS, ASSET_LINES } from '../../../../constants/assetLines';
import {
  ASSET_GAP_GATE_TAKES_NO_ITEMS,
  ASSET_GAP_NEEDS_AN_ANSWER,
  ASSET_GAP_NO_STILL_LISTS,
  ASSET_GAP_ROW_NEEDS_MORE,
  ASSET_GAP_UNDER_GATE,
  ASSET_GAP_YES_WITH_NO_ITEM,
  GATE_HAS_ONLY_NOS,
  ROW_WITH_NO_NAME,
} from '../../../../constants/copy';
import type { AssetLine } from '../../../../constants/assetLines';
import type { AssetInfo, AssetLineAnswer, WizardRow } from '../../../../types/api';

type Row = WizardRow<AssetInfo>;
type Answers = Record<string, AssetLineAnswer>;

/** Every line, less those whose gate isn't answered Yes */
export function shownLines(answers: Answers): AssetLine[] {
  return ASSET_LINES.filter((line) => line.gate === null || answers[line.gate] === 'yes');
}

// The shapes whose row shows no description box. Line 43's box shows under its Yes.
export const NO_TEXT_BOX: ReadonlySet<AssetLine['shape']> = new Set([
  'place',
  'vehicle',
  'vehicle_no_mileage',
  'cash',
]);

function blank(text: string | null | undefined) {
  return (text ?? '').trim() === '';
}

/** A value counts as given with a figure (a $0 included) or its "I don't know" flag */
function valueGiven(figure: number | null | undefined, flag: boolean | null | undefined) {
  return figure !== null && figure !== undefined ? true : Boolean(flag);
}

function rowIsComplete(line: AssetLine, row: Row) {
  const details = row.details ?? {};
  const hasText = !blank(row.description);
  const hasValue = valueGiven(row.current_value, details.value_unknown);
  const { shape } = line;
  if (shape === 'cash') return hasValue;
  if (shape === 'place' || shape === 'vehicle' || shape === 'vehicle_no_mileage') {
    if (!hasValue || !valueGiven(row.entire_value, details.entire_unknown)) return false;
    if (!details.who) return false;
    if (shape === 'place') {
      const kinds = details.property_kinds ?? [];
      return (
        !blank(details.street) &&
        kinds.length > 0 &&
        (!kinds.includes('other') || !blank(details.other_kind))
      );
    }
    return !blank(details.make);
  }
  if (shape === 'item_question') {
    const answer = details.has_personal_info;
    return answer !== null && answer !== undefined && (answer === false || hasText) && hasValue;
  }
  if (line.kinds.length > 0 && !details.kind) return false;
  if (shape === 'named_share' && (details.percent === null || details.percent === undefined)) {
    return false;
  }
  return hasText && hasValue;
}

/** A gate answered Yes with every line under it No, which Continue and Complete both refuse */
function gateHasOnlyNos(gate: AssetLine, answers: Answers) {
  if (answers[gate.key] !== 'yes') return false;
  const under = ASSET_LINES.filter((other) => other.gate === gate.key);
  return under.every((other) => answers[other.key] === 'no');
}

/** What the filer knows a row by, in the order Review names it */
export function rowName(row: Row) {
  return (
    row.description?.trim() ||
    row.details?.street?.trim() ||
    row.details?.make?.trim() ||
    ROW_WITH_NO_NAME
  );
}

// One pass with a function, so the filer's words are never read as a pattern or a placeholder
export function fill(template: string, values: Record<string, string>) {
  return template.replace(/\{(\w+)\}/g, (_, name: string) => values[name]);
}

/** The first thing a line still lacks, in Complete's words, or null */
function lineGap(line: AssetLine, rows: Row[], answers: Answers): string | null {
  const { key, gate } = line;
  const onLine = rows.filter((row) => row.ab_line === key);
  if (gate !== null && answers[gate] !== 'yes') {
    return onLine.length > 0 ? fill(ASSET_GAP_UNDER_GATE, { key, gate }) : null;
  }
  const answer = answers[key];
  if (answer !== 'yes' && answer !== 'no') return fill(ASSET_GAP_NEEDS_AN_ANSWER, { key });
  if (line.shape === 'gate') {
    if (onLine.length > 0) return fill(ASSET_GAP_GATE_TAKES_NO_ITEMS, { key });
    return gateHasOnlyNos(line, answers) ? fill(GATE_HAS_ONLY_NOS, { key }) : null;
  }
  if (answer === 'no') {
    return onLine.length > 0 ? fill(ASSET_GAP_NO_STILL_LISTS, { key }) : null;
  }
  if (onLine.length === 0) return fill(ASSET_GAP_YES_WITH_NO_ITEM, { key });
  const lacking = onLine.find((row) => !rowIsComplete(line, row));
  return lacking ? fill(ASSET_GAP_ROW_NEEDS_MORE, { key, name: rowName(lacking) }) : null;
}

/** The first thing the Part still lacks, in the form's order, or null when it lacks nothing */
export function firstGapOnPart(part: number, rows: Row[], answers: Answers): string | null {
  for (const line of ASSET_LINES) {
    if (line.part !== part) continue;
    const gap = lineGap(line, rows, answers);
    if (gap !== null) return gap;
  }
  return null;
}

/** Whether every line of the Part is answered and every row has what its line requires */
export function partIsComplete(part: number, rows: Row[], answers: Answers): boolean {
  return firstGapOnPart(part, rows, answers) === null;
}

/**
 * The first Part with something left, or Part 1 when nothing is: where the step opens. An old row
 * comes first, as in asset_step_gaps: it holds every Part back, and only Part 1 lists it (§9).
 */
export function firstIncompletePart(rows: Row[], answers: Answers): number {
  if (rows.some((row) => row.ab_line === null || row.ab_line === undefined)) return 1;
  return AB_PARTS.find((part) => !partIsComplete(part, rows, answers)) ?? 1;
}
