/**
 * FormDashboard - Checklist of the forms in the filer's packet, with status tracking
 *
 * Reached after completing the intake wizard. Shows the forms that apply to this filer,
 * their generation status, and actions for download/filing.
 * Includes UPL disclaimer on every form interaction.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { api, APIClientError } from '../api/client';
import {
  FormCard,
  GenerateAllButton,
  DebtExplanationsPanel,
  GapsNotice,
} from '../components/forms';
import type { DebtClassification } from '../components/forms/DebtExplanationsPanel';
import type { FormCardPair, FormRefusal } from '../components/forms/FormCard';
import { UPLDisclaimer } from '../components/compliance';
import { UPL_FORM_DISCLAIMER, UPL_MEANS_TEST_DISCLAIMER } from '../constants/upl';
import {
  DASHBOARD_ERROR,
  ERROR_GENERIC,
  FILING_FEE_CHANGE_LINK,
  FILING_FEE_CHOOSE_LINK,
  FORM_103A_LINK,
  FORM_103A_URL,
  INSTALLMENTS_NOTICE,
  MEANS_FILED_BEFORE_122A1,
  MEANS_FILED_BEFORE_122A2,
  MEANS_FILED_MISMATCH,
  MEANS_LINE_43_LINK,
  MEANS_OUTCOME_ANSWER_PAGE,
  MEANS_PAGE_PHRASE,
  MEANS_PAIR_NOTICE,
  MEANS_STALE_ANSWERS,
  MEANS_TEST_PREVIEW_TITLE,
  TABLE_NOTICE_MEDIAN,
  TABLE_NOTICE_NEW_FIGURES,
  TABLE_NOTICE_SECTION_104,
  TABLE_NOTICE_STANDARDS,
} from '../constants/copy';
import { LINE_8_LABEL, PAYMENT_CHOICE_WORDS } from '../constants/formText';
import { WIZARD_STEPS } from '../constants/wizardSteps';
import { Button } from '../components/common';
import { PostTaskSurvey } from '../components/survey/PostTaskSurvey';
import type {
  CompletionGap,
  GeneratedForm,
  FormType,
  GenerateAllFormsResponse,
  DatedTableUsed,
  MeansOutcome,
  Packet,
  PaymentChoice,
} from '../types/api';
import { FORM_TYPE_METADATA } from '../types/api';
import { trackEvent } from '../utils/analytics';
import { formatIsoDate } from '../utils/formatIsoDate';
import { formatMonthYear } from '../utils/formatMonthYear';
import { meansOutcomeSentences } from '../utils/meansOutcome';
import { windowNotice } from '../utils/windowNotice';

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
  '/filing-fee': 'Go to How you will pay the filing fee',
  '/sofa': 'Go to Statement of Financial Affairs',
  '/documents': 'Go to Upload your documents',
  '/exemptions': 'Go to The property you claim as exempt',
  '/means-test': 'Go to Form 122A-2: Chapter 7 Means Test Calculation',
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

/** The sentence that names each table set, by the name the server gives it (plan R9) */
const TABLE_NOTICES: Record<string, string> = {
  'Census median income': TABLE_NOTICE_MEDIAN,
  'IRS expense standards': TABLE_NOTICE_STANDARDS,
  'Bankruptcy Code dollar amounts': TABLE_NOTICE_SECTION_104,
};

/**
 * What the forms say about the dated table they were filled from (step 3a1 spec §3.6, 3h1 §7.4).
 * None for a table this page has no words for.
 */
function tableNotice(table: DatedTableUsed): string | null {
  if (!Object.hasOwn(TABLE_NOTICES, table.name)) return null;
  const first = TABLE_NOTICES[table.name].replace('{date}', formatIsoDate(table.effective_date));
  if (!table.valid_through) return first;
  return `${first} ${TABLE_NOTICE_NEW_FIGURES.replace('{date}', formatIsoDate(table.valid_through))}`;
}

/** Form 122A-1 and Form 122A-2 are prepared and filed together (3h1): they refuse together */
const MEANS_PAIR: FormType[] = ['form_122a1', 'form_122a2'];

/**
 * The form of the pair a refusal names (its `form_type`), which may be the pair's other form
 * from the one pressed; undefined when the body names none, or a form outside the pair
 */
function formTypeOf(err: unknown): FormType | undefined {
  if (!(err instanceof APIClientError)) return undefined;
  const named = err.body?.form_type;
  return named === 'form_122a1' || named === 'form_122a2' ? named : undefined;
}

