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
import type { FormRefusal } from '../components/forms/FormCard';
import { UPLDisclaimer } from '../components/compliance';
import { UPL_FORM_DISCLAIMER } from '../constants/upl';
import { DASHBOARD_ERROR, ERROR_GENERIC } from '../constants/copy';
import { WIZARD_STEPS } from '../constants/wizardSteps';
import { Button } from '../components/common';
import { PostTaskSurvey } from '../components/survey/PostTaskSurvey';
import type {
  GeneratedForm,
  FormType,
  GenerateAllFormsResponse,
  DatedTableUsed,
} from '../types/api';
import { FORM_TYPE_METADATA } from '../types/api';
import { trackEvent } from '../utils/analytics';

type GenerateAllError = GenerateAllFormsResponse['errors'][number];

/** What a refusal names as its fix: a wizard step (a `WIZARD_STEPS` key) or a page */
type Fix = { step?: string; page?: string };

/** A refusal in the filer's words, with what fixes it */
type Refusal = { message: string } & Fix;

/**
 * What the filer reads when a call is refused (forms step 2 §5.6), and what fixes it (step 3a2
 * spec §4.5): a 422 says in plain words what to fix, with the step or page that fixes it;
 * anything else gets the generic words, since a 500's text is for operations.
 */
function refusalOf(err: unknown, generic: string): Refusal {
  return err instanceof APIClientError && err.statusCode === 422
    ? { message: err.message, step: err.step, page: err.page }
    : { message: generic };
}

/**
 * The words of the link to each page a refusal can name as its fix (step 3a1 spec §4.3): the
 * intake's own words, and "Go to" with each other page's heading (step 3a2 spec §4.5, ruling R22)
 */
const PAGE_LINK_LABELS: Record<string, string> = {
  '/intake': 'Finish your intake',
  '/fee-waiver': 'Go to Filing Fee Waiver Application',
  '/sofa': 'Go to Statement of Financial Affairs',
  '/documents': 'Go to Upload your documents',
};

/**
 * The link to what fixes a refusal (step 3a2 spec §4.5): a wizard step opens the intake at that
 * step, `/ask/<form type>` takes its form's label, and any other page its words above. None when
 * the refusal names no fix, or one this page has no words for. Only the maps' own keys count, so a
 * name such as "constructor" is no form and no page.
 */
function fixLink({ step, page }: Fix): FormRefusal['link'] {
  const wizardStep = WIZARD_STEPS.find((s) => s.key === step);
  if (wizardStep) {
    return { to: `/intake?step=${wizardStep.key}`, label: `Go to ${wizardStep.label}` };
  }
  if (!page) return undefined;
  if (page.startsWith('/ask/')) {
    const formType = page.slice('/ask/'.length);
    return Object.hasOwn(FORM_TYPE_METADATA, formType)
      ? {
          to: page,
          label: `Answer the questions for ${FORM_TYPE_METADATA[formType as FormType].label}`,
        }
      : undefined;
  }
  return Object.hasOwn(PAGE_LINK_LABELS, page)
    ? { to: page, label: PAGE_LINK_LABELS[page] }
    : undefined;
}

/**
 * Hands out the link to each refusal's fix, called in the order the page shows them. "Finish your
 * intake" goes only to the first block that offers it (ruling R4-a), so `intakeLinked` says
 * whether a block above the refusals already does.
 */
function linksInPageOrder(intakeLinked: boolean) {
  let linked = intakeLinked;
  return (fix: Fix): FormRefusal['link'] => {
    const link = fixLink(fix);
    if (link?.to !== '/intake') return link;
    if (linked) return undefined;
    linked = true;
    return link;
  };
}

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

/**
 * "2026-04-01" as "April 1, 2026", built from the ISO string's parts. Never `new Date(iso)`:
 * that is UTC midnight, which shows the day before in Chicago.
 */
function formatIsoDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number);
  return `${MONTHS[month - 1]} ${day}, ${year}`;
}

/** What the forms say about the dated table they were filled from (step 3a1 spec §3.6) */
function tableNotice(table: DatedTableUsed): string {
  const first = `These forms use the median income figures the U.S. Trustee applies to cases filed on or after ${formatIsoDate(table.effective_date)}.`;
  if (!table.valid_through) return first;
  return `${first} New figures are expected after ${formatIsoDate(table.valid_through)}. If you file after that date, download your forms again.`;
}

