/**
 * Review Step - Summary of all entered information
 *
 * Allows users to review and edit their information before
 * submitting for means test calculation.
 */

import { useEffect } from 'react';
import { UPLDisclaimer } from '../../compliance';
import { UPL_REVIEW_DISCLAIMER } from '../../../constants/upl';
import type { DebtorInfo, IncomeInfo, ExpenseInfo, AssetInfo, DebtInfo } from '../../../types/api';

interface ReviewStepProps {
  debtorData: Partial<DebtorInfo>;
  incomeData: Partial<IncomeInfo>;
  expenseData: Partial<ExpenseInfo>;
  assetsData: Partial<AssetInfo>[];
  debtsData: Partial<DebtInfo>[];
  onValidationChange: (isValid: boolean) => void;
}

export function ReviewStep({
  debtorData,
  incomeData,
  expenseData,
  assetsData,
  debtsData,
  onValidationChange,
}: ReviewStepProps) {
  
  // Always valid to proceed from review (unless we add specific checks)
  useEffect(() => {
    onValidationChange(true);
  }, [onValidationChange]);

  const formatCurrency = (amount?: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount || 0);
  };

  return (
    <div className="space-y-8">
      <div className="bg-blue-50 p-4 rounded-md border border-blue-200">
        <h3 className="text-lg font-medium text-blue-900">Review Your Information</h3>
        <p className="text-blue-700 mt-1">
          Please review the information below carefully. This information will be used to calculate your eligibility.
        </p>
      </div>

      {/* Debtor Info Summary */}
      <section className="border rounded-md p-4">
        <h4 className="text-lg font-medium mb-4 border-b pb-2">Personal Information</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <span className="text-gray-600 block">Name:</span>
            <span className="font-medium">
              {debtorData.first_name} {debtorData.middle_name} {debtorData.last_name}
            </span>
          </div>
          <div>
            <span className="text-gray-600 block">SSN:</span>
            <span className="font-medium">***-**-{debtorData.ssn?.slice(-4) || '****'}</span>
          </div>
        </div>
      </section>

      {/* Income Summary */}
      <section className="border rounded-md p-4">
        <h4 className="text-lg font-medium mb-4 border-b pb-2">Income</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <span className="text-gray-600 block">Total Monthly Income:</span>
            <span className="font-medium">{formatCurrency(incomeData.total_monthly_income)}</span>
          </div>
        </div>
      </section>

      {/* Expenses Summary */}
      <section className="border rounded-md p-4">
        <h4 className="text-lg font-medium mb-4 border-b pb-2">Monthly Expenses</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <span className="text-gray-600 block">Rent/Mortgage:</span>
            <span className="font-medium">{formatCurrency(expenseData.rent_or_mortgage)}</span>
          </div>
          <div>
            <span className="text-gray-600 block">Total Expenses:</span>
            <span className="font-medium">{formatCurrency(expenseData.total_monthly_expenses)}</span>
          </div>
        </div>
      </section>

      {/* Assets Summary */}
      <section className="border rounded-md p-4">
        <h4 className="text-lg font-medium mb-4 border-b pb-2">Assets ({assetsData.length})</h4>
        {assetsData.length === 0 ? (
          <p className="text-gray-500 italic">No assets listed.</p>
        ) : (
          <ul className="space-y-2">
            {assetsData.map((asset, index) => (
              <li key={asset.id || index} className="flex justify-between">
                <span>{asset.description || 'Unnamed Asset'} ({asset.asset_type?.replace('_', ' ')})</span>
                <span className="font-medium">{formatCurrency(asset.current_value)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Debts Summary */}
      <section className="border rounded-md p-4">
        <h4 className="text-lg font-medium mb-4 border-b pb-2">Amounts Owed ({debtsData.length})</h4>
        {debtsData.length === 0 ? (
          <p className="text-gray-500 italic">No debts listed.</p>
        ) : (
          <ul className="space-y-2">
            {debtsData.map((debt, index) => (
              <li key={debt.id || index} className="flex justify-between">
                <span>{debt.creditor_name || 'Unnamed Creditor'} ({debt.debt_type})</span>
                <span className="font-medium">{formatCurrency(debt.amount_owed)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <UPLDisclaimer text={UPL_REVIEW_DISCLAIMER} variant="banner" />
    </div>
  );
}
