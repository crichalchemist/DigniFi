/**
 * ContractsStep - Executory contracts and unexpired leases (Schedule G)
 *
 * Asks Schedule G's first question, then lists the contracts and leases the filer is party to,
 * with the other party's address and what Schedule G asks of each. The wizard holds the list and
 * the answer, autosaves them while the step has a gap too, and saves them on Continue (DIG-147).
 * Continue waits for the step's gaps, in Complete's words (contractGaps.ts).
 */

import { useCallback, useEffect, useState } from 'react';
import { Button, FormField, FormSelect } from '../../common';
import {
  CHOOSE_ONE,
  CONTRACTS_STEP_WHY,
  CONTRACT_ADDRESS_HELP,
  CONTRACT_GAP_NO_NAME,
  GO_TO_AMOUNTS_OWED,
  LEASE_KIND_LABEL,
  LEASE_PAYMENT_LABEL,
  NAMELESS_DEBT,
  OWES_NOW_ADD_HELP,
  OWES_NOW_PICK_LABEL,
  OWES_NOW_QUESTION,
  VEHICLE_LEASE_HELP,
  VEHICLE_LEASE_LABEL,
} from '../../../constants/copy';
import {
  SCHEDULE_G_LINE_1_QUESTION,
  SCHEDULE_G_NAME_LABEL,
  SCHEDULE_G_PURPOSE_LABEL,
} from '../../../constants/formText';
import { CONTRACT_TYPE_WORDS, LEASE_KIND_WORDS } from '../../../constants/claims';
import { WIZARD_STEPS } from '../../../constants/wizardSteps';
import { isBlankContract, keptRows } from '../../../utils/claimRows';
import { YesNoField } from './YesNoQuestion';
import { AddressFields } from './claims/AddressFields';
import { AmountBox } from './claims/AmountBox';
import { assetLabel, claimRowName } from './claims/claimNames';
import { firstContractGap } from './claims/contractGaps';
import type { AssetInfo, ContractRow, DebtRow, WizardRow, YesNo } from '../../../types/api';

interface ContractsStepProps {
  rows: ContractRow[];
  onRowsChange: (rows: ContractRow[]) => void;
  /** Schedule G's first question: null while unanswered */
  answer: YesNo | null;
  onAnswerChange: (answer: YesNo) => void;
  /** The wizard's amounts owed and assets, for the links a contract can name */
  debts: DebtRow[];
  assets: WizardRow<AssetInfo>[];
  onValidationChange: (isValid: boolean) => void;
  /** Moves the wizard to a step by its number, saving nothing */
  onGoToStep: (stepNumber: number) => void;
}

const CONTRACT_TYPES = Object.entries(CONTRACT_TYPE_WORDS).map(([value, label]) => ({
  value,
  label,
}));

const LEASE_KIND_OPTIONS = Object.entries(LEASE_KIND_WORDS).map(([value, label]) => ({
  value,
  label,
}));

const DEBTS_STEP_NUMBER = WIZARD_STEPS.find((step) => step.key === 'debts')!.number;

// The last new row's key: unique while the page is open, and the prefix keeps it apart from a
// loaded row's key, which is its id
let nextKey = 0;

function newContract(): ContractRow {
  return {
    _key: `new-${++nextKey}`,
    counterparty_name: '',
    contract_type: '',
    description: '',
    street_address: '',
    street_2: '',
    city: '',
    state: '',
    zip_code: '',
    outside_us: false,
    lease_kind: null,
    monthly_payment: null,
    vehicle_asset: null,
    owes_now: null,
    owed_debt: null,
  };
}

const requiredMark = (
  <span className="required-indicator" aria-label="required">
    *
  </span>
);

const idOrNull = (value: string) => (value === '' ? null : Number(value));