export function FormDashboard() {
  const { session, isLoading: sessionLoading } = useIntake();
  const [forms, setForms] = useState<GeneratedForm[]>([]);
  // The form types that apply to this filer, in filing order
  const [packet, setPacket] = useState<FormType[]>([]);
  const [tables, setTables] = useState<DatedTableUsed[]>([]);
  const [incomePeriod, setIncomePeriod] = useState<Packet['income_period']>(null);
  // When the secured-debt answers were last changed, as the packet reply holds it
  const [meansDebtsAnswered, setMeansDebtsAnswered] =
    useState<Packet['means_debts_answered']>(null);
  // Form 101 line 8, as the packet reply holds it; undefined while no reply has come (a refusal carries none)
  const [paymentChoice, setPaymentChoice] = useState<PaymentChoice | null | undefined>(undefined);
  // The means test's result, as the packet reply holds it (null before it is worked out, or for
  // a row saved before 3h1; a refusal carries none)
  const [outcome, setOutcome] = useState<MeansOutcome | null>(null);
  const [familySize, setFamilySize] = useState<number | null>(null);
  const [tablesGap, setTablesGap] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Refusal | null>(null);
  const [showSurvey, setShowSurvey] = useState(false);
  const [generationErrors, setGenerationErrors] = useState<GenerateAllError[]>([]);
  const [generateAllRefusal, setGenerateAllRefusal] = useState<Refusal | null>(null);
  // Each form's last refused Generate or Download, until its own Generate or Download next
  // succeeds, Generate All answers (its lists then hold every checked form's current refusal; a
  // filed form, which it returns unchecked, shows none until its next Download), or it is marked
  // filed. A refusal of Generate All's whole call leaves them.
  const [formRefusals, setFormRefusals] = useState<Partial<Record<FormType, Refusal>>>({});
  const [dischargeData, setDischargeData] = useState<DebtClassification[]>([]);
  // What the server finds missing from the intake, read once on mount (not with each reload of the forms)
  const [gaps, setGaps] = useState<CompletionGap[]>([]);
  // One pair action at a time: a second press before the first answers sends nothing. Declared
  // before the early return below, with the other hooks.
  const markingPair = useRef(false);

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
      setIncomePeriod(loadedPacket.income_period);
      setMeansDebtsAnswered(loadedPacket.means_debts_answered);
      setPaymentChoice(loadedPacket.payment_choice);
      setOutcome(loadedPacket.outcome);
      setFamilySize(loadedPacket.family_size);
      setTablesGap(loadedPacket.tables_gap);
      setError(null);
    } catch (err) {
      setIncomePeriod(null);
      setMeansDebtsAnswered(null);
      setPaymentChoice(undefined);
      setOutcome(null);
      setFamilySize(null);
      setTablesGap(null);
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

  // The packet's own error path says when the forms can't load; a failed check shows no notice
  useEffect(() => {
    if (!session) return;
    api.intake
      .gaps(session.id)
      .then((response) => setGaps(response.gaps))
      .catch((err) => {
        console.error('Failed to read the gap list', err);
        setGaps([]);
      });
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
      // Generate All's answer replaces every card's refusal: a form it refused again is in its
      // list, so as it answers the same words and link don't show twice (a card's own refusal
      // after that can repeat them), and an older refusal can't stay
      setFormRefusals({});
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
      setIncomePeriod(reloaded.income_period);
      setMeansDebtsAnswered(reloaded.means_debts_answered);
      setPaymentChoice(reloaded.payment_choice);
      setOutcome(reloaded.outcome);
      setFamilySize(reloaded.family_size);
      setTablesGap(reloaded.tables_gap);
      setError(null);
    } catch (err) {
      setIncomePeriod(null);
      setMeansDebtsAnswered(null);
      setPaymentChoice(undefined);
      setOutcome(null);
      setFamilySize(null);
      setTablesGap(null);
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
    try {
      await api.forms.markFiled(formId);
    } catch (err) {
      // Form 122A-1 and 122A-2 are worked out before they are marked filed, so a refusal shows on
      // the card, which stays unfiled
      if (form) setFormRefusal(formTypeOf(err) ?? form.form_type, refusalOf(err, ERROR_GENERIC));
      return;
    }
    // A filed form prints what was filed, which no step changes (ruling R46)
    if (form) setFormRefusal(form.form_type, undefined);
    await loadForms();
  };

  // Marks Form 122A-1 and Form 122A-2 filed together. A refusal lands on the form it names, which
  // is the partner of the card pressed when the gap is the partner's, and on the pressed card when
  // it names none (a whole-call refusal).
  const handleMarkPairFiled = async (pressed: FormType) => {
    if (!session || markingPair.current) return;
    markingPair.current = true;
    try {
      try {
        await api.forms.markPairFiled(session.id);
      } catch (err) {
        // The answer replaces what either card showed before: only the form it names refuses now
        for (const formType of MEANS_PAIR) setFormRefusal(formType, undefined);
        setFormRefusal(formTypeOf(err) ?? pressed, refusalOf(err, ERROR_GENERIC));
        return;
      }
      for (const formType of MEANS_PAIR) setFormRefusal(formType, undefined);
      await loadForms();
    } finally {
      // Released only after the list is reloaded, so a press during the reload sends nothing
      markingPair.current = false;
    }
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
  // The income window notice comes with the packet, so a refusal (which sets no window) replaces it
  const incomeWindowNotice = incomePeriod
    ? windowNotice(incomePeriod.answered_for, incomePeriod.now)
    : null;
  const incomeLink = fixLink({ step: 'income_info' });
  const noticeLinksIntake = session.status !== 'completed';
  const linkTo = linksInPageOrder(noticeLinksIntake);
  const errorLink = error ? linkTo(error) : undefined;
  // A gate the gap notice lists already has its way forward there, so the refusal says it without
  // a second link; one the notice doesn't list (its check failed, or it names a page) keeps its own
  const noticeListsRefusedStep =
    generateAllRefusal?.step !== undefined &&
    fixLink({ step: generateAllRefusal.step }) !== undefined &&
    gaps.some((gap) => gap.step === generateAllRefusal.step);
  const refusalLink =
    generateAllRefusal && !noticeListsRefusedStep ? linkTo(generateAllRefusal) : undefined;
  // The pair's refusals are information (a gap, a table or a line the calculator can't work out, §6), so they show apart from the others, which
  // are errors; the others' links come first, as they sit first on the page
  const isPair = (e: GenerateAllError) => MEANS_PAIR.includes(e.form_type as FormType);
  const otherErrors = generationErrors.filter((e) => !isPair(e));
  const pairErrors = generationErrors.filter(isPair);
  const otherErrorLinks = otherErrors.map((e) => linkTo(e));
  const pairErrorLinks = pairErrors.map((e) => linkTo(e));
  const outcomeSentences = meansOutcomeSentences(outcome, familySize, tablesGap, 'dashboard');
  const hasMeansPair = packet.includes('form_122a2');
  // The answers about the filer's secured debts are from an earlier month than today
  const staleAnswers =
    meansDebtsAnswered !== null &&
    meansDebtsAnswered.answered_on.slice(0, 7) !== meansDebtsAnswered.now.slice(0, 7);
  const meansLink = fixLink({ page: '/means-test' });
  // Form 122A-2's questions are on the page; Form 122A-1's only while that form is in the packet
  // Form 101A's questions are Contracts & Leases' landlord block: it has no `/ask` page (4b2)
  const answerPathOf = (formType: FormType): string | undefined => {
    if (formType === 'form_101a') return '/intake?step=contracts';
    return formType === 'form_122a2' || (formType === 'form_122a1' && hasMeansPair)
      ? '/means-test'
      : undefined;
  };
  // The sentence that points to the page, with the page's name as the link
  const [answerBefore, answerAfter] = MEANS_OUTCOME_ANSWER_PAGE.split(MEANS_PAGE_PHRASE);
  // A card's notice is information about the form, never a refusal: a form filed before 3h
  // first, then a filed Form 122A-1 that doesn't say its result is worked out on Form 122A-2
  // (its box 1 stored) while Form 122A-2 now applies
  const noticeOf = (form?: GeneratedForm): string | undefined => {
    if (!form) return undefined;
    if (form.filed_before_means_test) {
      if (form.form_type === 'form_122a2') return MEANS_FILED_BEFORE_122A2;
      if (form.form_type === 'form_122a1') return MEANS_FILED_BEFORE_122A1;
      return undefined;
    }
    if (
      form.form_type === 'form_122a1' &&
      form.status === 'filed' &&
      form.stored_box_2 === false &&
      hasMeansPair
    ) {
      return MEANS_FILED_MISMATCH;
    }
    return undefined;
  };
  // What Mark as Filed asks on each card of the pair, which are filed together: the pair, unless
  // the partner is already filed. A filed partner with a notice (it disagrees with this form) is
  // shown before the card marks alone; one with none marks alone at once.
  const pairOf = (formType: FormType): FormCardPair | undefined => {
    if (!hasMeansPair || !MEANS_PAIR.includes(formType)) return undefined;
    const partnerType = formType === MEANS_PAIR[0] ? MEANS_PAIR[1] : MEANS_PAIR[0];
    const partner = formsByType.get(partnerType);
    if (!partner || partner.status !== 'filed') return { kind: 'both' };
    const partnerNotice = noticeOf(partner);
    return partnerNotice
      ? { kind: 'alone', partnerLabel: FORM_TYPE_METADATA[partner.form_type].label, partnerNotice }
      : undefined;
  };
  // A detail shows on the card of each form it concerns, unless the form is filed: it prints what
  // was filed (DIG-155), which no answer given now changes
  const details = gaps.filter((gap) => gap.kind === 'detail');
  const detailsOf = (formType: FormType): CompletionGap[] =>
    formsByType.get(formType)?.status === 'filed'
      ? []
      : details.filter((gap) => gap.forms.includes(formType));
  const errorList = (errors: GenerateAllError[], links: FormRefusal['link'][]) => (
    <ul>
      {errors.map((e, index) => {
        const link = links[index];
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
  );
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

      {otherErrors.length > 0 && (
        <div className="form-dashboard-error" role="alert">
          <p>
            {otherErrors.length} form{otherErrors.length > 1 ? 's' : ''} could not be generated.
            {/* Trying again is all the filer can do about a form whose refusal names no fix */}
            {otherErrors.some((e) => !fixLink(e)) &&
              ' You can try generating them individually below.'}
          </p>
          {errorList(otherErrors, otherErrorLinks)}
        </div>
      )}

      {/* Form 122A-1 and 122A-2 wait for each other: say so as information, not as an error. A
          polite region from the start, empty until then, so a screen reader reads out the
          refusals Generate All adds to it, as a card's refusal region is */}
      <div className="form-dashboard-notice form-dashboard-pair" role="status">
        {pairErrors.length > 0 && errorList(pairErrors, pairErrorLinks)}
      </div>

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

          {/* What is still missing, above the button that would refuse for it */}
          <GapsNotice gaps={gaps} />

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

      {tables.map((table) => {
        const notice = tableNotice(table);
        return (
          notice && (
            <p key={table.name} className="form-dashboard-notice">
              {notice}
            </p>
          )
        );
      })}

      {/* The result is shown only from the outcome (a row saved before 3h1 has none); the pair
          notice shows whenever Form 122A-2 is in the packet, first, so the closing sentence is
          the block's last (H21) */}
      {hasMeansPair && (
        <section
          className="form-dashboard-notice"
          role="status"
          aria-label={MEANS_TEST_PREVIEW_TITLE}
        >
          <p>{MEANS_PAIR_NOTICE}</p>
          {outcomeSentences.map((sentence) =>
            sentence === MEANS_OUTCOME_ANSWER_PAGE ? (
              <p key={sentence}>
                {answerBefore}
                <Link to="/means-test">{MEANS_PAGE_PHRASE}</Link>
                {answerAfter}
              </p>
            ) : (
              <p key={sentence}>{sentence}</p>
            )
          )}
          {outcome === 'presumption' && outcomeSentences.length > 0 && (
            <p>
              <Link to="/means-test#line-43">{MEANS_LINE_43_LINK}</Link>
            </p>
          )}
          {outcomeSentences.length > 0 && <p>{UPL_MEANS_TEST_DISCLAIMER}</p>}
        </section>
      )}

      {incomeWindowNotice && incomeLink && (
        <div className="form-dashboard-notice">
          <p>{incomeWindowNotice}</p>
          <Link to={incomeLink.to} className="button button--primary">
            {incomeLink.label}
          </Link>
        </div>
      )}

      {staleAnswers && meansDebtsAnswered && meansLink && (
        <div className="form-dashboard-notice">
          <p>
            {MEANS_STALE_ANSWERS.replace(
              '{month}',
              formatMonthYear(meansDebtsAnswered.answered_on)
            )}
          </p>
          <Link to={meansLink.to} className="button button--primary">
            {meansLink.label}
          </Link>
        </div>
      )}

      {paymentChoice !== undefined && (
        <section className="form-dashboard-notice" aria-label={LINE_8_LABEL}>
          {paymentChoice && (
            <p>
              {LINE_8_LABEL}: <span>{PAYMENT_CHOICE_WORDS[paymentChoice]}</span>
            </p>
          )}
          {paymentChoice === 'installments' && (
            <p>
              {INSTALLMENTS_NOTICE}{' '}
              <a href={FORM_103A_URL} target="_blank" rel="noreferrer">
                {FORM_103A_LINK}
              </a>
            </p>
          )}
          <Link to="/filing-fee" className="button button--primary">
            {paymentChoice ? FILING_FEE_CHANGE_LINK : FILING_FEE_CHOOSE_LINK}
          </Link>
        </section>
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
              notice={noticeOf(formsByType.get(formType))}
              details={detailsOf(formType)}
              answerPath={answerPathOf(formType)}
              refusal={cardRefusals.get(formType)}
              onGenerate={handleGenerate}
              onDownload={handleDownload}
              onMarkFiled={handleMarkFiled}
              pair={pairOf(formType)}
              onMarkPairFiled={() => handleMarkPairFiled(formType)}
            />
          ))}
          {filedOutsidePacket.map((form) => (
            <FormCard
              key={form.form_type}
              formType={form.form_type}
              generatedForm={form}
              leftPacket
              notice={noticeOf(form)}
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
