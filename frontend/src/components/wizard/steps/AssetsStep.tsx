/**
 * Assets Step - Schedule A/B, a Part at a time, in the form's words (3b spec §4)
 *
 * Trauma-informed design:
 * - Nothing starts answered, and having nothing to list is said to be no failure
 * - A value the filer doesn't know is an answer: it can be marked, and changed later
 * - No value is ever suggested, and removing what the filer typed asks first
 *
 * The wizard holds the rows, the answers and the Part, so an id a save writes into a row stays
 * there. The step holds no copies.
 */

import { useEffect } from 'react';
import { UPLDisclaimer } from '../../compliance';
import { AB_OWED_TO_YOU_HEADING, AB_PART_LEADS, AB_PART_TITLES } from '../../../constants/formText';
import { GATE_HAS_ONLY_NOS, LEASE_NOTE, NOTHING_TO_LIST_NOTE } from '../../../constants/copy';
import { UPL_EXEMPTION_DISCLAIMER } from '../../../constants/upl';
import { AB_PARTS, ASSET_LINES } from '../../../constants/assetLines';
import { AssetLine } from './assets/AssetLine';
import { gateHasOnlyNos, partIsComplete, shownLines } from './assets/assetGaps';
import type { AssetLine as Line } from '../../../constants/assetLines';
import type { AssetInfo, AssetLineAnswer, WizardRow } from '../../../types/api';

type Row = WizardRow<AssetInfo>;

interface AssetsStepProps {
  rows: Row[];
  onRowsChange: (rows: Row[]) => void;
  answers: Record<string, AssetLineAnswer>;
  onAnswersChange: (answers: Record<string, AssetLineAnswer>) => void;
  /** The Part showing, 1 to 7 */
  part: number;
  onValidationChange: (isValid: boolean) => void;
}

// A new row's key, from a count that outlives the step: the step remounts on each visit while
// unsaved rows stay in the wizard, so a count per mount could repeat a key
let lastKey = 0;

/** A row as a Yes opens it: every value unanswered, in the shape the server takes */
function newRow(key: string): Row {
  return {
    _key: `new-${++lastKey}`,
    ab_line: key,
    description: '',
    current_value: null,
    entire_value: null,
    details: {},
  };
}

function keysUnder(gate: string) {
  return new Set(ASSET_LINES.filter((line) => line.gate === gate).map((line) => line.key));
}

export function AssetsStep({
  rows,
  onRowsChange,
  answers,
  onAnswersChange,
  part,
  onValidationChange,
}: AssetsStepProps) {
  const hasOldRow = rows.some((row) => row.ab_line === null || row.ab_line === undefined);
  const isValid = !hasOldRow && partIsComplete(part, rows, answers);

  useEffect(() => {
    onValidationChange(isValid);
    // a useState setter in IntakeWizard — a stable identity
  }, [isValid, onValidationChange]);

  const lines = shownLines(answers).filter((line) => line.part === part);
  const rowsOn = (key: string) => rows.filter((row) => row.ab_line === key);

  const answerYes = (line: Line) => {
    onAnswersChange({ ...answers, [line.key]: 'yes' });
    // A gate takes no rows of its own, and a line that has rows keeps them
    if (line.shape !== 'gate' && rowsOn(line.key).length === 0) {
      onRowsChange([...rows, newRow(line.key)]);
    }
  };

  const answerNo = (line: Line) => {
    const next: Record<string, AssetLineAnswer> = { ...answers, [line.key]: 'no' };
    const removed = line.shape === 'gate' ? keysUnder(line.key) : new Set([line.key]);
    // A gate's No hides its lines: a later Yes on the gate shows them unanswered
    if (line.shape === 'gate') for (const key of removed) delete next[key];
    onAnswersChange(next);
    const kept = rows.filter((row) => !removed.has(row.ab_line ?? ''));
    if (kept.length !== rows.length) onRowsChange(kept);
  };

  const removedByNo = (line: Line) => {
    if (line.shape !== 'gate') return rowsOn(line.key).length;
    const under = keysUnder(line.key);
    return rows.filter((row) => under.has(row.ab_line ?? '')).length;
  };

  return (
    <div className="assets-step">
      {part === 1 && (
        <div className="info-box">
          <p className="info-message">{NOTHING_TO_LIST_NOTE}</p>
        </div>
      )}

      <p className="form-help-text">
        Part {part} of {AB_PARTS.length}
      </p>
      <h3 className="section-title">{AB_PART_TITLES[part]}</h3>
      {AB_PART_LEADS[part] && <p className="section-description">{AB_PART_LEADS[part]}</p>}
      {part === 2 && <p className="section-description">{LEASE_NOTE}</p>}

      {lines.map((line) => (
        <div key={line.key}>
          {line.key === '28' && <p className="ab-subheading">{AB_OWED_TO_YOU_HEADING}</p>}
          <AssetLine
            line={line}
            answer={answers[line.key]}
            rows={rowsOn(line.key)}
            removedByNo={removedByNo(line)}
            onYes={() => answerYes(line)}
            onNo={() => answerNo(line)}
            onAddRow={() => onRowsChange([...rows, newRow(line.key)])}
            onRowChange={(changed) =>
              onRowsChange(rows.map((row) => (row._key === changed._key ? changed : row)))
            }
            onRemoveRow={(removed) => onRowsChange(rows.filter((row) => row._key !== removed._key))}
          />
        </div>
      ))}

      {/* After the lines, not at the gate: the last No is pressed down here, beside Continue */}
      {lines
        .filter((line) => line.shape === 'gate' && gateHasOnlyNos(line, answers))
        .map((gate) => (
          <div key={gate.key} className="info-box" role="alert">
            <p className="info-message">{GATE_HAS_ONLY_NOS.replace('{key}', gate.key)}</p>
          </div>
        ))}

      <UPLDisclaimer text={UPL_EXEMPTION_DISCLAIMER} variant="inline" />
    </div>
  );
}

export default AssetsStep;
