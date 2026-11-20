import type { ReactNode, Ref } from 'react';
import { NOT_ANSWERED_YET } from '../../constants/copy';
import type { YesNo } from '../../types/api';
import { REQUIRED_MARK } from './steps/assets/AssetRowFields';

const YES_NO: YesNo[] = ['no', 'yes'];

interface YesNoThenDetailsProps {
  question: string;
  name: string;
  /** Nothing is checked while this is null */
  value: YesNo | null;
  onChange: (next: YesNo) => void;
  note?: string;
  /** Goes on the fieldset, so a link can name it */
  id?: string;
  /** With a ref, the legend takes focus (tabIndex -1) so the page can move it there */
  legendRef?: Ref<HTMLLegendElement>;
  /** Says "Not answered yet" under the radios, for a caller that has seen the filer skip it */
  unanswered?: boolean;
  /** The details: drawn inside the fieldset, under the answer */
  children?: ReactNode;
}

/**
 * A required Yes/No question, No then Yes, with its details under the answer: the filer answers
 * the yes/no before Continue, the details may wait and print blank.
 */
export function YesNoThenDetails({
  question,
  name,
  value,
  onChange,
  note,
  id,
  legendRef,
  unanswered,
  children,
}: YesNoThenDetailsProps) {
  return (
    <fieldset id={id} className="form-field fee-waiver-question">
      <legend
        className="form-label"
        ref={legendRef}
        tabIndex={legendRef === undefined ? undefined : -1}
      >
        {question}
        {REQUIRED_MARK}
      </legend>
      {note && <p className="form-help-text">{note}</p>}
      <div className="ab-yes-no">
        {YES_NO.map((choice) => (
          <label key={choice} className="ab-choice ab-answer">
            <input
              type="radio"
              name={name}
              value={choice}
              aria-required
              checked={value === choice}
              onChange={() => onChange(choice)}
            />
            {choice === 'yes' ? 'Yes' : 'No'}
          </label>
        ))}
      </div>
      {unanswered && <p className="form-help-text">{NOT_ANSWERED_YET}</p>}
      {children}
    </fieldset>
  );
}
