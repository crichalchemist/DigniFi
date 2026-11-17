import type { Ref } from 'react';
import { Button, FormTextarea } from '../../components/common';
import {
  FORM_122A2_LINE_43,
  FORM_122A2_LINE_43_AMOUNT,
  FORM_122A2_LINE_43_EXPLANATION,
  FORM_122A2_LINE_43_INSTRUCTIONS,
} from '../../constants/formText';
import {
  MEANS_LINE_43_ADD,
  MEANS_LINE_43_ASSEMBLE,
  MEANS_LINE_43_ASSEMBLE_NOTE,
  MEANS_LINE_43_BOX_NOTE,
  MEANS_LINE_43_CHANGE,
  MEANS_LINE_43_CHOICES,
  MEANS_LINE_43_EXAMPLES,
  MEANS_LINE_43_HAPPENED,
  MEANS_LINE_43_HAPPENED_HINT,
  MEANS_LINE_43_LAWYER,
  MEANS_LINE_43_LEGEND,
  MEANS_LINE_43_NO_SUGGESTION,
  MEANS_LINE_43_OWN_WORDS,
  MEANS_LINE_43_PAPERS,
  MEANS_LINE_43_REMOVE,
  MEANS_LINE_43_SKIPPED,
} from '../../constants/copy';
import type { MeansOutcome } from '../../types/api';
import { AmountBox } from './AmountBox';
import { assembleExplanation } from './meansDraft';
import { cents } from './money';
import { rebuttalSentences } from './meansRebuttal';
import { explanationKey, type KeyedCircumstance, type PageAnswers } from './pageState';
import { YesNoQuestion } from './YesNoQuestion';

/** The server refuses a list of more than 10 circumstances (MAX_ROWS in apps/intake/means_test.py) */
const MAX_CIRCUMSTANCES = 10;
interface Line43Props {
  answers: PageAnswers;
  /** The page's updater: `change` gets the latest answers */
  onChange: (change: (answers: PageAnswers) => PageAnswers) => void;
  outcome: MeansOutcome | null;
  line39c: string | null;
  /** True while nothing above line 43 differs from what the server last read or saved */
  savedAbove: boolean;
  /** Sentences about a box the server refused, by `circumstance:<_key>:explanation` */
  refusals: Record<string, string>;
  clearRefusal: (key: string) => void;
  /** The page's one counter: a new circumstance's `_key` */
  nextKey: () => string;
  legendRef: Ref<HTMLLegendElement>;
}

// split/join, not replace: replace reads $& in a figure as a pattern
const number = (sentence: string, n: number) => sentence.split('{n}').join(String(n));

/**
 * Line 43: the special circumstances. The filer's own words, with a draft they may ask for and
 * edit; nothing is chosen or written for them. The statute's arithmetic is shown beside the
 * circumstances only while it is true of what was saved.
 */
