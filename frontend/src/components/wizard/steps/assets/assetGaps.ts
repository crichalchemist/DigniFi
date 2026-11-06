/**
 * What the Assets step still lacks, for its Continue button. A copy of asset_step_gaps in the
 * backend's apps/intake/asset_lines.py, line for line, so Continue and Complete agree.
 */

import { AB_PARTS, ASSET_LINES } from '../../../../constants/assetLines';
import type { AssetLine } from '../../../../constants/assetLines';
import type { AssetInfo, AssetLineAnswer, WizardRow } from '../../../../types/api';

type Row = WizardRow<AssetInfo>;
type Answers = Record<string, AssetLineAnswer>;

/** Every line, less those whose gate isn't answered Yes */
export function shownLines(answers: Answers): AssetLine[] {
  return ASSET_LINES.filter((line) => line.gate === null || answers[line.gate] === 'yes');
}

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

function lineIsComplete(line: AssetLine, rows: Row[], answers: Answers) {
  const onLine = rows.filter((row) => row.ab_line === line.key);
  const shown = line.gate === null || answers[line.gate] === 'yes';
  if (!shown) return onLine.length === 0;
  const answer = answers[line.key];
  if (answer !== 'yes' && answer !== 'no') return false;
  if (line.shape === 'gate') {
    if (onLine.length > 0) return false;
    const under = ASSET_LINES.filter((other) => other.gate === line.key);
    return answer !== 'yes' || !under.every((other) => answers[other.key] === 'no');
  }
  if (answer === 'no') return onLine.length === 0;
  return onLine.length > 0 && onLine.every((row) => rowIsComplete(line, row));
}

/** Whether every line of the Part is answered and every row has what its line requires */
export function partIsComplete(part: number, rows: Row[], answers: Answers): boolean {
  return ASSET_LINES.filter((line) => line.part === part).every((line) =>
    lineIsComplete(line, rows, answers)
  );
}

/** The first Part with something left, or Part 1 when nothing is: where the step opens */
export function firstIncompletePart(rows: Row[], answers: Answers): number {
  return AB_PARTS.find((part) => !partIsComplete(part, rows, answers)) ?? 1;
}
