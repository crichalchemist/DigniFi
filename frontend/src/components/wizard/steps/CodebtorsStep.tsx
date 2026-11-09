/**
 * CodebtorsStep - Codebtor information (Schedule H)
 *
 * Lists people who are jointly liable on debts with the debtor.
 * Typically a spouse in community property states. The wizard holds the list,
 * autosaves it while the step can continue, and saves it on Continue (DIG-147).
 */

import { useEffect, useMemo } from 'react';
import { Button } from '../../common';
import { CHOOSE_ONE } from '../../../constants/copy';
import type { ClaimAnswers, Codebtor, CodebtorRow, ContractRow, DebtRow } from '../../../types/api';

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

const EMPTY_CODEBTOR: Codebtor = {
  name: '',
  street_address: '',
  city: '',
  state: '',
  zip_code: '',
  relationship: '',
};

// The last new row's key: unique while the page is open, and the prefix keeps it apart from a
// loaded row's key, which is its id
let nextKey = 0;

export function CodebtorsStep({ rows, onRowsChange, onValidationChange }: CodebtorsStepProps) {
  // A row left blank is not saved; a row the filer started needs the person's name. A stored
  // row can't lose its name: the list save deletes a stored row it leaves out
  const errors = useMemo(
    () =>
      rows.map((row) =>
        !row.name.trim() &&
        (row.id !== undefined ||
          [row.street_address, row.city, row.state, row.zip_code].some((value) => value.trim()))
          ? "Please enter this person's full name"
          : undefined
      ),
    [rows]
  );
  const isValid = errors.every((error) => !error);

  useEffect(() => onValidationChange(isValid), [isValid, onValidationChange]);

  const addCodebtor = () => {
    onRowsChange([...rows, { _key: `new-${++nextKey}`, ...EMPTY_CODEBTOR }]);
  };

  const updateCodebtor = (index: number, field: keyof Codebtor, value: string) => {
    const updated = [...rows];
    updated[index] = { ...updated[index], [field]: value };
    onRowsChange(updated);
  };

  const removeCodebtor = (index: number) => {
    onRowsChange(rows.filter((_, i) => i !== index));
  };

  return (
    <div className="codebtors-step">
      <h2 className="text-lg font-semibold mb-4">Codebtors</h2>
      <p className="text-gray-600 mb-4">List anyone who is jointly liable on any of your debts.</p>

      {rows.length === 0 && (
        <p className="text-gray-500 italic mb-4">
          No codebtors added yet. If no one is jointly liable on your debts, you can skip this step.
        </p>
      )}

      {rows.map((codebtor, index) => (
        <div key={codebtor._key} className="border rounded p-4 mb-4">
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
              <label
                htmlFor={`field-codebtor_relationship_${index}`}
                className="block text-sm font-medium mb-1"
              >
                Relationship
              </label>
              <select
                id={`field-codebtor_relationship_${index}`}
                className="w-full border rounded px-3 py-2"
                value={codebtor.relationship}
                onChange={(e) => updateCodebtor(index, 'relationship', e.target.value)}
              >
                <option value="">{CHOOSE_ONE}</option>
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
              <label
                htmlFor={`field-codebtor_street_address_${index}`}
                className="block text-sm font-medium mb-1"
              >
                Street Address
              </label>
              <input
                id={`field-codebtor_street_address_${index}`}
                type="text"
                className="w-full border rounded px-3 py-2"
                value={codebtor.street_address}
                onChange={(e) => updateCodebtor(index, 'street_address', e.target.value)}
                maxLength={255}
              />
            </div>
            <div>
              <label
                htmlFor={`field-codebtor_city_${index}`}
                className="block text-sm font-medium mb-1"
              >
                City
              </label>
              <input
                id={`field-codebtor_city_${index}`}
                type="text"
                className="w-full border rounded px-3 py-2"
                value={codebtor.city}
                onChange={(e) => updateCodebtor(index, 'city', e.target.value)}
                maxLength={100}
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label
                  htmlFor={`field-codebtor_state_${index}`}
                  className="block text-sm font-medium mb-1"
                >
                  State
                </label>
                <input
                  id={`field-codebtor_state_${index}`}
                  type="text"
                  className="w-full border rounded px-3 py-2"
                  value={codebtor.state}
                  onChange={(e) => updateCodebtor(index, 'state', e.target.value)}
                  maxLength={2}
                />
              </div>
              <div>
                <label
                  htmlFor={`field-codebtor_zip_code_${index}`}
                  className="block text-sm font-medium mb-1"
                >
                  ZIP
                </label>
                <input
                  id={`field-codebtor_zip_code_${index}`}
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
