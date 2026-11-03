import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { api } from '../api/client';
import { Button, FormTextarea } from '../components/common';
import { UPLDisclaimer } from '../components/compliance';
import { UPL_WIZARD_DISCLAIMER } from '../constants/upl';
import { FILING_FEE_TEXT_LIMITS } from '../constants/filingFee';
import { WIZARD_STEPS } from '../constants/wizardSteps';
import {
  FEE_LAW_SENTENCE,
  LINE_8_LABEL,
  PAYMENT_CHOICE_WORDS,
  WAIVER_IDENTIFY_WHO,
  WAIVER_LINE_4_EXPLAIN,
  WAIVER_LINE_4_QUESTION,
  WAIVER_LINE_5_QUESTION,
  WAIVER_LINE_7_QUESTION,
  WAIVER_LINE_9_EXPLAIN,
  WAIVER_LINE_9_QUESTION,
} from '../constants/formText';
import {
  FEE_CHOICE_MISSING,
  FEE_COURT_DECIDES,
  FEE_FIGURE_LEAD,
  FEE_GUIDELINE_LEAD,
  FEE_INCOME_GAP,
  FEE_LIMIT_LEAD,
  FEE_LINE_5_NOTE,
  FEE_NO_TABLE,
  FEE_OTHER_LINES_NOTE,
  FEE_READ_FAILED,
  FEE_SAVE_FAILED,
  FILING_FEE_TITLE,
  FORM_103A_LINK,
  FORM_103A_URL,
  INSTALLMENTS_NOTICE,
} from '../constants/copy';
import { formatIsoDate } from '../utils/formatIsoDate';
import type { FilingFee, PaymentChoice, YesNo } from '../types/api';

type Answers = Omit<FilingFee, 'information' | 'information_gap'>;

// 103B lines 4, 7 and 9: a Yes/No answer and the text its Yes asks for
type WaiverQuestion = {
  legend: string;
  answer: 'income_change_answer' | 'others_covered_answer' | 'expense_change_answer';
  text: 'income_change_explanation' | 'others_covered_who' | 'expense_change_explanation';
  textLabel: string;
};

const LINE_4: WaiverQuestion = {
  legend: WAIVER_LINE_4_QUESTION,
  answer: 'income_change_answer',
  text: 'income_change_explanation',
  textLabel: WAIVER_LINE_4_EXPLAIN,
};
const LINE_7: WaiverQuestion = {
  legend: WAIVER_LINE_7_QUESTION,
  answer: 'others_covered_answer',
  text: 'others_covered_who',
  textLabel: WAIVER_IDENTIFY_WHO,
};
const LINE_9: WaiverQuestion = {
  legend: WAIVER_LINE_9_QUESTION,
  answer: 'expense_change_answer',
  text: 'expense_change_explanation',
  textLabel: WAIVER_LINE_9_EXPLAIN,
};

const CHOICES: PaymentChoice[] = ['pay_in_full', 'installments', 'waiver'];

const money = (amount: string) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(amount));

const incomeStep = WIZARD_STEPS.find((s) => s.key === 'income_info')!;

/**
 * Form 101 line 8, which every filer answers after Complete (3f spec §6). Beside it, as
 * information, the court's limit and the filer's own 103B figure; the court decides. Under the
 * waiver it asks 103B lines 4, 5, 7 and 9. Continues to the SOFA step.
 */
