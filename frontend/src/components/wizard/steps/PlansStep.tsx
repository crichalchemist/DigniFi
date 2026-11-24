/**
 * Your Plans (forms step 4e): Form 108's questions, in the form's words. For each confirmed secured
 * debt, the form's four choices and "I haven't decided yet."; for each lease of personal property,
 * "Will the lease be assumed?". Nothing is pre-selected, nothing holds Continue (S:334), and every
 * row still open is listed in the step's status region in Review's words.
 *
 * Controlled: the wizard holds the answers by server id (R-SHAPE) and builds the save from the
 * rows this step shows (plansBody).
 */
import { useEffect, useState, type ChangeEvent } from 'react';
import { Button, FormTextarea } from '../../common';
import { tooLongNote } from '../../../constants/claimTextLimits';
import {
  HIDDEN_ANSWERS,
  NAMELESS_CONTRACT,
  NAMELESS_DEBT,
  PLANS_DEADLINE_LABEL,
  PLANS_EXEMPT_LATER,
  PLANS_EXEMPT_LISTED,
  PLANS_EXEMPT_NO_PROPERTY,
  PLANS_EXEMPT_NOT_CLAIMING,
  PLANS_EXEMPT_NOT_NAMED,
  PLANS_EXPLAIN_LABEL,
  PLANS_FROM_CONTRACTS,
  PLANS_FROM_DEBTS,
  PLANS_INTRO,
  PLANS_NOT_APPLICABLE,
  PLANS_TITLE,
  PLANS_UNDECIDED,
  PLANS_UNDECIDED_INFO,
} from '../../../constants/copy';
import {
  FORM_108_ASSUME_SENTENCE,
  FORM_108_ASSUMED,
  FORM_108_ASSUMED_QUESTION,
  FORM_108_CREDITOR_LABEL,
  FORM_108_DEADLINE,
  FORM_108_EXEMPT_QUESTION,
  FORM_108_INTENTION_QUESTION,
  FORM_108_INTENTIONS,
  FORM_108_LEASED_PROPERTY_LABEL,
  FORM_108_LESSOR_LABEL,
  FORM_108_PART_1_HEADING,
  FORM_108_PART_2_HEADING,
  FORM_108_PROPERTY_LABEL,
} from '../../../constants/formText';
import { claimRowName } from './claims/claimNames';
import { HiddenLine } from './petition/PetitionQuestions';
import {
  LeaseDefinition,
  SecuredDefinitions,
  leasePlanRows,
  openPlanRows,
  securedPlanRows,
} from './plans';
import type {
  Assumed,
  ContractRow,
  DebtRow,
  ExemptState,
  Intention,
  IntentionAnswers,
} from '../../../types/api';

interface PlansStepProps {
  debts: DebtRow[];
  contracts: ContractRow[];
  answers: IntentionAnswers;
  onAnswersChange: (next: IntentionAnswers) => void;
  /** Each secured debt's exempt state by id, from the session read (R-EXEMPT, 4e-R6) */
  exempt: Record<string, ExemptState>;
  onGoToStep: (key: string) => void;
  /** Always true: the step has no gate (S:334) */
  onValidationChange: (valid: boolean) => void;
}

// The record's hard ceiling on the words (IntentionAnswers.TEXT_CEILING, 4e-R17): the measured cap
// is a note beside the box, never a limit on it (R-EXPLAIN)
const EXPLAIN_CEILING = 500;

const INTENTIONS = Object.keys(FORM_108_INTENTIONS) as (keyof typeof FORM_108_INTENTIONS)[];
const ASSUMED = Object.keys(FORM_108_ASSUMED) as (keyof typeof FORM_108_ASSUMED)[];

const EXEMPT_SENTENCES: Record<ExemptState, string> = {
  listed: PLANS_EXEMPT_LISTED,
  not_claiming: PLANS_EXEMPT_NOT_CLAIMING,
  later: PLANS_EXEMPT_LATER,
  not_named: PLANS_EXEMPT_NOT_NAMED,
  no_property: PLANS_EXEMPT_NO_PROPERTY,
};

// The two step names in PLANS_NOT_APPLICABLE, each a way back to its step
const DEBTS_PHRASE = 'Amounts Owed';
const CONTRACTS_PHRASE = 'Contracts & Leases';

