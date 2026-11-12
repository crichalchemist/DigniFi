import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { api } from '../api/client';
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
import {
  EXEMPTIONS_INTRO,
  EXEMPTIONS_NO_TABLE,
  EXEMPTIONS_NOTE_12_1201,
  EXEMPTIONS_NOTE_DOMICILE,
  EXEMPTIONS_NOT_CLAIMING_BUTTON,
  EXEMPTIONS_READ_FAILED,
  EXEMPTIONS_SAVE_FAILED,
  EXEMPTIONS_TITLE,
} from '../constants/copy';
import { firstExemptionGap, type ClaimRow } from './exemptions/exemptionGaps';
import type { ExemptionLine1, Exemptions, YesNo } from '../types/api';

type Answers = Pick<Exemptions, 'line_1' | 'line_3' | 'line_3_1' | 'no_claims'>;

const LINE_1_CHOICES: ExemptionLine1[] = ['state_and_federal', 'federal'];
const YES_NO: YesNo[] = ['no', 'yes'];

// Claims are shown to the gap check only; this page sends none (Task 8 holds and sends them)
const claimRowOf = (claim: Exemptions['claims'][number]): ClaimRow => ({
  _key: String(claim.id),
  id: claim.id,
  asset: claim.asset,
  law: claim.law,
  otherLawChosen: claim.law === null && claim.other_law.trim() !== '',
  other_law: claim.other_law,
  amount_kind: claim.amount_kind,
  amount: claim.amount ?? '',
  short_description: claim.short_description ?? '',
});

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
  const [read, setRead] = useState<'pending' | 'done' | 'failed'>('pending');
  const [readAttempt, setReadAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // The questions wait for the saved answers: a blank page sent over them would undo them
  useEffect(() => {
    if (sessionId == null) return;
    let cancelled = false;
    api.intake.exemptions
      .get(sessionId)
      .then((loaded) => {
        if (cancelled) return;
        setSaved(loaded);
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

  const claims = useMemo(() => (saved ? saved.claims.map(claimRowOf) : []), [saved]);
  const lawKeys = useMemo(() => new Set(saved?.catalog?.laws.map((law) => law.key) ?? []), [saved]);

  const handleRetry = () => {
    setRead('pending');
    setReadAttempt((attempt) => attempt + 1);
  };

  const set = <K extends keyof Answers>(key: K, value: Answers[K]) =>
    setAnswers((current) => (current ? { ...current, [key]: value } : current));

  const gap = saved && answers ? firstExemptionGap(answers, claims, saved.items, lawKeys) : null;
  // A page nobody has touched says nothing yet
  const isStarted =
    answers !== null &&
    (answers.line_1 !== null || answers.line_3 !== null || answers.no_claims || claims.length > 0);

  const handleContinue = async () => {
    if (sessionId == null || !answers || gap !== null) return;
    setIsSaving(true);
    setError(null);
    try {
      // No `claims` key: this page holds none, and `claims: []` would delete the stored ones
      await api.intake.exemptions.put(sessionId, {
        line_1: answers.line_1,
        line_3: answers.line_3,
        line_3_1: answers.line_3 === 'yes' ? answers.line_3_1 : null,
        no_claims: answers.no_claims,
      });
      navigate('/sofa');
    } catch {
      setError(EXEMPTIONS_SAVE_FAILED);
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

          <Button type="button" onClick={handleContinue} disabled={isSaving || gap !== null}>
            Continue
          </Button>
        </>
      )}
    </main>
  );
}
