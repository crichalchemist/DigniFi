import { useEffect, useRef, useState, type Ref } from 'react';
import { api, APIClientError } from '../../api/client';
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
  MEANS_EXPLANATION_TOO_LONG,
  MEANS_POLISH_BLANK,
  MEANS_POLISH_IDENTIFIER,
  MEANS_POLISH_NO_REWRITE,
  MEANS_POLISH_PHRASE,
  MEANS_POLISH_TOO_MANY,
  MEANS_POLISH_UNAVAILABLE,
} from '../../constants/copy';
import type { MeansOutcome } from '../../types/api';
import { AmountBox } from './AmountBox';
import { assembleExplanation } from './meansDraft';
import { cents } from './money';
import { rebuttalSentences } from './meansRebuttal';
import { explanationKey, type KeyedCircumstance, type PageAnswers } from './pageState';
import { Polish, type Pending } from './Polish';
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
  sessionId: number;
  /** True when the server has an AI service set up for the rewrite */
  polishAvailable: boolean;
  /** Show a sentence beside a box, under the same key a refused save uses */
  setRefusal: (key: string, sentence: string) => void;
}

type Status = 'approved' | 'kept' | null;

/** The four sentences a 400 from the polish endpoint may carry for the explanation box */
const POLISH_REFUSALS = [
  MEANS_POLISH_BLANK,
  MEANS_EXPLANATION_TOO_LONG,
  MEANS_POLISH_IDENTIFIER,
  MEANS_POLISH_PHRASE,
];

