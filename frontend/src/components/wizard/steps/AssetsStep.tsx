/**
 * Assets Step - Property and accounts collection
 *
 * Trauma-informed design:
 * - Non-judgmental language about assets
 * - Clear explanations of what counts as an asset
 * - Multiple asset support (add/remove)
 * - Privacy-conscious (account numbers encrypted)
 */

import { useState, useEffect } from 'react';
import { FormField, FormSelect, Button } from '../../common';
import { UPLDisclaimer } from '../../compliance';
import { UPL_EXEMPTION_DISCLAIMER } from '../../../constants/upl';
import type { AssetInfo } from '../../../types/api';

interface AssetsStepProps {
  initialData?: Partial<AssetInfo>[];
  onDataChange: (data: Partial<AssetInfo>[]) => void;
  onValidationChange: (isValid: boolean) => void;
}

const ASSET_TYPES = [
  { value: 'real_property', label: 'Real Estate (home, land, rental property)' },
  { value: 'vehicle', label: 'Vehicle (car, truck, motorcycle, RV)' },
  { value: 'bank_account', label: 'Bank Account (checking, savings)' },
  { value: 'retirement_account', label: 'Retirement Account (401k, IRA, pension)' },
  { value: 'personal_property', label: 'Personal Property (furniture, jewelry, collectibles)' },
  { value: 'other', label: 'Other Asset' },
];