export function Line43({
  answers,
  onChange,
  outcome,
  line39c,
  savedAbove,
  refusals,
  clearRefusal,
  nextKey,
  legendRef,
}: Line43Props) {
  const rows = answers.line_43_circumstances;
  const change = (key: string, edit: Partial<KeyedCircumstance>) =>
    onChange((current) => ({
      ...current,
      line_43_circumstances: current.line_43_circumstances.map((row) =>
        row._key === key ? { ...row, ...edit } : row
      ),
    }));
  const add = () => {
    const key = nextKey();
    onChange((current) => ({
      ...current,
      line_43_circumstances: [
        ...current.line_43_circumstances,
        {
          _key: key,
          happened: '',
          change: '',
          choices: '',
          papers: '',
          amount: null,
          explanation: null,
        },
      ],
    }));
  };
  const remove = (key: string) =>
    onChange((current) => ({
      ...current,
      line_43_circumstances: current.line_43_circumstances.filter((row) => row._key !== key),
    }));
  // Only while the box is empty (once trimmed), and read from the latest state
  const assemble = (key: string) =>
    onChange((current) => ({
      ...current,
      line_43_circumstances: current.line_43_circumstances.map((row) =>
        row._key === key && (row.explanation ?? '').trim() === ''
          ? { ...row, explanation: assembleExplanation(row) }
          : row
      ),
    }));

  const amounts = rows.flatMap((row) => (row.amount === null ? [] : [row.amount]));
  const showFigure =
    outcome === 'presumption' &&
    answers.line_43_answer === 'yes' &&
    savedAbove &&
    amounts.some((amount) => cents(amount) > 0n);

  const text = (
    key: 'happened' | 'change' | 'choices' | 'papers',
    row: KeyedCircumstance,
    index: number,
    label: string,
    helpText?: string
  ) => (
    <FormTextarea
      label={label}
      name={`means_line_43_${index}_${key}`}
      value={row[key]}
      maxLength={450}
      helpText={helpText}
      onChange={(event) => change(row._key, { [key]: event.target.value })}
    />
  );

  return (
    <YesNoQuestion
      id="line-43"
      legendRef={legendRef}
      question={FORM_122A2_LINE_43}
      name="means_line_43"
      value={answers.line_43_answer}
      onChange={(next) => onChange((current) => ({ ...current, line_43_answer: next }))}
    >
      {outcome === 'no_presumption' && <p className="form-help-text">{MEANS_LINE_43_SKIPPED}</p>}
      {answers.line_43_answer === 'yes' && (
        <>
          <p className="form-help-text">{FORM_122A2_LINE_43_INSTRUCTIONS}</p>
          <p className="form-help-text">{MEANS_LINE_43_EXAMPLES}</p>
          <p className="form-help-text">{MEANS_LINE_43_OWN_WORDS}</p>
          <p className="form-help-text">{MEANS_LINE_43_NO_SUGGESTION}</p>
          <p className="form-help-text">{MEANS_LINE_43_LAWYER}</p>

          {rows.map((row, index) => {
            const boxKey = explanationKey(row._key);
            return (
              // Keyed by the row, so a removed circumstance's typed amount never shows in the next
              <fieldset key={row._key} className="form-field fee-waiver-question">
                <legend id={`means-line-43-${index}-legend`} className="form-label">
                  {number(MEANS_LINE_43_LEGEND, index + 1)}
                </legend>
                {text('happened', row, index, MEANS_LINE_43_HAPPENED, MEANS_LINE_43_HAPPENED_HINT)}
                {text('change', row, index, MEANS_LINE_43_CHANGE)}
                <AmountBox
                  name={`means_line_43_${index}_amount`}
                  label={FORM_122A2_LINE_43_AMOUNT}
                  value={row.amount}
                  onChange={(value) => change(row._key, { amount: value })}
                />
                {text('choices', row, index, MEANS_LINE_43_CHOICES)}
                {text('papers', row, index, MEANS_LINE_43_PAPERS)}
                <p className="form-help-text">{MEANS_LINE_43_ASSEMBLE_NOTE}</p>
                <Button
                  type="button"
                  variant="outline"
                  id={`means-line-43-${index}-assemble`}
                  aria-labelledby={`means-line-43-${index}-assemble means-line-43-${index}-legend`}
                  onClick={() => assemble(row._key)}
                >
                  {MEANS_LINE_43_ASSEMBLE}
                </Button>
                <FormTextarea
                  label={FORM_122A2_LINE_43_EXPLANATION}
                  name={`means_line_43_${index}_explanation`}
                  value={row.explanation ?? ''}
                  maxLength={2000}
                  rows={8}
                  error={refusals[boxKey]}
                  onChange={(event) => {
                    clearRefusal(boxKey);
                    change(row._key, { explanation: event.target.value });
                  }}
                />
                <p className="form-help-text">{MEANS_LINE_43_BOX_NOTE}</p>
                <Button type="button" variant="outline" onClick={() => remove(row._key)}>
                  {number(MEANS_LINE_43_REMOVE, index + 1)}
                </Button>
              </fieldset>
            );
          })}
          {rows.length < MAX_CIRCUMSTANCES && (
            <Button type="button" variant="outline" onClick={add}>
              {MEANS_LINE_43_ADD}
            </Button>
          )}

          {showFigure &&
            line39c !== null &&
            rebuttalSentences(line39c, amounts).map((sentence) => (
              <p key={sentence} className="form-help-text">
                {sentence}
              </p>
            ))}
        </>
      )}
    </YesNoQuestion>
  );
}