export function FilingFeePage() {
  const navigate = useNavigate();
  const { session } = useIntake();
  const sessionId = session?.id;

  const [answers, setAnswers] = useState<Answers | null>(null);
  const [information, setInformation] = useState<FilingFee['information']>(null);
  const [informationGap, setInformationGap] = useState<FilingFee['information_gap']>(null);
  const [read, setRead] = useState<'pending' | 'done' | 'failed'>('pending');
  const [readAttempt, setReadAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // The questions wait for the saved answers: a blank page sent over them would undo them
  useEffect(() => {
    if (sessionId == null) return;
    let cancelled = false;
    api.intake.filingFee
      .get(sessionId)
      .then((saved) => {
        if (cancelled) return;
        const { information: info, information_gap: gap, ...rest } = saved;
        setAnswers(rest);
        setInformation(info);
        setInformationGap(gap);
        setRead('done');
      })
      .catch(() => {
        if (!cancelled) setRead('failed');
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, readAttempt]);

  const handleRetry = () => {
    setRead('pending');
    setReadAttempt((attempt) => attempt + 1);
  };

  // Each control sets only its own key. Changing the choice clears nothing, so answers typed
  // under the waiver come back when it is picked again (§4).
  const set = <K extends keyof Answers>(key: K, value: Answers[K]) =>
    setAnswers((current) => (current ? { ...current, [key]: value } : current));

  // Only what the choice shows is sent. A text behind No is left out, so the server keeps it.
  const requestBody = (a: Answers): Partial<Answers> => {
    if (a.payment_choice !== 'waiver') return { payment_choice: a.payment_choice };
    const body: Partial<Answers> = {
      payment_choice: a.payment_choice,
      income_change_answer: a.income_change_answer,
      installments_explanation: a.installments_explanation,
      others_covered_answer: a.others_covered_answer,
      expense_change_answer: a.expense_change_answer,
    };
    for (const q of [LINE_4, LINE_7, LINE_9]) {
      if (a[q.answer] === 'yes') body[q.text] = a[q.text];
    }
    return body;
  };

  const handleContinue = async () => {
    if (sessionId == null || !answers) return;
    if (!answers.payment_choice) {
      setError(FEE_CHOICE_MISSING);
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await api.intake.filingFee.put(sessionId, requestBody(answers));
      // Form 107 is in every packet, so its questions come before the forms (DIG-149)
      navigate('/sofa');
    } catch {
      setError(FEE_SAVE_FAILED);
    } finally {
      setIsSaving(false);
    }
  };

  const yesNoQuestion = (a: Answers, q: WaiverQuestion) => (
    <fieldset className="form-field fee-waiver-question">
      <legend className="form-label">{q.legend}</legend>
      {(['no', 'yes'] as YesNo[]).map((value) => (
        <label key={value} className="fee-waiver-checkbox">
          <input
            type="radio"
            name={q.answer}
            value={value}
            checked={a[q.answer] === value}
            onChange={() => set(q.answer, value)}
          />{' '}
          {value === 'yes' ? 'Yes' : 'No'}
        </label>
      ))}
      {a[q.answer] === 'yes' && (
        <FormTextarea
          name={q.text}
          label={q.textLabel}
          value={a[q.text]}
          maxLength={FILING_FEE_TEXT_LIMITS[q.text]}
          onChange={(e) => set(q.text, e.target.value)}
        />
      )}
    </fieldset>
  );

  return (
    <main className="filing-fee-page">
      <h1>{FILING_FEE_TITLE}</h1>
      <p>{FEE_LAW_SENTENCE}</p>
      <UPLDisclaimer text={UPL_WIZARD_DISCLAIMER} variant="inline" />

      {read === 'failed' && (
        <div className="filing-fee-error">
          <p role="alert">{FEE_READ_FAILED}</p>
          <Button type="button" onClick={handleRetry}>
            Try again
          </Button>
        </div>
      )}

      {read === 'done' && answers && (
        <>
          {information && (
            <>
              <p>{`${FEE_LIMIT_LEAD} ${information.family_size}: ${money(information.limit_monthly)} a month.`}</p>
              <p>{`${FEE_GUIDELINE_LEAD} ${information.guideline.year}, published ${formatIsoDate(information.guideline.effective_date)}.`}</p>
              <p>{`${FEE_FIGURE_LEAD} ${money(information.family_income_monthly)} a month.`}</p>
            </>
          )}
          {informationGap === 'income' && (
            <>
              <p>{FEE_INCOME_GAP}</p>
              <p>
                <Link to={`/intake?step=${incomeStep.key}`}>{`Go to ${incomeStep.label}`}</Link>
              </p>
            </>
          )}
          {informationGap === 'no_table' && <p>{FEE_NO_TABLE}</p>}
          <p>{FEE_COURT_DECIDES}</p>

          <fieldset className="form-field fee-waiver-question">
            <legend className="form-label">{LINE_8_LABEL}</legend>
            {CHOICES.map((choice) => (
              <label key={choice} className="fee-waiver-checkbox">
                <input
                  type="radio"
                  name="payment_choice"
                  value={choice}
                  checked={answers.payment_choice === choice}
                  onChange={() => set('payment_choice', choice)}
                />{' '}
                {PAYMENT_CHOICE_WORDS[choice]}
              </label>
            ))}
          </fieldset>

          {answers.payment_choice === 'installments' && (
            <p className="info-box">
              {INSTALLMENTS_NOTICE}{' '}
              <a href={FORM_103A_URL} target="_blank" rel="noopener noreferrer">
                {FORM_103A_LINK}
              </a>
            </p>
          )}

          {answers.payment_choice === 'waiver' && (
            <>
              {yesNoQuestion(answers, LINE_4)}
              <FormTextarea
                name="installments_explanation"
                label={WAIVER_LINE_5_QUESTION}
                helpText={FEE_LINE_5_NOTE}
                value={answers.installments_explanation}
                maxLength={FILING_FEE_TEXT_LIMITS.installments_explanation}
                onChange={(e) => set('installments_explanation', e.target.value)}
              />
              {yesNoQuestion(answers, LINE_7)}
              {yesNoQuestion(answers, LINE_9)}
              <p className="form-help-text">{FEE_OTHER_LINES_NOTE}</p>
            </>
          )}

          {error && (
            <div className="filing-fee-error" role="alert">
              <p>{error}</p>
            </div>
          )}

          <Button type="button" onClick={handleContinue} disabled={isSaving}>
            Continue
          </Button>
        </>
      )}
    </main>
  );
}