const without = <T,>(record: Record<string, T>, key: string): Record<string, T> => {
  const { [key]: gone, ...rest } = record;
  void gone;
  return rest;
};

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
  sessionId,
  polishAvailable,
  setRefusal,
}: Line43Props) {
  const rows = answers.line_43_circumstances;
  // Consent is asked once while line 43 stays Yes, for every circumstance (R11)
  const [consented, setConsented] = useState(false);
  // The row whose consent panel is open
  const [asking, setAsking] = useState<string | null>(null);
  // A rewrite the filer hasn't approved lives here and nowhere else; it never goes with a save
  const [pending, setPending] = useState<Record<string, Pending>>({});
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [failure, setFailure] = useState<Record<string, string | null>>({});
  const [status, setStatus] = useState<Record<string, Status>>({});
  // The requests still out, so Remove, leaving Yes and leaving the page can call them off
  const requests = useRef<Record<string, AbortController>>({});
  // An element id to focus once the state that makes it focusable has been drawn
  const focusAfter = useRef<string | null>(null);
  useEffect(() => {
    if (focusAfter.current === null) return;
    document.getElementById(focusAfter.current)?.focus();
    focusAfter.current = null;
  });
  const boxId = (key: string) =>
    `field-means_line_43_${rows.findIndex((row) => row._key === key)}_explanation`;
  const buttonId = (key: string) =>
    `means-line-43-${rows.findIndex((row) => row._key === key)}-polish`;
  const statusId = (key: string) =>
    `means-line-43-${rows.findIndex((row) => row._key === key)}-status`;

  // Line43 never unmounts, only its controls do: leaving Yes calls every request off and forgets
  // the consent, the rewrites and the sentences about them
  useEffect(() => {
    if (answers.line_43_answer === 'yes') return;
    for (const controller of Object.values(requests.current)) controller.abort();
    for (const key of Object.keys(requests.current)) delete requests.current[key];
    setPending({});
    setBusy({});
    setFailure({});
    setStatus({});
    setAsking(null);
    setConsented(false);
  }, [answers.line_43_answer]);
  // Continue navigates away: a reply must not land on a page that has gone
  useEffect(() => {
    const live = requests.current;
    return () => {
      for (const controller of Object.values(live)) controller.abort();
    };
  }, []);
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
          original_explanation: null,
        },
      ],
    }));
  };
  const remove = (key: string) => {
    requests.current[key]?.abort();
    delete requests.current[key];
    setPending((current) => without(current, key));
    setBusy((current) => without(current, key));
    setFailure((current) => without(current, key));
    setStatus((current) => without(current, key));
    setAsking((current) => (current === key ? null : current));
    onChange((current) => ({
      ...current,
      line_43_circumstances: current.line_43_circumstances.filter((row) => row._key !== key),
    }));
  };
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

  // One press is one send: the words in the box, trimmed, and nothing else
  const request = async (key: string) => {
    const sent = (rows.find((row) => row._key === key)?.explanation ?? '').trim();
    const controller = new AbortController();
    requests.current[key] = controller;
    setBusy((current) => ({ ...current, [key]: true }));
    setFailure((current) => ({ ...current, [key]: null }));
    setStatus((current) => ({ ...current, [key]: null }));
    // The press disabled the button (or closed the panel that held focus): focus rests on the
    // status sentence, and stays there if the request fails
    focusAfter.current = statusId(key);
    try {
      const reply = await api.intake.meansTest.polish(sessionId, sent, controller.signal);
      // A request called off (Remove, leaving Yes) has been forgotten already
      if (requests.current[key] !== controller) return;
      setPending((current) => ({ ...current, [key]: { sent, rewrite: reply.rewrite } }));
    } catch (error) {
      if (requests.current[key] !== controller) return;
      const refused = error instanceof APIClientError ? error : null;
      const first = (refused?.body?.explanation as unknown[] | undefined)?.[0];
      const said = refused?.body?.error;
      if (refused?.statusCode === 400 && POLISH_REFUSALS.some((sentence) => sentence === first)) {
        setRefusal(explanationKey(key), first as string);
      } else if (refused?.statusCode === 429) {
        setFailure((current) => ({ ...current, [key]: MEANS_POLISH_TOO_MANY }));
      } else if (!(error instanceof DOMException && error.name === 'AbortError')) {
        const sentence =
          (refused?.statusCode === 422 || refused?.statusCode === 503) &&
          said === MEANS_POLISH_NO_REWRITE
            ? MEANS_POLISH_NO_REWRITE
            : MEANS_POLISH_UNAVAILABLE;
        setFailure((current) => ({ ...current, [key]: sentence }));
      }
    }
    delete requests.current[key];
    setBusy((current) => ({ ...current, [key]: false }));
  };
  const requestPolish = (key: string) => {
    if (consented) void request(key);
    else setAsking(key);
  };
  const answerConsent = (key: string, agree: boolean) => {
    setAsking(null);
    if (agree) {
      setConsented(true);
      void request(key);
    } else {
      focusAfter.current = buttonId(key);
    }
  };
  const approve = (row: KeyedCircumstance, edited: string) => {
    change(row._key, {
      explanation: edited,
      // The first approval records the filer's own words; a later one never relabels AI text
      original_explanation: row.original_explanation ?? pending[row._key].sent,
    });
    clearRefusal(explanationKey(row._key));
    setPending((current) => without(current, row._key));
    setStatus((current) => ({ ...current, [row._key]: 'approved' }));
    focusAfter.current = boxId(row._key);
  };
  const keep = (key: string) => {
    setPending((current) => without(current, key));
    setStatus((current) => ({ ...current, [key]: 'kept' }));
    focusAfter.current = buttonId(key);
  };
  const restore = (row: KeyedCircumstance) => {
    change(row._key, { explanation: row.original_explanation ?? null, original_explanation: null });
    clearRefusal(explanationKey(row._key));
    setStatus((current) => ({ ...current, [row._key]: null }));
    focusAfter.current = boxId(row._key);
  };

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
                  // An approval would overwrite an edit made meanwhile, unseen (R22): the box is held
                  // from the press until the rewrite is answered
                  disabled={busy[row._key] === true || pending[row._key] !== undefined}
                  onChange={(event) => {
                    const value = event.target.value;
                    clearRefusal(boxKey);
                    // A box emptied by hand holds no rewrite, so no original is kept (R13), and no
                    // sentence says it does
                    if (value.trim() === '') {
                      setStatus((current) =>
                        current[row._key] === 'approved'
                          ? { ...current, [row._key]: null }
                          : current
                      );
                    }
                    change(
                      row._key,
                      value.trim() === ''
                        ? { explanation: value, original_explanation: null }
                        : { explanation: value }
                    );
                  }}
                />
                <Polish
                  index={index}
                  row={row}
                  legendId={`means-line-43-${index}-legend`}
                  pending={pending[row._key]}
                  asking={asking === row._key}
                  status={status[row._key] ?? null}
                  busy={busy[row._key] ?? false}
                  failure={failure[row._key] ?? null}
                  available={polishAvailable}
                  onRequest={() => requestPolish(row._key)}
                  onConsent={(agree) => answerConsent(row._key, agree)}
                  onApprove={(edited) => approve(row, edited)}
                  onKeep={() => keep(row._key)}
                  onRestore={() => restore(row)}
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
