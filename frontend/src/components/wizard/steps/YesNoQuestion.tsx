import { NOT_ANSWERED_YET } from '../../../constants/copy';
import type { YesNo } from '../../../types/api';

interface YesNoQuestionProps {
  legend: string;
  name: string;
  answer: boolean | null | undefined;
  unanswered: boolean;
  onAnswer: (answer: boolean) => void;
}

/** A yes/no question, nothing checked until the filer answers */
export function YesNoQuestion({ legend, name, answer, unanswered, onAnswer }: YesNoQuestionProps) {
  return (
    <fieldset className="form-field fee-waiver-question">
      <legend className="form-label">{legend}</legend>
      <label className="fee-waiver-checkbox">
        <input
          type="radio"
          name={name}
          value="yes"
          checked={answer === true}
          onChange={() => onAnswer(true)}
        />{' '}
        Yes
      </label>
      <label className="fee-waiver-checkbox">
        <input
          type="radio"
          name={name}
          value="no"
          checked={answer === false}
          onChange={() => onAnswer(false)}
        />{' '}
        No
      </label>
      {unanswered && <p className="form-help-text">{NOT_ANSWERED_YET}</p>}
    </fieldset>
  );
}

interface YesNoFieldProps {
  legend: string;
  name: string;
  answer: YesNo | null | undefined;
  onAnswer: (answer: YesNo) => void;
  required?: boolean;
}

/** The same question for answers stored as "yes" or "no", with no "Not answered yet" line */
export function YesNoField({ legend, name, answer, onAnswer, required }: YesNoFieldProps) {
  return (
    <fieldset className="form-field fee-waiver-question">
      <legend className="form-label">
        {legend}
        {required && (
          <>
            {' '}
            <span className="required-indicator" aria-label="required">
              *
            </span>
          </>
        )}
      </legend>
      <label className="fee-waiver-checkbox">
        <input
          type="radio"
          name={name}
          value="yes"
          aria-required={required || undefined}
          checked={answer === 'yes'}
          onChange={() => onAnswer('yes')}
        />{' '}
        Yes
      </label>
      <label className="fee-waiver-checkbox">
        <input
          type="radio"
          name={name}
          value="no"
          aria-required={required || undefined}
          checked={answer === 'no'}
          onChange={() => onAnswer('no')}
        />{' '}
        No
      </label>
    </fieldset>
  );
}
