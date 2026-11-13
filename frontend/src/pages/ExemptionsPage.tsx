import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { api, APIClientError } from '../api/client';
import { Button } from '../components/common';
import { UPLDisclaimer } from '../components/compliance';
import { REQUIRED_MARK } from '../components/wizard/steps/assets/AssetRowFields';
import { UPL_EXEMPTION_DISCLAIMER } from '../constants/upl';
import {
  EXEMPTIONS_LINE_1_QUESTION,
  EXEMPTIONS_LINE_1_WORDS,
  EXEMPTIONS_LINE_3_1_QUESTION,
  EXEMPTIONS_LINE_3_NOTE,
  EXEMPTIONS_LINE_3_QUESTION,
} from '../constants/formText';
import { formatFigure } from '../components/wizard/steps/claims/linkedPayments';
import {
  EXEMPTIONS_ADD_CLAIM,
  EXEMPTIONS_DESCRIPTION_DOESNT_FIT,
  EXEMPTIONS_OTHER_LAW_DOESNT_FIT,
  EXEMPTIONS_CLAIMS_HEADING,
  EXEMPTIONS_FEDERAL_LAWS,
  EXEMPTIONS_ILLINOIS_LAWS,
  EXEMPTIONS_INTRO,
  EXEMPTIONS_LAWS_HEADING,
  EXEMPTIONS_NO_ITEMS,
  EXEMPTIONS_NO_TABLE,
  EXEMPTIONS_NOTE_12_1201,
  EXEMPTIONS_NOTE_DOMICILE,
  EXEMPTIONS_NOT_CLAIMING_BUTTON,
  EXEMPTIONS_READ_FAILED,
  EXEMPTIONS_SAVE_FAILED,
  EXEMPTIONS_TITLE,
  EXEMPTIONS_TOTALS_HEADING,
  EXEMPTION_LAW_SUMMARIES,
  EXEMPTION_NO_LIMIT,
  EXEMPTION_TOTAL_DOLLARS,
  EXEMPTION_TOTAL_FAIR_MARKET,
} from '../constants/copy';
import { ClaimRowFields } from './exemptions/ClaimRowFields';
import { claimAmountError, firstExemptionGap, type ClaimRow } from './exemptions/exemptionGaps';
import { lawTotals } from './exemptions/lawTotals';
import { parseAmount } from '../utils/parseAmount';
import type {
  ExemptionClaim,
  ExemptionItem,
  ExemptionLaw,
  ExemptionLine1,
  Exemptions,
  YesNo,
} from '../types/api';

type Answers = Pick<Exemptions, 'line_1' | 'line_3' | 'line_3_1' | 'no_claims'>;

const LINE_1_CHOICES: ExemptionLine1[] = ['state_and_federal', 'federal'];
const YES_NO: YesNo[] = ['no', 'yes'];

const claimRowOf = (claim: ExemptionClaim, items: ExemptionItem[]): ClaimRow => ({
  _key: `claim-${claim.id}`,
  id: claim.id,
  asset: claim.asset,
  law: claim.law,
  otherLawChosen: claim.law === null && claim.other_law.trim() !== '',
  other_law: claim.other_law,
  amount_kind: claim.amount_kind,
  amount: claim.amount ?? '',
  short_description: claim.short_description ?? '',
  itemGone: !items.some((item) => item.id === claim.asset),
});

// A claim as the PUT takes it: the typed law only while "Another law" is chosen, an amount only
// under a dollar claim, a shorter description only when the property's name doesn't fit
const claimRequestOf = (row: ClaimRow, items: ExemptionItem[]): ExemptionClaim => {
  const item = items.find((candidate) => candidate.id === row.asset);
  const short = row.short_description.trim();
  // To the cent, as the server takes it: "100.000" goes as "100.00" and "-0" as "0.00". Continue
  // waits while claimAmountError refuses the figure, so it has two places at most here.
  const amount = row.amount_kind === 'dollars' ? parseAmount(row.amount) : undefined;
  return {
    id: row.id,
    asset: row.asset,
    law: row.otherLawChosen ? null : row.law,
    other_law: row.otherLawChosen ? row.other_law.trim() : '',
    amount_kind: row.amount_kind,
    amount: amount === undefined ? null : amount.toFixed(2),
    short_description: item && !item.description_fits && short !== '' ? short : null,
  };
};

