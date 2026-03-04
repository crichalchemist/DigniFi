/**
 * Expense Info Step - Monthly expense collection
 *
 * Trauma-informed design:
 * - Non-judgmental language about expenses
 * - Clear explanations of categories
 * - Real-time total calculation
 * - Plain language help text
 */

import { useState, useEffect, useMemo } from 'react';
import { FormField } from '../../common';
import type { ExpenseInfo } from '../../../types/api';

interface ExpenseInfoStepProps {
  initialData?: Partial<ExpenseInfo>;
  onDataChange: (data: Partial<ExpenseInfo>) => void;
  onValidationChange: (isValid: boolean) => void;
}

export function ExpenseInfoStep({
  initialData,
  onDataChange,
  onValidationChange,
}: ExpenseInfoStepProps) {
  const [formData, setFormData] = useState<Partial<ExpenseInfo>>(
    initialData || {
      rent_or_mortgage: 0,
      utilities: 0,
      home_maintenance: 0,
      car_payment: 0,
      car_insurance: 0,
      gas_transportation: 0,
      food_groceries: 0,
      childcare: 0,
      medical_expenses: 0,
      insurance_not_deducted: 0,
      other_necessary_expenses: 0,
    }
  );

  // Calculate total monthly expenses
  const totalMonthlyExpenses =
    (formData.rent_or_mortgage || 0) +
    (formData.utilities || 0) +
    (formData.home_maintenance || 0) +
    (formData.car_payment || 0) +
    (formData.car_insurance || 0) +
    (formData.gas_transportation || 0) +
    (formData.food_groceries || 0) +
    (formData.childcare || 0) +
    (formData.medical_expenses || 0) +
    (formData.insurance_not_deducted || 0) +
    (formData.other_necessary_expenses || 0);

  const errors = useMemo<Record<string, string>>(() => {
    const newErrors: Record<string, string> = {};

    // Validate that at least one expense is provided
    if (totalMonthlyExpenses === 0) {
      newErrors.general =
        'Please enter at least one expense. If you have no expenses, enter 0 for all fields.';
    }

    // Validate non-negative values
    Object.keys(formData).forEach((key) => {
      const value = formData[key as keyof ExpenseInfo];
      if (typeof value === 'number' && value < 0) {
        newErrors[key] = 'Amount cannot be negative';
      }
    });

    return newErrors;
  }, [formData, totalMonthlyExpenses]);

  // Update parent when form data changes
  useEffect(() => {
    const dataWithTotal = {
      ...formData,
      total_monthly_expenses: totalMonthlyExpenses,
    };
    onDataChange(dataWithTotal);
    onValidationChange(Object.keys(errors).length === 0);
  }, [formData, totalMonthlyExpenses, errors]);

  const handleChange = (field: keyof ExpenseInfo, value: string) => {
    const numericValue = parseFloat(value) || 0;
    setFormData((prev) => ({ ...prev, [field]: numericValue }));
  };

  return (
    <div className="expense-info-step">
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
          <h3 className="info-title">Why we ask about expenses</h3>
          <p className="info-message">
            Monthly expenses help determine your financial situation. Enter your average
            monthly costs. If a category doesn't apply to you, enter $0.
          </p>
        </div>
      </div>

      {/* General error */}
      {errors.general && (
        <div className="form-error" role="alert">
          {errors.general}
        </div>
      )}

      {/* Housing Expenses */}
      <section className="form-section">
        <h3 className="section-title">Housing Expenses</h3>
        <p className="section-description">
          Include your monthly housing costs (rent or mortgage) and related expenses.
        </p>

        <FormField
          label="Rent or Mortgage Payment"
          name="rent_or_mortgage"
          type="number"
          min="0"
          step="0.01"
          value={formData.rent_or_mortgage || ''}
          onChange={(e) => handleChange('rent_or_mortgage', e.target.value)}
          error={errors.rent_or_mortgage}
          helpText="Monthly rent or mortgage payment"
          placeholder="0.00"
        />

        <div className="form-row">
          <FormField
            label="Utilities"
            name="utilities"
            type="number"
            min="0"
            step="0.01"
            value={formData.utilities || ''}
            onChange={(e) => handleChange('utilities', e.target.value)}
            error={errors.utilities}
            helpText="Electric, gas, water, trash, internet, phone"
            placeholder="0.00"
          />

          <FormField
            label="Home Maintenance"
            name="home_maintenance"
            type="number"
            min="0"
            step="0.01"
            value={formData.home_maintenance || ''}
            onChange={(e) => handleChange('home_maintenance', e.target.value)}
            error={errors.home_maintenance}
            helpText="Repairs, yard work, HOA fees"
            placeholder="0.00"
          />
        </div>
      </section>

      {/* Transportation Expenses */}
      <section className="form-section">
        <h3 className="section-title">Transportation Expenses</h3>
        <p className="section-description">
          Include car payments, insurance, gas, and other transportation costs.
        </p>

        <div className="form-row">
          <FormField
            label="Car Payment"
            name="car_payment"
            type="number"
            min="0"
            step="0.01"
            value={formData.car_payment || ''}
            onChange={(e) => handleChange('car_payment', e.target.value)}
            error={errors.car_payment}
            helpText="Monthly auto loan or lease payment"
            placeholder="0.00"
          />

          <FormField
            label="Car Insurance"
            name="car_insurance"
            type="number"
            min="0"
            step="0.01"
            value={formData.car_insurance || ''}
            onChange={(e) => handleChange('car_insurance', e.target.value)}
            error={errors.car_insurance}
            helpText="Monthly auto insurance premium"
            placeholder="0.00"
          />
        </div>

        <FormField
          label="Gas & Transportation"
          name="gas_transportation"
          type="number"
          min="0"
          step="0.01"
          value={formData.gas_transportation || ''}
          onChange={(e) => handleChange('gas_transportation', e.target.value)}
          error={errors.gas_transportation}
          helpText="Gas, public transit, parking, tolls"
          placeholder="0.00"
        />
      </section>

      {/* Living Expenses */}
      <section className="form-section">
        <h3 className="section-title">Living Expenses</h3>
        <p className="section-description">
          Include food, childcare, medical expenses, and other necessary costs.
        </p>

        <div className="form-row">
          <FormField
            label="Food & Groceries"
            name="food_groceries"
            type="number"
            min="0"
            step="0.01"
            value={formData.food_groceries || ''}
            onChange={(e) => handleChange('food_groceries', e.target.value)}
            error={errors.food_groceries}
            helpText="Groceries, dining out, household supplies"
            placeholder="0.00"
          />

          <FormField
            label="Childcare"
            name="childcare"
            type="number"
            min="0"
            step="0.01"
            value={formData.childcare || ''}
            onChange={(e) => handleChange('childcare', e.target.value)}
            error={errors.childcare}
            helpText="Daycare, after-school care, babysitting"
            placeholder="0.00"
          />
        </div>

        <div className="form-row">
          <FormField
            label="Medical Expenses"
            name="medical_expenses"
            type="number"
            min="0"
            step="0.01"
            value={formData.medical_expenses || ''}
            onChange={(e) => handleChange('medical_expenses', e.target.value)}
            error={errors.medical_expenses}
            helpText="Doctor visits, prescriptions, co-pays not covered by insurance"
            placeholder="0.00"
          />

          <FormField
            label="Insurance (Not Deducted from Pay)"
            name="insurance_not_deducted"
            type="number"
            min="0"
            step="0.01"
            value={formData.insurance_not_deducted || ''}
            onChange={(e) => handleChange('insurance_not_deducted', e.target.value)}
            error={errors.insurance_not_deducted}
            helpText="Health, life, or disability insurance you pay directly"
            placeholder="0.00"
          />
        </div>

        <FormField
          label="Other Necessary Expenses"
          name="other_necessary_expenses"
          type="number"
          min="0"
          step="0.01"
          value={formData.other_necessary_expenses || ''}
          onChange={(e) => handleChange('other_necessary_expenses', e.target.value)}
          error={errors.other_necessary_expenses}
          helpText="Clothing, laundry, personal care, pet care, other essentials"
          placeholder="0.00"
        />
      </section>

      {/* Total Summary */}
      <section className="form-section form-section--summary">
        <div className="expense-total">
          <h3 className="total-label">Total Monthly Expenses</h3>
          <p className="total-amount">
            ${totalMonthlyExpenses.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
          <p className="total-help-text">
            This is your total monthly expenses across all categories.
          </p>
        </div>
      </section>
    </div>
  );
}

export default ExpenseInfoStep;
