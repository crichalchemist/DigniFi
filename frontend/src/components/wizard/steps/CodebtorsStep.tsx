/**
 * CodebtorsStep - Codebtor information (Schedule H)
 *
 * Lists people who are jointly liable on debts with the debtor.
 * Typically a spouse in community property states. The wizard saves
 * the whole list when the filer presses Continue (DIG-147).
 */

import { useState, useEffect, useMemo } from 'react';
import { Button } from '../../common';
import type { Codebtor } from '../../../types/api';

interface CodebtorsStepProps {
  initialData?: Codebtor[];
  onDataChange: (data: Codebtor[]) => void;
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

const EMPTY_CODEBTOR: Codebtor = {
  name: '',
  street_address: '',
  city: '',
  state: '',
  zip_code: '',
  relationship: 'other',
};

export function CodebtorsStep({
  initialData,
  onDataChange,
  onValidationChange,
}: CodebtorsStepProps) {
  const [codebtors, setCodebtors] = useState<Codebtor[]>(initialData ?? []);

  // A row left blank is not saved; a row the filer started needs the person's name
  const errors = useMemo(
    () =>
      codebtors.map((codebtor) =>
        !codebtor.name.trim() &&
        [codebtor.street_address, codebtor.city, codebtor.state, codebtor.zip_code].some((value) =>
          value.trim()
        )
          ? "Please enter this person's full name"
          : undefined
      ),
    [codebtors]
  );
  const isValid = errors.every((error) => !error);

  // Update parent when codebtors change
  useEffect(() => {
    onDataChange(codebtors);
    onValidationChange(isValid);
    // both callbacks are useState setters in IntakeWizard — stable identities
  }, [codebtors, isValid, onDataChange, onValidationChange]);

  const addCodebtor = () => {
    setCodebtors([...codebtors, { ...EMPTY_CODEBTOR }]);
  };

  const updateCodebtor = (index: number, field: keyof Codebtor, value: string) => {
    const updated = [...codebtors];
    updated[index] = { ...updated[index], [field]: value };
    setCodebtors(updated);
  };

  const removeCodebtor = (index: number) => {
    setCodebtors(codebtors.filter((_, i) => i !== index));
  };

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
              <label
                htmlFor={`field-codebtor_name_${index}`}
                className="block text-sm font-medium mb-1"
              >
                Full Name
              </label>
              <input
                id={`field-codebtor_name_${index}`}
                type="text"
                className="w-full border rounded px-3 py-2"
                value={codebtor.name}
                onChange={(e) => updateCodebtor(index, 'name', e.target.value)}
                placeholder="e.g., Jane Smith"
                maxLength={255}
                aria-describedby={errors[index] ? `field-codebtor_name_${index}-error` : undefined}
                aria-invalid={errors[index] ? 'true' : 'false'}
              />
              {errors[index] && (
                <p
                  id={`field-codebtor_name_${index}-error`}
                  className="form-error"
                  role="alert"
                  aria-live="assertive"
                >
                  {errors[index]}
                </p>
              )}
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
                maxLength={255}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">City</label>
              <input
                type="text"
                className="w-full border rounded px-3 py-2"
                value={codebtor.city}
                onChange={(e) => updateCodebtor(index, 'city', e.target.value)}
                maxLength={100}
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
                  maxLength={10}
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
    </div>
  );
}
