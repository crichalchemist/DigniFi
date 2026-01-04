/**
 * Income Info Step - Monthly income collection
 *
 * Trauma-informed design:
 * - Non-judgmental language about income sources
 * - Clear explanations of why each field is needed
 * - Real-time total calculation
 * - Plain language help text
 */

import { useState, useEffect } from 'react';
import { FormField, FormSelect } from '../../common';
import type { IncomeInfo } from '../../../types/api';

interface IncomeInfoStepProps {
  initialData?: Partial<IncomeInfo>;
  onDataChange: (data: Partial<IncomeInfo>) => void;
  onValidationChange: (isValid: boolean) => void;
}

export function IncomeInfoStep({
  initialData,
  onDataChange,
  onValidationChange,
}: IncomeInfoStepProps) {
  const [formData, setFormData] = useState<Partial<IncomeInfo>>(
    initialData || {
      monthly_gross_wages: 0,
      monthly_overtime: 0,
      monthly_tips: 0,
      monthly_rental_income: 0,
      monthly_pension: 0,
      monthly_social_security: 0,
      monthly_unemployment: 0,
      monthly_child_support: 0,
      monthly_alimony: 0,
      monthly_other_income: 0,
    }
  );
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Calculate total monthly income
  const totalMonthlyIncome =
    (formData.monthly_gross_wages || 0) +
    (formData.monthly_overtime || 0) +
    (formData.monthly_tips || 0) +
    (formData.monthly_rental_income || 0) +
    (formData.monthly_pension || 0) +
    (formData.monthly_social_security || 0) +
    (formData.monthly_unemployment || 0) +
    (formData.monthly_child_support || 0) +
    (formData.monthly_alimony || 0) +
    (formData.monthly_other_income || 0);

  // Update parent when form data changes
  useEffect(() => {
    const dataWithTotal = {
      ...formData,
      total_monthly_income: totalMonthlyIncome,
    };
    onDataChange(dataWithTotal);
    validateForm();
  }, [formData, totalMonthlyIncome]);

  const handleChange = (field: keyof IncomeInfo, value: any) => {
    const numericValue = parseFloat(value) || 0;
    setFormData((prev) => ({ ...prev, [field]: numericValue }));
    // Clear error for this field
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    // Validate that at least one income source is provided
    if (totalMonthlyIncome === 0) {
      newErrors.general =
        'Please enter at least one source of income. If you have no income, enter 0 for all fields.';
    }

    // Validate non-negative values
    Object.keys(formData).forEach((key) => {
      const value = formData[key as keyof IncomeInfo];
      if (typeof value === 'number' && value < 0) {
        newErrors[key] = 'Amount cannot be negative';
      }
    });

    setErrors(newErrors);
    const isValid = Object.keys(newErrors).length === 0;
    onValidationChange(isValid);

    return isValid;
  };

  return (
    <div className="income-info-step">
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
          <h3 className="info-title">Why we ask about income</h3>
          <p className="info-message">
            Income information helps determine which bankruptcy chapter you may qualify
            for. Enter your average monthly income before taxes. If you don't have income
            from a source, enter $0.
          </p>
        </div>
      </div>

      {/* General error */}
      {errors.general && (
        <div className="form-error" role="alert">
          {errors.general}
        </div>
      )}

      {/* Employment Income */}
      <section className="form-section">
        <h3 className="section-title">Employment Income</h3>
        <p className="section-description">
          Include income from all jobs, before taxes and deductions.
        </p>

        <FormField
          label="Monthly Wages/Salary"
          name="monthly_gross_wages"
          type="number"
          min="0"
          step="0.01"
          value={formData.monthly_gross_wages || ''}
          onChange={(e) => handleChange('monthly_gross_wages', e.target.value)}
          error={errors.monthly_gross_wages}
          helpText="Regular wages before taxes"
          placeholder="0.00"
        />

        <div className="form-row">
          <FormField
            label="Monthly Overtime"
            name="monthly_overtime"
            type="number"
            min="0"
            step="0.01"
            value={formData.monthly_overtime || ''}
            onChange={(e) => handleChange('monthly_overtime', e.target.value)}
            error={errors.monthly_overtime}
            helpText="Average monthly overtime pay"
            placeholder="0.00"
          />

          <FormField
            label="Monthly Tips"
            name="monthly_tips"
            type="number"
            min="0"
            step="0.01"
            value={formData.monthly_tips || ''}
            onChange={(e) => handleChange('monthly_tips', e.target.value)}
            error={errors.monthly_tips}
            helpText="Average monthly tips and bonuses"
            placeholder="0.00"
          />
        </div>
      </section>

      {/* Government Benefits */}
      <section className="form-section">
        <h3 className="section-title">Government Benefits</h3>
        <p className="section-description">
          Include Social Security, unemployment, and other government assistance.
        </p>

        <div className="form-row">
          <FormField
            label="Social Security"
            name="monthly_social_security"
            type="number"
            min="0"
            step="0.01"
            value={formData.monthly_social_security || ''}
            onChange={(e) => handleChange('monthly_social_security', e.target.value)}
            error={errors.monthly_social_security}
            helpText="SSI, SSDI, or retirement benefits"
            placeholder="0.00"
          />

          <FormField
            label="Unemployment Benefits"
            name="monthly_unemployment"
            type="number"
            min="0"
            step="0.01"
            value={formData.monthly_unemployment || ''}
            onChange={(e) => handleChange('monthly_unemployment', e.target.value)}
            error={errors.monthly_unemployment}
            placeholder="0.00"
          />
        </div>
      </section>

      {/* Other Income */}
      <section className="form-section">
        <h3 className="section-title">Other Income</h3>
        <p className="section-description">
          Include rental income, pensions, child support, alimony, and other sources.
        </p>

        <div className="form-row">
          <FormField
            label="Pension/Retirement"
            name="monthly_pension"
            type="number"
            min="0"
            step="0.01"
            value={formData.monthly_pension || ''}
            onChange={(e) => handleChange('monthly_pension', e.target.value)}
            error={errors.monthly_pension}
            placeholder="0.00"
          />

          <FormField
            label="Rental Income"
            name="monthly_rental_income"
            type="number"
            min="0"
            step="0.01"
            value={formData.monthly_rental_income || ''}
            onChange={(e) => handleChange('monthly_rental_income', e.target.value)}
            error={errors.monthly_rental_income}
            placeholder="0.00"
          />
        </div>

        <div className="form-row">
          <FormField
            label="Child Support Received"
            name="monthly_child_support"
            type="number"
            min="0"
            step="0.01"
            value={formData.monthly_child_support || ''}
            onChange={(e) => handleChange('monthly_child_support', e.target.value)}
            error={errors.monthly_child_support}
            helpText="Child support you receive"
            placeholder="0.00"
          />

          <FormField
            label="Alimony Received"
            name="monthly_alimony"
            type="number"
            min="0"
            step="0.01"
            value={formData.monthly_alimony || ''}
            onChange={(e) => handleChange('monthly_alimony', e.target.value)}
            error={errors.monthly_alimony}
            helpText="Alimony/spousal support you receive"
            placeholder="0.00"
          />
        </div>

        <FormField
          label="Other Monthly Income"
          name="monthly_other_income"
          type="number"
          min="0"
          step="0.01"
          value={formData.monthly_other_income || ''}
          onChange={(e) => handleChange('monthly_other_income', e.target.value)}
          error={errors.monthly_other_income}
          helpText="Any other regular monthly income"
          placeholder="0.00"
        />
      </section>

      {/* Total Summary */}
      <section className="form-section form-section--summary">
        <div className="income-total">
          <h3 className="total-label">Total Monthly Income</h3>
          <p className="total-amount">
            ${totalMonthlyIncome.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
          <p className="total-help-text">
            This is your total monthly income before taxes and deductions.
          </p>
        </div>
      </section>
    </div>
  );
}

export default IncomeInfoStep;