export function ContractsStep({
  rows,
  onRowsChange,
  answer,
  onAnswerChange,
  debts,
  assets,
  onValidationChange,
  onGoToStep,
}: ContractsStepProps) {
  // A box holding only part of a number keeps the row's figure without showing it
  const [partialBoxes, setPartialBoxes] = useState(0);
  const countPartialBox = useCallback(
    (change: 1 | -1) => setPartialBoxes((count) => count + change),
    []
  );

  const gap = firstContractGap(rows, answer, debts, assets);
  const isValid = gap === null && partialBoxes === 0;
  useEffect(() => onValidationChange(isValid), [isValid, onValidationChange]);

  // No answers hide the rows the filer made: a No beside rows must show them, or the gap that
  // names them would point at nothing
  const showRows = answer === 'yes' || keptRows(rows, isBlankContract).length > 0;

  const updateContract = (index: number, changes: Partial<ContractRow>) =>
    onRowsChange(rows.map((row, i) => (i === index ? { ...row, ...changes } : row)));

  const vehicleOptions = (row: ContractRow) =>
    assets
      .filter(
        (asset) =>
          asset.id !== undefined &&
          (asset.id === row.vehicle_asset ||
            ((asset.ab_line === '3' || asset.ab_line === '4') &&
              asset.details?.lives_here !== 'yes'))
      )
      .map((asset) => ({ value: String(asset.id), label: assetLabel(asset) }));

  const debtOptions = debts
    .filter((debt) => debt.id !== undefined)
    .map((debt) => ({
      value: String(debt.id),
      label: claimRowName(debt.creditor_name, NAMELESS_DEBT),
    }));

  return (
    <div className="contracts-step">
      <h2 className="text-lg font-semibold mb-4">Contracts & Leases</h2>
      <p className="text-gray-600 mb-4">
        List any executory contracts or unexpired leases you are a party to. These are contracts
        where both sides still have obligations to perform.
      </p>
      <p className="text-gray-600 mb-4">{CONTRACTS_STEP_WHY}</p>

      <YesNoField
        legend={SCHEDULE_G_LINE_1_QUESTION}
        name="contracts_answer"
        answer={answer}
        onAnswer={onAnswerChange}
        required
      />

      {showRows && rows.length === 0 && (
        <p className="text-gray-500 italic mb-4">
          No contracts or leases added yet. Click &quot;Add Contract&quot; to begin.
        </p>
      )}

      {showRows &&
        rows.map((contract, index) => {
          const nameGap =
            contract.counterparty_name.trim() === '' && !isBlankContract(contract)
              ? CONTRACT_GAP_NO_NAME
              : undefined;
          const nameId = `field-counterparty_name_${index}`;
          const isLease = contract.contract_type === 'lease';
          const isVehicle = isLease && contract.lease_kind === 'vehicle';
          return (
            <div key={contract._key} className="border rounded p-4 mb-4">
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <label htmlFor={nameId} className="block text-sm font-medium mb-1">
                    {SCHEDULE_G_NAME_LABEL} {requiredMark}
                  </label>
                  <input
                    id={nameId}
                    name={`counterparty_name_${index}`}
                    type="text"
                    className="w-full border rounded px-3 py-2"
                    value={contract.counterparty_name}
                    onChange={(e) => updateContract(index, { counterparty_name: e.target.value })}
                    placeholder="e.g., Landlord Inc."
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
                  label="Type"
                  name={`contract_type_${index}`}
                  options={CONTRACT_TYPES}
                  placeholder={CHOOSE_ONE}
                  required
                  value={contract.contract_type}
                  onChange={(value) =>
                    updateContract(index, { contract_type: value as ContractRow['contract_type'] })
                  }
                />
              </div>

              {/* Draft until counsel rules on C-17 (DIG-280) */}
              <FormField
                label={SCHEDULE_G_PURPOSE_LABEL}
                name={`description_${index}`}
                type="text"
                required
                value={contract.description}
                onChange={(e) => updateContract(index, { description: e.target.value })}
                placeholder="e.g., Apartment lease, car lease"
              />

              <p className="form-help-text">{CONTRACT_ADDRESS_HELP}</p>
              <AddressFields
                prefix=""
                index={index}
                value={contract}
                onChange={(changes) => updateContract(index, changes)}
                required
              />

              {isLease && (
                <FormSelect
                  label={LEASE_KIND_LABEL}
                  name={`lease_kind_${index}`}
                  options={LEASE_KIND_OPTIONS}
                  placeholder={CHOOSE_ONE}
                  required
                  value={contract.lease_kind ?? ''}
                  onChange={(value) =>
                    updateContract(index, {
                      lease_kind: (value || null) as ContractRow['lease_kind'],
                    })
                  }
                />
              )}

              {isVehicle && (
                <>
                  <FormSelect
                    label={VEHICLE_LEASE_LABEL}
                    name={`vehicle_asset_${index}`}
                    options={vehicleOptions(contract)}
                    placeholder={CHOOSE_ONE}
                    required
                    helpText={VEHICLE_LEASE_HELP}
                    value={contract.vehicle_asset == null ? '' : String(contract.vehicle_asset)}
                    onChange={(value) => updateContract(index, { vehicle_asset: idOrNull(value) })}
                  />
                  <AmountBox
                    label={LEASE_PAYMENT_LABEL}
                    name={`monthly_payment_${index}`}
                    value={contract.monthly_payment}
                    required
                    maxDigits={10}
                    onValue={(value) => updateContract(index, { monthly_payment: value ?? null })}
                    onPartialBox={countPartialBox}
                  />
                </>
              )}

              {/* Draft until counsel rules on C-9 */}
              <YesNoField
                legend={OWES_NOW_QUESTION}
                name={`owes_now_${index}`}
                answer={contract.owes_now}
                onAnswer={(value) =>
                  updateContract(
                    index,
                    value === 'no' ? { owes_now: 'no', owed_debt: null } : { owes_now: 'yes' }
                  )
                }
                required
              />
              {contract.owes_now === 'yes' && (
                <>
                  <FormSelect
                    label={OWES_NOW_PICK_LABEL}
                    name={`owed_debt_${index}`}
                    options={debtOptions}
                    placeholder={CHOOSE_ONE}
                    required
                    helpText={OWES_NOW_ADD_HELP}
                    value={
                      debtOptions.some((option) => option.value === String(contract.owed_debt))
                        ? String(contract.owed_debt)
                        : ''
                    }
                    onChange={(value) => updateContract(index, { owed_debt: idOrNull(value) })}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    type="button"
                    onClick={() => onGoToStep(DEBTS_STEP_NUMBER)}
                  >
                    {GO_TO_AMOUNTS_OWED}
                  </Button>
                </>
              )}

              <div className="mt-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onRowsChange(rows.filter((_, i) => i !== index))}
                >
                  Remove
                </Button>
              </div>
            </div>
          );
        })}

      {showRows && (
        <Button
          variant="outline"
          onClick={() => onRowsChange([...rows, newContract()])}
          className="mt-2"
        >
          + Add Contract
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
