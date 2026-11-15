import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { api, APIClientError } from '../api/client';
import { Button, FormField, FormSelect } from '../components/common';
import { UPLDisclaimer } from '../components/compliance';
import { UPL_WIZARD_DISCLAIMER } from '../constants/upl';
import {
  FORM_122A2_LINE_11,
  FORM_122A2_LINE_25_ACTUAL,
  FORM_122A2_LINE_25_DISABILITY,
  FORM_122A2_LINE_25_HEALTH,
  FORM_122A2_LINE_25_HSA,
  FORM_122A2_LINE_25_SPENDS,
  FORM_122A2_LINE_3_AMOUNT,
  FORM_122A2_LINE_3_EXAMPLE,
  FORM_122A2_LINE_3_PURPOSE,
  FORM_122A2_LINE_3_QUESTION,
  FORM_122A2_LINE_34,
  FORM_122A2_LINE_34_CURE,
  FORM_122A2_LINE_34_DEBT,
  FORM_122A2_LINE_36,
  FORM_122A2_LINE_36_PAYMENT,
  FORM_122A2_LINE_WORDS,
  FORM_122A2_PART_2_AVERAGE,
  FORM_122A2_PART_2_LINE_3,
  FORM_122A2_PART_2_YOU,
  FORM_122A2_TITLE,
  FORM_122A2_VEHICLE_1,
  FORM_122A2_VEHICLE_2,
  FORM_122A2_VEHICLE_CLAIM,
  FORM_122A2_VEHICLE_LIMIT,
  type MeansAskedLine,
} from '../constants/formText';
import {
  MEANS_ADD_ROW,
  MEANS_EXPLANATION_LETTER,
  MEANS_EXPLANATION_TOO_LONG,
  MEANS_LINE_27_NOTE,
  MEANS_LINE_35,
  MEANS_LINE_36_LIMITS,
  MEANS_LINE_36_LINK,
  MEANS_LINE_36_MULTIPLIER,
  MEANS_LINE_36_OTHER_RULES,
  MEANS_LINE_36_PRODUCT,
  MEANS_LINE_36_TOTALS,
  MEANS_PAGE_AGES,
  MEANS_PAGE_INTRO,
  MEANS_PAGE_LOADING,
  MEANS_PAGE_READ_FAILED,
  MEANS_PAGE_SAVE_FAILED,
  MEANS_REMOVE_ROW,
  MEANS_RESULT_CHANGED,
  MEANS_ROW_LEGEND,
  MEANS_SPOUSE_VEHICLE_LEGEND,
  MEANS_TOO_LONG,
} from '../constants/copy';
import { formatIsoDate } from '../utils/formatIsoDate';
import { AmountBox } from './meansTest/AmountBox';
import { besideLine } from './meansTest/beside';
import { Line43 } from './meansTest/Line43';
import { DebtQuestions, type DebtItem } from './meansTest/DebtQuestions';
import { MeansResult } from './meansTest/MeansResult';
import { debtLines, slotCandidates } from './meansTest/meansRows';
import { firstMeansGap } from './meansTest/meansTestGaps';
import { dollars } from './meansTest/money';
import { planProduct } from './meansTest/meansProduct';
import {
  aboveLine43,
  adoptRefs,
  debtPrefix,
  explanationKey,
  fromReply,
  gapStateOf,
  line11Vehicles,
  rowsInputOf,
  spouseLoanHeading,
  spouseLoanViews,
  toPutBody,
  withLiveRefs,
  type PageAnswers,
  type PageState,
} from './meansTest/pageState';
import { SpouseBlock } from './meansTest/SpouseBlock';
import { YesNoQuestion } from './meansTest/YesNoQuestion';
import type { MeansDebtAnswers, MeansPage, YesNo } from '../types/api';

/** The server refuses a list of more than 10 rows (MAX_ROWS in apps/intake/means_test.py) */
const MAX_LIST_ROWS = 10;