export function PlansStep({
  debts,
  contracts,
  answers,
  onAnswersChange,
  exempt,
  onGoToStep,
  onValidationChange,
}: PlansStepProps) {
  // Words kept under another choice the filer asked to see again, by debt id
  const [shown, setShown] = useState<Record<string, boolean>>({});
  useEffect(() => onValidationChange(true), [onValidationChange]);

  const secured = securedPlanRows(debts);
  const leases = leasePlanRows(contracts);

  const setSecured = (id: string, entry: { intention?: Intention; explain?: string }) =>
    onAnswersChange({ ...answers, secured: { ...answers.secured, [id]: entry } });
  const setLease = (id: string, assumed: Assumed) =>
    onAnswersChange({ ...answers, leases: { ...answers.leases, [id]: { assumed } } });

  if (secured.length === 0 && leases.length === 0) {
    const [before, rest] = PLANS_NOT_APPLICABLE.split(DEBTS_PHRASE);
    const [middle, after] = rest.split(CONTRACTS_PHRASE);
    return (
      <div className="plans-step">
        <h3 className="section-title">{PLANS_TITLE}</h3>
        <p>
          {before}
          <Button variant="text" size="sm" type="button" onClick={() => onGoToStep('debts')}>
            {DEBTS_PHRASE}
          </Button>
          {middle}
          <Button variant="text" size="sm" type="button" onClick={() => onGoToStep('contracts')}>
            {CONTRACTS_PHRASE}
          </Button>
          {after}
        </p>
      </div>
    );
  }

  const open = openPlanRows(answers, secured, leases);

  return (
    <div className="plans-step">
      <h3 className="section-title">{PLANS_TITLE}</h3>
      <p className="section-description">{PLANS_INTRO}</p>
      <p className="form-help-text">{PLANS_UNDECIDED_INFO}</p>
      <p className="form-help-text">{PLANS_DEADLINE_LABEL}</p>
      <blockquote>{FORM_108_DEADLINE}</blockquote>

      {secured.length > 0 && (
        <section className="form-section">
          <h4 className="section-title">{FORM_108_PART_1_HEADING}</h4>
          <p>{FORM_108_INTENTION_QUESTION}</p>
          <SecuredDefinitions />
          {secured.map((debt, index) => {
            const id = String(debt.id);
            const entry = answers.secured?.[id] ?? {};
            const name = claimRowName(debt.creditor_name, NAMELESS_DEBT);
            const explaining = entry.intention === 'retain_explain';
            const kept = !explaining && (entry.explain ?? '').trim() !== '';
            const boxName = `plans_secured_${index}_explain`;
            const note = explaining ? tooLongNote('explain', debt, entry.explain) : null;
            const state = exempt[id];
            return (
              <fieldset key={debt._key} className="plans-row">
                <legend>{name}</legend>
                <p className="form-help-text">{PLANS_FROM_DEBTS}</p>
                <p>
                  <span className="form-label">{FORM_108_CREDITOR_LABEL}</span> {name}
                </p>
                <p>
                  <span className="form-label">{FORM_108_PROPERTY_LABEL}</span>{' '}
                  {debt.collateral_description ?? ''}
                </p>
                {INTENTIONS.map((choice) => (
                  <label key={choice} className="ab-choice">
                    <input
                      type="radio"
                      name={`plans_secured_${index}_intention`}
                      value={choice}
                      checked={entry.intention === choice}
                      onChange={() => {
                        setShown((current) => ({ ...current, [id]: false }));
                        setSecured(id, { ...entry, intention: choice });
                      }}
                    />
                    {FORM_108_INTENTIONS[choice]}
                  </label>
                ))}
                <label className="ab-choice">
                  <input
                    type="radio"
                    name={`plans_secured_${index}_intention`}
                    value="undecided"
                    checked={entry.intention === 'undecided'}
                    onChange={() => {
                      setShown((current) => ({ ...current, [id]: false }));
                      setSecured(id, { ...entry, intention: 'undecided' });
                    }}
                  />
                  {PLANS_UNDECIDED}
                </label>
                {explaining || shown[id] ? (
                  <>
                    <FormTextarea
                      label={PLANS_EXPLAIN_LABEL}
                      name={boxName}
                      value={entry.explain ?? ''}
                      maxLength={EXPLAIN_CEILING}
                      rows={2}
                      onChange={(e: ChangeEvent<HTMLTextAreaElement>) =>
                        setSecured(id, { ...entry, explain: e.target.value })
                      }
                      aria-describedby={note ? `field-${boxName}-note` : undefined}
                    />
                    {note && (
                      <p id={`field-${boxName}-note`} className="form-help-text">
                        {note}
                      </p>
                    )}
                  </>
                ) : (
                  kept && (
                    <HiddenLine
                      sentence={HIDDEN_ANSWERS}
                      onShow={() => setShown((current) => ({ ...current, [id]: true }))}
                      onDelete={() => {
                        const rest = { ...entry };
                        delete rest.explain;
                        setSecured(id, rest);
                      }}
                    />
                  )
                )}
                {state && (
                  <>
                    <p>
                      <span className="form-label">{FORM_108_EXEMPT_QUESTION}</span>
                    </p>
                    <p className="form-help-text">{EXEMPT_SENTENCES[state]}</p>
                  </>
                )}
              </fieldset>
            );
          })}
        </section>
      )}

      {leases.length > 0 && (
        <section className="form-section">
          <h4 className="section-title">{FORM_108_PART_2_HEADING}</h4>
          <p>{FORM_108_ASSUME_SENTENCE}</p>
          <p>{FORM_108_ASSUMED_QUESTION}</p>
          <LeaseDefinition />
          {leases.map((contract, index) => {
            const id = String(contract.id);
            const assumed = answers.leases?.[id]?.assumed;
            const name = claimRowName(contract.counterparty_name, NAMELESS_CONTRACT);
            return (
              <fieldset key={contract._key} className="plans-row">
                <legend>{name}</legend>
                <p className="form-help-text">{PLANS_FROM_CONTRACTS}</p>
                <p>
                  <span className="form-label">{FORM_108_LESSOR_LABEL}</span> {name}
                </p>
                <p>
                  <span className="form-label">{FORM_108_LEASED_PROPERTY_LABEL}</span>{' '}
                  {contract.description}
                </p>
                {[...ASSUMED, 'undecided' as const].map((answer) => (
                  <label key={answer} className="ab-choice">
                    <input
                      type="radio"
                      name={`plans_lease_${index}_assumed`}
                      value={answer}
                      checked={assumed === answer}
                      onChange={() => setLease(id, answer)}
                    />
                    {answer === 'undecided' ? PLANS_UNDECIDED : FORM_108_ASSUMED[answer]}
                  </label>
                ))}
              </fieldset>
            );
          })}
        </section>
      )}

      <div role="status">
        {open.map((sentence, index) => (
          <p key={index}>{sentence}</p>
        ))}
      </div>
    </div>
  );
}
