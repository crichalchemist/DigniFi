/**
 * Debts Step - Creditor and amounts owed collection
 *
 * Trauma-informed design:
 * - "Amounts owed" language (not "debt")
 * - Non-judgmental tone
 * - Clear explanations of debt types
 * - Multiple debts support (add/remove)
 * - Privacy-conscious (account numbers encrypted)
 */

import { useState, useEffect } from 'react';
import { FormField, FormTextarea, Button } from '../../common';
import { UPLDisclaimer } from '../../compliance';
import { UPL_EXEMPTION_DISCLAIMER } from '../../../constants/upl';
import type { DebtInfo } from '../../../types/api';

interface DebtsStepProps {
  initialData?: Partial<DebtInfo>[];
  onDataChange: (data: Partial<DebtInfo>[]) => void;
  onValidationChange: (isValid: boolean) => void;
}

const DEBT_TYPES = [
  {
    value: 'secured',
    label: 'Secured (backed by collateral)',
    description: 'Mortgage, car loan, or other debt backed by property',
  },
  {
    value: 'unsecured',
    label: 'Unsecured (no collateral)',
    description: 'Credit cards, medical bills, personal loans',
  },
  {
    value: 'priority',
    label: 'Priority (legally prioritized)',
    description: 'Taxes, child support, alimony, student loans',
  },
];

