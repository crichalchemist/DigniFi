/**
 * ContractsStep - Executory contracts and unexpired leases (Schedule G)
 *
 * Lists contracts/leases the debtor is party to. Each entry needs
 * counterparty name, type, and description. The wizard holds the list, autosaves
 * it while the step can continue, and saves it on Continue (DIG-147).
 */

import { useEffect, useMemo } from 'react';
import { Button } from '../../common';
import type { ContractRow, ExecutoryContract } from '../../../types/api';

interface ContractsStepProps {
  rows: ContractRow[];
  onRowsChange: (rows: ContractRow[]) => void;
  onValidationChange: (isValid: boolean) => void;
}

const CONTRACT_TYPES = [
  { value: 'lease', label: 'Lease' },
  { value: 'contract', label: 'Executory Contract' },
  { value: 'other', label: 'Other' },
];

const EMPTY_CONTRACT: ExecutoryContract = {
  counterparty_name: '',
  contract_type: 'contract',
  description: '',
};

// The last new row's key: unique while the page is open, and the prefix keeps it apart from a
// loaded row's key, which is its id
let nextKey = 0;

export function ContractsStep({ rows, onRowsChange, onValidationChange }: ContractsStepProps) {
  // A row left blank is not saved; a row the filer started needs the other party's name. A
  // stored row can't lose its name: the list save deletes a stored row it leaves out
  const errors = useMemo(
    () =>
      rows.map((row) =>
        !row.counterparty_name.trim() && (row.id !== undefined || row.description.trim())
          ? 'Please enter the name of the other party'
          : undefined
      ),
    [rows]
  );
  const isValid = errors.every((error) => !error);

  useEffect(() => onValidationChange(isValid), [isValid, onValidationChange]);

  const addContract = () => {
    onRowsChange([...rows, { _key: `new-${++nextKey}`, ...EMPTY_CONTRACT }]);
  };

  const updateContract = (index: number, field: keyof ExecutoryContract, value: string) => {
    const updated = [...rows];
    updated[index] = { ...updated[index], [field]: value };
    onRowsChange(updated);
  };

  const removeContract = (index: number) => {
    onRowsChange(rows.filter((_, i) => i !== index));
  };

  return (
    <div className="contracts-step">
      <h2 className="text-lg font-semibold mb-4">Contracts & Leases</h2>
      <p className="text-gray-600 mb-4">
        List any executory contracts or unexpired leases you are a party to. These are contracts
        where both sides still have obligations to perform.
      </p>

      {rows.length === 0 && (
        <p className="text-gray-500 italic mb-4">
          No contracts or leases added yet. Click &quot;Add Contract&quot; to begin.
        </p>
      )}

      {rows.map((contract, index) => (
        <div key={contract._key} className="border rounded p-4 mb-4">
          <div className="grid grid-cols-2 gap-4 mb-3">
            <div>
              <label
                htmlFor={`field-counterparty_name_${index}`}
                className="block text-sm font-medium mb-1"
              >
                Counterparty Name
              </label>
              <input
                id={`field-counterparty_name_${index}`}
                type="text"
                className="w-full border rounded px-3 py-2"
                value={contract.counterparty_name}
                onChange={(e) => updateContract(index, 'counterparty_name', e.target.value)}
                placeholder="e.g., Landlord Inc."
                maxLength={255}
                aria-describedby={
                  errors[index] ? `field-counterparty_name_${index}-error` : undefined
                }
                aria-invalid={errors[index] ? 'true' : 'false'}
              />
              {errors[index] && (
                <p
                  id={`field-counterparty_name_${index}-error`}
                  className="form-error"
                  role="alert"
                  aria-live="assertive"
                >
                  {errors[index]}
                </p>
              )}
            </div>
            <div>
              <label
                htmlFor={`field-contract_type_${index}`}
                className="block text-sm font-medium mb-1"
              >
                Type
              </label>
              <select
                id={`field-contract_type_${index}`}
                className="w-full border rounded px-3 py-2"
                value={contract.contract_type}
                onChange={(e) => updateContract(index, 'contract_type', e.target.value)}
              >
                {CONTRACT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="mb-3">
            <label
              htmlFor={`field-description_${index}`}
              className="block text-sm font-medium mb-1"
            >
              Description
            </label>
            {/* Draft until counsel rules on C-17 (DIG-280) */}
            <input
              id={`field-description_${index}`}
              type="text"
              className="w-full border rounded px-3 py-2"
              value={contract.description}
              onChange={(e) => updateContract(index, 'description', e.target.value)}
              placeholder="e.g., Apartment lease, car lease"
            />
          </div>
          <Button variant="outline" size="sm" onClick={() => removeContract(index)}>
            Remove
          </Button>
        </div>
      ))}

      <Button variant="outline" onClick={addContract} className="mt-2">
        + Add Contract
      </Button>
    </div>
  );
}
