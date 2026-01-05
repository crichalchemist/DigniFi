/**
 * Means Test Result Page
 *
 * Displays the result of the means test calculation with UPL-compliant messaging.
 * Trauma-informed design:
 * - Clear, non-threatening language
 * - Explains what the result means
 * - Emphasizes that this is an estimate, not a final legal determination
 */

import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { MeansTestResult as MeansTestResultType } from '../types/api';

interface MeansTestResultProps {
  sessionId: number;
}

export function MeansTestResult({ sessionId }: MeansTestResultProps) {
  const [result, setResult] = useState<MeansTestResultType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const response = await api.intake.calculateMeansTest(sessionId);
        setResult(response.means_test_result);
      } catch (err) {
        setError('Failed to calculate means test result. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
        <p className="text-gray-600">Calculating your eligibility...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto p-6 bg-red-50 rounded-lg border border-red-200 text-center">
        <h3 className="text-lg font-medium text-red-800 mb-2">Error</h3>
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (!result) return <div>No result available.</div>;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  return (
    <div className="max-w-3xl mx-auto p-6 bg-white rounded-lg shadow-sm">
      <h2 className="text-2xl font-bold mb-6 text-gray-900">Eligibility Assessment Result</h2>
      
      <div className={`p-6 rounded-md mb-8 ${result.passes_means_test ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'}`}>
        <div className="flex items-start">
          <div className={`flex-shrink-0 h-6 w-6 ${result.passes_means_test ? 'text-green-600' : 'text-yellow-600'}`}>
            {result.passes_means_test ? (
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            )}
          </div>
          <div className="ml-3">
            <h3 className={`text-lg font-medium ${result.passes_means_test ? 'text-green-800' : 'text-yellow-800'}`}>
              {result.passes_means_test ? 'You appear to qualify for Chapter 7 Bankruptcy' : 'Further Review May Be Needed'}
            </h3>
            <div className={`mt-2 text-sm ${result.passes_means_test ? 'text-green-700' : 'text-yellow-700'}`}>
              <p>{result.message}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-6 mb-8">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Calculation Details</h3>
        <div className="space-y-4">
          <div className="flex justify-between items-center border-b border-gray-200 pb-3">
            <span className="text-gray-600">Household Size</span>
            <span className="font-medium text-gray-900">{result.details.household_size}</span>
          </div>
          <div className="flex justify-between items-center border-b border-gray-200 pb-3">
            <span className="text-gray-600">Current Monthly Income (CMI)</span>
            <span className="font-medium text-gray-900">{formatCurrency(result.current_monthly_income)}</span>
          </div>
          <div className="flex justify-between items-center border-b border-gray-200 pb-3">
            <span className="text-gray-600">State Median Income ({result.details.district_name})</span>
            <span className="font-medium text-gray-900">{formatCurrency(result.median_income_threshold)}</span>
          </div>
          <div className="flex justify-between items-center pt-2">
            <span className="text-gray-600 font-medium">Disposable Monthly Income</span>
            <span className={`font-bold ${result.disposable_monthly_income > 0 ? 'text-green-600' : 'text-gray-900'}`}>
              {formatCurrency(result.disposable_monthly_income)}
            </span>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 p-4 rounded-md border border-blue-100 text-sm text-blue-800">
        <p className="font-bold mb-2 flex items-center">
          <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Important Legal Disclaimer
        </p>
        <p>
          DigniFi provides self-help legal information, not legal advice. This calculation is an estimate based on the information you provided and the current median income data for your state. 
          Only a qualified attorney can provide legal advice about your specific situation and confirm your eligibility.
        </p>
      </div>
    </div>
  );
}