type AmountKey = {
  [K in keyof PageAnswers]: PageAnswers[K] extends string | null ? K : never;
}[keyof PageAnswers];

const PLAIN_LINES = ['16', '17', '18', '19', '20', '21', '23'] as const;
const OPT_IN_LINES = ['22', '26', '27', '28', '29', '30', '31'] as const;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

// The whole number as the server's whole dollars: its § 104 amounts are whole, so no ".00"
const wholeDollars = (amount: string) => dollars(amount).replace(/\.00$/, '');

// split/join, not replace: replace reads $& in a figure as a pattern
const fill = (sentence: string, values: Record<string, string | number>) =>
  Object.entries(values).reduce(
    (text, [key, value]) => text.split(`{${key}}`).join(String(value)),
    sentence
  );

/** True once any answer is given (a row counts, however empty): a page nobody began says nothing */
function anythingAnswered(state: PageState): boolean {
  const given = (value: unknown): boolean => {
    if (value === null || value === undefined) return false;
    // A row counts however empty its boxes are; the Vehicle 1 and 2 pair counts once one is chosen
    if (Array.isArray(value)) return value.some(given);
    if (isRecord(value)) return Object.values(value).some(given);
    return true;
  };
  const debtKeys = [
    'payments_left',
    'payment_changes',
    'total_60_months',
    'taxes_or_insurance',
    'necessary_for_support',
    'cure',
  ] as const;
  return (
    Object.values(state.answers).some(given) ||
    state.debts.some((debt) => debtKeys.some((key) => given(debt[key])))
  );
}

// The lists whose text boxes the server measures, each box's sentence key by the row's `_key`
const FIT_BOXES: Record<
  string,
  {
    rows: (sent: PageState) => { _key: string }[];
    boxes: Record<string, (key: string) => string>;
  }
> = {
  line_3_rows: {
    rows: (sent) => sent.answers.line_3_rows,
    boxes: { purpose: (key) => `line_3:${key}` },
  },
  spouse_vehicles: {
    rows: (sent) => sent.answers.spouse_vehicles,
    boxes: { description: (key) => `spouse_vehicle:${key}:description` },
  },
  spouse_loans: {
    rows: (sent) => sent.answers.spouse_loans,
    boxes: {
      creditor: (key) => `spouse_loan:${key}:creditor`,
      property: (key) => `spouse_loan:${key}:property`,
    },
  },
};

/** The two sentences the server gives for an explanation it refuses (F10) */
const EXPLANATION_REFUSALS: unknown[] = [MEANS_EXPLANATION_TOO_LONG, MEANS_EXPLANATION_LETTER];

/**
 * What a failed save says about the boxes sent. `fields` holds the boxes a 400 refuses for not
 * fitting, keyed by `FIT_BOXES` (`line_3:<_key>`, `spouse_vehicle:<_key>:description`, ...).
 * `other` is true for any other failure, or a box the page doesn't show: only the save sentence
 * says it.
 */
function readRefusal(
  caught: unknown,
  sent: PageState
): { fields: Record<string, string>; other: boolean } {
  if (!(caught instanceof APIClientError) || caught.statusCode !== 400 || !caught.body) {
    return { fields: {}, other: true };
  }
  const fields: Record<string, string> = {};
  let other = false;
  for (const [name, value] of Object.entries(caught.body)) {
    if (name === 'line_43_circumstances' && isRecord(value)) {
      for (const [index, errors] of Object.entries(value)) {
        const row = sent.answers.line_43_circumstances[Number(index)];
        if (row === undefined || !isRecord(errors)) {
          other = true;
          continue;
        }
        for (const [field, messages] of Object.entries(errors)) {
          const first = Array.isArray(messages) ? messages[0] : undefined;
          // The circumstances are drawn only under a Yes; under No the sentence has no box
          if (
            field === 'explanation' &&
            EXPLANATION_REFUSALS.includes(first) &&
            sent.answers.line_43_answer === 'yes'
          ) {
            fields[explanationKey(row._key)] = String(first);
          } else {
            other = true;
          }
        }
      }
      continue;
    }
    const list = FIT_BOXES[name];
    if (list === undefined || !isRecord(value)) {
      other = true;
      continue;
    }
    for (const [index, errors] of Object.entries(value)) {
      const row = list.rows(sent)[Number(index)];
      if (row === undefined || !isRecord(errors)) {
        other = true;
        continue;
      }
      for (const field of Object.keys(errors)) {
        const box = list.boxes[field];
        if (box === undefined) other = true;
        else fields[box(row._key)] = MEANS_TOO_LONG;
      }
    }
  }
  return { fields, other };
}

