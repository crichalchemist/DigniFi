/**
 * CodebtorsStep - Codebtor information (Schedule H)
 *
 * Lists people who are jointly liable on debts with the debtor.
 * Typically a spouse in community property states.
 */

import { useState } from 'react';
import { useIntake } from '../../../context/IntakeContext';
import { api } from '../../../api/client';
import { Button } from '../../common';

interface Codebtor {
  id?: number;
  name: string;
  street_address: string;
  city: string;
  state: string;
  zip_code: string;
  relationship: string;
}

const RELATIONSHIPS = [
  { value: 'spouse', label: 'Spouse' },
  { value: 'former_spouse', label: 'Former Spouse' },
  { value: 'relative', label: 'Relative' },
  { value: 'friend', label: 'Friend' },
  { value: 'business_partner', label: 'Business Partner' },
  { value: 'other', label: 'Other' },
];

const EMPTY_CODEBTOR: Codebtor = {
  name: '',
  street_address: '',
  city: '',
  state: '',
  zip_code: '',
  relationship: 'other',
};

export function CodebtorsStep() {
  const { session } = useIntake();
  const [codebtors, setCodebtors] = useState<Codebtor[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadCodebtors = async () => {
    if (!session) return;
    try {
      const data = await api.intake.codebtors(session.id);
      setCodebtors(data);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  };

  useState(() => {
    loadCodebtors();
  });

  const addCodebtor = () => {
    setCodebtors([...codebtors, { ...EMPTY_CODEBTOR }]);
  };

  const updateCodebtor = (index: number, field: keyof Codebtor, value: string) => {
    const updated = [...codebtors];
    updated[index] = { ...updated[index], [field]: value };
    setCodebtors(updated);
  };

  const removeCodebtor = async (index: number) => {
    const codebtor = codebtors[index];
    if (codebtor.id && session) {
      try {
        await api.intake.deleteCodebtor(session.id, codebtor.id);
      } catch {
        // ignore
      }
    }
    setCodebtors(codebtors.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    if (!session) return;
    for (const codebtor of codebtors) {
      if (!codebtor.name.trim()) continue;
      if (codebtor.id) continue;
      try {
        await api.intake.createCodebtor(session.id, codebtor);
      } catch {
        // ignore
      }
    }
  };

  if (isLoading) return <div>Loading codebtors...</div>;

  return (
    <div className="codebtors-step">
      <h2 className="text-lg font-semibold mb-4">Codebtors</h2>
      <p className="text-gray-600 mb-4">
        List anyone who is jointly liable on any of your debts. If you filed jointly with your
        spouse, they will appear automatically.
      </p>

      {codebtors.length === 0 && (
        <p className="text-gray-500 italic mb-4">
          No codebtors added yet. If no one is jointly liable on your debts, you can skip this step.
        </p>
      )}

      {codebtors.map((codebtor, index) => (
        <div key={index} className="border rounded p-4 mb-4">
          <div className="grid grid-cols-2 gap-4 mb-3">
            <div>
              <label className="block text-sm font-medium mb-1">Full Name</label>
              <input
                type="text"
                className="w-full border rounded px-3 py-2"
                value={codebtor.name}
                onChange={(e) => updateCodebtor(index, 'name', e.target.value)}
                placeholder="e.g., Jane Smith"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Relationship</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={codebtor.relationship}
                onChange={(e) => updateCodebtor(index, 'relationship', e.target.value)}
              >
                {RELATIONSHIPS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4 mb-3">
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">Street Address</label>
              <input
                type="text"
                className="w-full border rounded px-3 py-2"
                value={codebtor.street_address}
                onChange={(e) => updateCodebtor(index, 'street_address', e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">City</label>
              <input
                type="text"
                className="w-full border rounded px-3 py-2"
                value={codebtor.city}
                onChange={(e) => updateCodebtor(index, 'city', e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-sm font-medium mb-1">State</label>
                <input
                  type="text"
                  className="w-full border rounded px-3 py-2"
                  value={codebtor.state}
                  onChange={(e) => updateCodebtor(index, 'state', e.target.value)}
                  maxLength={2}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">ZIP</label>
                <input
                  type="text"
                  className="w-full border rounded px-3 py-2"
                  value={codebtor.zip_code}
                  onChange={(e) => updateCodebtor(index, 'zip_code', e.target.value)}
                />
              </div>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={() => removeCodebtor(index)}>
            Remove
          </Button>
        </div>
      ))}

      <Button variant="outline" onClick={addCodebtor} className="mt-2">
        + Add Codebtor
      </Button>

      {codebtors.length > 0 && (
        <div className="mt-4">
          <Button variant="primary" onClick={handleSave}>
            Save Codebtors
          </Button>
        </div>
      )}
    </div>
  );
}
