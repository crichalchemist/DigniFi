/**
 * ContractsStep - Executory contracts and unexpired leases (Schedule G)
 *
 * Lists contracts/leases the debtor is party to. Each entry needs
 * counterparty name, type, and description.
 */

import { useState } from 'react';
import { useIntake } from '../../../context/IntakeContext';
import { api } from '../../../api/client';
import { Button } from '../../common';

interface Contract {
  id?: number;
  counterparty_name: string;
  contract_type: string;
  description: string;
}

const CONTRACT_TYPES = [
  { value: 'lease', label: 'Lease' },
  { value: 'contract', label: 'Executory Contract' },
  { value: 'other', label: 'Other' },
];

const EMPTY_CONTRACT: Contract = {
  counterparty_name: '',
  contract_type: 'contract',
  description: '',
};

export function ContractsStep() {
  const { session } = useIntake();
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadContracts = async () => {
    if (!session) return;
    try {
      const data = await api.intake.contracts(session.id);
      setContracts(data);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  };

  // Load on mount
  useState(() => {
    loadContracts();
  });

  const addContract = () => {
    setContracts([...contracts, { ...EMPTY_CONTRACT }]);
  };

  const updateContract = (index: number, field: keyof Contract, value: string) => {
    const updated = [...contracts];
    updated[index] = { ...updated[index], [field]: value };
    setContracts(updated);
  };

  const removeContract = async (index: number) => {
    const contract = contracts[index];
    if (contract.id && session) {
      try {
        await api.intake.deleteContract(session.id, contract.id);
      } catch {
        // ignore
      }
    }
    setContracts(contracts.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    if (!session) return;
    for (const contract of contracts) {
      if (!contract.counterparty_name.trim()) continue;
      if (contract.id) continue; // already saved
      try {
        await api.intake.createContract(session.id, contract);
      } catch {
        // ignore
      }
    }
  };

  if (isLoading) return <div>Loading contracts...</div>;

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
              <label className="block text-sm font-medium mb-1">Counterparty Name</label>
              <input
                type="text"
                className="w-full border rounded px-3 py-2"
                value={contract.counterparty_name}
                onChange={(e) => updateContract(index, 'counterparty_name', e.target.value)}
                placeholder="e.g., Landlord Inc."
              />
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

      {contracts.length > 0 && (
        <div className="mt-4">
          <Button variant="primary" onClick={handleSave}>
            Save Contracts
          </Button>
        </div>
      )}
    </div>
  );
}
