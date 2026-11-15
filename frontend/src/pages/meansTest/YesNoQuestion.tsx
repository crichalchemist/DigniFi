import type { ReactNode, Ref } from 'react';
import { REQUIRED_MARK } from '../../components/wizard/steps/assets/AssetRowFields';
import type { YesNo } from '../../types/api';

const YES_NO: YesNo[] = ['no', 'yes'];

interface YesNoQuestionProps {
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
  /** Drawn inside the fieldset, after the answer */
  children?: ReactNode;
}

/** A required Yes/No question, No then Yes, as the exemptions page asks its own */
export function YesNoQuestion({
  question,
  name,
  value,
  onChange,
  note,
  id,
  legendRef,
  children,
}: YesNoQuestionProps) {
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
      {children}
    </fieldset>
  );
}