export function DebtsStep({
  initialData,
  onDataChange,
  onValidationChange,
}: DebtsStepProps) {
  const [debts, setDebts] = useState<Partial<DebtInfo>[]>(
    initialData && initialData.length > 0
      ? initialData
      : [createEmptyDebt()]
  );
  const [errors, setErrors] = useState<Record<number, Record<string, string>>>({});

  // Update parent when debts change
  useEffect(() => {
    onDataChange(debts);
    validateForm();
  }, [debts]);

  function createEmptyDebt(): Partial<DebtInfo> {
    return {
      debt_type: undefined,
      creditor_name: '',
      account_number: '',
      amount_owed: 0,
      monthly_payment: 0,
      is_secured: false,
      collateral_description: '',
    };
  }

  const handleAddDebt = () => {
    setDebts([...debts, createEmptyDebt()]);
  };

  const handleRemoveDebt = (index: number) => {
    if (debts.length === 1) {
      // Keep at least one debt form
      setDebts([createEmptyDebt()]);
    } else {
      setDebts(debts.filter((_, i) => i !== index));
    }
    // Clear errors for removed debt
    const newErrors = { ...errors };
    delete newErrors[index];
    setErrors(newErrors);
  };

  const handleDebtChange = (
    index: number,
    field: keyof DebtInfo,
    value: any
  ) => {
    const updatedDebts = [...debts];

    if (field === 'amount_owed' || field === 'monthly_payment') {
      updatedDebts[index] = {
        ...updatedDebts[index],
        [field]: parseFloat(value) || 0,
      };
    } else if (field === 'debt_type') {
      // Auto-set is_secured based on debt type
      updatedDebts[index] = {
        ...updatedDebts[index],
        [field]: value,
        is_secured: value === 'secured',
      };
    } else {
      updatedDebts[index] = {
        ...updatedDebts[index],
        [field]: value,
      };
    }

    setDebts(updatedDebts);

    // Clear error for this field
    if (errors[index]?.[field]) {
      const newErrors = { ...errors };
      delete newErrors[index][field];
      setErrors(newErrors);
    }
  };

  const validateForm = () => {
    const newErrors: Record<number, Record<string, string>> = {};
    let hasValidDebt = false;

    debts.forEach((debt, index) => {
      const debtErrors: Record<string, string> = {};

      // Check if this debt has any data filled in
      const hasData =
        debt.debt_type ||
        debt.creditor_name ||
        (debt.amount_owed && debt.amount_owed > 0);

      if (hasData) {
        hasValidDebt = true;

        // Validate required fields if debt has data
        if (!debt.debt_type) {
          debtErrors.debt_type = 'Please select the type of amount owed';
        }

        if (!debt.creditor_name?.trim()) {
          debtErrors.creditor_name = 'Please enter the creditor name';
        }

        if (!debt.amount_owed || debt.amount_owed <= 0) {
          debtErrors.amount_owed = 'Please enter the amount owed';
        }

        // Validate collateral description for secured debts
        if (debt.debt_type === 'secured' && !debt.collateral_description?.trim()) {
          debtErrors.collateral_description =
            'Please describe what secures this amount owed';
        }

        // Validate non-negative values
        if (debt.monthly_payment && debt.monthly_payment < 0) {
          debtErrors.monthly_payment = 'Payment cannot be negative';
        }
      }

      if (Object.keys(debtErrors).length > 0) {
        newErrors[index] = debtErrors;
      }
    });

    setErrors(newErrors);
    const isValid = Object.keys(newErrors).length === 0 && hasValidDebt;
    onValidationChange(isValid);

    return isValid;
  };

  return (
    <div className="debts-step">
      {/* Explainer */}
      <div className="info-box">
        <svg
          className="info-icon"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
            clipRule="evenodd"
          />
        </svg>
        <div>
          <h3 className="info-title">About amounts you owe</h3>
          <p className="info-message">
            List all creditors (companies or people you owe money to). Include credit
            cards, medical bills, loans, and any other amounts owed. This helps determine
            which type of bankruptcy may work for your situation.
          </p>
        </div>
      </div>

      {/* Debts List */}
      {debts.map((debt, index) => (
        <section key={index} className="form-section debt-card">
          <div className="debt-card-header">
            <h3 className="section-title">
              Amount Owed {index + 1}
              {debt.creditor_name && ` - ${debt.creditor_name}`}
            </h3>
            {debts.length > 1 && (
              <button
                type="button"
                onClick={() => handleRemoveDebt(index)}
                className="remove-debt-button"
                aria-label={`Remove amount owed ${index + 1}`}
              >
                <svg
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="remove-icon"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                Remove
              </button>
            )}
          </div>

          {/* Debt Type with Helpful Descriptions */}
          <div className="debt-type-selector">
            <label className="form-label">
              Type of Amount Owed <span className="required-indicator">*</span>
            </label>
            <div className="debt-type-options">
              {DEBT_TYPES.map((type) => (
                <label
                  key={type.value}
                  className={`debt-type-option ${
                    debt.debt_type === type.value ? 'selected' : ''
                  }`}
                >
                  <input
                    type="radio"
                    name={`debt_type_${index}`}
                    value={type.value}
                    checked={debt.debt_type === type.value}
                    onChange={(e) =>
                      handleDebtChange(index, 'debt_type', e.target.value)
                    }
                  />
                  <div className="option-content">
                    <div className="option-label">{type.label}</div>
                    <div className="option-description">{type.description}</div>
                  </div>
                </label>
              ))}
            </div>
            {errors[index]?.debt_type && (
              <p className="form-error" role="alert">
                {errors[index].debt_type}
              </p>
            )}
          </div>

          <div className="form-row">
            <FormField
              label="Creditor Name"
              name={`creditor_name_${index}`}
              type="text"
              value={debt.creditor_name || ''}
              onChange={(e) =>
                handleDebtChange(index, 'creditor_name', e.target.value)
              }
              error={errors[index]?.creditor_name}
              required
              helpText="Company or person you owe money to"
              placeholder="e.g., Capital One, Dr. Smith, ABC Collections"
            />

            <FormField
              label="Account Number (Last 4 Digits)"
              name={`account_number_${index}`}
              type="text"
              value={debt.account_number || ''}
              onChange={(e) =>
                handleDebtChange(index, 'account_number', e.target.value)
              }
              helpText="Optional - helps identify the account. Your account number is encrypted."
              placeholder="XXXX-1234"
            />
          </div>

          <div className="form-row">
            <FormField
              label="Amount Owed"
              name={`amount_owed_${index}`}
              type="number"
              min="0"
              step="0.01"
              value={debt.amount_owed || ''}
              onChange={(e) =>
                handleDebtChange(index, 'amount_owed', e.target.value)
              }
              error={errors[index]?.amount_owed}
              required
              helpText="Total amount you currently owe"
              placeholder="0.00"
            />

            <FormField
              label="Monthly Payment"
              name={`monthly_payment_${index}`}
              type="number"
              min="0"
              step="0.01"
              value={debt.monthly_payment || ''}
              onChange={(e) =>
                handleDebtChange(index, 'monthly_payment', e.target.value)
              }
              error={errors[index]?.monthly_payment}
              helpText="Your regular monthly payment (if any)"
              placeholder="0.00"
            />
          </div>

          {/* Collateral description for secured debts */}
          {debt.debt_type === 'secured' && (
            <FormTextarea
              label="What secures this amount owed?"
              name={`collateral_description_${index}`}
              value={debt.collateral_description || ''}
              onChange={(e: any) =>
                handleDebtChange(index, 'collateral_description', e.target.value)
              }
              error={errors[index]?.collateral_description}
              required
              rows={3}
              helpText="Describe the property that secures this (e.g., '2015 Honda Civic VIN: XXX', 'Family home at 123 Main St')"
              placeholder="e.g., 2015 Honda Civic, Family home at 123 Main Street"
            />
          )}
        </section>
      ))}

      {/* Add Debt Button */}
      <div className="add-debt-section">
        <Button
          variant="outline"
          onClick={handleAddDebt}
          icon={
            <svg
              viewBox="0 0 20 20"
              fill="currentColor"
              className="icon"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                clipRule="evenodd"
              />
            </svg>
          }
        >
          Add Another Amount Owed
        </Button>
      </div>

      <UPLDisclaimer text={UPL_EXEMPTION_DISCLAIMER} variant="inline" />

      {/* Total Summary */}
      <section className="form-section form-section--summary">
        <div className="debts-total">
          <h3 className="total-label">Total Amounts Owed</h3>
          <p className="total-amount">
            ${debts
              .reduce((sum, debt) => sum + (debt.amount_owed || 0), 0)
              .toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
          </p>
          <p className="total-help-text">
            This is the total of all amounts you currently owe to creditors.
          </p>
        </div>
      </section>
    </div>
  );
}

export default DebtsStep;
