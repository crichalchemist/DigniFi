/**
 * CodebtorsStep - Codebtor information (Schedule H)
 *
 * Asks Schedule H's first question and its line 2 (community property), then lists the people who
 * are jointly liable on debts with the debtor: each one's name, address, relationship and the
 * amounts owed or contracts they share. The wizard holds the list and the answers, autosaves them
 * while the step has a gap too, and saves them on Continue (DIG-147). Continue waits for the
 * step's gaps, in Complete's words (codebtorGaps.ts).
 */

import { useEffect } from 'react';
import { Button, FormField, FormSelect } from '../../common';
import {
  CHOOSE_ONE,
  CODEBTORS_STEP_WHY,
  CODEBTOR_ADDRESS_HELP,
  CODEBTOR_GAP_NO_NAME,
  CODEBTOR_LINKS_CONTRACTS,
  CODEBTOR_LINKS_DEBTS,
  CODEBTOR_LINKS_HELP,
  CODEBTOR_LINKS_NONE,
  NAMELESS_CONTRACT,
  NAMELESS_DEBT,
} from '../../../constants/copy';
import {
  SCHEDULE_H_COLUMN_2,
  SCHEDULE_H_LINE_1_QUESTION,
  SCHEDULE_H_LINE_2_NAME_LABEL,
  SCHEDULE_H_LINE_2_PERSON_LEAD,
  SCHEDULE_H_LINE_2_QUESTION,
  SCHEDULE_H_LINE_2_SPOUSE_QUESTION,
  SCHEDULE_H_LINE_2_STATE_LABEL,
} from '../../../constants/formText';
import { isBlankCodebtor, keptRows } from '../../../utils/claimRows';
import { YesNoField } from './YesNoQuestion';
import { AddressFields } from './claims/AddressFields';
import { claimRowName, linkIsLive, type AddressValue } from './claims/claimNames';
import { firstCodebtorGap, spouseAddress } from './claims/codebtorGaps';
import type {
  ClaimAnswers,
  CodebtorLink,
  CodebtorRow,
  ContractRow,
  DebtRow,
} from '../../../types/api';

interface CodebtorsStepProps {
  rows: CodebtorRow[];
  onRowsChange: (rows: CodebtorRow[]) => void;
  /** The claim answers: Schedule H's first question and its line 2 */
  answers: ClaimAnswers;
  /** Takes the whole object, merged */
  onAnswersChange: (answers: ClaimAnswers) => void;
  /** The wizard's amounts owed and contracts, for the links a codebtor can name */
  debts: DebtRow[];
  contracts: ContractRow[];
  onValidationChange: (isValid: boolean) => void;
}

const RELATIONSHIPS = [
  { value: 'spouse', label: 'Spouse' },
  { value: 'former_spouse', label: 'Former Spouse' },
  { value: 'relative', label: 'Relative' },
  { value: 'friend', label: 'Friend' },
  { value: 'business_partner', label: 'Business Partner' },
  { value: 'other', label: 'Other' },
];

// The last new row's key: unique while the page is open, and the prefix keeps it apart from a
// loaded row's key, which is its id
let nextKey = 0;

function newCodebtor(): CodebtorRow {
  return {
    _key: `new-${++nextKey}`,
    name: '',
    street_address: '',
    street_2: '',
    city: '',
    state: '',
    zip_code: '',
    outside_us: false,
    relationship: '',
    links: [],
  };
}

const requiredMark = (
  <span className="required-indicator" aria-label="required">
    *
  </span>
);

