/**
 * FormDashboard - Checklist of the forms in the filer's packet, with status tracking
 *
 * Reached after completing the intake wizard. Shows the forms that apply to this filer,
 * their generation status, and actions for download/filing.
 * Includes UPL disclaimer on every form interaction.
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { api, APIClientError } from '../api/client';
import { FormCard, GenerateAllButton, DebtExplanationsPanel } from '../components/forms';
import type { DebtClassification } from '../components/forms/DebtExplanationsPanel';
import { UPLDisclaimer } from '../components/compliance';
import { UPL_FORM_DISCLAIMER } from '../constants/upl';
import { DASHBOARD_ERROR, ERROR_GENERIC } from '../constants/copy';
import { Button } from '../components/common';
import { PostTaskSurvey } from '../components/survey/PostTaskSurvey';
import type { GeneratedForm, FormType, GenerateAllFormsResponse } from '../types/api';
import { FORM_TYPE_METADATA } from '../types/api';
import { trackEvent } from '../utils/analytics';

type GenerateAllError = GenerateAllFormsResponse['errors'][number];

/**
 * What the filer reads when Generate All or the packet list is refused as a whole
 * (forms step 2 §5.6): a 422 says in plain words what to fix; anything else gets the
 * generic words, since a 500's text is for operations.
 */
function wholeCallRefusal(err: unknown, generic: string): string {
  return err instanceof APIClientError && err.statusCode === 422 ? err.message : generic;
}

