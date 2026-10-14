/**
 * ContractsStep - Executory contracts and unexpired leases (Schedule G)
 *
 * Lists contracts/leases the debtor is party to. Each entry needs
 * counterparty name, type, and description. The wizard saves the whole
 * list when the filer presses Continue (DIG-147).
 */

import { useState, useEffect, useMemo } from 'react';
import { Button } from '../../common';
import type { ExecutoryContract } from '../../../types/api';

interface ContractsStepProps {
  initialData?: ExecutoryContract[];
  onDataChange: (data: ExecutoryContract[]) => void;
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

export function ContractsStep({
  initialData,
  onDataChange,
  onValidationChange,
}: ContractsStepProps) {
  const [contracts, setContracts] = useState<ExecutoryContract[]>(initialData ?? []);

  // A row left blank is not saved; a row the filer started needs the other party's name
  const errors = useMemo(
    () =>
      contracts.map((contract) =>
        !contract.counterparty_name.trim() && contract.description.trim()
          ? 'Please enter the name of the other party'
          : undefined
      ),
    [contracts]
  );
  const isValid = errors.every((error) => !error);

  // Update parent when contracts change
  useEffect(() => {
    onDataChange(contracts);
    onValidationChange(isValid);
    // both callbacks are useState setters in IntakeWizard — stable identities
  }, [contracts, isValid, onDataChange, onValidationChange]);

  const addContract = () => {
    setContracts([...contracts, { ...EMPTY_CONTRACT }]);
  };

  const updateContract = (index: number, field: keyof ExecutoryContract, value: string) => {
    const updated = [...contracts];
    updated[index] = { ...updated[index], [field]: value };
    setContracts(updated);
  };

  const removeContract = (index: number) => {
    setContracts(contracts.filter((_, i) => i !== index));
  };

  return (
    <div className="contracts-step">
      <h2 className="text-lg font-semibold mb-4">Contracts & Leases</h2>
      <p className="text-gray-600 mb-4">
        List any executory contracts or unexpired leases you are a party to. These are contracts
        where both sides still have obligations to perform.
      </p>

      {contracts.length === 0 && (
        <p className="text-gray-500 italic mb-4">
          No contracts or leases added yet. Click &quot;Add Contract&quot; to begin.
        </p>
      )}

      {contracts.map((contract, index) => (
        <div key={index} className="border rounded p-4 mb-4">
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
              <label className="block text-sm font-medium mb-1">Type</label>
              <select
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
            <label className="block text-sm font-medium mb-1">Description</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              value={contract.description}
              onChange={(e) => updateContract(index, 'description', e.target.value)}
              placeholder="e.g., Apartment lease, car loan"
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