export function AssetsStep({
  initialData,
  onDataChange,
  onValidationChange,
}: AssetsStepProps) {
  const [assets, setAssets] = useState<Partial<AssetInfo>[]>(
    initialData && initialData.length > 0
      ? initialData
      : [createEmptyAsset()]
  );
  const [errors, setErrors] = useState<Record<number, Record<string, string>>>({});

  // Update parent when assets change
  useEffect(() => {
    onDataChange(assets);
    validateForm();
  }, [assets]);

  function createEmptyAsset(): Partial<AssetInfo> {
    return {
      asset_type: undefined,
      description: '',
      current_value: 0,
      amount_owed: 0,
      account_number: '',
    };
  }

  const handleAddAsset = () => {
    setAssets([...assets, createEmptyAsset()]);
  };

  const handleRemoveAsset = (index: number) => {
    if (assets.length === 1) {
      // Keep at least one asset form
      setAssets([createEmptyAsset()]);
    } else {
      setAssets(assets.filter((_, i) => i !== index));
    }
    // Clear errors for removed asset
    const newErrors = { ...errors };
    delete newErrors[index];
    setErrors(newErrors);
  };

  const handleAssetChange = (
    index: number,
    field: keyof AssetInfo,
    value: any
  ) => {
    const updatedAssets = [...assets];

    if (field === 'current_value' || field === 'amount_owed') {
      updatedAssets[index] = {
        ...updatedAssets[index],
        [field]: parseFloat(value) || 0,
      };
    } else {
      updatedAssets[index] = {
        ...updatedAssets[index],
        [field]: value,
      };
    }

    setAssets(updatedAssets);

    // Clear error for this field
    if (errors[index]?.[field]) {
      const newErrors = { ...errors };
      delete newErrors[index][field];
      setErrors(newErrors);
    }
  };

  const validateForm = () => {
    const newErrors: Record<number, Record<string, string>> = {};
    let hasValidAsset = false;

    assets.forEach((asset, index) => {
      const assetErrors: Record<string, string> = {};

      // Check if this asset has any data filled in
      const hasData =
        asset.asset_type ||
        asset.description ||
        (asset.current_value && asset.current_value > 0);

      if (hasData) {
        hasValidAsset = true;

        // Validate required fields if asset has data
        if (!asset.asset_type) {
          assetErrors.asset_type = 'Please select an asset type';
        }

        if (!asset.description?.trim()) {
          assetErrors.description = 'Please describe this asset';
        }

        if (!asset.current_value || asset.current_value <= 0) {
          assetErrors.current_value = 'Please enter the current value';
        }

        // Validate non-negative values
        if (asset.amount_owed && asset.amount_owed < 0) {
          assetErrors.amount_owed = 'Amount cannot be negative';
        }
      }

      if (Object.keys(assetErrors).length > 0) {
        newErrors[index] = assetErrors;
      }
    });

    setErrors(newErrors);
    // Valid if: no errors AND (has a complete asset OR everything is blank/empty)
    const allBlank = !hasValidAsset;
    const isValid = Object.keys(newErrors).length === 0 && (hasValidAsset || allBlank);
    onValidationChange(isValid);

    return isValid;
  };

  const calculateEquity = (asset: Partial<AssetInfo>): number => {
    const value = asset.current_value || 0;
    const owed = asset.amount_owed || 0;
    return Math.max(0, value - owed);
  };

  return (
    <div className="assets-step">
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
          <h3 className="info-title">What are assets?</h3>
          <p className="info-message">
            Assets are things you own that have value: your home, car, bank accounts,
            retirement savings, and personal property. List all assets, even if you owe
            money on them. If you don't have any assets, you can skip to the next step.
          </p>
        </div>
      </div>

      {/* Assets List */}
      {assets.map((asset, index) => (
        <section key={index} className="form-section asset-card">
          <div className="asset-card-header">
            <h3 className="section-title">
              Asset {index + 1}
              {asset.asset_type && ` - ${ASSET_TYPES.find(t => t.value === asset.asset_type)?.label}`}
            </h3>
            {assets.length > 1 && (
              <button
                type="button"
                onClick={() => handleRemoveAsset(index)}
                className="remove-asset-button"
                aria-label={`Remove asset ${index + 1}`}
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

          <FormSelect
            label="Asset Type"
            name={`asset_type_${index}`}
            options={ASSET_TYPES}
            value={asset.asset_type || ''}
            onChange={(value) => handleAssetChange(index, 'asset_type', value)}
            error={errors[index]?.asset_type}
            required
          />

          <FormField
            label="Description"
            name={`description_${index}`}
            type="text"
            value={asset.description || ''}
            onChange={(e) => handleAssetChange(index, 'description', e.target.value)}
            error={errors[index]?.description}
            required
            helpText="Brief description (e.g., '2015 Honda Civic', 'Family home at 123 Main St')"
            placeholder="Describe this asset"
          />

          <div className="form-row">
            <FormField
              label="Current Value"
              name={`current_value_${index}`}
              type="number"
              min="0"
              step="0.01"
              value={asset.current_value || ''}
              onChange={(e) => handleAssetChange(index, 'current_value', e.target.value)}
              error={errors[index]?.current_value}
              required
              helpText="Estimated current market value"
              placeholder="0.00"
            />

            <FormField
              label="Amount Owed"
              name={`amount_owed_${index}`}
              type="number"
              min="0"
              step="0.01"
              value={asset.amount_owed || ''}
              onChange={(e) => handleAssetChange(index, 'amount_owed', e.target.value)}
              error={errors[index]?.amount_owed}
              helpText="Loan balance or lien amount (if any)"
              placeholder="0.00"
            />
          </div>

          {/* Account number for bank/retirement accounts */}
          {(asset.asset_type === 'bank_account' ||
            asset.asset_type === 'retirement_account') && (
            <FormField
              label="Account Number (Last 4 Digits)"
              name={`account_number_${index}`}
              type="text"
              value={asset.account_number || ''}
              onChange={(e) => handleAssetChange(index, 'account_number', e.target.value)}
              helpText="Optional - helps identify the account. Your account number is encrypted."
              placeholder="XXXX-1234"
            />
          )}

          {/* Equity calculation */}
          {(asset.current_value || 0) > 0 && (
            <div className="equity-display">
              <span className="equity-label">Equity (Value - Amount Owed):</span>
              <span className="equity-value">
                ${calculateEquity(asset).toLocaleString('en-US', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </span>
            </div>
          )}
        </section>
      ))}

      {/* Add Asset Button */}
      <div className="add-asset-section">
        <Button
          variant="outline"
          onClick={handleAddAsset}
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
          Add Another Asset
        </Button>
      </div>

      <UPLDisclaimer text={UPL_EXEMPTION_DISCLAIMER} variant="inline" />

      {/* No Assets Option */}
      <div className="info-box info-box--secondary">
        <p>
          <strong>Don't have any assets?</strong> That's okay. You can leave this section
          blank and continue to the next step. Many people filing for bankruptcy don't
          have significant assets.
        </p>
      </div>
    </div>
  );
}

export default AssetsStep;