/**
 * Form 122A-2's questions, in the form's order (forms step 3h2 spec §8). The filer answers every
 * one and nothing is chosen for them. The page holds its answers itself and saves them on
 * Continue, which leaves for the SOFA step only when nothing is missing and the result hasn't
 * changed under the filer.
 */
export function MeansTestPage() {
  const navigate = useNavigate();
  const { hash } = useLocation();
  const { session } = useIntake();
  const sessionId = session?.id;

  const [page, setPage] = useState<MeansPage | null>(null);
  const [state, setState] = useState<PageState | null>(null);
  const [read, setRead] = useState<'pending' | 'done' | 'failed'>('pending');
  const [readAttempt, setReadAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [pressed, setPressed] = useState(false);
  const [changed, setChanged] = useState(false);
  const [replyGap, setReplyGap] = useState<string | null>(null);
  // What sits above line 43 as the server last read it, or as the last save's reply was taken
  const [savedAboveCopy, setSavedAboveCopy] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  // One counter for every list a row is added to, so a `new-<n>` is never used twice
  const newRows = useRef(0);
  const saving = useRef(false);
  const resultRef = useRef<HTMLElement>(null);
  const line43Ref = useRef<HTMLLegendElement>(null);

  // Nothing is drawn until the saved answers are read: a blank page sent over them would undo them
  useEffect(() => {
    if (sessionId == null) return;
    let cancelled = false;
    api.intake.meansTest
      .get(sessionId)
      .then((loaded) => {
        if (cancelled) return;
        setPage(loaded);
        const fresh = fromReply(loaded);
        setState(fresh);
        setSavedAboveCopy(aboveLine43(fresh));
        setRead('done');
      })
      .catch(() => {
        if (!cancelled) setRead('failed');
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, readAttempt]);

  const applies = read === 'done' && page ? page.applies : undefined;

  // The form doesn't apply (or stopped applying after a save): the page follows the server
  useEffect(() => {
    if (applies === false) navigate('/sofa', { replace: true });
  }, [applies, navigate]);

  // Opened with #line-43: bring line 43 into view and focus its legend
  useEffect(() => {
    if (applies !== true || hash !== '#line-43') return;
    const legend = line43Ref.current;
    legend?.closest('fieldset')?.scrollIntoView?.();
    legend?.focus();
  }, [applies, hash]);

  useEffect(() => {
    if (changed) resultRef.current?.focus();
  }, [changed]);

  const rows = useMemo(() => (page && state ? rowsInputOf(page, state) : null), [page, state]);
  const browserGap = useMemo(
    () => (page && state ? firstMeansGap(gapStateOf(page, state)) : null),
    [page, state]
  );

  const handleRetry = () => {
    setRead('pending');
    setReadAttempt((attempt) => attempt + 1);
  };

  const edit = (change: (current: PageState) => PageState) => {
    setState((current) => (current ? change(current) : current));
    setReplyGap(null);
    setChanged(false);
  };
  // A sentence about a box goes once that box changes
  const clearFieldError = (key: string) =>
    setFieldErrors((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });
  const setAnswer = <K extends keyof PageAnswers>(key: K, value: PageAnswers[K]) =>
    edit((current) => ({ ...current, answers: { ...current.answers, [key]: value } }));
  const setAmount = (key: AmountKey, value: string | null) =>
    setAnswer(key, value as PageAnswers[typeof key]);

  const nextKey = () => {
    newRows.current += 1;
    return `new-${newRows.current}`;
  };
  const addRow = () => {
    const key = nextKey();
    edit((current) => ({
      ...current,
      answers: {
        ...current.answers,
        line_3_rows: [...current.answers.line_3_rows, { _key: key, purpose: '', amount: null }],
      },
    }));
  };

  const handleContinue = async () => {
    if (!page || !state || saving.current) return;
    if (applies === null) {
      navigate('/sofa');
      return;
    }
    if (sessionId == null) return;
    saving.current = true;
    setIsSaving(true);
    setPressed(true);
    setError(null);
    setFieldErrors({});
    setChanged(false);
    setReplyGap(null);
    // The controls hold still while the save is on its way, so this is what is on screen
    const sent = state;
    const shown = page.outcome;
    try {
      const reply = await api.intake.meansTest.put(sessionId, toPutBody(withLiveRefs(page, sent)));
      const next = adoptRefs(sent, sent, reply);
      const nextPage: MeansPage = {
        ...page,
        applies: reply.applies,
        applies_gap: reply.applies_gap,
        debt_lines: reply.debt_lines,
        information: reply.information,
        outcome: reply.outcome,
        family_size: reply.family_size,
        tables_gap: reply.tables_gap,
        gap: reply.gap,
        debts_answered_on: reply.debts_answered_on,
      };
      setState(next);
      setSavedAboveCopy(aboveLine43(next));
      setPage(nextPage);
      if (reply.applies !== true) return;
      const ours = firstMeansGap(gapStateOf(nextPage, next));
      if (ours !== null || reply.gap !== null) {
        setReplyGap(reply.gap);
      } else if (reply.outcome !== shown) {
        setChanged(true);
      } else {
        navigate('/sofa');
      }
    } catch (caught) {
      const { fields, other } = readRefusal(caught, sent);
      setFieldErrors(fields);
      if (other || Object.keys(fields).length === 0) setError(MEANS_PAGE_SAVE_FAILED);
    } finally {
      saving.current = false;
      setIsSaving(false);
    }
  };

  const linkToLine43 = () => {
    const legend = line43Ref.current;
    legend?.closest('fieldset')?.scrollIntoView?.();
    legend?.focus();
  };

  if (read === 'pending') {
    return (
      <main className="filing-fee-page">
        <p>{MEANS_PAGE_LOADING}</p>
      </main>
    );
  }
  if (read === 'failed' || !page || !state || !rows) {
    return (
      <main className="filing-fee-page">
        <div className="filing-fee-error">
          <p role="alert">{MEANS_PAGE_READ_FAILED}</p>
          <Button type="button" onClick={handleRetry}>
            Try again
          </Button>
        </div>
      </main>
    );
  }
  if (page.applies === false) return null;

  const gapRegion = (text: string | null) => (
    <div role="status">
      {text !== null && (
        <div className="info-box">
          <p className="info-message">{text}</p>
        </div>
      )}
    </div>
  );

  if (page.applies === null) {
    return (
      <main className="filing-fee-page">
        <h1>{FORM_122A2_TITLE}</h1>
        <UPLDisclaimer text={UPL_WIZARD_DISCLAIMER} variant="inline" />
        {gapRegion(page.applies_gap)}
        <Button type="button" onClick={handleContinue}>
          Continue
        </Button>
      </main>
    );
  }

  const { answers } = state;
  const { information } = page;
  const together = page.married_together;
  const besides = (line: MeansAskedLine) =>
    besideLine(line, information, together).map((sentence) => (
      <p key={sentence} className="form-help-text">
        {sentence}
      </p>
    ));

  const amountOf = (key: AmountKey) => answers[key] as string | null;
  const answerOf = (key: keyof PageAnswers) => answers[key] as YesNo | null;

  const plainLine = (line: (typeof PLAIN_LINES)[number]) => {
    const key = `line_${line}` as AmountKey;
    return (
      <div className="means-line" key={line}>
        <AmountBox
          name={`means_line_${line}`}
          label={FORM_122A2_LINE_WORDS[line]}
          value={amountOf(key)}
          onChange={(value) => setAmount(key, value)}
        />
        {besides(line)}
      </div>
    );
  };

  // A line the filer may decline: a Yes/No, and under Yes its amount (and any extra boxes)
  const optInLine = (line: MeansAskedLine, extra?: ReactNode, note?: string) => {
    const answerKey = `line_${line}_answer` as keyof PageAnswers;
    const amountKey = `line_${line}_amount` as AmountKey;
    const answer = answerOf(answerKey);
    return (
      <div className="means-line" key={line}>
        <YesNoQuestion
          question={FORM_122A2_LINE_WORDS[line]}
          name={`means_line_${line}`}
          value={answer}
          note={note}
          onChange={(next) => setAnswer(answerKey, next as never)}
        />
        {answer === 'yes' &&
          (extra ?? (
            <AmountBox
              name={`means_line_${line}_amount`}
              label={FORM_122A2_LINE_WORDS[line]}
              value={amountOf(amountKey)}
              onChange={(value) => setAmount(amountKey, value)}
            />
          ))}
        {besides(line)}
      </div>
    );
  };

  // What the page shows is read as the server will read it: a reference to a removed row is none
  const live = withLiveRefs(page, state).answers;
  const listedVehicles = line11Vehicles(page, answers);
  // A candidate spouse row with no description reads as its legend, never its ref
  const vehicleNames = new Map([
    ...page.vehicles.map((vehicle) => [vehicle.ref, vehicle.name] as const),
    ...answers.spouse_vehicles.map(
      (row, index) =>
        [
          row.ref,
          row.description.trim() === ''
            ? fill(MEANS_SPOUSE_VEHICLE_LEGEND, { n: index + 1 })
            : row.description,
        ] as const
    ),
  ]);
  const candidates = slotCandidates(rows);
  const chooseSlot = (index: 0 | 1, ref: string) =>
    edit((current) => {
      const choice: [string | null, string | null] = [...current.answers.vehicle_choice];
      choice[index] = ref === '' ? null : ref;
      return { ...current, answers: { ...current.answers, vehicle_choice: choice } };
    });
  const slotSelect = (index: 0 | 1) => {
    const other = live.vehicle_choice[index === 0 ? 1 : 0];
    return (
      <FormSelect
        label={index === 0 ? FORM_122A2_VEHICLE_1 : FORM_122A2_VEHICLE_2}
        name={`means_vehicle_${index + 1}`}
        placeholder=""
        required
        value={live.vehicle_choice[index] ?? ''}
        options={(candidates ?? [])
          .filter((ref) => ref !== other)
          .map((ref) => ({ value: ref, label: vehicleNames.get(ref) ?? '' }))}
        onChange={(ref) => chooseSlot(index, ref)}
      />
    );
  };

  const claimedVehicle = rows.vehicles.some((vehicle) => vehicle.claimed);

  // Each secured debt, as the page asks about it: the filer's, then the spouse's loans whose
  // identity is given (a loan with none has no line to ask about)
  const lines = debtLines(rows);
  const debtItems: (DebtItem & { creditor: string })[] = [
    ...state.debts.map((debt) => ({
      key: debt.ref,
      ref: debt.ref,
      prefix: debtPrefix(debt.ref),
      heading: debt.creditor,
      creditor: debt.creditor,
      property: debt.property,
      monthlyPayment: debt.monthly_payment,
      answers: debt as MeansDebtAnswers,
    })),
    ...spouseLoanViews(page, state)
      .filter((view) => view.identityGiven)
      .map((view) => ({
        key: view.loan._key,
        ref: view.loan.ref,
        prefix: debtPrefix(view.loan.ref),
        heading: spouseLoanHeading(view.creditor),
        creditor: view.creditor,
        property: view.property,
        monthlyPayment: null,
        answers: view.loan as MeansDebtAnswers,
      })),
  ];
  const changeDebt = (key: string, change: Partial<MeansDebtAnswers>) =>
    edit((current) => ({
      ...current,
      debts: current.debts.map((debt) => (debt.ref === key ? { ...debt, ...change } : debt)),
      answers: {
        ...current.answers,
        spouse_loans: current.answers.spouse_loans.map((loan) =>
          loan._key === key ? { ...loan, ...change } : loan
        ),
      },
    }));
  const shownGap = pressed || anythingAnswered(state) ? (browserGap ?? replyGap) : null;
  const gapText = changed ? MEANS_RESULT_CHANGED : shownGap;

  return (
    <main className="filing-fee-page">
      <h1>{FORM_122A2_TITLE}</h1>
      <MeansResult page={page} linkToLine43={linkToLine43} ref={resultRef} />
      <p>{MEANS_PAGE_INTRO}</p>
      <p>{MEANS_PAGE_AGES}</p>
      <UPLDisclaimer text={UPL_WIZARD_DISCLAIMER} variant="inline" />

      {/* Every answer holds still while the save is on its way: an edit made meanwhile would be
          lost when the page moves on, and a refusal could name a row no longer shown */}
      <fieldset className="fee-waiver-question" disabled={isSaving}>
        {together && (
          <div className="means-line">
            <YesNoQuestion
              question={FORM_122A2_LINE_3_QUESTION}
              name="means_line_3"
              value={answers.line_3_answer}
              note={FORM_122A2_LINE_3_EXAMPLE}
              onChange={(next) =>
                edit((current) => ({
                  ...current,
                  answers: {
                    ...current.answers,
                    line_3_answer: next,
                  },
                }))
              }
            />
            {answers.line_3_answer === 'yes' && (
              <>
                {answers.line_3_rows.map((row, index) => (
                  <fieldset key={row._key} className="form-field fee-waiver-question">
                    <legend className="form-label">
                      {MEANS_ROW_LEGEND.replace('{n}', String(index + 1))}
                    </legend>
                    <FormField
                      label={FORM_122A2_LINE_3_PURPOSE}
                      name={`means_line_3_${index}_purpose`}
                      value={row.purpose}
                      error={fieldErrors[`line_3:${row._key}`]}
                      onChange={(event) => {
                        clearFieldError(`line_3:${row._key}`);
                        edit((current) => ({
                          ...current,
                          answers: {
                            ...current.answers,
                            line_3_rows: current.answers.line_3_rows.map((own) =>
                              own._key === row._key ? { ...own, purpose: event.target.value } : own
                            ),
                          },
                        }));
                      }}
                    />
                    <AmountBox
                      name={`means_line_3_${index}_amount`}
                      label={FORM_122A2_LINE_3_AMOUNT}
                      value={row.amount}
                      onChange={(value) =>
                        edit((current) => ({
                          ...current,
                          answers: {
                            ...current.answers,
                            line_3_rows: current.answers.line_3_rows.map((own) =>
                              own._key === row._key ? { ...own, amount: value } : own
                            ),
                          },
                        }))
                      }
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() =>
                        edit((current) => ({
                          ...current,
                          answers: {
                            ...current.answers,
                            line_3_rows: current.answers.line_3_rows.filter(
                              (own) => own._key !== row._key
                            ),
                          },
                        }))
                      }
                    >
                      {MEANS_REMOVE_ROW.replace('{n}', String(index + 1))}
                    </Button>
                  </fieldset>
                ))}
                {answers.line_3_rows.length < MAX_LIST_ROWS && (
                  <Button type="button" variant="outline" onClick={addRow}>
                    {MEANS_ADD_ROW}
                  </Button>
                )}
              </>
            )}
          </div>
        )}

        {together && (
          <SpouseBlock
            page={page}
            answers={answers}
            edit={edit}
            nextKey={nextKey}
            boxErrors={fieldErrors}
            clearBoxError={clearFieldError}
          />
        )}

        {listedVehicles.length > 0 && (
          <div className="means-line">
            <p className="form-label">{FORM_122A2_LINE_11}</p>
            {listedVehicles.map((vehicle) => {
              // A spouse's claim is on its row, so a new row's claim travels with it
              const spouseRow = vehicle.spouse
                ? answers.spouse_vehicles.find((row) => row.ref === vehicle.ref)
                : undefined;
              return (
                <YesNoQuestion
                  key={spouseRow?._key ?? vehicle.ref}
                  question={fill(FORM_122A2_VEHICLE_CLAIM, { name: vehicle.name })}
                  name={`means_vehicle_${vehicle.ref.replace('asset-', '').replace('-', '_')}_claimed`}
                  value={
                    spouseRow ? spouseRow.claimed : (answers.vehicle_claims[vehicle.ref] ?? null)
                  }
                  onChange={(next) =>
                    edit((current) =>
                      spouseRow
                        ? {
                            ...current,
                            answers: {
                              ...current.answers,
                              spouse_vehicles: current.answers.spouse_vehicles.map((row) =>
                                row._key === spouseRow._key ? { ...row, claimed: next } : row
                              ),
                            },
                          }
                        : {
                            ...current,
                            // The server replaces the claims whole: every other claim goes with this one
                            answers: {
                              ...current.answers,
                              vehicle_claims: {
                                ...current.answers.vehicle_claims,
                                [vehicle.ref]: next,
                              },
                            },
                          }
                    )
                  }
                />
              );
            })}
            {candidates !== null && candidates.length > 2 && (
              <>
                <p className="form-help-text">{FORM_122A2_VEHICLE_LIMIT}</p>
                {slotSelect(0)}
                {slotSelect(1)}
              </>
            )}
          </div>
        )}

        {claimedVehicle && optInLine('15')}

        <p className="form-help-text">{FORM_122A2_PART_2_AVERAGE}</p>
        <p className="form-help-text">{FORM_122A2_PART_2_LINE_3}</p>
        {together && <p className="form-help-text">{FORM_122A2_PART_2_YOU}</p>}

        {PLAIN_LINES.filter((line) => line !== '23').map(plainLine)}
        {optInLine('22')}
        {plainLine('23')}

        {optInLine(
          '25',
          <>
            <AmountBox
              name="means_line_25_health"
              label={FORM_122A2_LINE_25_HEALTH}
              value={answers.line_25_health}
              onChange={(value) => setAmount('line_25_health', value)}
            />
            <AmountBox
              name="means_line_25_disability"
              label={FORM_122A2_LINE_25_DISABILITY}
              value={answers.line_25_disability}
              onChange={(value) => setAmount('line_25_disability', value)}
            />
            <AmountBox
              name="means_line_25_hsa"
              label={FORM_122A2_LINE_25_HSA}
              value={answers.line_25_hsa}
              onChange={(value) => setAmount('line_25_hsa', value)}
            />
            <YesNoQuestion
              question={FORM_122A2_LINE_25_SPENDS}
              name="means_line_25_spends"
              value={answers.line_25_spends}
              onChange={(next) => setAnswer('line_25_spends', next)}
            />
            {answers.line_25_spends === 'no' && (
              <AmountBox
                name="means_line_25_actual"
                label={FORM_122A2_LINE_25_ACTUAL}
                value={answers.line_25_actual}
                onChange={(value) => setAmount('line_25_actual', value)}
              />
            )}
          </>
        )}

        {OPT_IN_LINES.filter((line) => line !== '22').map((line) =>
          optInLine(line, undefined, line === '27' ? MEANS_LINE_27_NOTE : undefined)
        )}

        <DebtQuestions items={debtItems} lines={lines} onChange={changeDebt} />

        <div className="means-line">
          <YesNoQuestion
            question={FORM_122A2_LINE_34}
            name="means_line_34"
            value={answers.line_34_answer}
            onChange={(next) => setAnswer('line_34_answer', next)}
          />
          {answers.line_34_answer === 'yes' &&
            debtItems
              .filter((item) => (lines[item.ref] ?? null) !== null)
              .map((item) => (
                <div key={item.key}>
                  <YesNoQuestion
                    question={fill(FORM_122A2_LINE_34_DEBT, { name: item.creditor })}
                    name={`${item.prefix}_support`}
                    value={item.answers.necessary_for_support}
                    onChange={(next) => changeDebt(item.key, { necessary_for_support: next })}
                  />
                  {item.answers.necessary_for_support === 'yes' && (
                    <AmountBox
                      name={`${item.prefix}_cure`}
                      label={FORM_122A2_LINE_34_CURE}
                      value={item.answers.cure}
                      onChange={(value) => changeDebt(item.key, { cure: value })}
                    />
                  )}
                </div>
              ))}
        </div>

        {information !== null && information.line_35 !== null && (
          <p className="form-help-text">
            {fill(MEANS_LINE_35, { amount: dollars(information.line_35) })}
          </p>
        )}

        <div className="means-line">
          <YesNoQuestion
            question={FORM_122A2_LINE_36}
            name="means_line_36"
            value={answers.line_36_answer}
            onChange={(next) => setAnswer('line_36_answer', next)}
          />
          <p className="form-help-text">
            <a
              href="https://www.uscourts.gov/court-programs/bankruptcy/bankruptcy-basics"
              target="_blank"
              rel="noopener noreferrer"
            >
              {MEANS_LINE_36_LINK}
            </a>
          </p>
          {information && (
            <>
              <p className="form-help-text">
                {fill(MEANS_LINE_36_LIMITS, {
                  date: formatIsoDate(information.limits.effective_date),
                  unsecured: wholeDollars(information.limits.unsecured),
                  secured: wholeDollars(information.limits.secured),
                })}
              </p>
              <p className="form-help-text">
                {fill(MEANS_LINE_36_TOTALS, {
                  ef: dollars(information.totals.unsecured),
                  d: dollars(information.totals.secured),
                })}
              </p>
            </>
          )}
          <p className="form-help-text">{MEANS_LINE_36_OTHER_RULES}</p>
          {answers.line_36_answer === 'yes' && (
            <>
              <AmountBox
                name="means_line_36_payment"
                label={FORM_122A2_LINE_36_PAYMENT}
                value={answers.line_36_payment}
                onChange={(value) => setAmount('line_36_payment', value)}
              />
              {information && (
                <>
                  <p className="form-help-text">
                    {fill(MEANS_LINE_36_MULTIPLIER, { m: information.multiplier })}
                  </p>
                  {answers.line_36_payment !== null && (
                    <p className="form-help-text">
                      {fill(MEANS_LINE_36_PRODUCT, {
                        m: information.multiplier,
                        payment: dollars(answers.line_36_payment),
                        product: dollars(
                          planProduct(answers.line_36_payment, information.multiplier)
                        ),
                      })}
                    </p>
                  )}
                </>
              )}
            </>
          )}
        </div>

        <div className="means-line">
          <Line43
            answers={answers}
            onChange={(change) =>
              edit((current) => ({ ...current, answers: change(current.answers) }))
            }
            outcome={page.outcome}
            line39c={information?.line_39c ?? null}
            savedAbove={aboveLine43(state) === savedAboveCopy}
            refusals={fieldErrors}
            clearRefusal={clearFieldError}
            nextKey={nextKey}
            legendRef={line43Ref}
          />
        </div>
      </fieldset>

      {/* A status, not an alert. It stays mounted because a screen reader may not read a status
          region that arrives with its text. */}
      {gapRegion(gapText)}

      {error && (
        <div className="filing-fee-error" role="alert">
          <p>{error}</p>
        </div>
      )}

      <Button type="button" onClick={handleContinue} disabled={isSaving}>
        Continue
      </Button>
    </main>
  );
}