export function FormDashboard() {
  const { session, isLoading: sessionLoading } = useIntake();
  const [forms, setForms] = useState<GeneratedForm[]>([]);
  // The form types that apply to this filer, in filing order
  const [packet, setPacket] = useState<FormType[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSurvey, setShowSurvey] = useState(false);
  const [generationErrors, setGenerationErrors] = useState<GenerateAllError[]>([]);
  const [generateAllRefusal, setGenerateAllRefusal] = useState<string | null>(null);
  const [dischargeData, setDischargeData] = useState<DebtClassification[]>([]);

  // Load existing forms on mount
  const loadForms = useCallback(async () => {
    if (!session) return;

    setIsLoading(true);
    try {
      const [loadedForms, packetTypes] = await Promise.all([
        api.forms.listBySession(session.id),
        api.forms.packet(session.id),
      ]);
      setForms(loadedForms);
      setPacket(packetTypes);
      setError(null);
    } catch (err) {
      setError(wholeCallRefusal(err, DASHBOARD_ERROR));
    } finally {
      setIsLoading(false);
    }
  }, [session]);

  useEffect(() => {
    loadForms();
  }, [loadForms]);

  useEffect(() => {
    if (!session) return;
    api.intake
      .getDischargeability(session.id)
      .then((data) => setDischargeData(data as DebtClassification[]))
      .catch(() => {});
  }, [session]);

  // Map form_type → GeneratedForm for quick lookup
  const formsByType = new Map(forms.map((f) => [f.form_type, f]));
  // A filed form stays after it leaves the packet, with what was filed (forms step 2 §5.6)
  const filedOutsidePacket = forms.filter(
    (f) => f.status === 'filed' && !packet.includes(f.form_type)
  );

  const handleGenerate = async (formType: FormType) => {
    if (!session) return;
    const response = await api.forms.generate(session.id, formType);
    setForms((prev) => [...prev.filter((f) => f.form_type !== formType), response.form]);
    trackEvent('form_generated', { form_type: formType, session_id: session.id });
  };

  const handleGenerateAll = async () => {
    if (!session) return;
    setGenerationErrors([]);
    setGenerateAllRefusal(null);
    try {
      const response = await api.forms.generateAll(session.id);
      setForms(response.generated);
      setGenerationErrors(response.errors);
      trackEvent('form_generated', { form_type: 'all', session_id: session.id });
      setShowSurvey(true);
    } catch (err) {
      setGenerateAllRefusal(wholeCallRefusal(err, ERROR_GENERIC));
    }
    // Generate All works the means test out again, so the packet may have changed
    try {
      setPacket(await api.forms.packet(session.id));
      setError(null);
    } catch (err) {
      setError(wholeCallRefusal(err, DASHBOARD_ERROR));
    }
  };

  const handleDownload = async (formId: number) => {
    const form = forms.find((f) => f.id === formId);
    const filename = form ? `${form.form_type}.pdf` : `form_${formId}.pdf`;
    await api.forms.downloadForm(formId, filename);
    await loadForms();
  };

  const handleMarkFiled = async (formId: number) => {
    await api.forms.markFiled(formId);
    await loadForms();
  };

  if (!session) {
    // IntakeProvider is still loading session from localStorage
    if (sessionLoading) {
      return (
        <div className="form-dashboard-loading" aria-live="polite">
          <p>Loading your session...</p>
        </div>
      );
    }
    return (
      <div className="form-dashboard-empty">
        <p>No active intake session found.</p>
        <Link to="/intake" className="button button--primary">
          Start your intake
        </Link>
      </div>
    );
  }

  const filedCount = forms.filter((f) => f.status === 'filed').length;
  const generatedCount = forms.filter((f) => packet.includes(f.form_type)).length;
  const totalCount = packet.length;

  return (
    <div className="form-dashboard">
      <header className="form-dashboard-header" id="main-content" tabIndex={-1}>
        <h1 className="form-dashboard-title">Your Court Forms</h1>
        <p className="form-dashboard-subtitle">
          These are the official bankruptcy forms prepared from your intake information. Review each
          form carefully before filing with the court.
        </p>
      </header>

      <UPLDisclaimer text={UPL_FORM_DISCLAIMER} variant="banner" />

      {/* Forms are prepared only from an intake the server marked complete (forms step 2 §5.3) */}
      {session.status !== 'completed' && (
        <div className="form-dashboard-notice">
          <p>
            Your forms are prepared from your finished intake. To finish it, go back to your intake
            and press Complete Intake on the last step.
          </p>
          <Link to="/intake" className="button button--primary">
            Finish your intake
          </Link>
        </div>
      )}

      {error && (
        <div className="form-dashboard-error" role="alert">
          <p>{error}</p>
          {/* Our own words mean the load failed and may work again; a 422's words name
              something to fix at the intake, which a retry can't */}
          {error === DASHBOARD_ERROR ? (
            <Button variant="outline" size="sm" onClick={loadForms}>
              Try Again
            </Button>
          ) : (
            <Link to="/intake" className="button button--primary">
              Finish your intake
            </Link>
          )}
        </div>
      )}

      {generateAllRefusal && (
        <div className="form-dashboard-error" role="alert">
          <p>{generateAllRefusal}</p>
        </div>
      )}

      {generationErrors.length > 0 && (
        <div className="form-dashboard-error" role="alert">
          <p>
            {generationErrors.length} form{generationErrors.length > 1 ? 's' : ''} could not be
            generated. You can try generating them individually below.
          </p>
          <ul>
            {generationErrors.map((e) => (
              <li key={e.form_type}>
                {FORM_TYPE_METADATA[e.form_type as FormType]?.label ?? e.form_type}: {e.error}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Nothing to count until the packet has loaded */}
      {totalCount > 0 && (
        <>
          {/* Progress summary */}
          <div className="form-dashboard-progress" aria-label="Form generation progress">
            <div className="form-dashboard-progress-bar">
              <div
                className="form-dashboard-progress-fill"
                style={{ width: `${(generatedCount / totalCount) * 100}%` }}
                role="progressbar"
                aria-valuenow={generatedCount}
                aria-valuemin={0}
                aria-valuemax={totalCount}
                aria-label={`${generatedCount} of ${totalCount} forms generated`}
              />
            </div>
            <p className="form-dashboard-progress-text">
              {generatedCount} of {totalCount} generated
              {filedCount > 0 && ` | ${filedCount} filed`}
            </p>
          </div>

          {/* Generate All button */}
          <div className="form-dashboard-generate-all">
            <GenerateAllButton
              onGenerateAll={handleGenerateAll}
              generatedCount={generatedCount}
              totalCount={totalCount}
              disabled={isLoading}
            />
          </div>
        </>
      )}

      {/* Form cards grid */}
      {isLoading ? (
        <div className="form-dashboard-loading" aria-live="polite">
          <p>Loading your forms...</p>
        </div>
      ) : (
        <div className="form-dashboard-grid">
          {packet.map((formType) => (
            <FormCard
              key={formType}
              formType={formType}
              generatedForm={formsByType.get(formType)}
              onGenerate={handleGenerate}
              onDownload={handleDownload}
              onMarkFiled={handleMarkFiled}
            />
          ))}
          {filedOutsidePacket.map((form) => (
            <FormCard
              key={form.form_type}
              formType={form.form_type}
              generatedForm={form}
              leftPacket
              onGenerate={handleGenerate}
              onDownload={handleDownload}
              onMarkFiled={handleMarkFiled}
            />
          ))}
        </div>
      )}

      {/* Dischargeability summary */}
      <DebtExplanationsPanel debts={dischargeData} />

      {/* Post-task survey — shown after generating all forms */}
      {showSurvey && session && (
        <PostTaskSurvey sessionId={session.id} onComplete={() => setShowSurvey(false)} />
      )}
    </div>
  );
}

export default FormDashboard;
