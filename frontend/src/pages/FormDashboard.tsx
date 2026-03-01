/**
 * FormDashboard - Checklist of all 13 bankruptcy forms with status tracking
 *
 * Reached after completing the intake wizard. Shows all required forms,
 * their generation status, and actions for download/filing.
 * Includes UPL disclaimer on every form interaction.
 */

import { useState, useEffect, useCallback } from 'react';
import { useIntake } from '../context/IntakeContext';
import { api } from '../api/client';
import { FormCard, GenerateAllButton } from '../components/forms';
import { UPLDisclaimer } from '../components/compliance';
import { UPL_FORM_DISCLAIMER } from '../constants/upl';
import { Button } from '../components/common';
import { PostTaskSurvey } from '../components/survey/PostTaskSurvey';
import type { GeneratedForm, FormType } from '../types/api';
import { FORM_TYPE_METADATA } from '../types/api';
import { trackEvent } from '../utils/analytics';

/** All form types in filing order */
const ALL_FORM_TYPES: FormType[] = (
  Object.entries(FORM_TYPE_METADATA) as [FormType, { order: number }][]
)
  .sort(([, a], [, b]) => a.order - b.order)
  .map(([key]) => key);

export function FormDashboard() {
  const { session } = useIntake();
  const [forms, setForms] = useState<GeneratedForm[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSurvey, setShowSurvey] = useState(false);

  // Load existing forms on mount
  const loadForms = useCallback(async () => {
    if (!session) return;

    setIsLoading(true);
    try {
      const loadedForms = await api.forms.listBySession(session.id);
      setForms(loadedForms);
      setError(null);
    } catch {
      setError('Unable to load your forms. Please try refreshing the page.');
    } finally {
      setIsLoading(false);
    }
  }, [session]);

  useEffect(() => {
    loadForms();
  }, [loadForms]);

  // Map form_type → GeneratedForm for quick lookup
  const formsByType = new Map(forms.map((f) => [f.form_type, f]));

  const handleGenerate = async (formType: FormType) => {
    if (!session) return;
    const response = await api.forms.generate(session.id, formType);
    setForms((prev) => [...prev.filter((f) => f.form_type !== formType), response.form]);
    trackEvent('form_generated', { form_type: formType, session_id: session.id });
  };

  const handleGenerateAll = async () => {
    if (!session) return;
    const response = await api.forms.generateAll(session.id);
    setForms(response.forms);
    trackEvent('form_generated', { form_type: 'all', session_id: session.id });
    setShowSurvey(true);
  };

  const handleMarkDownloaded = async (formId: number) => {
    await api.forms.markDownloaded(formId);
    await loadForms();
  };

  const handleMarkFiled = async (formId: number) => {
    await api.forms.markFiled(formId);
    await loadForms();
  };

  if (!session) {
    // IntakeProvider is loading session from localStorage — show loading state
    if (isLoading) {
      return (
        <div className="form-dashboard-loading" aria-live="polite">
          <p>Loading your session...</p>
        </div>
      );
    }
    return (
      <div className="form-dashboard-empty">
        <p>No active intake session found. Please complete the intake wizard first.</p>
      </div>
    );
  }

  const filedCount = forms.filter((f) => f.status === 'filed').length;
  const generatedCount = forms.length;

  return (
    <div className="form-dashboard">
      <header className="form-dashboard-header" id="main-content" tabIndex={-1}>
        <h1 className="form-dashboard-title">Your Court Forms</h1>
        <p className="form-dashboard-subtitle">
          These are the official bankruptcy forms prepared from your intake information.
          Review each form carefully before filing with the court.
        </p>
      </header>

      <UPLDisclaimer text={UPL_FORM_DISCLAIMER} variant="banner" />

      {error && (
        <div className="form-dashboard-error" role="alert">
          <p>{error}</p>
          <Button variant="outline" size="sm" onClick={loadForms}>
            Try Again
          </Button>
        </div>
      )}

      {/* Progress summary */}
      <div className="form-dashboard-progress" aria-label="Form generation progress">
        <div className="form-dashboard-progress-bar">
          <div
            className="form-dashboard-progress-fill"
            style={{ width: `${(generatedCount / ALL_FORM_TYPES.length) * 100}%` }}
            role="progressbar"
            aria-valuenow={generatedCount}
            aria-valuemin={0}
            aria-valuemax={ALL_FORM_TYPES.length}
            aria-label={`${generatedCount} of ${ALL_FORM_TYPES.length} forms generated`}
          />
        </div>
        <p className="form-dashboard-progress-text">
          {generatedCount} of {ALL_FORM_TYPES.length} generated
          {filedCount > 0 && ` | ${filedCount} filed`}
        </p>
      </div>

      {/* Generate All button */}
      <div className="form-dashboard-generate-all">
        <GenerateAllButton
          onGenerateAll={handleGenerateAll}
          generatedCount={generatedCount}
          totalCount={ALL_FORM_TYPES.length}
          disabled={isLoading}
        />
      </div>

      {/* Form cards grid */}
      {isLoading ? (
        <div className="form-dashboard-loading" aria-live="polite">
          <p>Loading your forms...</p>
        </div>
      ) : (
        <div className="form-dashboard-grid">
          {ALL_FORM_TYPES.map((formType) => (
            <FormCard
              key={formType}
              formType={formType}
              generatedForm={formsByType.get(formType)}
              onGenerate={handleGenerate}
              onMarkDownloaded={handleMarkDownloaded}
              onMarkFiled={handleMarkFiled}
            />
          ))}
        </div>
      )}

      {/* Post-task survey — shown after generating all forms */}
      {showSurvey && session && (
        <PostTaskSurvey
          sessionId={session.id}
          onComplete={() => setShowSurvey(false)}
        />
      )}
    </div>
  );
}

export default FormDashboard;
