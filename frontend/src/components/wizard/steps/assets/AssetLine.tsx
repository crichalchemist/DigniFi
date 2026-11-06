/**
 * One line of Schedule A/B: its words and examples, a No and a Yes that start unselected, and the
 * rows a Yes opens. A No that would remove rows asks in the page first.
 */

import { useState } from 'react';
import { Button } from '../../../common';
import { AssetRowFields } from './AssetRowFields';
import {
  ADD_AN_ITEM,
  ADD_ANOTHER_ITEM,
  KEEP_THEM,
  LINE_NEEDS_AN_ITEM,
  REMOVE_THEM,
  REMOVE_UNDER_LINE,
  REMOVE_ON_LINE,
} from '../../../../constants/copy';
import { AB_LINE_WORDS, AB_NO, AB_YES } from '../../../../constants/formText';
import type { AssetLine as Line } from '../../../../constants/assetLines';
import type { AssetInfo, AssetLineAnswer, WizardRow } from '../../../../types/api';

type Row = WizardRow<AssetInfo>;

interface AssetLineProps {
  line: Line;
  answer: AssetLineAnswer | undefined;
  /** The rows on this line, in the wizard's order */
  rows: Row[];
  /** How many rows a No would remove: this line's, or for a gate those on the lines under it */
  removedByNo: number;
  onYes: () => void;
  /** Answers No and removes the rows it counted */
  onNo: () => void;
  onAddRow: () => void;
  onRowChange: (row: Row) => void;
  onRemoveRow: (row: Row) => void;
  onPartialBox: (change: 1 | -1) => void;
}

export function AssetLine({
  line,
  answer,
  rows,
  removedByNo,
  onYes,
  onNo,
  onAddRow,
  onRowChange,
  onRemoveRow,
  onPartialBox,
}: AssetLineProps) {
  const [asking, setAsking] = useState(false);
  const { key, shape } = line;
  const words = AB_LINE_WORDS[key];
  const isGate = shape === 'gate';
  // Line 16 takes one row (3b spec §5). Every other line's rows past its slots go on a sheet.
  const offersAnother = shape !== 'cash' && rows.length > 0;
  const showsAdd = !isGate && answer === 'yes' && (rows.length === 0 || offersAnother);

  // The ask ends once there is nothing left for it to remove, so a later row doesn't bring it back
  if (asking && removedByNo === 0) setAsking(false);

  const pressNo = () => {
    if (removedByNo > 0) {
      setAsking(true);
      return;
    }
    onNo();
  };

  const question = (isGate ? REMOVE_UNDER_LINE : REMOVE_ON_LINE).replace(
    '{n}',
    String(removedByNo)
  );

  return (
    <div className="ab-line">
      <fieldset className="form-field fee-waiver-question">
        <legend className="ab-line-words">
          {key}. {words.words}
        </legend>
        {words.examples && <p className="form-help-text">{words.examples}</p>}
        <div className="ab-yes-no">
          <label className="ab-choice ab-answer">
            <input
              type="radio"
              name={`line_${key}_answer`}
              value="no"
              checked={answer === 'no'}
              onChange={pressNo}
            />
            {words.no ?? AB_NO}
          </label>
          <label className="ab-choice ab-answer">
            <input
              type="radio"
              name={`line_${key}_answer`}
              value="yes"
              checked={answer === 'yes'}
              onChange={() => {
                setAsking(false);
                onYes();
              }}
            />
            {words.yes ?? AB_YES}
          </label>
        </div>
      </fieldset>

      {asking && (
        <div className="info-box ab-ask" role="alert">
          <p className="info-message">{question}</p>
          <div className="ab-ask-buttons">
            <Button
              variant="secondary"
              onClick={() => {
                setAsking(false);
                onNo();
              }}
            >
              {REMOVE_THEM}
            </Button>
            <Button variant="outline" onClick={() => setAsking(false)}>
              {KEEP_THEM}
            </Button>
          </div>
        </div>
      )}

      {/* Shown whatever the answer, so a row the answer disagrees with can still be seen */}
      {rows.map((row, rowIndex) => (
        // Keyed by the row's own key, so each answer stays with its row when one is removed
        <AssetRowFields
          key={row._key}
          line={line}
          row={row}
          rowIndex={rowIndex}
          onRowChange={onRowChange}
          onRemove={() => onRemoveRow(row)}
          onPartialBox={onPartialBox}
        />
      ))}

      {!isGate && answer === 'yes' && rows.length === 0 && (
        <p className="form-help-text">{LINE_NEEDS_AN_ITEM}</p>
      )}

      {showsAdd && (
        <div className="add-asset-section">
          <Button variant="outline" onClick={onAddRow}>
            {rows.length === 0 ? ADD_AN_ITEM : ADD_ANOTHER_ITEM}
          </Button>
        </div>
      )}
    </div>
  );
}

export default AssetLine;