export function FormDashboard() {
  const { session, isLoading: sessionLoading } = useIntake();
  const [forms, setForms] = useState<GeneratedForm[]>([]);
  // The form types that apply to this filer, in filing order
  const [packet, setPacket] = useState<FormType[]>([]);
  const [tables, setTables] = useState<DatedTableUsed[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Refusal | null>(null);
  const [showSurvey, setShowSurvey] = useState(false);
  const [generationErrors, setGenerationErrors] = useState<GenerateAllError[]>([]);
  const [generateAllRefusal, setGenerateAllRefusal] = useState<Refusal | null>(null);
  // Each form's last refused Generate or Download, until its own Generate or Download next
  // succeeds, Generate All returns it in `generated` (a filed form included), or it is marked filed
  const [formRefusals, setFormRefusals] = useState<Partial<Record<FormType, Refusal>>>({});
  const [dischargeData, setDischargeData] = useState<DebtClassification[]>([]);

  // Load existing forms on mount
  const loadForms = useCallback(async () => {
    if (!session) return;

    setIsLoading(true);
    try {
      const [loadedForms, loadedPacket] = await Promise.all([
        api.forms.listBySession(session.id),
        api.forms.packet(session.id),
      ]);
      setForms(loadedForms);
      setPacket(loadedPacket.form_types);
      setTables(loadedPacket.tables);
      setError(null);
    } catch (err) {
      setError(refusalOf(err, DASHBOARD_ERROR));
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

  const setFormRefusal = (formType: FormType, refusal?: Refusal) =>
    setFormRefusals((prev) => ({ ...prev, [formType]: refusal }));

  const handleGenerate = async (formType: FormType) => {
    if (!session) return;
    try {
      const response = await api.forms.generate(session.id, formType);
      setForms((prev) => [...prev.filter((f) => f.form_type !== formType), response.form]);
      setFormRefusal(formType, undefined);
      trackEvent('form_generated', { form_type: formType, session_id: session.id });
    } catch (err) {
      setFormRefusal(formType, refusalOf(err, ERROR_GENERIC));
    }
  };

  const handleGenerateAll = async () => {
    if (!session) return;
    setGenerationErrors([]);
    setGenerateAllRefusal(null);
    try {
      const response = await api.forms.generateAll(session.id);
      setForms(response.generated);
      // Every form Generate All returns in `generated` loses its card's refusal, a filed form
      // included, which Generate All returns untouched
      response.generated.forEach((form) => setFormRefusal(form.form_type, undefined));
      setGenerationErrors(response.errors);
      trackEvent('form_generated', { form_type: 'all', session_id: session.id });
      setShowSurvey(true);
    } catch (err) {
      setGenerateAllRefusal(refusalOf(err, ERROR_GENERIC));
    }
    // Generate All works the means test out again, so the packet may have changed
    try {
      const reloaded = await api.forms.packet(session.id);
      setPacket(reloaded.form_types);
      setTables(reloaded.tables);
      setError(null);
    } catch (err) {
      setError(refusalOf(err, DASHBOARD_ERROR));
    }
  };

  const handleDownload = async (formId: number) => {
    const form = forms.find((f) => f.id === formId);
    const filename = form ? `${form.form_type}.pdf` : `form_${formId}.pdf`;
    try {
      await api.forms.downloadForm(formId, filename);
    } catch (err) {
      if (form) setFormRefusal(form.form_type, refusalOf(err, ERROR_GENERIC));
      return;
    }
    if (form) setFormRefusal(form.form_type, undefined);
    await loadForms();
  };

  const handleMarkFiled = async (formId: number) => {
    const form = forms.find((f) => f.id === formId);
    await api.forms.markFiled(formId);
    // A filed form prints what was filed, which no step changes (ruling R46)
    if (form) setFormRefusal(form.form_type, undefined);
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
  // Each refusal links to what fixes it, a step or a page (step 3a2 spec §4.5). "Finish your
  // intake" shows at most once, on the first block that offers it: the notice for an unfinished
  // intake, then the packet list's refusal, then Generate All's, then each form Generate All
  // refused, then each card's refusal (ruling R4-a). The context's status and the server's can
  // disagree.
  const noticeLinksIntake = session.status !== 'completed';
  const linkTo = linksInPageOrder(noticeLinksIntake);
  const errorLink = error ? linkTo(error) : undefined;
  const refusalLink = generateAllRefusal ? linkTo(generateAllRefusal) : undefined;
  const generationErrorLinks = generationErrors.map((e) => linkTo(e));
  const cardRefusals = new Map<FormType, FormRefusal>();
  for (const formType of [...packet, ...filedOutsidePacket.map((form) => form.form_type)]) {
    const refusal = formRefusals[formType];
    if (refusal) cardRefusals.set(formType, { message: refusal.message, link: linkTo(refusal) });
  }

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
      {noticeLinksIntake && (
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
          <p>{error.message}</p>
          {/* Our own words mean the load failed and may work again; a 422's words name
              something to fix, which a retry can't. Only a refusal that names a step or page
              links to its fix (ruling R4-b). */}
          {error.message === DASHBOARD_ERROR ? (
            <Button variant="outline" size="sm" onClick={loadForms}>
              Try Again
            </Button>
          ) : (
            errorLink && (
              <Link to={errorLink.to} className="button button--primary">
                {errorLink.label}
              </Link>
            )
          )}
        </div>
      )}

      {generateAllRefusal && (
        <div className="form-dashboard-error" role="alert">
          <p>{generateAllRefusal.message}</p>
          {refusalLink && (
            <Link to={refusalLink.to} className="button button--primary">
              {refusalLink.label}
            </Link>
          )}
        </div>
      )}

      {generationErrors.length > 0 && (
        <div className="form-dashboard-error" role="alert">
          <p>
            {generationErrors.length} form{generationErrors.length > 1 ? 's' : ''} could not be
            generated.
            {/* Trying again is all the filer can do about a form whose refusal names no fix */}
            {generationErrors.some((e) => !fixLink(e)) &&
              ' You can try generating them individually below.'}
          </p>
          <ul>
            {generationErrors.map((e, index) => {
              const link = generationErrorLinks[index];
              return (
                <li key={e.form_type}>
                  {FORM_TYPE_METADATA[e.form_type as FormType]?.label ?? e.form_type}: {e.error}
                  {link && (
                    <>
                      {' '}
                      <Link to={link.to} className="button button--primary">
                        {link.label}
                      </Link>
                    </>
                  )}
                </li>
              );
            })}
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

      {tables.map((table) => (
        <p key={table.name} className="form-dashboard-notice">
          {tableNotice(table)}
        </p>
      ))}

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
              refusal={cardRefusals.get(formType)}
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
              refusal={cardRefusals.get(form.form_type)}
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
