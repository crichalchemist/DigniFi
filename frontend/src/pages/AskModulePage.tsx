/**
 * AskModulePage - Hosts the DynamicFormWizard for a specific form type.
 *
 * Reached via /ask/:formType. Fetches the UI-spec from the backend and
 * renders the dynamic wizard. On completion, navigates back to /forms.
 */

import { useParams, useNavigate } from 'react-router-dom';
import { DynamicFormWizard } from '../components/forms/DynamicFormWizard';
import { Button } from '../components/common';

const FORM_LABELS: Record<string, string> = {
  form_103b: 'Fee Waiver Application',
  form_106dec: 'Declaration About Schedules',
  form_106sum: 'Summary of Assets and Liabilities',
  form_121: 'Statement About Social Security Numbers',
  form_122a1: 'Chapter 7 Means Test',
  schedule_a_b: 'Schedule A/B - Property',
  schedule_c: 'Schedule C - Exempt Property',
  schedule_d: 'Schedule D - Secured Debts',
  schedule_e_f: 'Schedule E/F - Unsecured Debts',
  schedule_i: 'Schedule I - Current Income',
  schedule_j: 'Schedule J - Current Expenditures',
};

export function AskModulePage() {
  const { formType } = useParams<{ formType: string }>();
  const navigate = useNavigate();

  if (!formType) {
    return (
      <div className="p-6">
        <h1 className="text-xl font-bold mb-4">Form Not Found</h1>
        <p>No form type specified.</p>
        <Button onClick={() => navigate('/forms')} className="mt-4">
          Back to Forms
        </Button>
      </div>
    );
  }

  const label = FORM_LABELS[formType] || formType;

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-6">
        <Button variant="outline" size="sm" onClick={() => navigate('/forms')} className="mb-4">
          &larr; Back to Forms
        </Button>
        <h1 className="text-2xl font-bold">{label}</h1>
        <p className="text-gray-600 mt-1">Answer the questions below to complete this form.</p>
      </div>

      <DynamicFormWizard formType={formType} onComplete={() => navigate('/forms')} />
    </div>
  );
}