const blankClaim = (key: string): ClaimRow => ({
  _key: key,
  id: null,
  asset: null,
  law: null,
  otherLawChosen: false,
  other_law: '',
  amount_kind: null,
  amount: '',
  short_description: '',
  itemGone: false,
});

type FitErrors = Record<string, { description?: true; otherLaw?: true }>;

const withoutFit = (current: FitErrors, key: string, field: 'description' | 'otherLaw') => {
  if (!current[key]?.[field]) return current;
  const row = { ...current[key] };
  delete row[field];
  const next = { ...current };
  if (Object.keys(row).length === 0) delete next[key];
  else next[key] = row;
  return next;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

// What a failed save says about the claims sent. `fit` holds the boxes a 400 refuses for a short
// description or a typed law Schedule C can't hold, by row: the body is {claims: {"<index>":
// {short_description: [...], other_law: [...]}}}, the index being the row's place in the list
// sent. `other` is true when the failure says anything else, or names a box the row doesn't
// show: only the save-failed sentence can tell the filer about those.
function readRefusal(
  caught: unknown,
  sent: ClaimRow[],
  items: ExemptionItem[]
): { fit: FitErrors; other: boolean } {
  if (!(caught instanceof APIClientError) || caught.statusCode !== 400 || !caught.body) {
    return { fit: {}, other: true };
  }
  const fit: FitErrors = {};
  let other = false;
  for (const [name, value] of Object.entries(caught.body)) {
    if (name !== 'claims' || !isRecord(value)) {
      other = true;
      continue;
    }
    for (const [index, errors] of Object.entries(value)) {
      const row = sent[Number(index)];
      if (row === undefined || !isRecord(errors)) {
        other = true;
        continue;
      }
      const item = items.find((candidate) => candidate.id === row.asset);
      for (const field of Object.keys(errors)) {
        if (field === 'short_description' && item && !item.description_fits) {
          fit[row._key] = { ...fit[row._key], description: true };
        } else if (field === 'other_law' && row.otherLawChosen) {
          fit[row._key] = { ...fit[row._key], otherLaw: true };
        } else {
          other = true;
        }
      }
    }
  }
  return { fit, other };
}

function LawList({ title, laws }: { title: string; laws: ExemptionLaw[] }) {
  return (
    <>
      <h3>{title}</h3>
      <ul>
        {laws.map((law) => (
          <li key={law.key}>
            <strong>{law.citation}</strong>
            {EXEMPTION_LAW_SUMMARIES[law.key] && <p>{EXEMPTION_LAW_SUMMARIES[law.key]}</p>}
            <p>{law.limit_text || EXEMPTION_NO_LIMIT}</p>
          </li>
        ))}
      </ul>
    </>
  );
}

/**
 * Schedule C's line 1, "not claiming" and line 3 (3g1 spec §5.4). The filer answers every
 * question; nothing is chosen for them. Saves on Continue, then goes to the SOFA step.
 */
export function ExemptionsPage() {
  const navigate = useNavigate();
  const { session } = useIntake();
  const sessionId = session?.id;

  const [saved, setSaved] = useState<Exemptions | null>(null);
  const [answers, setAnswers] = useState<Answers | null>(null);
  const [claims, setClaims] = useState<ClaimRow[]>([]);
  const newClaims = useRef(0);
  const [read, setRead] = useState<'pending' | 'done' | 'failed'>('pending');
  const [readAttempt, setReadAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  // The server's refusals of a short description or a typed law, by row and then by field
  const [fitErrors, setFitErrors] = useState<
    Record<string, { description?: true; otherLaw?: true }>
  >({});

  // The questions wait for the saved answers: a blank page sent over them would undo them
  useEffect(() => {
    if (sessionId == null) return;
    let cancelled = false;
    api.intake.exemptions
      .get(sessionId)
      .then((loaded) => {
        if (cancelled) return;
        setSaved(loaded);
        setClaims(loaded.claims.map((claim) => claimRowOf(claim, loaded.items)));
        setAnswers({
          line_1: loaded.line_1,
          line_3: loaded.line_3,
          line_3_1: loaded.line_3_1,
          no_claims: loaded.no_claims,
        });
        setRead('done');
      })
      .catch(() => {
        if (!cancelled) setRead('failed');
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, readAttempt]);

  const laws = useMemo(() => saved?.catalog?.laws ?? [], [saved]);
  const totals = useMemo(() => lawTotals(claims, laws), [claims, laws]);
  const lawKeys = useMemo(() => new Set(saved?.catalog?.laws.map((law) => law.key) ?? []), [saved]);

  const handleRetry = () => {
    setRead('pending');
    setReadAttempt((attempt) => attempt + 1);
  };

  const set = <K extends keyof Answers>(key: K, value: Answers[K]) =>
    setAnswers((current) => (current ? { ...current, [key]: value } : current));

  const addClaim = () => {
    newClaims.current += 1;
    setClaims((current) => [...current, blankClaim(`new-${newClaims.current}`)]);
    set('no_claims', false);
  };

  const gap = saved && answers ? firstExemptionGap(answers, claims, saved.items, lawKeys) : null;
  // An amount the server would refuse holds Continue too, though it is no gap in the server's list
  const amountRefused = claims.some((row) => claimAmountError(row) !== undefined);
  // A page nobody has touched says nothing yet
  const isStarted =
    answers !== null &&
    (answers.line_1 !== null || answers.line_3 !== null || answers.no_claims || claims.length > 0);

  const handleContinue = async () => {
    if (sessionId == null || !answers || gap !== null || amountRefused) return;
    setIsSaving(true);
    setError(null);
    setFitErrors({});
    // The controls hold still while the save is on its way, so these are the rows on screen
    const sent = claims;
    try {
      // Every claim goes: the server deletes a stored claim that is missing from the list
      await api.intake.exemptions.put(sessionId, {
        line_1: answers.line_1,
        line_3: answers.line_3,
        line_3_1: answers.line_3 === 'yes' ? answers.line_3_1 : null,
        no_claims: answers.no_claims,
        claims: sent.map((row) => claimRequestOf(row, saved?.items ?? [])),
      });
      navigate('/sofa');
    } catch (caught) {
      const { fit, other } = readRefusal(caught, sent, saved?.items ?? []);
      setFitErrors(fit);
      if (other || Object.keys(fit).length === 0) setError(EXEMPTIONS_SAVE_FAILED);
    } finally {
      setIsSaving(false);
    }
  };

  const yesNo = (
    question: string,
    name: string,
    value: YesNo | null,
    onChange: (next: YesNo) => void,
    note?: string
  ) => (
    <fieldset className="form-field fee-waiver-question">
      <legend className="form-label">
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
    </fieldset>
  );

  return (
    <main className="filing-fee-page">
      <h1>{EXEMPTIONS_TITLE}</h1>
      <p>{EXEMPTIONS_INTRO}</p>
      <UPLDisclaimer text={UPL_EXEMPTION_DISCLAIMER} variant="inline" />

      {read === 'failed' && (
        <div className="filing-fee-error">
          <p role="alert">{EXEMPTIONS_READ_FAILED}</p>
          <Button type="button" onClick={handleRetry}>
            Try again
          </Button>
        </div>
      )}

      {read === 'done' && saved && answers && (
        <>
          {/* Every answer holds still while the save is on its way: an edit made meanwhile would
              be lost when the page moves on, and a refusal could name a row no longer shown */}
          <fieldset className="fee-waiver-question" disabled={isSaving}>
            <fieldset className="form-field fee-waiver-question">
              <legend className="form-label">
                {EXEMPTIONS_LINE_1_QUESTION}
                {REQUIRED_MARK}
              </legend>
              <div className="ab-yes-no">
                {LINE_1_CHOICES.map((choice) => (
                  <label key={choice} className="ab-choice ab-answer">
                    <input
                      type="radio"
                      name="exemptions_line_1"
                      value={choice}
                      aria-required
                      checked={answers.line_1 === choice}
                      onChange={() => set('line_1', choice)}
                    />
                    {EXEMPTIONS_LINE_1_WORDS[choice]}
                  </label>
                ))}
              </div>
              <div className="form-help-text">
                <p>{EXEMPTIONS_NOTE_12_1201}</p>
                <p>{EXEMPTIONS_NOTE_DOMICILE}</p>
              </div>
            </fieldset>

            {saved.catalog_gap === 'no_table' && <p>{EXEMPTIONS_NO_TABLE}</p>}

            {saved.catalog && (
              <section aria-labelledby="exemptions-laws-heading">
                <h2 id="exemptions-laws-heading">{EXEMPTIONS_LAWS_HEADING}</h2>
                <LawList
                  title={EXEMPTIONS_ILLINOIS_LAWS}
                  laws={saved.catalog.laws.filter((law) => law.jurisdiction === 'illinois')}
                />
                <LawList
                  title={EXEMPTIONS_FEDERAL_LAWS}
                  laws={saved.catalog.laws.filter((law) => law.jurisdiction === 'federal')}
                />
              </section>
            )}

            <section aria-labelledby="exemptions-claims-heading">
              <h2 id="exemptions-claims-heading">{EXEMPTIONS_CLAIMS_HEADING}</h2>
              {claims.map((row, index) => (
                <ClaimRowFields
                  key={row._key}
                  index={index}
                  row={row}
                  items={saved.items}
                  laws={laws}
                  descriptionError={
                    fitErrors[row._key]?.description ? EXEMPTIONS_DESCRIPTION_DOESNT_FIT : undefined
                  }
                  otherLawError={
                    fitErrors[row._key]?.otherLaw ? EXEMPTIONS_OTHER_LAW_DOESNT_FIT : undefined
                  }
                  onChange={(next) => {
                    // A sentence about a box goes once that box changes
                    if (next.short_description !== row.short_description) {
                      setFitErrors((current) => withoutFit(current, row._key, 'description'));
                    }
                    if (next.other_law !== row.other_law) {
                      setFitErrors((current) => withoutFit(current, row._key, 'otherLaw'));
                    }
                    setClaims((current) => current.map((r) => (r._key === row._key ? next : r)));
                  }}
                  onRemove={() =>
                    setClaims((current) => current.filter((r) => r._key !== row._key))
                  }
                />
              ))}
              {saved.items.length === 0 ? (
                <p>{EXEMPTIONS_NO_ITEMS}</p>
              ) : (
                <Button type="button" variant="outline" onClick={addClaim}>
                  {EXEMPTIONS_ADD_CLAIM}
                </Button>
              )}
            </section>

            {totals.length > 0 && (
              <section aria-labelledby="exemptions-totals-heading">
                <h2 id="exemptions-totals-heading">{EXEMPTIONS_TOTALS_HEADING}</h2>
                <ul>
                  {totals.map((total) => (
                    <li key={`${total.limitText === null ? 'typed' : 'law'}:${total.label}`}>
                      <strong>{total.label}</strong>
                      <p className="exemption-total">
                        {EXEMPTION_TOTAL_DOLLARS.replace(
                          '{amount}',
                          `$${formatFigure(total.dollars)}`
                        )}
                      </p>
                      {total.fairMarketCount > 0 && (
                        <p className="exemption-total">
                          {EXEMPTION_TOTAL_FAIR_MARKET.replace(
                            '{n}',
                            String(total.fairMarketCount)
                          )}
                        </p>
                      )}
                      {total.limitText !== null && (
                        <p className="exemption-total">{total.limitText || EXEMPTION_NO_LIMIT}</p>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {claims.length === 0 && (
              <Button
                variant="outline"
                name="no_exemptions"
                aria-pressed={answers.no_claims}
                onClick={() => set('no_claims', !answers.no_claims)}
              >
                {EXEMPTIONS_NOT_CLAIMING_BUTTON}
              </Button>
            )}

            {yesNo(
              EXEMPTIONS_LINE_3_QUESTION,
              'exemptions_line_3',
              answers.line_3,
              (next) =>
                setAnswers((current) =>
                  current
                    ? {
                        ...current,
                        line_3: next,
                        line_3_1: next === 'no' ? null : current.line_3_1,
                      }
                    : current
                ),
              EXEMPTIONS_LINE_3_NOTE
            )}
            {answers.line_3 === 'yes' &&
              yesNo(EXEMPTIONS_LINE_3_1_QUESTION, 'exemptions_line_3_1', answers.line_3_1, (next) =>
                set('line_3_1', next)
              )}
          </fieldset>

          {/* A status, not an alert. It stays mounted because a screen reader may not read a
              status region that arrives with its text. */}
          <div role="status">
            {gap !== null && isStarted && (
              <div className="info-box">
                <p className="info-message">{gap}</p>
              </div>
            )}
          </div>

          {error && (
            <div className="filing-fee-error" role="alert">
              <p>{error}</p>
            </div>
          )}

          <Button
            type="button"
            onClick={handleContinue}
            disabled={isSaving || gap !== null || amountRefused}
          >
            Continue
          </Button>
        </>
      )}
    </main>
  );
}