export function CodebtorsStep({
  rows,
  onRowsChange,
  answers,
  onAnswersChange,
  debts,
  contracts,
  onValidationChange,
}: CodebtorsStepProps) {
  const gap = firstCodebtorGap(rows, answers, debts, contracts);
  const isValid = gap === null;
  useEffect(() => onValidationChange(isValid), [isValid, onValidationChange]);

  // No answer hides the rows the filer made: a No beside rows must show them, or the gap that
  // names them would point at nothing
  const showRows = answers.codebtors_answer === 'yes' || keptRows(rows, isBlankCodebtor).length > 0;
  const lived = answers.community_lived === 'yes';
  const withSpouse = lived && answers.community_spouse_lived_with === 'yes';

  const setAnswers = (changes: ClaimAnswers) => onAnswersChange({ ...answers, ...changes });

  const updateCodebtor = (index: number, changes: Partial<CodebtorRow>) =>
    onRowsChange(rows.map((row, i) => (i === index ? { ...row, ...changes } : row)));

  const liveLinks = (row: CodebtorRow): CodebtorLink[] =>
    (row.links ?? []).filter((link) =>
      linkIsLive(link.id, link.kind === 'debt' ? debts : contracts)
    );

  const toggleLink = (index: number, link: CodebtorLink, checked: boolean) => {
    const others = liveLinks(rows[index]).filter(
      (held) => !(held.kind === link.kind && held.id === link.id)
    );
    updateCodebtor(index, { links: checked ? [...others, link] : others });
  };

  const writeSpouseAddress = (changes: Partial<AddressValue>) =>
    setAnswers(
      Object.fromEntries(
        Object.entries(changes).map(([key, value]) => [`community_spouse_${key}`, value])
      ) as ClaimAnswers
    );

  const debtsWithId = debts.filter((debt) => debt.id !== undefined);
  const contractsWithId = contracts.filter((contract) => contract.id !== undefined);

  return (
    <div className="codebtors-step">
      <h2 className="text-lg font-semibold mb-4">Codebtors</h2>
      <p className="text-gray-600 mb-4">List anyone who is jointly liable on any of your debts.</p>
      <p className="text-gray-600 mb-4">{CODEBTORS_STEP_WHY}</p>

      <YesNoField
        legend={SCHEDULE_H_LINE_1_QUESTION}
        name="codebtors_answer"
        answer={answers.codebtors_answer}
        onAnswer={(value) => setAnswers({ codebtors_answer: value })}
        required
      />

      <YesNoField
        legend={SCHEDULE_H_LINE_2_QUESTION}
        name="community_lived"
        answer={answers.community_lived}
        onAnswer={(value) => setAnswers({ community_lived: value })}
        required
      />
      {lived && (
        <YesNoField
          legend={SCHEDULE_H_LINE_2_SPOUSE_QUESTION}
          name="community_spouse_lived_with"
          answer={answers.community_spouse_lived_with}
          onAnswer={(value) => setAnswers({ community_spouse_lived_with: value })}
          required
        />
      )}
      {withSpouse && (
        <>
          <FormField
            label={SCHEDULE_H_LINE_2_STATE_LABEL}
            name="community_state"
            type="text"
            maxLength={100}
            required
            value={answers.community_state ?? ''}
            onChange={(e) => setAnswers({ community_state: e.target.value })}
          />
          <p className="text-gray-600 mb-2">{SCHEDULE_H_LINE_2_PERSON_LEAD}</p>
          <FormField
            label={SCHEDULE_H_LINE_2_NAME_LABEL}
            name="community_spouse_name"
            type="text"
            maxLength={255}
            required
            value={answers.community_spouse_name ?? ''}
            onChange={(e) => setAnswers({ community_spouse_name: e.target.value })}
          />
          <AddressFields
            prefix="community_spouse_"
            value={spouseAddress(answers)}
            onChange={writeSpouseAddress}
            required
          />
        </>
      )}

      {showRows &&
        rows.map((codebtor, index) => {
          const nameGap =
            codebtor.name.trim() === '' && !isBlankCodebtor(codebtor)
              ? CODEBTOR_GAP_NO_NAME
              : undefined;
          const nameId = `field-codebtor_name_${index}`;
          const live = liveLinks(codebtor);
          const isChecked = (kind: CodebtorLink['kind'], id: number) =>
            live.some((link) => link.kind === kind && link.id === id);
          const linkBox = (kind: CodebtorLink['kind'], id: number, label: string) => (
            <label key={`${kind}-${id}`} className="fee-waiver-checkbox">
              <input
                type="checkbox"
                name={`codebtor_links_${index}`}
                value={`${kind}-${id}`}
                checked={isChecked(kind, id)}
                onChange={(e) => toggleLink(index, { kind, id }, e.target.checked)}
              />{' '}
              {label}
            </label>
          );
          return (
            <div key={codebtor._key} className="border rounded p-4 mb-4">
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <label htmlFor={nameId} className="block text-sm font-medium mb-1">
                    Full Name {requiredMark}
                  </label>
                  <input
                    id={nameId}
                    name={`codebtor_name_${index}`}
                    type="text"
                    className="w-full border rounded px-3 py-2"
                    value={codebtor.name}
                    onChange={(e) => updateCodebtor(index, { name: e.target.value })}
                    placeholder="e.g., Jane Smith"
                    maxLength={255}
                    aria-required="true"
                    aria-describedby={nameGap ? `${nameId}-error` : undefined}
                    aria-invalid={nameGap ? 'true' : 'false'}
                  />
                  {nameGap && (
                    <p id={`${nameId}-error`} className="form-error">
                      {nameGap}
                    </p>
                  )}
                </div>
                <FormSelect
                  label="Relationship"
                  name={`codebtor_relationship_${index}`}
                  options={RELATIONSHIPS}
                  placeholder={CHOOSE_ONE}
                  value={codebtor.relationship}
                  onChange={(value) =>
                    updateCodebtor(index, { relationship: value as CodebtorRow['relationship'] })
                  }
                />
              </div>

              {/* Draft until counsel rules on C-9 */}
              <p className="form-help-text">{CODEBTOR_ADDRESS_HELP}</p>
              <AddressFields
                prefix="codebtor_"
                index={index}
                value={codebtor}
                onChange={(changes) => updateCodebtor(index, changes)}
                required
              />

              <fieldset className="form-field">
                <legend className="form-label">
                  {SCHEDULE_H_COLUMN_2} {requiredMark}
                </legend>
                <p className="form-help-text">{CODEBTOR_LINKS_HELP}</p>
                {debtsWithId.length > 0 && (
                  <>
                    <p className="form-label">{CODEBTOR_LINKS_DEBTS}</p>
                    {debtsWithId.map((debt) =>
                      linkBox(
                        'debt',
                        debt.id as number,
                        claimRowName(debt.creditor_name, NAMELESS_DEBT)
                      )
                    )}
                  </>
                )}
                {contractsWithId.length > 0 && (
                  <>
                    <p className="form-label">{CODEBTOR_LINKS_CONTRACTS}</p>
                    {contractsWithId.map((contract) =>
                      linkBox(
                        'contract',
                        contract.id as number,
                        claimRowName(contract.counterparty_name, NAMELESS_CONTRACT)
                      )
                    )}
                  </>
                )}
                {debtsWithId.length === 0 && contractsWithId.length === 0 && (
                  <p className="form-help-text">{CODEBTOR_LINKS_NONE}</p>
                )}
              </fieldset>

              <Button
                variant="outline"
                size="sm"
                onClick={() => onRowsChange(rows.filter((_, i) => i !== index))}
              >
                Remove
              </Button>
            </div>
          );
        })}

      {showRows && (
        <Button
          variant="outline"
          onClick={() => onRowsChange([...rows, newCodebtor()])}
          className="mt-2"
        >
          + Add Codebtor
        </Button>
      )}

      {/* A status, not an alert: a sentence can quote a row's name while it's typed. It stays
          mounted because a screen reader may not read a status region that arrives with its text. */}
      <div role="status">
        {gap !== null && (
          <div className="info-box">
            <p className="info-message">{gap}</p>
          </div>
        )}
      </div>
    </div>
  );
}
