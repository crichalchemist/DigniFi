/**
 * Debtor Info Step - Personal information collection
 *
 * Trauma-informed design:
 * - Clear explanation of why information is needed
 * - Privacy assurance messaging
 * - Dignity-preserving field labels
 * - Plain language help text
 */

import { useState, useEffect } from 'react';
import { FormField, FormSelect } from '../../common';
import type { DebtorInfo } from '../../../types/api';

interface DebtorInfoStepProps {
  initialData?: Partial<DebtorInfo>;
  onDataChange: (data: Partial<DebtorInfo>) => void;
  onValidationChange: (isValid: boolean) => void;
}

// US States for dropdown
const US_STATES = [
  { value: 'IL', label: 'Illinois' },
  { value: 'IN', label: 'Indiana' },
  { value: 'WI', label: 'Wisconsin' },
  // Add more states as needed for MVP
];

const FILING_TYPES = [
  { value: 'individual', label: 'Individual (filing alone)' },
  { value: 'joint', label: 'Joint (filing with spouse)' },
];

export function DebtorInfoStep({
  initialData,
  onDataChange,
  onValidationChange,
}: DebtorInfoStepProps) {
  const [formData, setFormData] = useState<Partial<DebtorInfo>>(
    initialData || {}
  );
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Update parent when form data changes
  useEffect(() => {
    onDataChange(formData);
    validateForm();
  }, [formData]);

  const handleChange = (field: keyof DebtorInfo, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    // Required fields validation
    if (!formData.first_name?.trim()) {
      newErrors.first_name = 'Please enter your first name';
    }

    if (!formData.last_name?.trim()) {
      newErrors.last_name = 'Please enter your last name';
    }

    if (!formData.date_of_birth) {
      newErrors.date_of_birth = 'Please enter your date of birth';
    } else {
      // Validate age (must be 18+)
      const dob = new Date(formData.date_of_birth);
      const today = new Date();
      const age = today.getFullYear() - dob.getFullYear();
      if (age < 18) {
        newErrors.date_of_birth =
          'You must be 18 or older to file for bankruptcy';
      }
    }

    if (!formData.ssn?.trim()) {
      newErrors.ssn = 'Please enter your Social Security Number';
    } else if (!/^\d{3}-?\d{2}-?\d{4}$/.test(formData.ssn)) {
      newErrors.ssn = 'Please enter a valid Social Security Number (XXX-XX-XXXX)';
    }

    if (!formData.street_address?.trim()) {
      newErrors.street_address = 'Please enter your street address';
    }

    if (!formData.city?.trim()) {
      newErrors.city = 'Please enter your city';
    }

    if (!formData.state) {
      newErrors.state = 'Please select your state';
    }

    if (!formData.zip_code?.trim()) {
      newErrors.zip_code = 'Please enter your ZIP code';
    } else if (!/^\d{5}(-\d{4})?$/.test(formData.zip_code)) {
      newErrors.zip_code = 'Please enter a valid ZIP code (XXXXX or XXXXX-XXXX)';
    }

    if (!formData.email?.trim()) {
      newErrors.email = 'Please enter your email address';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!formData.phone_number?.trim()) {
      newErrors.phone_number = 'Please enter your phone number';
    } else if (!/^\d{3}-?\d{3}-?\d{4}$/.test(formData.phone_number)) {
      newErrors.phone_number = 'Please enter a valid phone number (XXX-XXX-XXXX)';
    }

    if (!formData.household_size || formData.household_size < 1) {
      newErrors.household_size = 'Please enter your household size';
    }

    if (!formData.filing_type) {
      newErrors.filing_type = 'Please select your filing type';
    }

    setErrors(newErrors);
    const isValid = Object.keys(newErrors).length === 0;
    onValidationChange(isValid);

    return isValid;
  };

  return (
    <div className="debtor-info-step">
      {/* Privacy assurance */}
      <div className="info-box">
        <svg
          className="info-icon"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
            clipRule="evenodd"
          />
        </svg>
        <div>
          <h3 className="info-title">Your information is secure</h3>
          <p className="info-message">
            All personal information is encrypted and stored securely. We only collect
            what's required for bankruptcy forms.
          </p>
        </div>
      </div>

      {/* Personal Information */}
      <section className="form-section">
        <h3 className="section-title">Personal Information</h3>

        <div className="form-row">
          <FormField
            label="First Name"
            name="first_name"
            type="text"
            value={formData.first_name || ''}
            onChange={(e) => handleChange('first_name', e.target.value)}
            error={errors.first_name}
            required
            autoComplete="given-name"
          />

          <FormField
            label="Middle Name"
            name="middle_name"
            type="text"
            value={formData.middle_name || ''}
            onChange={(e) => handleChange('middle_name', e.target.value)}
            autoComplete="additional-name"
            helpText="Optional"
          />

          <FormField
            label="Last Name"
            name="last_name"
            type="text"
            value={formData.last_name || ''}
            onChange={(e) => handleChange('last_name', e.target.value)}
            error={errors.last_name}
            required
            autoComplete="family-name"
          />
        </div>

        <div className="form-row">
          <FormField
            label="Date of Birth"
            name="date_of_birth"
            type="date"
            value={formData.date_of_birth || ''}
            onChange={(e) => handleChange('date_of_birth', e.target.value)}
            error={errors.date_of_birth}
            required
            autoComplete="bday"
            helpText="Must be 18 or older"
          />

          <FormField
            label="Social Security Number"
            name="ssn"
            type="text"
            value={formData.ssn || ''}
            onChange={(e) => handleChange('ssn', e.target.value)}
            error={errors.ssn}
            required
            autoComplete="off"
            placeholder="XXX-XX-XXXX"
            helpText="Required for bankruptcy filing. Your SSN is encrypted."
          />
        </div>
      </section>

      {/* Contact Information */}
      <section className="form-section">
        <h3 className="section-title">Contact Information</h3>

        <FormField
          label="Street Address"
          name="street_address"
          type="text"
          value={formData.street_address || ''}
          onChange={(e) => handleChange('street_address', e.target.value)}
          error={errors.street_address}
          required
          autoComplete="street-address"
        />

        <div className="form-row">
          <FormField
            label="City"
            name="city"
            type="text"
            value={formData.city || ''}
            onChange={(e) => handleChange('city', e.target.value)}
            error={errors.city}
            required
            autoComplete="address-level2"
          />

          <FormSelect
            label="State"
            name="state"
            options={US_STATES}
            value={formData.state || ''}
            onChange={(value) => handleChange('state', value)}
            error={errors.state}
            required
          />

          <FormField
            label="ZIP Code"
            name="zip_code"
            type="text"
            value={formData.zip_code || ''}
            onChange={(e) => handleChange('zip_code', e.target.value)}
            error={errors.zip_code}
            required
            autoComplete="postal-code"
            placeholder="XXXXX"
          />
        </div>

        <div className="form-row">
          <FormField
            label="Email Address"
            name="email"
            type="email"
            value={formData.email || ''}
            onChange={(e) => handleChange('email', e.target.value)}
            error={errors.email}
            required
            autoComplete="email"
            helpText="We'll send important updates here"
          />

          <FormField
            label="Phone Number"
            name="phone_number"
            type="tel"
            value={formData.phone_number || ''}
            onChange={(e) => handleChange('phone_number', e.target.value)}
            error={errors.phone_number}
            required
            autoComplete="tel"
            placeholder="XXX-XXX-XXXX"
          />
        </div>
      </section>

      {/* Household & Filing Information */}
      <section className="form-section">
        <h3 className="section-title">Household & Filing Information</h3>

        <div className="form-row">
          <FormField
            label="Household Size"
            name="household_size"
            type="number"
            min="1"
            value={formData.household_size || ''}
            onChange={(e) =>
              handleChange('household_size', parseInt(e.target.value, 10))
            }
            error={errors.household_size}
            required
            helpText="Number of people living in your household (including yourself)"
          />

          <FormSelect
            label="Filing Type"
            name="filing_type"
            options={FILING_TYPES}
            value={formData.filing_type || ''}
            onChange={(value) => handleChange('filing_type', value)}
            error={errors.filing_type}
            required
            helpText="Are you filing alone or with your spouse?"
          />
        </div>

        {/* Joint filing co-debtor fields (conditional) */}
        {formData.filing_type === 'joint' && (
          <>
            <div className="info-box info-box--secondary">
              <p>
                For joint filings, please provide your spouse's information below.
              </p>
            </div>

            <h4 className="subsection-title">Spouse Information</h4>

            <div className="form-row">
              <FormField
                label="Spouse's First Name"
                name="co_debtor_first_name"
                type="text"
                value={formData.co_debtor_first_name || ''}
                onChange={(e) => handleChange('co_debtor_first_name', e.target.value)}
                required
              />

              <FormField
                label="Spouse's Middle Name"
                name="co_debtor_middle_name"
                type="text"
                value={formData.co_debtor_middle_name || ''}
                onChange={(e) =>
                  handleChange('co_debtor_middle_name', e.target.value)
                }
                helpText="Optional"
              />

              <FormField
                label="Spouse's Last Name"
                name="co_debtor_last_name"
                type="text"
                value={formData.co_debtor_last_name || ''}
                onChange={(e) => handleChange('co_debtor_last_name', e.target.value)}
                required
              />
            </div>

            <div className="form-row">
              <FormField
                label="Spouse's Date of Birth"
                name="co_debtor_date_of_birth"
                type="date"
                value={formData.co_debtor_date_of_birth || ''}
                onChange={(e) =>
                  handleChange('co_debtor_date_of_birth', e.target.value)
                }
                required
              />

              <FormField
                label="Spouse's Social Security Number"
                name="co_debtor_ssn"
                type="text"
                value={formData.co_debtor_ssn || ''}
                onChange={(e) => handleChange('co_debtor_ssn', e.target.value)}
                required
                autoComplete="off"
                placeholder="XXX-XX-XXXX"
              />
            </div>
          </>
        )}
      </section>
    </div>
  );
}

export default DebtorInfoStep;
