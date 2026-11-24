import { render, screen, waitFor, act, fireEvent, within } from '@testing-library/react';
import { vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { http, HttpResponse, delay } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider, useIntake } from '../../context/IntakeContext';
import IntakeWizard from '../IntakeWizard';
import {
  CURRENT_INCOME_FIELDS,
  DEDUCTION_FIELDS,
  EXPENSE_FIELDS,
  EXPENSE_SPECIFY_FIELDS,
  INCOME_FIELDS,
} from '../../types/api';
import {
  AB_PART_TITLES,
  EXPENSE_LINE_WORDS,
  SCHEDULE_G_NAME_LABEL,
} from '../../constants/formText';
import { ASSET_LINES } from '../../constants/assetLines';
import { fill } from '../../components/wizard/steps/claims/claimNames';
import {
  AMOUNT_DECIMALS,
  AMOUNT_NEGATIVE,
  AMOUNT_TOO_LARGE,
  CLAIM_GAP_LINE_4,
  CLAIM_GAP_LEGACY_VEHICLE,
  CODEBTOR_GAP_NO_NAME,
  CONTRACT_GAP_NO_NAME,
  DELETE_HIDDEN,
  EXPENSES_LEGACY_UTILITIES,
  HIDDEN_ANSWERS,
  ITIN_SAVED,
  LEGACY_REMOVE,
  LINE_4_PAY_BOTH,
  NOT_SAVED_TRY_AGAIN,
  NO_DEBTS_BUTTON,
  OLD_ROWS_NOTE,
  OTHER_SSN_SAVED,
  PAYSTUB_EMPLOYER_HINT,
  PETITION_ADD_OTHER_NAME,
  PETITION_GATE_EVICTION,
  REPLACE_SAVED,
  REVIEW_GAPS_UNAVAILABLE,
  REVIEW_NO_DEBTS,
  REVIEW_NOTHING_MISSING,
  SCHEDULE_I_GATE_J24,
  SCHEDULE_I_GATE_LINE_11,
  SCHEDULE_I_GATE_LINE_13,
} from '../../constants/copy';

// DebtorInfoStep reads account email via useAuth; wizard test renders without
// AuthProvider, so we stub just the user object the step needs.
vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'jane@example.com' } }),
}));

// The real layout, unless a test sets `forceContinue` to press Continue while the wizard holds it,
// so handleNext's own refusal is tested apart from the disabled button (4c-R4)
const layoutOverride = vi.hoisted(() => ({ forceContinue: false }));
vi.mock('../../components/wizard/WizardLayout', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../components/wizard/WizardLayout')>();
  const Layout = (props: Parameters<typeof actual.WizardLayout>[0]) => (
    <actual.WizardLayout {...props} canGoNext={layoutOverride.forceContinue || props.canGoNext} />
  );
  return { ...actual, WizardLayout: Layout, default: Layout };
});

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

// Form 101's gates on Assets (line 14), Amounts Owed (line 16 and Form 122A-1Supp's two military
// questions, 4d) and Contracts & Leases (line 11), answered, so a session past those steps can
// continue from them as it could before 4b and 4d asked them (PF2-T9-6)
const LATER_PETITION_GATES = {
  hazard_answer: 'no' as const,
  debt_nature: 'consumer' as const,
  disabled_veteran: 'no' as const,
  reservist: 'no' as const,
  rents_residence: 'no' as const,
};

const sessionAtStep9 = {
  id: 1,
  user: 1,
  district: 1,
  current_step: 9,
  status: 'in_progress' as const,
  created_at: '2026-01-20T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
  completed_at: null,
  income_window: { start: '2026-04-01', end: '2026-09-30' },
  debtor_info: { first_name: 'Jane', last_name: 'Doe' },
  income_info: { monthly_gross_wages: '1200.00', total_monthly_income: 1200 },
  expense_info: { rent_or_mortgage: 1000 },
  assets: [],
  debts: [],
  petition_answers: LATER_PETITION_GATES,
};

/** Session sitting on step 1 with no pre-filled data (autosave tests). */
const sessionAtStep1 = {
  id: 1,
  user: 1,
  district: 1,
  current_step: 1,
  status: 'in_progress' as const,
  created_at: '2026-01-20T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
  completed_at: null,
  income_window: { start: '2026-04-01', end: '2026-09-30' },
  debtor_info: null,
  income_info: null,
  expense_info: null,
  assets: [],
  debts: [],
};

function renderWizard(entry = '/intake') {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <IntakeProvider>
        <Routes>
          <Route path="/intake" element={<IntakeWizard />} />
          <Route path="/filing-fee" element={<div>FilingFeePage</div>} />
          <Route path="/forms" element={<div>FormDashboard</div>} />
          <Route path="/sofa" element={<div>Statement of Financial Affairs</div>} />
          <Route path="/documents" element={<div>DocumentUploadPage</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

/**
 * Presses Complete once it is enabled. Review is locked while a returned gap list holds a gate
 * (step 4a), so a press that did not wait would click a disabled button and do nothing.
 */
async function pressComplete() {
  const btn = await screen.findByRole('button', { name: /complete intake/i });
  await waitFor(() => expect(btn).toBeEnabled());
  await userEvent.click(btn);
}

// ---------------------------------------------------------------------------
// Helpers: fill every required field in DebtorInfoStep
// ---------------------------------------------------------------------------

/**
 * Fill all required DebtorInfoStep fields so that onValidationChange(true) fires.
 * Must be called after the wizard has rendered and the step is visible.
 */
async function fillDebtorInfoFields(county: string | null = 'Cook') {
  // The email field is readOnly and auto-populated from useAuth via useEffect —
  // we do not need to change it manually.

  fireEvent.change(screen.getByRole('textbox', { name: /first name/i }), {
    target: { value: 'Jane' },
  });
  fireEvent.change(screen.getByRole('textbox', { name: /last name/i }), {
    target: { value: 'Doe' },
  });
  // date input — use name selector via label
  fireEvent.change(screen.getByLabelText(/date of birth/i), {
    target: { value: '1985-06-15' },
  });
  fireEvent.change(screen.getByLabelText(/social security number/i), {
    target: { value: '900-12-3456' },
  });
  fireEvent.change(screen.getByRole('textbox', { name: /street address/i }), {
    target: { value: '123 Main St' },
  });
  fireEvent.change(screen.getByRole('textbox', { name: /city/i }), {
    target: { value: 'Chicago' },
  });
  fireEvent.change(screen.getByRole('combobox', { name: /state/i }), {
    target: { value: 'IL' },
  });
  fireEvent.change(screen.getByRole('textbox', { name: /zip code/i }), {
    target: { value: '60601' },
  });
  fireEvent.change(screen.getByRole('textbox', { name: /phone number/i }), {
    target: { value: '312-555-1234' },
  });
  if (county !== null) {
    fireEvent.change(screen.getByRole('combobox', { name: /county/i }), {
      target: { value: county },
    });
  }
  // Form 101's seven yes/noes hold Continue until each is answered (step 4b). fireEvent, not
  // userEvent, since some callers run this under fake timers.
  for (const gate of STEP_1_GATES) {
    fireEvent.click(document.querySelector(`input[name="${gate}"][value="no"]`) as HTMLElement);
  }
}

// Step 1's Form 101 yes/noes, each a gate (apps/intake/petition.py STEP_1_GATES)
const STEP_1_GATES = [
  'other_names_answer',
  'itin_answer',
  'other_ssn_answer',
  'mailing_answer',
  'prior_bankruptcy_answer',
  'pending_case_answer',
  'sole_proprietor_answer',
] as const;

// Form 101A's five landlord keys, which step 7's body sends with the rent keys, null until typed
const NO_LANDLORD = {
  landlord_name: null,
  landlord_street: null,
  landlord_city: null,
  landlord_state: null,
  landlord_zip: null,
};
// The same five keys answered, which a rent or eviction No keeps and sends
const STORED_LANDLORD = {
  landlord_name: 'Demo Property Holdings LLC',
  landlord_street: '100 Demo St',
  landlord_city: 'Chicago',
  landlord_state: 'IL',
  landlord_zip: '60601',
};

// Every key step 1's body sends under `petition_answers`, the secrets aside
const STEP_1_PETITION_KEYS = [
  'name_suffix',
  'other_names_answer',
  'itin_answer',
  'other_ssn_answer',
  'ein',
  'mailing_answer',
  'mailing_street',
  'mailing_po_box',
  'mailing_city',
  'mailing_state',
  'mailing_zip',
  'venue_choice',
  'venue_reason',
  'prior_bankruptcy_answer',
  'pending_case_answer',
  'sole_proprietor_answer',
  'business_name',
  'business_street',
  'business_city',
  'business_state',
  'business_zip',
  'business_kind',
  'other_names',
  'other_business_names',
  'prior_cases',
  'pending_cases',
];

// ===========================================================================
// Existing tests — handleComplete routing
// ===========================================================================

describe('IntakeWizard handleComplete routing', { timeout: 30_000 }, () => {
  beforeEach(() => {
    // POST (createSession) return step 9 (Review & Results — the last step)
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep9)
      ),
      http.post('http://localhost:8000/api/intake/sessions/', () =>
        HttpResponse.json({ session: sessionAtStep9, message: 'Session created.' }, { status: 201 })
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep9)
      )
    );
  });

  it.each([
    [true, 'at_or_below_median'],
    [false, 'presumption'],
    [null, 'cannot_work_out'],
  ])(
    'opens the filing-fee page after Complete whatever the means test returns (passes %s)',
    async (passes, outcome) => {
      renderWizard();
      await screen.findByRole('button', { name: /complete intake/i });
      // Registered after the session GET resolves, as the test it replaces did (load race)
      server.use(
        http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
          HttpResponse.json({
            means_test_result: {
              passes_means_test: passes,
              cmi: passes ? 1000 : 9000,
              median_income_threshold: 5000,
              outcome,
              tables_gap: null,
            },
            session_id: 1,
          })
        )
      );
      await pressComplete();
      expect(await screen.findByText('FilingFeePage')).toBeInTheDocument();
      expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
    }
  );

  // DIG-150: the dashboard can't prepare forms from an unfinished intake, and it never showed
  // why the filer had landed there. The reason belongs on Review, where they can act on it.
  it('keeps the filer on Review with the reason when Complete fails', async () => {
    // The wizard logs the failure; silenced so it doesn't read as a broken test
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    renderWizard();
    await screen.findByRole('button', { name: /complete intake/i });
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
        HttpResponse.json(
          {
            errors: [
              {
                step: 'expense_info',
                message: 'Go through the Expenses step, even if you have no expenses to enter.',
              },
            ],
            message: 'Please complete all required sections before finalizing',
          },
          { status: 400 }
        )
      )
    );

    await pressComplete();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Please complete all required sections before finalizing'
    );
    expect(
      screen.getByRole('heading', { name: /review & results/i, level: 2 })
    ).toBeInTheDocument();
    expect(screen.queryByText('FormDashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
    expect(consoleError).toHaveBeenCalledWith('Error completing intake:', expect.anything());
    consoleError.mockRestore();
  });

  // A filer who left every Income box blank is refused by the means test. Its 400 carries its own
  // sentence, which says what to do, beside a generic message, which doesn't (ruling C-5).
  it('keeps the filer on Review with the reason when only the means test fails', async () => {
    // The wizard logs the failure; silenced so it doesn't read as a broken test
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    renderWizard();
    await screen.findByRole('button', { name: /complete intake/i });
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
        HttpResponse.json(
          {
            error: 'Enter your income by source on the Income step.',
            message:
              'Unable to calculate means test. Please ensure all income information is provided.',
          },
          { status: 400 }
        )
      )
    );

    await pressComplete();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Enter your income by source on the Income step.');
    expect(alert).not.toHaveTextContent(/unable to calculate means test/i);
    expect(
      screen.getByRole('heading', { name: /review & results/i, level: 2 })
    ).toBeInTheDocument();
    expect(screen.queryByText('FormDashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('FilingFeePage')).not.toBeInTheDocument();
    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
    expect(consoleError).toHaveBeenCalledWith('Error completing intake:', expect.anything());
    consoleError.mockRestore();
  });
});

// ===========================================================================
// What Complete found missing (step 3a1 spec §4.4, DIG-181)
// ===========================================================================

describe("IntakeWizard Complete's reasons", { timeout: 30_000 }, () => {
  const REFUSED = 'Please complete all required sections before finalizing';
  const NO_INCOME = {
    step: 'income_info',
    message: 'Enter your income by source on the Income step.',
  };
  const NO_EXPENSES = {
    step: 'expense_info',
    message: 'Go through the Expenses step, even if you have no expenses to enter.',
  };

  /**
   * Complete refuses with these reasons; returns the update_step bodies the wizard sends. The
   * gap list the server holds is two-phase: empty until Complete has refused once, these reasons
   * (each a gate) after. `refused` is flipped in the Complete handler and never flipped back, so
   * Review is valid before the press and lists the refusal after it. A list that held the gates
   * from the start would lock Complete before the press. Each read of the list pushes whether
   * Complete had refused by then onto `gapReads`.
   */
  function refuseComplete(
    errors: Array<{ step: string; message: string }>,
    gapReads: boolean[] = []
  ) {
    const stepUpdates: unknown[] = [];
    let refused = false;
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () => {
        refused = true;
        return HttpResponse.json({ message: REFUSED, errors }, { status: 400 });
      }),
      http.get('http://localhost:8000/api/intake/sessions/:id/gaps/', () => {
        gapReads.push(refused);
        return HttpResponse.json({
          gaps: refused ? errors.map((error) => ({ ...error, kind: 'gate' })) : [],
        });
      }),
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          stepUpdates.push(await request.json());
          return HttpResponse.json({ session: sessionAtStep9, message: 'Step updated.' });
        }
      )
    );
    return stepUpdates;
  }

  beforeEach(() => {
    // The wizard logs each refusal; silenced so it doesn't read as a broken test
    vi.spyOn(console, 'error').mockImplementation(() => {});
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep9)
      )
    );
  });
  afterEach(() => vi.mocked(console.error).mockRestore());

  it('lists each thing Complete found missing under its general message, with a way to each step', async () => {
    renderWizard();
    await screen.findByRole('button', { name: /complete intake/i });
    const stepUpdates = refuseComplete([NO_INCOME, NO_EXPENSES]);

    await pressComplete();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(REFUSED);
    // The list comes from the gaps re-read the refusal starts, which can land after the alert
    const firstReason = await screen.findByText(NO_INCOME.message);
    // The general message comes first, then the list
    expect(
      alert.compareDocumentPosition(firstReason) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    expect(screen.getByText(NO_EXPENSES.message)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go to Income' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Go to Expenses' }));

    expect(await screen.findByRole('heading', { name: 'Expenses', level: 2 })).toBeInTheDocument();
    // Like Go Back, it moves without telling the server where the filer is
    expect(stepUpdates).toEqual([]);
  });

  it('a refused Complete naming take-home pay links to the Take-home pay step', async () => {
    renderWizard();
    await screen.findByRole('button', { name: /complete intake/i });
    refuseComplete([
      {
        step: 'take_home_pay',
        message:
          'Enter what is taken out of your pay on the Take-home pay step. If nothing is, enter $0 in one box.',
      },
    ]);

    await pressComplete();
    await userEvent.click(await screen.findByRole('button', { name: 'Go to Take-home pay' }));

    expect(
      await screen.findByRole('heading', { name: 'Take-home pay', level: 2 })
    ).toBeInTheDocument();
  });

  // A live region announces only changes to a region already on the page
  it('reads the reasons out to a screen reader, in a polite region that was on Review before them', async () => {
    const { container } = renderWizard();
    await screen.findByRole('button', { name: /complete intake/i });
    const politeRegionsBefore = Array.from(container.querySelectorAll('[aria-live="polite"]'));
    refuseComplete([NO_INCOME, NO_EXPENSES]);

    await pressComplete();

    const reason = await screen.findByText(NO_INCOME.message);
    const region = reason.closest('[aria-live="polite"]');
    expect(politeRegionsBefore).toContain(region);
    expect(region).toHaveTextContent(NO_EXPENSES.message);
  });

  it('keeps the reasons on Review after the filer dismisses the general message', async () => {
    renderWizard();
    await screen.findByRole('button', { name: /complete intake/i });
    refuseComplete([NO_INCOME, NO_EXPENSES]);
    await pressComplete();
    await screen.findByRole('alert');

    await userEvent.click(screen.getByRole('button', { name: 'Dismiss error message' }));

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText(NO_INCOME.message)).toBeInTheDocument();
    expect(screen.getByText(NO_EXPENSES.message)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go to Income' })).toBeInTheDocument();
  });

  it('shows the server\'s current list, not the old reasons, after "Go to" a step and back to Review', async () => {
    const UNCHECKED_DEBTS = {
      step: 'debts',
      message: 'Check the debts read from your documents on the Amounts Owed step.',
    };
    // Amounts Owed lets the filer continue once it holds a debt
    // and every claim question is answered, set here so the shared sessions keep theirs
    const sessionWithDebt = {
      ...sessionAtStep9,
      debts: [storedDebt],
      claim_answers: { contracts_answer: 'no', codebtors_answer: 'no', community_lived: 'no' },
    };
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionWithDebt)
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionWithDebt)
      )
    );
    const { container } = renderWizard();
    await screen.findByRole('button', { name: /complete intake/i });
    refuseComplete([UNCHECKED_DEBTS]);
    await pressComplete();

    await userEvent.click(await screen.findByRole('button', { name: 'Go to Amounts Owed' }));
    // The filer fixed it while away: the server's list is empty when Review reads it again
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/gaps/', () =>
        HttpResponse.json({ gaps: [] })
      )
    );
    for (const next of ['Contracts & Leases', 'Codebtors', 'Review & Results']) {
      const continueBtn = screen.getByRole('button', { name: 'Continue' });
      await waitFor(() => expect(continueBtn).toBeEnabled());
      await userEvent.click(continueBtn);
      await waitFor(() => expect(container.querySelector('.step-title')).toHaveTextContent(next));
    }

    expect(await screen.findByText(REVIEW_NOTHING_MISSING)).toBeInTheDocument();
    expect(screen.queryByText(UNCHECKED_DEBTS.message)).not.toBeInTheDocument();
  });

  it("shows the server's current list once the filer leaves Review and comes back", async () => {
    // Continue from Codebtors waits until Schedule H's two questions are answered (No to both,
    // with no one listed), and saves its claim answers with a session PATCH too
    const answered = {
      ...sessionAtStep9,
      claim_answers: { codebtors_answer: 'no', community_lived: 'no' },
    };
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(answered)),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(answered)
      )
    );
    renderWizard();
    await screen.findByRole('button', { name: /complete intake/i });
    const stepUpdates = refuseComplete([NO_EXPENSES]);
    await pressComplete();
    await screen.findByText(NO_EXPENSES.message);

    await userEvent.click(screen.getByRole('button', { name: 'Go Back' }));
    // The filer fixed it while away: the server's list is empty when Review reads it again
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/gaps/', () =>
        HttpResponse.json({ gaps: [] })
      )
    );
    // On Codebtors, the step before Review
    const continueBtn = await screen.findByRole('button', { name: 'Continue' });
    await waitFor(() => expect(continueBtn).toBeEnabled());
    await userEvent.click(continueBtn);

    await screen.findByRole('heading', { name: /review & results/i, level: 2 });
    expect(stepUpdates).toEqual([{ current_step: 9 }]);
    expect(await screen.findByText(REVIEW_NOTHING_MISSING)).toBeInTheDocument();
    expect(screen.queryByText(NO_EXPENSES.message)).not.toBeInTheDocument();
  });

  it('drops the reasons once Complete accepts the intake, even if the eligibility check then fails', async () => {
    // With a gate standing Review locks Complete, so the filer can't press it twice: they leave
    // Review, fix what was missing and come back. Continue from Codebtors waits until Schedule H's
    // two questions are answered
    const answered = {
      ...sessionAtStep9,
      claim_answers: { codebtors_answer: 'no', community_lived: 'no' },
    };
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(answered)),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(answered)
      )
    );
    renderWizard();
    await screen.findByRole('button', { name: /complete intake/i });
    refuseComplete([NO_EXPENSES]);
    await pressComplete();
    await screen.findByText(NO_EXPENSES.message);

    await userEvent.click(screen.getByRole('button', { name: 'Go Back' }));
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/gaps/', () =>
        HttpResponse.json({ gaps: [] })
      ),
      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
        HttpResponse.json({ message: 'Session completed.' })
      ),
      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
        HttpResponse.json(
          {
            error: NO_INCOME.message,
            message:
              'Unable to calculate means test. Please ensure all income information is provided.',
          },
          { status: 400 }
        )
      )
    );
    // On Codebtors, the step before Review
    const continueBtn = await screen.findByRole('button', { name: 'Continue' });
    await waitFor(() => expect(continueBtn).toBeEnabled());
    await userEvent.click(continueBtn);
    await screen.findByRole('heading', { name: /review & results/i, level: 2 });

    await pressComplete();

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(NO_INCOME.message));
    expect(screen.queryByText(NO_EXPENSES.message)).not.toBeInTheDocument();
  });

  it('Review reads the gap list when it opens, before Complete is pressed', async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/gaps/', () =>
        HttpResponse.json({ gaps: [{ ...NO_INCOME, kind: 'gate' }] })
      )
    );
    renderWizard();

    expect(await screen.findByText(NO_INCOME.message)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go to Income' })).toBeInTheDocument();
    // A gate standing locks the button; no press was made
    // Review reports the lock in an effect after the list shows
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /complete intake/i })).toBeDisabled()
    );
  });

  it('a refused Complete re-reads the list', async () => {
    const gapReads: boolean[] = [];
    // Installed before Review opens, so its own read is counted too
    refuseComplete([NO_INCOME, NO_EXPENSES], gapReads);
    renderWizard();
    await pressComplete();

    expect(await screen.findByText(NO_INCOME.message)).toBeInTheDocument();
    expect(screen.getByText(NO_EXPENSES.message)).toBeInTheDocument();
    // Two reads: one when Review opened (Complete not yet refused), one after the refusal
    expect(gapReads).toEqual([false, true]);
  });

  // A 400, not a 500: apiFetch retries a 5xx or a network error three times with a backoff of
  // 0.5 to 3.5 seconds, which would make this test take seconds
  it('a gap check the server refuses leaves Complete enabled and says so', async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/gaps/', () =>
        HttpResponse.json({ error: 'Demo refusal' }, { status: 400 })
      )
    );
    renderWizard();

    expect(await screen.findByText(REVIEW_GAPS_UNAVAILABLE)).toBeInTheDocument();
    // A check that failed is no answer: Review must not say nothing is missing
    expect(screen.queryByText(REVIEW_NOTHING_MISSING)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /complete intake/i })).toBeEnabled();
    expect(console.error).toHaveBeenCalledWith('Error reading what is missing:', expect.anything());
  });

  // A 500 is read three times with a backoff before it rejects, so this one takes seconds
  it('a gap check that fails with a 500 never says Nothing is missing', async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/gaps/', () =>
        HttpResponse.json({ error: 'Server error' }, { status: 500 })
      )
    );
    renderWizard();

    expect(
      await screen.findByText(REVIEW_GAPS_UNAVAILABLE, {}, { timeout: 10_000 })
    ).toBeInTheDocument();
    expect(screen.queryByText(REVIEW_NOTHING_MISSING)).not.toBeInTheDocument();
  });

  it('a gap check that returns an empty list says Nothing is missing, and not that it failed', async () => {
    renderWizard();

    expect(await screen.findByText(REVIEW_NOTHING_MISSING)).toBeInTheDocument();
    expect(screen.queryByText(REVIEW_GAPS_UNAVAILABLE)).not.toBeInTheDocument();
  });

  it("keeps Complete's own reasons, each with its step link, when the re-read after a refusal fails", async () => {
    renderWizard();
    await screen.findByRole('button', { name: /complete intake/i });
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
        HttpResponse.json({ message: REFUSED, errors: [NO_INCOME, NO_EXPENSES] }, { status: 400 })
      ),
      http.get('http://localhost:8000/api/intake/sessions/:id/gaps/', () =>
        HttpResponse.json({ error: 'Demo refusal' }, { status: 400 })
      )
    );

    await pressComplete();

    expect(await screen.findByText(NO_INCOME.message)).toBeInTheDocument();
    expect(screen.getByText(NO_EXPENSES.message)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go to Income' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go to Expenses' })).toBeInTheDocument();
    expect(screen.queryByText(REVIEW_GAPS_UNAVAILABLE)).not.toBeInTheDocument();
    // The re-read failed, so a press of Complete is still allowed to try again
    expect(screen.getByRole('button', { name: /complete intake/i })).toBeEnabled();
  });

  it("shows only the re-read list, never Complete's own reasons, when the re-read succeeds", async () => {
    renderWizard();
    await screen.findByRole('button', { name: /complete intake/i });
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
        HttpResponse.json({ message: REFUSED, errors: [NO_INCOME, NO_EXPENSES] }, { status: 400 })
      ),
      // The filer's income was fixed from another tab: the server now lists only the expenses
      http.get('http://localhost:8000/api/intake/sessions/:id/gaps/', () =>
        HttpResponse.json({ gaps: [{ ...NO_EXPENSES, kind: 'gate' }] })
      )
    );

    await pressComplete();

    expect(await screen.findByText(NO_EXPENSES.message)).toBeInTheDocument();
    expect(screen.queryByText(NO_INCOME.message)).not.toBeInTheDocument();
    expect(screen.queryByText(REVIEW_GAPS_UNAVAILABLE)).not.toBeInTheDocument();
    // A returned list holding a gate still locks Complete
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /complete intake/i })).toBeDisabled()
    );
  });
});

// ===========================================================================
// Stepping back after Complete (forms step 2 §5.3)
// ===========================================================================

/**
 * A completed intake as the API returns it. Any intake save reopens it on the server, so the
 * filer would have to press Complete again. The expenses have cents, the filer listed no assets,
 * and the debt amounts arrive as decimal strings.
 */
const completedSession = {
  ...sessionAtStep9,
  status: 'completed' as const,
  completed_at: '2026-10-12T10:00:00Z',
  debtor_info: {
    first_name: 'Jane',
    last_name: 'Doe',
    date_of_birth: '1985-06-15',
    street_address: '123 Main St',
    city: 'Chicago',
    state: 'IL',
    zip_code: '60601',
    email: 'jane@example.com',
  },
  income_info: {
    marital_status: 'not_married',
    // The API sends each amount as a decimal string, and an amount never given as null
    monthly_gross_wages: '3100.50',
    monthly_overtime: null,
    monthly_tips: '0.00',
    monthly_interest_and_dividends: null,
    monthly_pension: null,
    monthly_social_security: '99.50',
    monthly_unemployment: null,
    monthly_child_support: null,
    monthly_alimony: null,
    monthly_other_income: null,
    monthly_income: null,
    total_monthly_income: 3200,
  },
  household: { county: 'Cook', members: [] },
  expense_info: {
    data_source: 'manual',
    rent_or_mortgage: '1100.00',
    utilities: '180.10',
    home_maintenance: '0.00',
    vehicle_insurance: '85.00',
    vehicle_maintenance: '40.00',
    food_and_groceries: '450.20',
    clothing: '60.00',
    medical_expenses: '75.00',
    childcare: '400.00',
    child_support_paid: '0.00',
    insurance_not_deducted: '120.00',
    other_expenses: '50.15',
    // The server's exact decimal sum; adding the amounts in the browser gives 2560.4500000000003
    total_monthly_expenses: 2560.45,
    created_at: '2026-10-01T10:00:00Z',
    updated_at: '2026-10-01T10:00:00Z',
  },
  assets: [],
  debts: [
    {
      id: 7,
      session: 1,
      data_source: 'manual',
      creditor_name: 'Chase',
      debt_type: 'credit_card',
      amount_owed: '2500.00',
      monthly_payment: '75.00',
      is_in_collections: false,
      is_secured: false,
      collateral_description: '',
      notes: '',
      is_draft: false,
      source_document_name: null,
    },
  ],
};

describe('IntakeWizard stepping back', { timeout: 30_000 }, () => {
  it('sends no save when the filer steps back through a completed intake without changing it', async () => {
    let sessionSaves = 0;
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(completedSession)
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () => {
        sessionSaves += 1;
        return HttpResponse.json({ ...completedSession, status: 'in_progress' });
      }),
      http.get('http://localhost:8000/api/intake/sessions/:id/contracts/', () =>
        HttpResponse.json([])
      ),
      http.get('http://localhost:8000/api/intake/sessions/:id/codebtors/', () =>
        HttpResponse.json([])
      ),
      // A list save reopens a completed intake too
      http.put('http://localhost:8000/api/intake/sessions/:id/contracts/', () => {
        sessionSaves += 1;
        return HttpResponse.json([]);
      }),
      http.put('http://localhost:8000/api/intake/sessions/:id/codebtors/', () => {
        sessionSaves += 1;
        return HttpResponse.json([]);
      }),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );

    const { container } = renderWizard();
    await screen.findByRole('heading', { name: /review & results/i, level: 2 });

    // Each step gets longer than the 2 s autosave delay. findBy needs real timers, so the
    // step title is read directly while the clock is fake.
    vi.useFakeTimers();
    try {
      for (const step of [
        'Codebtors',
        'Contracts & Leases',
        'Amounts Owed',
        'Assets',
        'Expenses',
        'Take-home pay',
        'Income',
        'Your Information',
      ]) {
        act(() => {
          fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
        });
        for (let second = 0; second < 3; second += 1) {
          await act(() => vi.advanceTimersByTimeAsync(1000));
        }
        expect(container.querySelector('.step-title')).toHaveTextContent(step);
      }
    } finally {
      vi.useRealTimers();
    }

    expect(sessionSaves).toBe(0);
  });
});

// ===========================================================================
// New tests — autosave
// ===========================================================================

describe('IntakeWizard autosave', { timeout: 15_000 }, () => {
  beforeEach(() => {
    // Serve a step-1 session so the wizard lands on DebtorInfoStep
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep1)
      ),
      http.post('http://localhost:8000/api/intake/sessions/', () =>
        HttpResponse.json({ session: sessionAtStep1, message: 'Session created.' }, { status: 201 })
      ),
      // Default happy-path PATCH (overridden per-test when failure is needed)
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep1)
      )
    );
  });

  it('autosaves the current step via a debounced PATCH after the user edits a field', async () => {
    // Record PATCH bodies so we can assert what autosave actually sent.
    const patchBodies: unknown[] = [];
    server.use(
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        patchBodies.push(await request.json());
        return HttpResponse.json(sessionAtStep1);
      })
    );

    renderWizard();

    // Hydrate the session under REAL timers: findBy polls via real setTimeout, so
    // fake timers must NOT be installed while the async session load is in flight
    // (installing them earlier is what previously hung this test indefinitely).
    await screen.findByRole('heading', { name: /your information/i, level: 2 });

    // Drive the 2 s autosave debounce with fake timers (installed only AFTER the
    // async session load, so the findBy above could poll under real timers).
    vi.useFakeTimers();
    try {
      // First settle the form: filling every required field makes the step valid,
      // which flips canProceed → autosave `enabled` in a follow-up commit.
      await act(async () => {
        await fillDebtorInfoFields();
      });
      // With autosave now enabled, one more edit arms a clean debounce cycle;
      // advancing past 2 s fires it. (fireEvent is synchronous → safe under fake timers.)
      await act(async () => {
        fireEvent.change(screen.getByRole('textbox', { name: /first name/i }), {
          target: { value: 'Janet' },
        });
        await vi.advanceTimersByTimeAsync(2000);
      });
    } finally {
      vi.useRealTimers();
    }

    // Autosave must have sent at least one PATCH carrying the debtor_info slice.
    await waitFor(() => expect(patchBodies.length).toBeGreaterThan(0));
    expect(patchBodies[patchBodies.length - 1]).toEqual(
      expect.objectContaining({
        debtor_info: expect.any(Object),
        household: expect.any(Object),
        petition_answers: expect.any(Object),
      })
    );
  });

  it('sends the filer to document upload after basic info, so uploads can pre-fill the money steps', async () => {
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await fillDebtorInfoFields();

    await act(async () => {
      await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    });

    await waitFor(() => {
      expect(screen.getByText('DocumentUploadPage')).toBeInTheDocument();
    });
  });

  it('persists current_step 2 before detouring, so returning from upload resumes at Income rather than bouncing back to upload', async () => {
    // updateCurrentStep is POST /update_step/, not the PATCH that saves step data.
    const persistedSteps: unknown[] = [];
    server.use(
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          const body = (await request.json()) as Record<string, unknown>;
          persistedSteps.push(body.current_step);
          return HttpResponse.json({
            session: { ...sessionAtStep1, current_step: 2 },
            message: 'Step updated.',
          });
        }
      )
    );

    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await fillDebtorInfoFields();

    await act(async () => {
      await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    });

    await waitFor(() => {
      expect(screen.getByText('DocumentUploadPage')).toBeInTheDocument();
    });
    expect(persistedSteps).toContain(2);
  });

  it('shows save-error copy and does NOT advance to step 2 when the PATCH fails', async () => {
    // Override the PATCH to fail with a 400 so saveCurrentStepData() throws.
    // A client error is thrown immediately (utils/retry only retries 5xx), so the
    // save rejects fast instead of incurring the multi-second 5xx backoff.
    server.use(
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({ detail: 'Invalid data' }, { status: 400 })
      )
    );

    renderWizard();

    // Wait for the wizard to hydrate — step 1 heading should be visible
    await screen.findByRole('heading', { name: /your information/i, level: 2 });

    // Fill all required fields so canProceed becomes true (Continue button enabled)
    await act(async () => {
      await fillDebtorInfoFields();
    });

    // Wait for canProceed to propagate so Continue is enabled
    const continueBtn = await screen.findByRole('button', { name: /continue/i });

    // Click Continue — handleNext() calls saveNow() which calls updateSession.
    // The PATCH returns 500 → executeSave catches → saveStatus = 'error' →
    // handleNext sees `!saved` and does NOT advance the step.
    await act(async () => {
      await userEvent.click(continueBtn);
    });

    // The WizardLayout renders the error copy inside role="status" when saveStatus === 'error'
    expect(await screen.findByText(/couldn't save just now/i)).toBeInTheDocument();

    // Must still be on step 1 — the Income step heading must NOT be present
    expect(screen.queryByRole('heading', { name: /income/i, level: 2 })).not.toBeInTheDocument();
  });
});

// ===========================================================================
// Re-reading the session on every wizard entry (DIG-1, DIG-30)
// ===========================================================================

/** Session sitting on step 6 (Amounts Owed) with no debts yet. */
const sessionAtStep6 = {
  ...sessionAtStep1,
  current_step: 6,
  debtor_info: { first_name: 'Jane', last_name: 'Doe' },
  petition_answers: LATER_PETITION_GATES,
};

/** A draft debt the document processor created from an uploaded bill. */
const debtFromUploadedBill = {
  id: 7,
  session: 1,
  data_source: 'uploaded_document',
  creditor_name: 'Lakeshore Medical Group',
  debt_type: 'medical',
  monthly_payment: '0.00',
  is_in_collections: false,
  notes: '',
  created_at: '2026-10-09T10:00:00Z',
  updated_at: '2026-10-09T10:00:00Z',
  is_draft: true,
  source_document_name: 'lakeshore-bill.pdf',
};

/** Stands in for DocumentUploadPage, whose Continue button only navigates to /intake. */
function UploadPageStandIn() {
  const navigate = useNavigate();
  const { session } = useIntake();
  if (!session) return <p>Loading uploads</p>;
  return (
    <button type="button" onClick={() => navigate('/intake')}>
      Continue
    </button>
  );
}

describe('IntakeWizard session re-read', { timeout: 15_000 }, () => {
  it('shows a debt read from an uploaded bill at Amounts Owed when the filer continues from uploads, without a reload', async () => {
    // The filer reached Amounts Owed, went back to /documents (header link or browser Back)
    // and uploaded a bill. The provider loaded the session before the upload, so the copy
    // in context has no debts; only the server holds the draft.
    let serverSession: Record<string, unknown> = sessionAtStep6;
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(serverSession)
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(serverSession)
      )
    );
    localStorage.setItem('current_session_id', '1');
    render(
      <MemoryRouter initialEntries={['/documents']}>
        <IntakeProvider>
          <Routes>
            <Route path="/intake" element={<IntakeWizard />} />
            <Route path="/documents" element={<UploadPageStandIn />} />
          </Routes>
        </IntakeProvider>
      </MemoryRouter>
    );
    const continueButton = await screen.findByRole('button', { name: 'Continue' });

    // The bill has been read: the server now holds a draft debt the context never saw.
    serverSession = { ...sessionAtStep6, debts: [debtFromUploadedBill] };
    await userEvent.click(continueButton);

    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
    expect(screen.getByDisplayValue('Lakeshore Medical Group')).toBeInTheDocument();
    expect(screen.getByText('From scan')).toBeInTheDocument();
  });

  it("keeps the filer's saved place and lets them try again when the re-read fails", async () => {
    let serverBusy = true;
    let sessionsCreated = 0;
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        serverBusy
          ? HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
          : HttpResponse.json({ ...sessionAtStep1, current_step: 4 })
      ),
      http.post('http://localhost:8000/api/intake/sessions/', () => {
        sessionsCreated += 1;
        return HttpResponse.json(
          { session: sessionAtStep1, message: 'Session created.' },
          { status: 201 }
        );
      }),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({ ...sessionAtStep1, current_step: 4 })
      )
    );

    renderWizard();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "We couldn't get your latest information just now. Please try again in a moment."
    );
    // No step renders after a failed read, so autosave has nothing stale to send.
    expect(screen.queryByRole('heading', { level: 2 })).not.toBeInTheDocument();

    serverBusy = false;
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('heading', { name: /expenses/i, level: 2 })).toBeInTheDocument();
    // The filer kept their own session: nothing started a new one behind their back.
    expect(sessionsCreated).toBe(0);
  });

  it('starts one new session when the saved one is gone or belongs to someone else', async () => {
    // A shared computer: the resume pointer names another account's session, so DRF says 404.
    let sessionsCreated = 0;
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({ detail: 'Not found.' }, { status: 404 })
      ),
      http.post('http://localhost:8000/api/intake/sessions/', () => {
        sessionsCreated += 1;
        return HttpResponse.json(
          { session: { ...sessionAtStep1, id: 2 }, message: 'Session created.' },
          { status: 201 }
        );
      })
    );

    renderWizard();

    expect(
      await screen.findByRole('heading', { name: /your information/i, level: 2 })
    ).toBeInTheDocument();
    expect(sessionsCreated).toBe(1);
  });

  /** The server holds this session; returns how many update_step calls went out. */
  function savedAs(saved: Record<string, unknown>) {
    const stepUpdates = { count: 0 };
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(saved)),
      http.post('http://localhost:8000/api/intake/sessions/:id/update_step/', () => {
        stepUpdates.count += 1;
        return HttpResponse.json({ session: saved, message: 'Step updated.' });
      })
    );
    return stepUpdates;
  }

  /** What the address bar holds, and the browser's Back button */
  function AddressBar() {
    const location = useLocation();
    const navigate = useNavigate();
    return (
      <>
        <p data-testid="address">{location.pathname + location.search}</p>
        <button type="button" onClick={() => navigate(-1)}>
          Browser back
        </button>
      </>
    );
  }

  // The dashboard links a refusal to the step that fixes it (step 3a2 spec §4.5)
  it('opens at the step a link names, without moving the filer’s saved place', async () => {
    // The intake is complete, so it would open at Review
    const stepUpdates = savedAs({ ...sessionAtStep9, status: 'completed' });

    renderWizard('/intake?step=expense_info');

    expect(await screen.findByRole('heading', { name: 'Expenses', level: 2 })).toBeInTheDocument();
    expect(stepUpdates.count).toBe(0);
  });

  /** The forms dashboard's link to a step, shown once the shared session has loaded */
  function DashboardLink() {
    const { session } = useIntake();
    const navigate = useNavigate();
    return session ? (
      <button type="button" onClick={() => navigate('/intake?step=expense_info')}>
        Go to Expenses
      </button>
    ) : null;
  }

  // The dashboard and the wizard share one IntakeProvider (App's IntakeLayout): the session is
  // already loaded when a link opens the wizard, so an update_step sent through the context, as
  // Continue sends it, would reach the server
  it('opens the step a dashboard link names, the session already loaded, without moving the filer’s saved place', async () => {
    const stepUpdates = savedAs({ ...sessionAtStep9, status: 'completed' });
    localStorage.setItem('current_session_id', '1');
    render(
      <MemoryRouter initialEntries={['/forms']}>
        <IntakeProvider>
          <Routes>
            <Route path="/intake" element={<IntakeWizard />} />
            <Route path="/forms" element={<DashboardLink />} />
          </Routes>
        </IntakeProvider>
      </MemoryRouter>
    );

    await userEvent.click(await screen.findByRole('button', { name: 'Go to Expenses' }));

    expect(await screen.findByRole('heading', { name: 'Expenses', level: 2 })).toBeInTheDocument();
    // Long enough for a request sent as the step opened to reach the server
    await new Promise((resolve) => setTimeout(resolve, 1000));
    expect(stepUpdates.count).toBe(0);
  });

  // A refresh then opens the saved step, and Back leaves the wizard rather than reopening the link
  it('drops the step from the address once it has opened it, without a new history entry', async () => {
    const stepUpdates = savedAs({ ...sessionAtStep9, status: 'completed' });
    localStorage.setItem('current_session_id', '1');
    render(
      <MemoryRouter initialEntries={['/forms', '/intake?step=expense_info']} initialIndex={1}>
        <IntakeProvider>
          <Routes>
            <Route path="/intake" element={<IntakeWizard />} />
            <Route path="/forms" element={<div>FormDashboard</div>} />
          </Routes>
          <AddressBar />
        </IntakeProvider>
      </MemoryRouter>
    );

    await screen.findByRole('heading', { name: 'Expenses', level: 2 });
    await waitFor(() => expect(screen.getByTestId('address')).toHaveTextContent(/^\/intake$/));
    expect(stepUpdates.count).toBe(0);

    await userEvent.click(screen.getByRole('button', { name: 'Browser back' }));

    expect(await screen.findByText('FormDashboard')).toBeInTheDocument();
  });

  // The step is dropped only once it has opened, so a refresh during a failed read still opens it
  it('keeps the linked step in the address while the read fails, and drops it once Try again opens it', async () => {
    let serverBusy = true;
    const stepUpdates = { count: 0 };
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        serverBusy
          ? HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
          : HttpResponse.json({ ...sessionAtStep9, status: 'completed' })
      ),
      http.post('http://localhost:8000/api/intake/sessions/:id/update_step/', () => {
        stepUpdates.count += 1;
        return HttpResponse.json({ session: sessionAtStep9, message: 'Step updated.' });
      })
    );
    localStorage.setItem('current_session_id', '1');
    render(
      <MemoryRouter initialEntries={['/intake?step=expense_info']}>
        <IntakeProvider>
          <Routes>
            <Route path="/intake" element={<IntakeWizard />} />
          </Routes>
          <AddressBar />
        </IntakeProvider>
      </MemoryRouter>
    );

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "We couldn't get your latest information just now. Please try again in a moment."
    );
    expect(screen.getByTestId('address')).toHaveTextContent('/intake?step=expense_info');

    serverBusy = false;
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('heading', { name: 'Expenses', level: 2 })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('address')).toHaveTextContent(/^\/intake$/));
    expect(stepUpdates.count).toBe(0);
  });

  it('opens at the saved step when a link names no step of the wizard', async () => {
    // Saved mid-wizard, so neither the first step nor the last stands in for it
    const stepUpdates = savedAs({ ...sessionAtStep1, current_step: 6 });

    renderWizard('/intake?step=sofa');

    expect(
      await screen.findByRole('heading', { name: 'Amounts Owed', level: 2 })
    ).toBeInTheDocument();
    expect(stepUpdates.count).toBe(0);
  });
});

// ===========================================================================
// Amounts loaded from the server (DIG-2)
// ===========================================================================

/** What Continue on Amounts Owed waits on besides a name and an amount (3c3): a Demo address and the three answers */
const CLAIM_ANSWERS_DONE = {
  street_address: '1 Demo Street',
  street_2: '',
  city: 'Demo City',
  state: 'IL',
  zip_code: '60601',
  outside_us: false,
  claim_status: [],
  offset_answer: 'no',
  priority_answer: 'no',
  notice_parties: [],
};

/** A returning filer on Amounts Owed. DRF sends decimal amounts as strings. */
const sessionAtStep6WithDebts = {
  ...sessionAtStep1,
  current_step: 6,
  petition_answers: LATER_PETITION_GATES,
  debts: [
    {
      id: 7,
      session: 1,
      data_source: 'uploaded_document',
      creditor_name: 'Chase',
      debt_type: 'credit_card',
      amount_owed: '2500.00',
      monthly_payment: '75.00',
      is_in_collections: false,
      notes: '',
      is_draft: false,
      source_document_name: null,
      ...CLAIM_ANSWERS_DONE,
    },
    {
      id: 8,
      session: 1,
      data_source: 'manual',
      creditor_name: 'Mercy Hospital',
      debt_type: 'medical',
      amount_owed: '100.50',
      monthly_payment: null,
      is_in_collections: false,
      notes: '',
      is_draft: false,
      source_document_name: null,
      ...CLAIM_ANSWERS_DONE,
    },
  ],
};

/** A returning filer on Assets. The API never sends an asset's account number. */
const sessionAtStep5WithAssets = {
  ...sessionAtStep1,
  current_step: 5,
  petition_answers: LATER_PETITION_GATES,
  assets: [
    {
      id: 3,
      session: 1,
      ab_line: '1',
      asset_type: null,
      data_source: 'manual',
      description: '',
      current_value: '8000.00',
      entire_value: '8000.00',
      details: { street: '1 Elm', property_kinds: ['land'], who: 'only_you' },
    },
  ],
};

describe('IntakeWizard amounts a returning filer already entered', { timeout: 15_000 }, () => {
  let patchBodies: unknown[];

  beforeEach(() => {
    patchBodies = [];
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep6WithDebts)
      ),
      // Continue saves the step, even when the filer changed nothing. A saved list comes back
      // in the order sent, each row with its id (DIG-273).
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        patchBodies.push(body);
        return HttpResponse.json({ ...sessionAtStep6WithDebts, ...body });
      }),
      http.get('http://localhost:8000/api/intake/sessions/:id/contracts/', () =>
        HttpResponse.json([])
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
  });

  it('shows each saved amount and adds them up instead of joining them as text', async () => {
    renderWizard();

    expect(await screen.findByText('$2,600.50')).toBeInTheDocument();
    const amountInputs = screen.getAllByRole('spinbutton', { name: /^amount owed/i });
    expect(amountInputs[0]).toHaveValue(2500);
    expect(amountInputs[1]).toHaveValue(100.5);
  });

  // A row saved without its id is deleted and created again, losing what the browser never
  // receives: the account number, the link to the scanned bill and the secured flag (DIG-21).
  it('saves each debt back under its own id, with its amounts as numbers', async () => {
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));

    await waitFor(() => expect(patchBodies.length).toBeGreaterThan(0));
    const { debts } = patchBodies[0] as { debts: Record<string, unknown>[] };
    expect(debts.map((debt) => debt.id)).toEqual([7, 8]);
    expect(debts[0].amount_owed).toBe(2500);
    expect(debts[0].monthly_payment).toBe(75);
  });

  it('saves each asset back under its own id, with its amounts as numbers', async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep5WithAssets)
      )
    );
    renderWizard();
    await screen.findByRole('heading', { name: /assets/i, level: 2 });
    fireEvent.click(document.querySelector('input[name="line_1_answer"][value="yes"]')!);
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));

    await waitFor(() => expect(patchBodies.length).toBeGreaterThan(0));
    const { assets } = patchBodies[0] as { assets: Record<string, unknown>[] };
    expect(assets.map((asset) => asset.id)).toEqual([3]);
    expect(assets[0].current_value).toBe(8000);
    expect(assets[0].entire_value).toBe(8000);
  });
});

// ===========================================================================
// New assets and debts keep one id (step 3a1 spec §5, DIG-273)
// ===========================================================================

/**
 * The session server for one filer. GET sends `loaded`. A PATCH that carries assets, debts or a
 * household list stores that list as sent and returns it in the order sent, each row with its id:
 * a row sent without an id, or with one the server doesn't hold, gets the next new id, and a
 * stored row left out is gone. A household list sent as null is stored as null. Amounts come back
 * as decimal strings, and any save reopens a completed intake.
 */
function serveSessionSaves(
  loaded: Record<string, unknown>,
  held: Record<string, unknown> = loaded
) {
  let stored = held;
  let nextId = 101;
  let heldReply: Promise<void> | null = null;
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(loaded)),
    http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push(body);
      stored = { ...stored, status: 'in_progress' };
      for (const list of ['assets', 'debts']) {
        const sent = body[list] as Record<string, unknown>[] | undefined;
        if (!sent) continue;
        const heldIds = (stored[list] as Record<string, unknown>[]).map((row) => row.id);
        stored[list] = sent.map((row) => {
          const saved: Record<string, unknown> = {
            ...row,
            id: heldIds.includes(row.id) ? row.id : nextId++,
          };
          for (const amount of [
            'current_value',
            'entire_value',
            'amount_owed',
            'monthly_payment',
            'priority_amount',
            'nonpriority_amount',
            'past_due_amount',
          ]) {
            if (typeof saved[amount] === 'number') saved[amount] = saved[amount].toFixed(2);
          }
          return saved;
        });
      }
      const household = body.household as
        | { members?: Record<string, unknown>[] | null }
        | undefined;
      if (household?.members !== undefined) {
        const storedHousehold = (stored.household ?? {}) as {
          members?: Record<string, unknown>[] | null;
        };
        const heldIds = (storedHousehold.members ?? []).map((row) => row.id);
        stored.household = {
          ...storedHousehold,
          members:
            household.members === null
              ? null
              : household.members.map((row) => ({
                  ...row,
                  id: heldIds.includes(row.id) ? row.id : nextId++,
                })),
        };
      }
      // The filer's entries, then the spouse's: the same pattern as the household's members, so
      // ids come in that order (members first, then entries, then the spouse's entries)
      for (const section of ['income_info', 'spouse_income']) {
        const sent = (body[section] as { business_and_rental?: Record<string, unknown>[] | null })
          ?.business_and_rental;
        if (sent === undefined) continue;
        const storedSection = (stored[section] ?? {}) as {
          business_and_rental?: Record<string, unknown>[] | null;
        };
        const heldIds = (storedSection.business_and_rental ?? []).map((row) => row.id);
        stored[section] = {
          ...storedSection,
          business_and_rental:
            sent === null
              ? null
              : sent.map((row) => {
                  const entry: Record<string, unknown> = {
                    ...row,
                    id: heldIds.includes(row.id) ? row.id : nextId++,
                  };
                  for (const amount of ['gross', 'expenses', 'current_gross', 'current_expenses']) {
                    if (typeof entry[amount] === 'number') entry[amount] = entry[amount].toFixed(2);
                  }
                  return entry;
                }),
        };
      }
      const reply = HttpResponse.json(stored);
      if (heldReply) {
        const wait = heldReply;
        heldReply = null;
        await wait;
      }
      return reply;
    }),
    http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () => {
      stored = { ...stored, status: 'completed' };
      return HttpResponse.json({ message: 'Session completed.' });
    })
  );
  return {
    bodies,
    stored: () => stored,
    /** Keeps the next save's reply on its way until the returned function is called */
    holdNextReply: () => {
      let release = () => {};
      heldReply = new Promise<void>((resolve) => {
        release = resolve;
      });
      return release;
    },
  };
}

/** A form control by its name, as the journeys find them */
function field(name: string) {
  const control = document.querySelector(`[name="${name}"]`);
  if (!control) throw new Error(`No control named ${name}`);
  return control;
}

/** Moves the fake clock on in 1 s steps, so each save's reply lands before the next timer */
async function waitSeconds(seconds: number) {
  for (let second = 0; second < seconds; second += 1) {
    await act(() => vi.advanceTimersByTimeAsync(1000));
  }
}

/** A debt the server holds, as the amounts owed step and the list steps' Continue see it */
const storedDebt = {
  id: 7,
  session: 1,
  data_source: 'manual',
  creditor_name: 'Northwind Card Services',
  debt_type: 'credit_card',
  amount_owed: '2500.00',
  monthly_payment: '75.00',
  is_in_collections: false,
  is_secured: false,
  collateral_description: '',
  notes: '',
  is_draft: false,
  source_document_name: null,
  street_address: '1 Demo Street',
  street_2: '',
  city: 'Demo City',
  state: 'IL',
  zip_code: '60601',
  outside_us: false,
  secured_by: null,
  home_payment_line: null,
  collateral_who: null,
  lien: null,
  claim_status: [],
  offset_answer: 'no',
  priority_answer: 'no',
  notice_parties: [],
  community_debt: '',
  date_incurred: '',
  account_last_4: '',
};

describe.each([
  {
    list: 'debts',
    step: 6,
    title: /amounts owed/i,
    nameField: (index: number) => `creditor_name_${index}`,
    nameOf: (row: Record<string, unknown>) => row.creditor_name,
    amountKey: 'amount_owed',
    removeLabel: 'Remove amount owed 1',
    addLabel: /add another amount owed/i,
    // The first row is open from the start
    open: () => {},
    // Continue leaves the step
    expectMovedOn: () =>
      expect(document.querySelector('.step-title')).not.toHaveTextContent(/amounts owed/i),
    fill: (index: number, name: string, amount: string) => {
      fireEvent.change(field(`debt_type_${index}`), { target: { value: 'credit_card' } });
      fireEvent.change(field(`creditor_name_${index}`), { target: { value: name } });
      fireEvent.input(field(`amount_owed_${index}`), { target: { value: amount } });
      // The rest of what Continue now waits on (3c3): the address, and the three answers
      fireEvent.change(field(`street_address_${index}`), { target: { value: '1 Demo Street' } });
      fireEvent.change(field(`city_${index}`), { target: { value: 'Demo City' } });
      fireEvent.change(field(`state_${index}`), { target: { value: 'IL' } });
      fireEvent.change(field(`zip_code_${index}`), { target: { value: '60601' } });
      for (const [control, value] of [
        [`claim_status_${index}`, 'none'],
        [`offset_answer_${index}`, 'no'],
        [`priority_answer_${index}`, 'no'],
        [`notice_${index}`, 'no'],
      ]) {
        fireEvent.click(document.querySelector(`input[name="${control}"][value="${value}"]`)!);
      }
    },
    stored: storedDebt,
  },
  {
    list: 'assets',
    step: 5,
    title: /assets/i,
    // Line 1 opens the walk: the street names a row, and every box below completes it
    nameField: (index: number) => `line_1_${index}_street`,
    nameOf: (row: Record<string, unknown>) => (row.details as { street?: string }).street,
    amountKey: 'current_value',
    removeLabel: 'Remove item 1 on line 1',
    addLabel: 'Add another',
    open: () => {
      fireEvent.click(document.querySelector('input[name="line_1_answer"][value="yes"]')!);
    },
    // Continue shows the next Part, on the same step
    expectMovedOn: () => {
      expect(screen.getByText('Part 2 of 7')).toBeInTheDocument();
      expect(document.querySelector('.step-title')).toHaveTextContent(/assets/i);
    },
    fill: (index: number, name: string, amount: string) => {
      const box = `line_1_${index}`;
      fireEvent.change(field(`${box}_street`), { target: { value: name } });
      fireEvent.click(document.querySelector(`input[name="${box}_property_kinds"][value="land"]`)!);
      fireEvent.click(document.querySelector(`input[name="${box}_who"][value="only_you"]`)!);
      fireEvent.input(field(`${box}_entire_value`), { target: { value: amount } });
      fireEvent.input(field(`${box}_current_value`), { target: { value: amount } });
    },
    stored: {
      id: 3,
      session: 1,
      ab_line: '1',
      asset_type: null,
      data_source: 'manual',
      description: '',
      current_value: '8000.00',
      entire_value: '8000.00',
      details: { street: '1 Elm', property_kinds: ['land'], who: 'only_you' },
    },
  },
])(
  'IntakeWizard new $list keep one id',
  { timeout: 30_000 },
  ({
    list,
    step,
    title,
    nameField,
    nameOf,
    amountKey,
    removeLabel,
    addLabel,
    open,
    expectMovedOn,
    fill,
    stored,
  }) => {
    // Amounts Owed's Continue also waits for line 16 and the Supp's gates (4d), answered here
    const onStep = {
      ...sessionAtStep1,
      current_step: step,
      ...(list === 'debts' && { petition_answers: LATER_PETITION_GATES }),
    };
    const rowsSent = (body: Record<string, unknown>) => body[list] as Record<string, unknown>[];
    const idsSent = (bodies: Record<string, unknown>[]) =>
      bodies.map((body) => rowsSent(body).map((row) => row.id));

    beforeEach(() => {
      server.use(
        http.post(
          'http://localhost:8000/api/intake/sessions/:id/update_step/',
          async ({ request }) => {
            const { current_step } = (await request.json()) as { current_step: number };
            return HttpResponse.json({
              session: { ...onStep, current_step },
              message: 'Step updated.',
            });
          }
        ),
        http.post(
          'http://localhost:8000/api/audit/logs/',
          () => new HttpResponse(null, { status: 201 })
        )
      );
    });

    // A save of a row without its id replaces the row, and step 3c links rows by id
    it('saves a new row under one id across autosave, an edit and autosave, once per edit', async () => {
      const { bodies } = serveSessionSaves(onStep);
      renderWizard();
      await screen.findByRole('heading', { name: title, level: 2 });

      vi.useFakeTimers();
      try {
        // Each wait outlasts the 2 s autosave delay after the save lands
        open();
        fill(0, 'Elm Street Clinic', '1200');
        await waitSeconds(5);
        fireEvent.change(field(nameField(0)), { target: { value: 'Elm Street Health' } });
        await waitSeconds(5);
      } finally {
        vi.useRealTimers();
      }

      expect(idsSent(bodies)).toEqual([[undefined], [101]]);
      const [, second] = bodies.map(rowsSent);
      expect(nameOf(second[0])).toBe('Elm Street Health');
      // The amount the filer typed, never the reply's decimal string
      expect(second[0][amountKey]).toBe(1200);
      // The browser's own key stays in the browser
      expect(second[0]).not.toHaveProperty('_key');
    });

    it('saves a new row under one id across Continue, Go Back, an edit and Continue', async () => {
      const { bodies } = serveSessionSaves(onStep);
      renderWizard();
      await screen.findByRole('heading', { name: title, level: 2 });

      vi.useFakeTimers();
      try {
        open();
        fill(0, 'Elm Street Clinic', '1200');
        fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
        await waitSeconds(1);
        expectMovedOn();

        // Going back sends nothing: the new row's id is already in the saved copy
        fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
        await waitSeconds(3);
        expect(bodies).toHaveLength(1);

        fireEvent.change(field(nameField(0)), { target: { value: 'Elm Street Health' } });
        fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
        await waitSeconds(3);
      } finally {
        vi.useRealTimers();
      }

      expect(idsSent(bodies)).toEqual([[undefined], [101]]);
    });

    // Another tab, or a save the filer never saw land, can leave the browser with an id the server
    // no longer holds: the server stores that row under a new id, and the browser must use it
    it('saves a row sent with an id the server no longer holds under the new id it got', async () => {
      const { bodies } = serveSessionSaves(
        { ...onStep, [list]: [stored] },
        { ...onStep, [list]: [] }
      );
      renderWizard();
      await screen.findByRole('heading', { name: title, level: 2 });

      vi.useFakeTimers();
      try {
        open();
        fireEvent.change(field(nameField(0)), { target: { value: 'Edited once' } });
        await waitSeconds(3);
        fireEvent.change(field(nameField(0)), { target: { value: 'Edited twice' } });
        await waitSeconds(3);
      } finally {
        vi.useRealTimers();
      }

      expect(idsSent(bodies)).toEqual([[stored.id], [101]]);
    });

    it('drops a row the filer removed while its save was on its way, and keeps the other new row', async () => {
      const saves = serveSessionSaves(onStep);
      renderWizard();
      await screen.findByRole('heading', { name: title, level: 2 });
      const landSave = saves.holdNextReply();

      vi.useFakeTimers();
      try {
        open();
        fill(0, 'Elm Street Clinic', '1200');
        fireEvent.click(screen.getByRole('button', { name: addLabel }));
        fill(1, 'Harbor Light Dental', '300');
        await waitSeconds(3);
        expect(saves.bodies).toHaveLength(1);

        fireEvent.click(screen.getByRole('button', { name: removeLabel }));
        await act(async () => landSave());
        await waitSeconds(4);
      } finally {
        vi.useRealTimers();
      }

      expect(idsSent(saves.bodies)).toEqual([[undefined, undefined], [102]]);
      expect(nameOf(rowsSent(saves.bodies[1])[0])).toBe('Harbor Light Dental');
      expect(rowsSent(saves.stored()).map((row) => [row.id, nameOf(row)])).toEqual([
        [102, 'Harbor Light Dental'],
      ]);
    });

    // On a slow link the filer's next edit can be saved before the first save's reply brings the
    // new row's id. The wizard must settle on the id the server holds: a save carrying an id the
    // server has already replaced creates the row again, and each such save can start another.
    it('keeps the id the server holds when the filer edits while a save is on its way, without a save loop', async () => {
      const saves = serveSessionSaves(onStep);
      renderWizard();
      await screen.findByRole('heading', { name: title, level: 2 });
      const landFirstSave = saves.holdNextReply();

      vi.useFakeTimers();
      try {
        open();
        fill(0, 'Elm Street Clinic', '1200');
        await waitSeconds(3);
        expect(saves.bodies).toHaveLength(1);

        const landSecondSave = saves.holdNextReply();
        fireEvent.change(field(nameField(0)), { target: { value: 'Elm Street Health' } });
        await waitSeconds(3);
        // The two replies land 2.5 s apart, longer than the autosave delay
        await act(async () => landFirstSave());
        await waitSeconds(2);
        await act(() => vi.advanceTimersByTimeAsync(500));
        await act(async () => landSecondSave());
        await waitSeconds(15);

        // The next edit updates the row the server holds instead of replacing it
        fireEvent.change(field(nameField(0)), { target: { value: 'Elm Street Health Center' } });
        await waitSeconds(5);
      } finally {
        vi.useRealTimers();
      }

      expect(saves.bodies.length).toBeLessThanOrEqual(3);
      const [lastSent] = rowsSent(saves.bodies[saves.bodies.length - 1]);
      expect(lastSent.id).toBe(rowsSent(saves.stored())[0].id);
    });

    it('keeps the id the server holds when the filer presses Continue while a save is on its way', async () => {
      const saves = serveSessionSaves(onStep);
      renderWizard();
      await screen.findByRole('heading', { name: title, level: 2 });
      const landAutosave = saves.holdNextReply();

      vi.useFakeTimers();
      try {
        open();
        fill(0, 'Elm Street Clinic', '1200');
        await waitSeconds(3);
        expect(saves.bodies).toHaveLength(1);

        const landContinue = saves.holdNextReply();
        fireEvent.change(field(nameField(0)), { target: { value: 'Elm Street Health' } });
        fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
        await waitSeconds(1);
        // The two replies land 2.5 s apart, longer than the autosave delay
        await act(async () => landAutosave());
        await waitSeconds(2);
        await act(() => vi.advanceTimersByTimeAsync(500));
        await act(async () => landContinue());
        await waitSeconds(3);
        expectMovedOn();

        // Back on the step, the next edit updates the row the server holds instead of replacing it
        fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
        await waitSeconds(3);
        fireEvent.change(field(nameField(0)), { target: { value: 'Elm Street Health Center' } });
        await waitSeconds(5);
      } finally {
        vi.useRealTimers();
      }

      expect(saves.bodies.length).toBeLessThanOrEqual(3);
      const [lastSent] = rowsSent(saves.bodies[saves.bodies.length - 1]);
      expect(lastSent.id).toBe(rowsSent(saves.stored())[0].id);
    });
  }
);

describe('IntakeWizard the monthly payment on the Amounts Owed step', () => {
  // The server keeps what it holds for a key left out, so a cleared box must go as null
  async function continueWithPayment(value: string) {
    const { bodies } = serveSessionSaves({
      ...sessionAtStep1,
      current_step: 6,
      debts: [storedDebt],
    });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
    fireEvent.input(field('monthly_payment_0'), { target: { value } });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() => expect(bodies.length).toBeGreaterThan(0));
    return (bodies[0] as { debts: Record<string, unknown>[] }).debts[0];
  }

  it('empties a monthly payment the filer cleared, instead of keeping the old figure', async () => {
    const debt = await continueWithPayment('');
    expect(debt.monthly_payment).toBeNull();
  });

  it('saves a monthly payment typed as $0 as 0, not as empty', async () => {
    const debt = await continueWithPayment('0');
    expect(debt.monthly_payment).toBe(0);
  });
});

describe('IntakeWizard the priority answers on the Amounts Owed step', () => {
  const heldDebt = {
    ...storedDebt,
    priority_answer: 'taxes',
    priority_other: null,
    priority_amount: '3000.00',
    nonpriority_amount: '25.00',
    past_due_amount: '0.00',
  };

  async function continueWith(debt: Record<string, unknown>) {
    const { bodies } = serveSessionSaves({
      ...sessionAtStep1,
      current_step: 6,
      debts: [debt],
      petition_answers: LATER_PETITION_GATES,
    });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() => expect(bodies.length).toBeGreaterThan(0));
    return (bodies[0] as { debts: Record<string, unknown>[] }).debts[0];
  }

  it('saves each priority figure back as a number', async () => {
    expect(await continueWith(heldDebt)).toMatchObject({
      priority_answer: 'taxes',
      priority_amount: 3000,
      nonpriority_amount: 25,
      past_due_amount: 0,
    });
  });

  it('saves a blank priority figure as null', async () => {
    expect(await continueWith({ ...heldDebt, nonpriority_amount: null })).toMatchObject({
      nonpriority_amount: null,
    });
  });
});

describe('IntakeWizard the rows of the Assets step', { timeout: 30_000 }, () => {
  // A stored row left out of a save is deleted, and asset_type is read-only, so a new row has none
  it('keeps every row through Continue, whatever its type, text or Part', async () => {
    const onStep = {
      ...sessionAtStep1,
      current_step: 5,
      assets: [
        {
          id: 3,
          session: 1,
          ab_line: '1',
          asset_type: null,
          description: '',
          current_value: '8000.00',
          entire_value: '8000.00',
          details: { street: '1 Elm', property_kinds: ['land'], who: 'only_you' },
        },
        // Line 16 has no text, and Part 4 isn't the one showing
        {
          id: 4,
          session: 1,
          ab_line: '16',
          asset_type: null,
          description: '',
          current_value: '20.00',
          entire_value: null,
          details: {},
        },
      ],
    };
    const { bodies } = serveSessionSaves(onStep);
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/update_step/', () =>
        HttpResponse.json({ session: onStep, message: 'Step updated.' })
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
    renderWizard();
    await screen.findByRole('heading', { name: /assets/i, level: 2 });

    fireEvent.click(document.querySelector('input[name="line_1_answer"][value="yes"]')!);
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }));

    await waitFor(() => expect(bodies.length).toBeGreaterThan(0));
    const { assets } = bodies[0] as { assets: Record<string, unknown>[] };
    expect(assets.map((asset) => asset.id)).toEqual([3, 4]);
  });
});

describe('IntakeWizard the walk through Schedule A/B', { timeout: 30_000 }, () => {
  const onAssets = { ...sessionAtStep1, current_step: 5, petition_answers: LATER_PETITION_GATES };
  // Every line that shows, answered No
  const everyLineNo = Object.fromEntries(
    ASSET_LINES.filter((line) => line.gate === null).map((line) => [line.key, 'no'])
  );
  const asset = (overrides: Record<string, unknown>) => ({
    session: 1,
    asset_type: null,
    description: '',
    current_value: null,
    entire_value: null,
    details: {},
    ...overrides,
  });
  const oldRow = asset({
    id: 9,
    ab_line: null,
    asset_type: 'vehicle',
    description: 'Blue car',
    current_value: '5000.00',
  });
  const answerRow = asset({
    id: 3,
    ab_line: '1',
    current_value: '8000.00',
    entire_value: '8000.00',
    details: { street: '1 Elm', property_kinds: ['land'], who: 'only_you' },
  });
  const rowsSent = (body: Record<string, unknown>) => body.assets as Record<string, unknown>[];
  const answersSent = (body: Record<string, unknown>) =>
    body.asset_lines as Record<string, string | null>;
  const continueButton = () => screen.getByRole('button', { name: 'Continue' });
  const say = (key: string, value: 'yes' | 'no') =>
    fireEvent.click(document.querySelector(`input[name="line_${key}_answer"][value="${value}"]`)!);

  let stepUpdates: number[];

  beforeEach(() => {
    stepUpdates = [];
    server.use(
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          const { current_step } = (await request.json()) as { current_step: number };
          stepUpdates.push(current_step);
          return HttpResponse.json({
            session: { ...onAssets, current_step },
            message: 'Step updated.',
          });
        }
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
  });

  async function open(session: Record<string, unknown>) {
    const saves = serveSessionSaves(session);
    renderWizard();
    await screen.findByRole('heading', { name: /assets/i, level: 2 });
    return saves;
  }

  // A stored row left out of a save is deleted, so no Part may send only its own
  it('sends rows of every Part on each save, a half-filled row and an old row included', async () => {
    const { bodies } = await open({
      ...onAssets,
      assets: [
        oldRow,
        asset({ id: 4, ab_line: '16', current_value: '20.00' }),
        asset({ id: 5, ab_line: '3', details: { make: 'Ford' } }),
      ],
      asset_lines: { '16': 'yes', '3': 'yes' },
    });

    say('1', 'no');

    await waitFor(() => expect(bodies).toHaveLength(1), { timeout: 4000 });
    expect(rowsSent(bodies[0]).map((row) => row.id)).toEqual([9, 4, 5]);
    expect(rowsSent(bodies[0]).every((row) => !('_key' in row))).toBe(true);
    expect(answersSent(bodies[0])).toMatchObject({ '1': 'no', '16': 'yes', '3': 'yes' });
  });

  // Only a real edit is saved, and on the server it reopens a completed intake
  it('sends nothing when a loaded step is only visited', async () => {
    const { bodies } = await open({
      ...onAssets,
      assets: [answerRow, oldRow],
      asset_lines: { ...everyLineNo, '1': 'yes' },
    });

    vi.useFakeTimers();
    try {
      await waitSeconds(4);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies).toEqual([]);
  });

  it('the Assets body carries only the hazard keys of the petition record', async () => {
    // Every Part complete and the hazard open: the step opens at Part 7, which asks it (PF2-T9-1)
    const { bodies } = await open({
      ...onAssets,
      asset_lines: everyLineNo,
      petition_answers: { name_suffix: 'Jr.', other_names_answer: 'no', rents_residence: 'no' },
    });
    expect(screen.getByText('Part 7 of 7')).toBeInTheDocument();
    expect(continueButton()).toBeDisabled();

    fireEvent.click(document.querySelector('input[name="hazard_answer"][value="no"]')!);

    await waitFor(() => expect(bodies).toHaveLength(1), { timeout: 4000 });
    // Step 1's keys and the rent stay out: each step's body names only its own (spec §5.6)
    expect(bodies[0].petition_answers).toEqual({
      hazard_answer: 'no',
      hazard_what: null,
      hazard_why: null,
      hazard_street: null,
      hazard_city: null,
      hazard_state: null,
      hazard_zip: null,
    });
    await waitFor(() => expect(continueButton()).toBeEnabled());
  });

  it('sends nothing when the step shows again, and keeps sending a hazard text kept under a No', async () => {
    const { bodies } = await open({
      ...onAssets,
      asset_lines: everyLineNo,
      petition_answers: { hazard_answer: 'no', hazard_what: 'Barn roof' },
    });

    vi.useFakeTimers();
    try {
      await waitSeconds(4);
    } finally {
      vi.useRealTimers();
    }
    // PF2-7: the widened body is built the same way from loaded and edited answers
    expect(bodies).toEqual([]);

    say('1', 'yes');
    await waitFor(() => expect(bodies).toHaveLength(1), { timeout: 4000 });
    // PF2-T9-8: the text stays stored under the No, so it goes with every save
    expect(bodies[0].petition_answers).toMatchObject({
      hazard_answer: 'no',
      hazard_what: 'Barn roof',
    });
  });

  it('autosaves mid-Part while Continue is disabled', async () => {
    const { bodies } = await open(onAssets);

    say('1', 'yes');

    expect(continueButton()).toBeDisabled();
    await waitFor(() => expect(bodies).toHaveLength(1), { timeout: 4000 });
    expect(rowsSent(bodies[0])).toEqual([
      expect.objectContaining({ ab_line: '1', current_value: null, entire_value: null }),
    ]);
    expect(answersSent(bodies[0])['1']).toBe('yes');
  });

  // The server merges the answers and only a null clears one: a key left out keeps a hidden
  // line's old answer, and a later Yes on the gate would show it answered
  it('sends every line of the form, null for what is unanswered and for the lines a gate hides', async () => {
    const { bodies } = await open({
      ...onAssets,
      asset_lines: { ...everyLineNo, '37': 'yes', '38': 'yes', '39': 'no' },
      assets: [asset({ id: 6, ab_line: '38', description: 'Tools', current_value: '10.00' })],
    });

    expect(screen.getByText('Part 5 of 7')).toBeInTheDocument();
    say('37', 'no');
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }));

    await waitFor(() => expect(bodies).toHaveLength(1), { timeout: 4000 });
    const answers = answersSent(bodies[0]);
    expect(Object.keys(answers).sort()).toEqual(ASSET_LINES.map((line) => line.key).sort());
    expect(answers['37']).toBe('no');
    expect(answers['38']).toBeNull();
    expect(answers['39']).toBeNull();
    expect(answers['40']).toBeNull();
    expect(answers['1']).toBe('no');
  });

  it('moves Part by Part with no update_step until it leaves Part 7', async () => {
    const { bodies } = await open({ ...onAssets, asset_lines: everyLineNo });

    for (const part of [1, 2, 3, 4, 5, 6]) {
      expect(screen.getByText(`Part ${part} of 7`)).toBeInTheDocument();
      await waitFor(() => expect(continueButton()).toBeEnabled());
      await userEvent.click(continueButton());
      await screen.findByText(`Part ${part + 1} of 7`);
    }

    expect(bodies).toHaveLength(6);
    expect(stepUpdates).toEqual([]);
    expect(document.querySelector('.step-title')).toHaveTextContent('Assets');
    // Continue sits at the bottom of a long Part: the filer lands at the top of the next one
    await waitFor(() => expect(document.activeElement).toHaveTextContent(AB_PART_TITLES[7]));
  });

  it('sends update_step once on leaving Part 7', async () => {
    await open({ ...onAssets, asset_lines: everyLineNo });
    for (const part of [1, 2, 3, 4, 5, 6]) {
      await waitFor(() => expect(continueButton()).toBeEnabled());
      await userEvent.click(continueButton());
      await screen.findByText(`Part ${part + 1} of 7`);
    }

    await waitFor(() => expect(continueButton()).toBeEnabled());
    await userEvent.click(continueButton());

    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
    expect(stepUpdates).toEqual([6]);
  });

  it('Back moves to the previous Part, then the previous step', async () => {
    const { bodies } = await open({
      ...onAssets,
      asset_lines: { '1': 'no', '3': 'no', '4': 'no' },
    });
    expect(screen.getByText('Part 3 of 7')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
    expect(await screen.findByText('Part 2 of 7')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
    expect(await screen.findByText('Part 1 of 7')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));

    await screen.findByRole('heading', { name: /expenses/i, level: 2 });
    expect(stepUpdates).toEqual([]);
    expect(bodies).toEqual([]);
  });

  it('opens at the first Part with an unanswered line or an incomplete row', async () => {
    const parts1To3 = Object.fromEntries(
      ASSET_LINES.filter((line) => line.part <= 3).map((line) => [line.key, 'no'])
    );
    const { bodies } = await open({ ...onAssets, asset_lines: parts1To3 });
    expect(screen.getByText('Part 4 of 7')).toBeInTheDocument();
    expect(bodies).toEqual([]);
  });

  // The save can land after the filer has moved: Continue must not count from the Part it began on
  it('stays on the Part the filer went back to when a slow Continue lands', async () => {
    const answeredToPart3 = Object.fromEntries(
      ['1', '3', '4', '6', '7', '8', '9', '10', '11', '12', '13', '14'].map((key) => [key, 'no'])
    );
    const saves = await open({ ...onAssets, asset_lines: answeredToPart3 });
    expect(screen.getByText('Part 4 of 7')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
    await screen.findByText('Part 3 of 7');
    await waitFor(() => expect(continueButton()).toBeEnabled());

    const landSave = saves.holdNextReply();
    fireEvent.click(continueButton());
    await waitFor(() => expect(saves.bodies).toHaveLength(1));
    fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
    await screen.findByText('Part 2 of 7');

    await act(async () => {
      landSave();
      await new Promise((resolve) => setTimeout(resolve, 200));
    });

    expect(screen.getByText('Part 2 of 7')).toBeInTheDocument();
    expect(stepUpdates).toEqual([]);
  });

  it('opens at the Part of a row that lacks what its line requires, with every line answered', async () => {
    await open({
      ...onAssets,
      asset_lines: { ...everyLineNo, '3': 'yes' },
      assets: [asset({ id: 5, ab_line: '3', current_value: '100.00', details: { make: 'Ford' } })],
    });
    expect(screen.getByText('Part 2 of 7')).toBeInTheDocument();
    await waitFor(() => expect(continueButton()).toBeDisabled());
  });

  it('opens at the first Part with something left when the filer comes back from the next step', async () => {
    serveSessionSaves({ ...onAssets, current_step: 6, asset_lines: { '1': 'no' } });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));

    expect(await screen.findByText('Part 2 of 7')).toBeInTheDocument();
  });

  // T9-showstep: every way back onto the step, not only the first read, opens where the hazard is
  // asked while every line is answered and the hazard isn't (PF2-T9-1)
  it('opens at Part 7 when the filer comes back from the next step with only the hazard left', async () => {
    serveSessionSaves({
      ...onAssets,
      current_step: 6,
      asset_lines: everyLineNo,
      petition_answers: { rents_residence: 'no' },
    });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));

    expect(await screen.findByText('Part 7 of 7')).toBeInTheDocument();
    expect(document.querySelector('input[name="hazard_answer"]')).not.toBeNull();
  });

  // No line is ever suggested, not even from the old type: which line a row goes on is the filer's
  // answer, and the list says why Continue waits
  it('blocks Continue while an old row has no line, and suggests no line', async () => {
    await open({ ...onAssets, assets: [oldRow], asset_lines: everyLineNo });

    expect(screen.getByText('Part 1 of 7')).toBeInTheDocument();
    await waitFor(() => expect(continueButton()).toBeDisabled());
    expect(screen.getByText(OLD_ROWS_NOTE)).toBeInTheDocument();
    expect(screen.getByText('Blue car')).toBeInTheDocument();
    expect(screen.getByText('$5,000.00')).toBeInTheDocument();
    expect(screen.getByText('Vehicle')).toBeInTheDocument();

    const picker = field('old_row_0_line') as HTMLSelectElement;
    expect(picker.value).toBe('');
    // A gate takes no items of its own
    const offered = [...picker.options].map((option) => option.value);
    expect(offered).not.toContain('37');
    expect(offered).not.toContain('46');
    expect(offered).toContain('38');

    fireEvent.click(screen.getByRole('button', { name: 'Remove Blue car' }));
    await waitFor(() => expect(continueButton()).toBeEnabled());
  });

  it('picking a line keeps the old figure as the portion and asks for the entire value on line 3', async () => {
    const { bodies } = await open({ ...onAssets, assets: [oldRow] });

    fireEvent.change(field('old_row_0_line'), { target: { value: '3' } });
    expect(screen.queryByText(OLD_ROWS_NOTE)).toBeNull();
    say('1', 'no');
    await waitFor(() => expect(continueButton()).toBeEnabled());
    await userEvent.click(continueButton());
    await screen.findByText('Part 2 of 7');

    expect(field('line_3_0_current_value')).toHaveValue(5000);
    expect(field('line_3_0_entire_value')).toHaveValue(null);
    await waitFor(() => expect(continueButton()).toBeDisabled());
    const [row] = rowsSent(bodies[0]);
    expect(row).toMatchObject({
      id: 9,
      ab_line: '3',
      description: '',
      current_value: 5000,
      entire_value: null,
    });
    expect(answersSent(bodies[0])['3']).toBe('yes');
  });

  // Part 5 can't be reached while an old row waits on Part 1, so a filer with no answers could never
  // put a row on a line under a gate. A row on a hidden line is refused by Complete.
  it('picking a line under a gate answers the gate Yes too', async () => {
    const { bodies } = await open({ ...onAssets, assets: [oldRow] });

    fireEvent.change(field('old_row_0_line'), { target: { value: '38' } });

    await waitFor(() => expect(bodies).toHaveLength(1), { timeout: 4000 });
    expect(answersSent(bodies[0])).toMatchObject({ '37': 'yes', '38': 'yes' });
  });

  it('keeps ids across saves when a row is added on one Part and another is removed on the next', async () => {
    const { bodies, stored } = await open({
      ...onAssets,
      asset_lines: { ...everyLineNo, '3': 'yes' },
      assets: [
        asset({
          id: 7,
          ab_line: '3',
          current_value: '100.00',
          entire_value: '100.00',
          details: { make: 'Ford', who: 'only_you' },
        }),
      ],
    });

    say('1', 'yes');
    fireEvent.change(field('line_1_0_street'), { target: { value: '1 Elm' } });
    fireEvent.click(document.querySelector('input[name="line_1_0_property_kinds"][value="land"]')!);
    fireEvent.click(document.querySelector('input[name="line_1_0_who"][value="only_you"]')!);
    fireEvent.input(field('line_1_0_entire_value'), { target: { value: '500' } });
    fireEvent.input(field('line_1_0_current_value'), { target: { value: '500' } });
    await waitFor(() => expect(continueButton()).toBeEnabled());
    await userEvent.click(continueButton());
    await screen.findByText('Part 2 of 7');

    fireEvent.click(screen.getByRole('button', { name: 'Remove item 1 on line 3' }));
    say('3', 'no');
    await waitFor(() => expect(continueButton()).toBeEnabled());
    await userEvent.click(continueButton());
    await screen.findByText('Part 3 of 7');

    // An autosave can land between the presses on a slow run, so the first and last are the point:
    // the new row left with no id, and came back on the next Part with the one it was given.
    const idsSent = bodies.map((body) => rowsSent(body).map((row) => row.id));
    expect(idsSent[0]).toEqual([7, undefined]);
    expect(idsSent[idsSent.length - 1]).toEqual([101]);
    expect((stored().assets as { id: number }[]).map((row) => row.id)).toEqual([101]);
  });

  it('reads back a completed intake with no save and reopens only on an edit', async () => {
    const { bodies, stored } = await open({
      ...onAssets,
      status: 'completed',
      assets: [answerRow],
      asset_lines: { ...everyLineNo, '1': 'yes' },
    });

    vi.useFakeTimers();
    try {
      await waitSeconds(4);
      expect(bodies).toEqual([]);
      expect(stored().status).toBe('completed');

      fireEvent.change(field('line_1_0_street'), { target: { value: '2 Elm' } });
      await waitSeconds(4);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies).toHaveLength(1);
    expect(stored().status).toBe('in_progress');
  });

  // A $0 is an answer: on a leased car, it must not come back as unanswered
  it('takes a stored $0 back through the wizard as an answer, not a blank', async () => {
    const { bodies } = await open({
      ...onAssets,
      asset_lines: { ...everyLineNo, '1': 'yes' },
      assets: [{ ...answerRow, current_value: '0.00', entire_value: '0.00' }],
    });

    expect(field('line_1_0_current_value')).toHaveValue(0);
    expect(field('line_1_0_entire_value')).toHaveValue(0);
    await waitFor(() => expect(continueButton()).toBeEnabled());
    await userEvent.click(continueButton());

    await screen.findByText('Part 2 of 7');
    expect(rowsSent(bodies[0])[0]).toMatchObject({ current_value: 0, entire_value: 0 });
  });

  // An absent key leaves the server's figure in place, so it must go as null
  it('clears a stored figure when the filer presses I do not know after a reload', async () => {
    const { bodies } = await open({
      ...onAssets,
      asset_lines: { ...everyLineNo, '1': 'yes' },
      assets: [answerRow],
    });

    fireEvent.click(field('line_1_0_entire_unknown'));

    await waitFor(() => expect(bodies).toHaveLength(1), { timeout: 4000 });
    const [row] = rowsSent(bodies[0]);
    expect(row).toHaveProperty('entire_value', null);
    expect(row.details).toMatchObject({ entire_unknown: true });
  });
});

describe('IntakeWizard a new debt after Complete', { timeout: 30_000 }, () => {
  // Any save reopens a completed intake, and the filer would have to press Complete again. Once a
  // new debt has its id, stepping back over Amounts Owed must not save it again.
  it('keeps a completed intake completed when the filer steps back to the debt they added', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    // The answers Contracts and Codebtors will wait on, so Continue is enabled at both
    const saves = serveSessionSaves({
      ...sessionAtStep1,
      current_step: 6,
      claim_answers: {
        no_debts: null,
        contracts_answer: 'no',
        codebtors_answer: 'no',
        community_lived: 'no',
      },
      petition_answers: LATER_PETITION_GATES,
    });
    server.use(
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          const { current_step } = (await request.json()) as { current_step: number };
          return HttpResponse.json({
            session: { ...sessionAtStep1, current_step },
            message: 'Step updated.',
          });
        }
      ),
      // The means test fails after Complete accepts the intake, so the filer stays on Review
      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
        HttpResponse.json({ message: 'Unable to calculate means test.' }, { status: 400 })
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
    const { container } = renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
    const stepTitle = () => container.querySelector('.step-title');

    fireEvent.change(field('debt_type_0'), { target: { value: 'credit_card' } });
    fireEvent.change(field('creditor_name_0'), { target: { value: 'Elm Street Clinic' } });
    fireEvent.input(field('amount_owed_0'), { target: { value: '1200' } });
    fireEvent.change(field('street_address_0'), { target: { value: '1 Demo Street' } });
    fireEvent.change(field('city_0'), { target: { value: 'Demo City' } });
    fireEvent.change(field('state_0'), { target: { value: 'IL' } });
    fireEvent.change(field('zip_code_0'), { target: { value: '60601' } });
    for (const [control, value] of [
      ['claim_status_0', 'none'],
      ['offset_answer_0', 'no'],
      ['priority_answer_0', 'no'],
      ['notice_0', 'no'],
    ]) {
      fireEvent.click(document.querySelector(`input[name="${control}"][value="${value}"]`)!);
    }
    for (const next of ['Contracts & Leases', 'Codebtors', 'Review & Results']) {
      const continueBtn = screen.getByRole('button', { name: 'Continue' });
      await waitFor(() => expect(continueBtn).toBeEnabled());
      await userEvent.click(continueBtn);
      await waitFor(() => expect(stepTitle()).toHaveTextContent(next));
    }
    await userEvent.click(screen.getByRole('button', { name: /complete intake/i }));
    await screen.findByRole('alert');
    expect(saves.stored().status).toBe('completed');
    // Steps 7 and 8 each send a PATCH of their claim answers too, so the count is taken here
    const savesBefore = saves.bodies.length;

    vi.useFakeTimers();
    try {
      for (const step of ['Codebtors', 'Contracts & Leases', 'Amounts Owed']) {
        fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
        await waitSeconds(3);
        expect(stepTitle()).toHaveTextContent(step);
      }
    } finally {
      vi.useRealTimers();
    }

    expect(saves.bodies).toHaveLength(savesBefore);
    expect(saves.stored().status).toBe('completed');
    consoleError.mockRestore();
  });
});

// Step 2's Schedule I answers while none is given (4c-R7): yours and lines 11 and 13, each null
const SCHEDULE_I_STEP_2_NULL = {
  employment_status: null,
  occupation: null,
  employer_name: null,
  employer_street: null,
  employer_street_2: null,
  employer_city: null,
  employer_state: null,
  employer_zip: null,
  time_employed: null,
  line_11_answer: null,
  line_11_text: null,
  line_11_amount: null,
  line_13_answer: null,
  line_13_text: null,
};
// The spouse's line 1, sent only for a spouse at home (married_together, not filing)
const SCHEDULE_I_SPOUSE_NULL = {
  spouse_employment_status: null,
  spouse_occupation: null,
  spouse_employer_name: null,
  spouse_employer_street: null,
  spouse_employer_street_2: null,
  spouse_employer_city: null,
  spouse_employer_state: null,
  spouse_employer_zip: null,
  spouse_time_employed: null,
};
// Lines 11 and 13 answered No, so a test that presses Continue on step 2 can leave the step
// (4c-R4, PF-4c-I: never in the shared onIncome, whose radios all start unchecked)
const LINES_11_13_NO = { line_11_answer: 'no' as const, line_13_answer: 'no' as const };

// ===========================================================================
// Income save (DIG-41)
// ===========================================================================

describe('IntakeWizard income save', { timeout: 15_000 }, () => {
  // What the API returns for a filer who saved income by source through the wizard: decimal
  // strings, null for a box left empty, and null for the marriage question not yet answered.
  // The old total is read-only.
  const savedSession = {
    ...sessionAtStep1,
    current_step: 2,
    income_info: {
      marital_status: null,
      monthly_gross_wages: '3100.50',
      monthly_overtime: null,
      monthly_tips: '0.00',
      monthly_interest_and_dividends: null,
      monthly_pension: null,
      monthly_social_security: '99.50',
      monthly_unemployment: null,
      monthly_child_support: null,
      monthly_alimony: null,
      monthly_other_income: null,
      monthly_income: null,
      total_monthly_income: 3200,
      created_at: '2026-10-01T10:00:00Z',
    },
    // Lines 11 and 13 answered, so Continue can leave the step (4c-R4); answered_on is read-only
    schedule_i_answers: { ...LINES_11_13_NO, answered_on: '2026-10-16' },
  };
  const savedAmounts = {
    monthly_gross_wages: 3100.5,
    monthly_overtime: null,
    monthly_tips: 0,
    monthly_interest_and_dividends: null,
    monthly_pension: null,
    monthly_social_security: 99.5,
    monthly_unemployment: null,
    monthly_child_support: null,
    monthly_alimony: null,
    monthly_other_income: null,
  };
  let patchBodies: unknown[];

  beforeEach(() => {
    patchBodies = [];
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(savedSession)
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        patchBodies.push(await request.json());
        return HttpResponse.json(savedSession);
      }),
      http.post('http://localhost:8000/api/intake/sessions/:id/update_step/', () =>
        HttpResponse.json({
          session: { ...savedSession, current_step: 3 },
          message: 'Step updated.',
        })
      ),
      // Continue also posts a step-completed analytics event; answer it so this test adds
      // no unhandled-request warning (DIG-93 tracks the older tests that still do).
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
  });

  it("sends a returning filer's ten amounts as numbers, a box left empty as empty, and the unanswered marriage question and household list as null", async () => {
    renderWizard();
    await screen.findByRole('heading', { name: /income/i, level: 2 });
    expect(screen.getByLabelText(/monthly wages/i)).toHaveValue(3100.5);
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByRole('heading', { name: /take-home pay/i, level: 2 });

    expect(patchBodies.length).toBeGreaterThan(0);
    for (const body of patchBodies) {
      expect(body).toEqual({
        income_info: {
          ...savedAmounts,
          marital_status: null,
          business_and_rental: null,
          ...NEW_ANSWERS,
        },
        household: { members: null },
        schedule_i_answers: { ...SCHEDULE_I_STEP_2_NULL, ...LINES_11_13_NO },
      });
    }
  });

  it('empties a box on the server too when the filer clears it', async () => {
    renderWizard();
    await screen.findByRole('heading', { name: /income/i, level: 2 });
    await userEvent.clear(screen.getByLabelText(/social security/i));
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByRole('heading', { name: /take-home pay/i, level: 2 });

    expect(patchBodies.at(-1)).toEqual({
      income_info: {
        ...savedAmounts,
        monthly_social_security: null,
        marital_status: null,
        business_and_rental: null,
        ...NEW_ANSWERS,
      },
      household: { members: null },
      schedule_i_answers: { ...SCHEDULE_I_STEP_2_NULL, ...LINES_11_13_NO },
    });
  });
});

// The step 2 body's new answers while the filer has given none (3e2 spec §7.4): the current ten
// stay out until "yes", and the five assistance fields are always sent
const NEW_ANSWERS = {
  income_now_different: null,
  assistance_answer: null,
  cash_assistance_kind: '',
  cash_assistance_amount: null,
  noncash_assistance_kind: '',
  noncash_assistance_value: null,
};

// Shared by the Income step's describes below
const onIncome = { ...sessionAtStep1, current_step: 2 };
const TEN_ZERO = Object.fromEntries(INCOME_FIELDS.map((field) => [field, '0.00']));
const TEN_NULL = Object.fromEntries(INCOME_FIELDS.map((field) => [field, null]));
const priyaAtIncome = {
  ...onIncome,
  income_info: {
    ...TEN_ZERO,
    monthly_gross_wages: '12000.00',
    marital_status: 'married_together',
    total_monthly_income: 12000,
  },
  household: {
    county: 'Cook',
    members: [
      {
        id: 1,
        relationship: 'spouse',
        age: 45,
        lives_with_you: true,
        claimed_or_supported: true,
        spouse_is_dependent: false,
      },
      {
        id: 2,
        relationship: 'daughter',
        age: 10,
        lives_with_you: true,
        claimed_or_supported: true,
      },
      { id: 3, relationship: 'son', age: 7, lives_with_you: true, claimed_or_supported: true },
    ],
  },
  spouse_income: { ...TEN_ZERO, monthly_gross_wages: '1800.00' },
};
const pick = (name: string, value: string) => {
  const radio = document.querySelector(`input[name="${name}"][value="${value}"]`);
  if (!radio) throw new Error(`No answer ${value} to ${name}`);
  fireEvent.click(radio);
};

// ===========================================================================
// Household and spouse on the Income step (3e1 spec §8.2)
// ===========================================================================

describe('IntakeWizard household and spouse', { timeout: 30_000 }, () => {
  const NO_ONE_ELSE = 'No one else lives with me or depends on me.';
  const members = (body: Record<string, unknown>) =>
    (body.household as { members: Record<string, unknown>[] | null }).members;
  const openIncome = () => screen.findByRole('heading', { name: /income/i, level: 2 });

  beforeEach(() => {
    server.use(
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          const { current_step } = (await request.json()) as { current_step: number };
          return HttpResponse.json({
            session: { ...onIncome, current_step },
            message: 'Step updated.',
          });
        }
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
  });

  // Line 1 has no fifth answer: Complete names the unanswered question
  it('a half-answered line 1 saves marital_status null', async () => {
    const { bodies } = serveSessionSaves({
      ...onIncome,
      income_info: { ...TEN_ZERO, marital_status: 'not_married', total_monthly_income: 0 },
    });
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      pick('marital_status', 'not_filing');
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    const last = bodies.at(-1) as Record<string, unknown>;
    expect((last.income_info as Record<string, unknown>).marital_status).toBeNull();
    expect(last).not.toHaveProperty('spouse_income');
    expect(
      document.querySelector('input[name="marital_status"][value="not_filing"]')
    ).toBeChecked();
  });

  // An unanswered question never blocks a save; Complete names it
  it('a half-finished household row saves with the rest of the step', async () => {
    const { bodies } = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: '+ Add a person' }));
      fireEvent.change(field('relationship_0'), { target: { value: 'daughter' } });
      await waitSeconds(3);
      // The id the reply gives the row sends nothing more
      await waitSeconds(5);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies).toHaveLength(1);
    expect(bodies.at(-1)).toEqual({
      income_info: expect.any(Object),
      household: {
        members: [
          { relationship: 'daughter', age: null, lives_with_you: null, claimed_or_supported: null },
        ],
      },
      schedule_i_answers: SCHEDULE_I_STEP_2_NULL,
    });
  });

  it('a row added and never touched is not sent', async () => {
    const { bodies } = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: '+ Add a person' }));
      fireEvent.change(field('monthly_gross_wages'), { target: { value: '3200' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(members(bodies.at(-1) as Record<string, unknown>)).toBeNull();
  });

  // An empty list is only ever the filer's answer, so a save never drops a row they didn't remove
  it('No one else… sends [] and a list never answered sends null', async () => {
    const { bodies } = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('monthly_gross_wages'), { target: { value: '3200' } });
      await waitSeconds(3);
      expect(members(bodies.at(-1) as Record<string, unknown>)).toBeNull();

      fireEvent.click(screen.getByRole('button', { name: NO_ONE_ELSE }));
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(members(bodies.at(-1) as Record<string, unknown>)).toEqual([]);
    expect(screen.getByRole('button', { name: NO_ONE_ELSE })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
  });

  // A row saved without its id is stored again as a new row
  it("a saved row's id reaches the row that sent it, wherever it now sits", async () => {
    const saves = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();
    const landSave = saves.holdNextReply();

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: '+ Add a person' }));
      fireEvent.change(field('relationship_0'), { target: { value: 'son' } });
      fireEvent.click(screen.getByRole('button', { name: '+ Add a person' }));
      fireEvent.change(field('relationship_1'), { target: { value: 'daughter' } });
      await waitSeconds(3);
      expect(saves.bodies).toHaveLength(1);

      fireEvent.click(screen.getByRole('button', { name: 'Remove person 1' }));
      await act(async () => landSave());
      await waitSeconds(4);
    } finally {
      vi.useRealTimers();
    }

    expect(saves.bodies.map((body) => members(body)?.map((row) => row.id))).toEqual([
      [undefined, undefined],
      [102],
    ]);
    const [daughter] = members(saves.bodies[1]) ?? [];
    expect(daughter.relationship).toBe('daughter');
    expect(daughter).not.toHaveProperty('_key');
  });

  // P10 #2: the server refuses the spouse's question on any other row, so every save would fail
  it('a row changed away from spouse sends no spouse question at all', async () => {
    const { bodies } = serveSessionSaves(priyaAtIncome);
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('relationship_0'), { target: { value: 'other_relative' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    const [first] = members(bodies.at(-1) as Record<string, unknown>) ?? [];
    expect(first).toEqual({
      id: 1,
      relationship: 'other_relative',
      age: 45,
      lives_with_you: true,
      claimed_or_supported: true,
    });
    expect(first).not.toHaveProperty('spouse_is_dependent');
  });

  // 122A-1 fills Column B only for a spouse in the same household (§5.1)
  it("the spouse's income is sent only while living together", async () => {
    const { bodies } = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      pick('marital_status', 'not_filing');
      pick('spouse_household', 'married_together');
      fireEvent.change(field('spouse_monthly_gross_wages'), { target: { value: '1800' } });
      await waitSeconds(3);
      expect((bodies.at(-1) as Record<string, unknown>).spouse_income).toEqual({
        ...TEN_NULL,
        monthly_gross_wages: 1800,
        business_and_rental: null,
        ...NEW_ANSWERS,
      });

      pick('spouse_household', 'married_separately');
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies.at(-1)).not.toHaveProperty('spouse_income');
  });

  // Any intake save reopens a completed intake, and the filer would have to press Complete again
  it('showing the Income step again sends nothing, so a completed intake stays completed', async () => {
    const saves = serveSessionSaves({
      ...priyaAtIncome,
      status: 'completed',
      current_step: 4,
      expense_info: completedSession.expense_info,
      // Every Schedule I key the step shows, the spouse's too, an employer kept under Not
      // employed, the amount as the server's string, and the read-only keys (4c-R7)
      schedule_i_answers: {
        employment_status: 'employed',
        occupation: 'Analyst',
        employer_name: 'Demo Analytics',
        employer_street: '1 Demo Way',
        employer_city: 'Chicago',
        employer_state: 'IL',
        employer_zip: '60601',
        time_employed: '4 years',
        spouse_employment_status: 'not_employed',
        spouse_employer_name: 'Demo Kept Employer',
        line_11_answer: 'yes',
        line_11_text: 'My mother',
        line_11_amount: '250.00',
        line_13_answer: 'no',
        schedule_j_line_24_answer: 'no',
        answered_on: '2026-10-16',
      },
      paystub_employer_name: 'Demo Analytics LLC',
    });
    const { container } = renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
      await waitSeconds(3);
      expect(container.querySelector('.step-title')).toHaveTextContent('Take-home pay');
      fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(container.querySelector('.step-title')).toHaveTextContent('Income');
    expect(saves.bodies).toEqual([]);
    expect(saves.stored().status).toBe('completed');
  });

  it('a session with no household or spouse loads without error', async () => {
    serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();

    for (const radio of screen.getAllByRole('radio')) expect(radio).not.toBeChecked();
    expect(screen.getByRole('button', { name: NO_ONE_ELSE })).toHaveAttribute(
      'aria-pressed',
      'false'
    );
    expect(document.querySelector('[name^="spouse_"]')).toBeNull();
  });

  // AuditLog.details is plaintext (§8.5)
  it('no household or spouse value is sent to analytics', async () => {
    const auditBodies: unknown[] = [];
    serveSessionSaves({
      ...priyaAtIncome,
      spouse_income: { ...priyaAtIncome.spouse_income, monthly_gross_wages: '1234.56' },
      schedule_i_answers: LINES_11_13_NO,
    });
    server.use(
      http.post('http://localhost:8000/api/audit/logs/', async ({ request }) => {
        auditBodies.push(await request.json());
        return new HttpResponse(null, { status: 201 });
      })
    );
    renderWizard();
    await openIncome();

    await userEvent.click(screen.getByRole('button', { name: 'Continue' }));
    await waitFor(() => expect(auditBodies.length).toBeGreaterThan(0));

    expect(JSON.stringify(auditBodies)).not.toMatch(
      /spouse|household|members|relationship|marital/i
    );
    // No duration or timestamp can hold this figure
    expect(JSON.stringify(auditBodies)).not.toContain('1234.56');
  });

  // §8.2: a list loaded as [] shows the button pressed, and null would replace the stored "no one"
  it('a list loaded as no one stays no one after another edit', async () => {
    const { bodies } = serveSessionSaves({
      ...onIncome,
      household: { county: 'Cook', members: [] },
    });
    renderWizard();
    await openIncome();
    expect(screen.getByRole('button', { name: NO_ONE_ELSE })).toHaveAttribute(
      'aria-pressed',
      'true'
    );

    vi.useFakeTimers();
    try {
      fireEvent.change(field('monthly_gross_wages'), { target: { value: '3200' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(members(bodies.at(-1) as Record<string, unknown>)).toEqual([]);
  });

  // Every session reaches Income from step 1 with a county and a list never answered
  it('a list never answered loads as unanswered, not as no one', async () => {
    const { bodies } = serveSessionSaves({
      ...onIncome,
      household: { county: 'Cook', members: null },
    });
    renderWizard();
    await openIncome();
    expect(screen.getByRole('button', { name: NO_ONE_ELSE })).toHaveAttribute(
      'aria-pressed',
      'false'
    );

    vi.useFakeTimers();
    try {
      fireEvent.change(field('monthly_gross_wages'), { target: { value: '3200' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(members(bodies.at(-1) as Record<string, unknown>)).toBeNull();
  });

  // DRF sends the spouse's amounts as decimal strings, which would join as text in the total
  it("the spouse's saved amounts load as numbers, so their total adds up", async () => {
    serveSessionSaves({
      ...onIncome,
      income_info: {
        ...TEN_ZERO,
        monthly_gross_wages: '3200.00',
        marital_status: 'married_together',
        total_monthly_income: 3200,
      },
      spouse_income: { ...TEN_NULL, monthly_gross_wages: '1800.00', monthly_tips: '200.50' },
    });
    renderWizard();
    await openIncome();

    expect(
      screen.getByText("Your spouse's income", { selector: 'dt' }).nextElementSibling
    ).toHaveTextContent('$2,000.50');
  });

  // A later save left without the earlier reply's ids, and the server has already replaced any
  // row the earlier save created
  it("an older save's reply writes no ids once a later save of the list has gone out", async () => {
    const saves = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();
    const landFirstSave = saves.holdNextReply();

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: '+ Add a person' }));
      fireEvent.change(field('relationship_0'), { target: { value: 'son' } });
      await waitSeconds(3);
      fireEvent.change(field('age_0'), { target: { value: '8' } });
      await waitSeconds(3);
      expect(saves.bodies).toHaveLength(2);

      await act(async () => landFirstSave());
      await waitSeconds(4);
      // The next edit updates the row the server holds
      fireEvent.change(field('age_0'), { target: { value: '9' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    const held = (saves.stored().household as { members: { id: number }[] }).members;
    expect(held.map((row) => row.id)).toEqual([102]);
    expect(saves.bodies.map((body) => members(body)?.map((row) => row.id))).toEqual([
      [undefined],
      [undefined],
      [102],
    ]);
  });

  // An unanswered list is a save of the list too: the server no longer holds the row an earlier
  // save created, so that save's reply must not give the row its id
  it('a reply that lands after the list was saved as unanswered writes no id', async () => {
    const saves = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();
    const landFirstSave = saves.holdNextReply();

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: '+ Add a person' }));
      fireEvent.change(field('relationship_0'), { target: { value: 'son' } });
      await waitSeconds(3);
      // Taking back the row's only answer leaves no row to send
      fireEvent.change(field('relationship_0'), { target: { value: '' } });
      await waitSeconds(3);
      expect(saves.bodies.map((body) => members(body))).toEqual([[expect.any(Object)], null]);

      await act(async () => landFirstSave());
      await waitSeconds(4);
      fireEvent.change(field('relationship_0'), { target: { value: 'daughter' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(saves.bodies.map((body) => members(body)?.map((row) => row.id) ?? null)).toEqual([
      [undefined],
      null,
      [undefined],
    ]);
  });

  // As for assets and debts: ids are paired by position, never guessed
  it("a reply that doesn't list each household row sent fails the save", async () => {
    // Lines 11 and 13 answered, so it is Continue's save that fails (4c-R4)
    serveSessionSaves({ ...onIncome, schedule_i_answers: LINES_11_13_NO });
    const unanswered = { age: null, lives_with_you: null, claimed_or_supported: null };
    server.use(
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({
          ...onIncome,
          household: {
            county: 'Cook',
            members: [
              { id: 101, relationship: 'son', ...unanswered },
              { id: 102, relationship: 'daughter', ...unanswered },
            ],
          },
        })
      )
    );
    const { container } = renderWizard();
    await openIncome();

    fireEvent.click(screen.getByRole('button', { name: '+ Add a person' }));
    fireEvent.change(field('relationship_0'), { target: { value: 'son' } });
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }));

    expect(await screen.findByText(/couldn't save just now/i)).toBeInTheDocument();
    expect(container.querySelector('.step-title')).toHaveTextContent('Income');
  });
});

// ===========================================================================
// Schedule I lines 1, 11 and 13 on the Income step (4c spec §6.2)
// ===========================================================================

describe('IntakeWizard Schedule I on the Income step', { timeout: 30_000 }, () => {
  const openIncome = () => screen.findByRole('heading', { name: /income/i, level: 2 });
  const scheduleI = (body: Record<string, unknown> | undefined) =>
    body?.schedule_i_answers as Record<string, unknown> | undefined;
  const statusLine = () => document.querySelector('.income-info-step > [role="status"]');
  const continueButton = () => screen.getByRole('button', { name: 'Continue' });
  let stepUpdates: number[];

  beforeEach(() => {
    stepUpdates = [];
    server.use(
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          const { current_step } = (await request.json()) as { current_step: number };
          stepUpdates.push(current_step);
          return HttpResponse.json({
            session: { ...onIncome, current_step },
            message: 'Step updated.',
          });
        }
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
  });

  // Each step sends only its own keys, so neither step's saved copy overwrites the other's
  it("step 2's body carries only step 2's Schedule I keys", async () => {
    const { bodies } = serveSessionSaves({
      ...onIncome,
      schedule_i_answers: {
        employment_status: 'employed',
        employer_name: 'Demo Diner',
        line_11_answer: 'no',
        schedule_j_line_24_answer: 'yes',
        schedule_j_line_24_text: 'The car loan ends in May',
        answered_on: '2026-10-16',
      },
      paystub_employer_name: 'Demo Diner LLC',
    });
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('occupation'), { target: { value: 'Cook' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    const body = bodies.at(-1) as Record<string, unknown>;
    expect(Object.keys(body)).toEqual(['income_info', 'household', 'schedule_i_answers']);
    // Line 24 is step 4's; the read-only date and the pay stub's name are never sent
    expect(scheduleI(body)).toEqual({
      ...SCHEDULE_I_STEP_2_NULL,
      employment_status: 'employed',
      occupation: 'Cook',
      employer_name: 'Demo Diner',
      line_11_answer: 'no',
    });
  });

  // A hidden spouse block neither saves nor clears what the server holds (D5)
  it('the spouse keys are sent only for a spouse at home', async () => {
    const { bodies } = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      pick('marital_status', 'not_filing');
      pick('spouse_household', 'married_together');
      pick('spouse_employment_status', 'employed');
      fireEvent.change(field('spouse_employer_name'), { target: { value: 'Demo Clinic' } });
      await waitSeconds(3);
      expect(scheduleI(bodies.at(-1))).toEqual({
        ...SCHEDULE_I_STEP_2_NULL,
        ...SCHEDULE_I_SPOUSE_NULL,
        spouse_employment_status: 'employed',
        spouse_employer_name: 'Demo Clinic',
      });

      pick('spouse_household', 'married_separately');
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(scheduleI(bodies.at(-1))).toEqual(SCHEDULE_I_STEP_2_NULL);
    expect(document.querySelector('[name="spouse_employment_status"]')).toBeNull();
  });

  // D4: Continue waits for the two gates, but a page of typed income still saves meanwhile
  it('Continue waits for lines 11 and 13 while autosave still saves typed income', async () => {
    const { bodies } = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();
    // Every box on the step is valid, so the gate alone holds Continue: the status line names it
    // before the lines are touched, for a filer a gap link brought to the top of the step (FR-1)
    expect(statusLine()).toHaveTextContent(SCHEDULE_I_GATE_LINE_11);
    expect(continueButton()).toBeDisabled();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('monthly_gross_wages'), { target: { value: '3200' } });
      await waitSeconds(3);
      expect(bodies).toHaveLength(1);
      expect((bodies[0].income_info as Record<string, unknown>).monthly_gross_wages).toBe(3200);
      expect(continueButton()).toBeDisabled();

      pick('line_11_answer', 'no');
      await waitSeconds(3);
      expect(statusLine()).toHaveTextContent(SCHEDULE_I_GATE_LINE_13);
      expect(continueButton()).toBeDisabled();
      expect(scheduleI(bodies.at(-1))?.line_11_answer).toBe('no');

      pick('line_13_answer', 'no');
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(statusLine()).toBeEmptyDOMElement();
    expect(continueButton()).toBeEnabled();
    await userEvent.click(continueButton());
    await waitFor(() => expect(stepUpdates).toEqual([3]));
  });

  // The disabled button is not the only guard: Continue's own handler refuses while a gate is
  // open, so no other way of pressing it moves the filer past an unanswered line (4c-R4)
  it('Continue pressed while line 11 is unanswered neither saves nor moves on', async () => {
    layoutOverride.forceContinue = true;
    try {
      const { bodies } = serveSessionSaves(onIncome);
      renderWizard();
      await openIncome();
      expect(continueButton()).toBeEnabled();

      await userEvent.click(continueButton());
      await act(() => new Promise((resolve) => setTimeout(resolve, 300)));
      expect(bodies).toHaveLength(0);
      expect(stepUpdates).toEqual([]);

      // With both lines answered the same press saves and moves on
      pick('line_11_answer', 'no');
      pick('line_13_answer', 'no');
      await userEvent.click(continueButton());
      await waitFor(() => expect(stepUpdates).toEqual([3]));
      expect(bodies.length).toBeGreaterThan(0);
    } finally {
      layoutOverride.forceContinue = false;
    }
  });

  // While a box says why Continue is held, the gate waits its turn: it names line 11 first once
  // focus leaves the two lines
  it('the status line waits while a box holds Continue, until focus leaves the two lines', async () => {
    serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();
    fireEvent.change(field('monthly_gross_wages'), { target: { value: '-5' } });
    expect(screen.getByText(AMOUNT_NEGATIVE)).toBeInTheDocument();
    expect(statusLine()).toBeEmptyDOMElement();
    fireEvent.blur(field('line_13_answer'), { relatedTarget: field('monthly_gross_wages') });
    expect(statusLine()).toHaveTextContent(SCHEDULE_I_GATE_LINE_11);
  });

  it('a loaded record hydrates the step', async () => {
    serveSessionSaves({
      ...onIncome,
      schedule_i_answers: {
        employment_status: 'employed',
        occupation: 'Analyst',
        employer_name: 'Demo Analytics',
        employer_state: 'IL',
        employer_zip: '60601',
        line_11_answer: 'yes',
        line_11_text: 'My mother',
        line_11_amount: '250.00',
        line_13_answer: 'yes',
        line_13_text: 'A raise in March',
        answered_on: '2026-10-16',
      },
      paystub_employer_name: 'Demo Analytics LLC',
    });
    renderWizard();
    await openIncome();

    expect(
      document.querySelector('input[name="employment_status"][value="employed"]')
    ).toBeChecked();
    expect(field('occupation')).toHaveValue('Analyst');
    expect(field('employer_name')).toHaveValue('Demo Analytics');
    expect(field('employer_state')).toHaveValue('IL');
    expect(field('employer_zip')).toHaveValue('60601');
    // The amount stays the server's string, never a hydrated number
    expect(field('line_11_amount')).toHaveValue('250.00');
    expect(field('line_11_text')).toHaveValue('My mother');
    expect(field('line_13_text')).toHaveValue('A raise in March');
    expect(
      screen.getByText(PAYSTUB_EMPLOYER_HINT.replace('{name}', 'Demo Analytics LLC'))
    ).toBeInTheDocument();
    // Both lines answered: Continue needs nothing more
    await waitFor(() => expect(continueButton()).toBeEnabled());
  });

  // PF-4c-C: every string the step sends is one the server takes, or one stray keystroke would
  // fail every autosave on the step
  it('a line 11 amount the server would refuse holds autosave and Continue and shows why', async () => {
    const { bodies } = serveSessionSaves({
      ...onIncome,
      schedule_i_answers: { line_11_answer: 'yes', line_13_answer: 'no' },
    });
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      for (const [typed, reason] of [
        ['12.', AMOUNT_DECIMALS],
        ['1e3', AMOUNT_DECIMALS],
        ['abc', AMOUNT_DECIMALS],
        ['12.505', AMOUNT_DECIMALS],
        ['-5', AMOUNT_NEGATIVE],
        ['10000000000', AMOUNT_TOO_LARGE],
      ]) {
        fireEvent.change(field('line_11_amount'), { target: { value: typed } });
        await waitSeconds(3);
        expect(bodies, typed).toHaveLength(0);
        expect(field('line_11_amount'), typed).toHaveValue(typed);
        expect(screen.getByText(reason), typed).toBeInTheDocument();
        expect(continueButton(), typed).toBeDisabled();
      }

      // A refused amount rides the body under No too, so it still holds and its box stays shown
      pick('line_11_answer', 'no');
      await waitSeconds(3);
      expect(bodies).toHaveLength(0);
      expect(field('line_11_amount')).toHaveValue('10000000000');
      expect(continueButton()).toBeDisabled();
      pick('line_11_answer', 'yes');

      // The server's own shape goes as typed
      fireEvent.change(field('line_11_amount'), { target: { value: '12.50' } });
      await waitSeconds(3);
      expect(bodies).toHaveLength(1);
      expect(scheduleI(bodies[0])?.line_11_amount).toBe('12.50');
      expect(screen.queryByText(AMOUNT_TOO_LARGE)).not.toBeInTheDocument();
      expect(continueButton()).toBeEnabled();

      // A blank box goes as null, never as ""
      fireEvent.change(field('line_11_amount'), { target: { value: '' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies).toHaveLength(2);
    expect(scheduleI(bodies[1])?.line_11_amount).toBeNull();
    expect(continueButton()).toBeEnabled();
  });

  // FR-2: "250." is on its way to "250.50", so no alert interrupts a screen reader while the box
  // has focus; the amount still holds autosave and Continue, and the reason shows once focus leaves
  it('a lone trailing point holds quietly while the line 11 box has focus', async () => {
    const { bodies } = serveSessionSaves({
      ...onIncome,
      schedule_i_answers: { line_11_answer: 'yes', line_13_answer: 'no' },
    });
    renderWizard();
    await openIncome();
    const box = field('line_11_amount') as HTMLInputElement;

    vi.useFakeTimers();
    try {
      act(() => box.focus());
      fireEvent.change(box, { target: { value: '250.' } });
      await waitSeconds(3);
      expect(screen.queryByText(AMOUNT_DECIMALS)).not.toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(bodies).toHaveLength(0);
      expect(continueButton()).toBeDisabled();

      // Only a point on an amount that is otherwise good waits: anything else says why at once
      fireEvent.change(box, { target: { value: '-5.' } });
      expect(screen.getByText(AMOUNT_NEGATIVE)).toBeInTheDocument();
      fireEvent.change(box, { target: { value: '250.' } });
      expect(screen.queryByText(AMOUNT_NEGATIVE)).not.toBeInTheDocument();

      act(() => box.blur());
      expect(screen.getByText(AMOUNT_DECIMALS)).toBeInTheDocument();
      expect(field('line_11_amount')).toHaveValue('250.');
      await waitSeconds(3);
      expect(bodies).toHaveLength(0);
      expect(continueButton()).toBeDisabled();
    } finally {
      vi.useRealTimers();
    }
  });
});

// ===========================================================================
// Expenses read back from the server (DIG-45)
// ===========================================================================

describe('IntakeWizard expense hydration', { timeout: 15_000 }, () => {
  it("adds up a returning filer's saved expenses, which the API sends as decimal strings", async () => {
    const savedSession = {
      ...sessionAtStep1,
      current_step: 4,
      expense_info: {
        data_source: 'manual',
        rent_or_mortgage: '1100.00',
        utilities: '180.00',
        home_maintenance: '0.00',
        vehicle_insurance: '85.00',
        vehicle_maintenance: '40.00',
        food_and_groceries: '450.00',
        clothing: '60.00',
        medical_expenses: '75.00',
        childcare: '400.00',
        child_support_paid: '0.00',
        insurance_not_deducted: '120.00',
        other_expenses: '50.00',
        total_monthly_expenses: 2560.0,
        created_at: '2026-10-01T10:00:00Z',
        updated_at: '2026-10-01T10:00:00Z',
      },
    };
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(savedSession)
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(savedSession)
      )
    );

    renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    expect(screen.getByText('$2,560.00')).toBeInTheDocument();
  });
});

// ===========================================================================
// Phone number (DIG-120)
// ===========================================================================

// The server stores the phone as `phone`, and DRF drops any other name without an error, so a
// number sent under another name never reached Form 101 and a returning filer had to retype it.
describe('IntakeWizard phone number', { timeout: 15_000 }, () => {
  let patchBodies: Record<string, unknown>[];

  beforeEach(() => {
    patchBodies = [];
    server.use(
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        patchBodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(sessionAtStep1);
      }),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
  });

  it('shows a returning filer the phone number they saved', async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({
          ...sessionAtStep1,
          debtor_info: { first_name: 'Jane', last_name: 'Doe', phone: '312-555-0188' },
        })
      )
    );

    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });

    expect(screen.getByRole('textbox', { name: /phone number/i })).toHaveValue('312-555-0188');
  });

  it('saves the phone number under the name the server stores', async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep1)
      )
    );

    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await fillDebtorInfoFields();
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByText('DocumentUploadPage');

    const debtorInfo = patchBodies[patchBodies.length - 1].debtor_info as Record<string, unknown>;
    expect(debtorInfo.phone).toBe('312-555-1234');
    expect(debtorInfo).not.toHaveProperty('phone_number');
  });
});

// Form 101 prints the county, so step 1 asks for one and saves it under `household`.
describe('IntakeWizard county', { timeout: 15_000 }, () => {
  let patchBodies: Record<string, unknown>[];

  beforeEach(() => {
    patchBodies = [];
    server.use(
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        patchBodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(sessionAtStep1);
      }),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      ),
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep1)
      )
    );
  });

  it('step 1 neither saves nor continues until a county is picked', async () => {
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    vi.useFakeTimers();
    try {
      await act(async () => {
        await fillDebtorInfoFields(null);
      });
      await waitSeconds(3);
      expect(patchBodies).toHaveLength(0);
      expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled();
      fireEvent.change(screen.getByRole('combobox', { name: /county/i }), {
        target: { value: 'Cook' },
      });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }
    expect(patchBodies).toHaveLength(1);
    expect(patchBodies[0]).toEqual({
      debtor_info: expect.objectContaining({ first_name: 'Jane' }),
      household: { county: 'Cook' },
      petition_answers: expect.any(Object),
    });
  });

  it("step 1 sends the county beside the debtor's answers", async () => {
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await fillDebtorInfoFields();
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByText('DocumentUploadPage');
    expect(patchBodies.at(-1)).toEqual({
      debtor_info: expect.objectContaining({ first_name: 'Jane', zip_code: '60601' }),
      household: { county: 'Cook' },
      petition_answers: expect.any(Object),
    });
  });

  it('the step 1 body carries the petition answers beside debtor_info and household', async () => {
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await fillDebtorInfoFields();
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByText('DocumentUploadPage');
    const petition = patchBodies.at(-1)!.petition_answers as Record<string, unknown>;
    // Every step-1 key, an unanswered one as null, so the body is built the same way from a
    // loaded record as from typing; no ITIN goes when none was typed
    expect(Object.keys(petition)).toEqual(STEP_1_PETITION_KEYS);
    for (const gate of STEP_1_GATES) expect(petition[gate]).toBe('no');
    expect(petition.venue_choice).toBeNull();
    expect(petition.other_names).toBeNull();
    expect(petition).not.toHaveProperty('itin');
    expect(petition).not.toHaveProperty('other_ssn');
  });

  /** A step 1 the server already holds whole: an SSN and an ITIN saved, every gate answered */
  const savedStep1 = {
    ...sessionAtStep1,
    debtor_info: {
      ...completedSession.debtor_info,
      phone: '312-555-0100',
      ssn_saved: true,
    },
    household: { county: 'Boone', members: null },
    petition_answers: {
      other_names_answer: 'yes',
      other_names: [{ first: 'Demo', middle: '', last: 'Maiden' }],
      itin_answer: 'yes',
      itin_saved: true,
      other_ssn_answer: 'no',
      other_ssn_saved: false,
      mailing_answer: 'no',
      prior_bankruptcy_answer: 'no',
      pending_case_answer: 'no',
      sole_proprietor_answer: 'no',
      venue_choice: 'lived_here',
      answered_on: '2026-10-16',
    },
  };

  it('showing step 1 again sends nothing', async () => {
    // A loaded step 1 is complete now that a saved SSN counts (owner ruling Q3), so autosave is
    // live on mount: a body built differently from loaded data would save, and reopen a completed
    // intake, on every visit
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(savedStep1)
      )
    );
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await waitFor(() => expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled());
    vi.useFakeTimers();
    try {
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }
    expect(patchBodies).toHaveLength(0);
  });

  it('Delete removes a saved other number under a No in its own PATCH, and it reads as not saved', async () => {
    // F10: the filer can remove a number typed by mistake. The one request carries only that key
    // as null, which the server removes, and step 1's own body never carries it
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({
          ...savedStep1,
          petition_answers: { ...savedStep1.petition_answers, other_ssn_saved: true },
        })
      )
    );
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    const block = (
      document.querySelector('input[name="other_ssn_answer"][value="no"]') as HTMLElement
    ).closest('fieldset') as HTMLElement;
    expect(within(block).getByText(HIDDEN_ANSWERS)).toBeInTheDocument();
    await userEvent.click(within(block).getByRole('button', { name: DELETE_HIDDEN }));
    await waitFor(() => expect(patchBodies).toEqual([{ petition_answers: { other_ssn: null } }]));
    await waitFor(() => expect(within(block).queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument());

    // The saved flag now reads false: a Yes opens an empty box, not "Another ... is saved."
    fireEvent.click(
      document.querySelector('input[name="other_ssn_answer"][value="yes"]') as HTMLElement
    );
    expect(document.querySelector('input[name="other_ssn"]')).toHaveValue('');
    expect(screen.queryByText(OTHER_SSN_SAVED)).not.toBeInTheDocument();
  });

  it('Delete drops the digits typed for that number, so the next save cannot send them again', async () => {
    // A number typed under a Yes, then the answer changed to No and Delete pressed: the typed
    // digits must not ride the next save and undo the Delete
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({
          ...savedStep1,
          petition_answers: { ...savedStep1.petition_answers, other_ssn_saved: true },
        })
      )
    );
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    fireEvent.click(
      document.querySelector('input[name="other_ssn_answer"][value="yes"]') as HTMLElement
    );
    const block = (
      document.querySelector('input[name="other_ssn_answer"][value="no"]') as HTMLElement
    ).closest('fieldset') as HTMLElement;
    await userEvent.click(within(block).getByRole('button', { name: REPLACE_SAVED }));
    fireEvent.change(document.querySelector('input[name="other_ssn"]') as HTMLElement, {
      target: { value: '900-12-3456' },
    });
    fireEvent.click(
      document.querySelector('input[name="other_ssn_answer"][value="no"]') as HTMLElement
    );
    await userEvent.click(within(block).getByRole('button', { name: DELETE_HIDDEN }));
    await waitFor(() =>
      expect(patchBodies).toContainEqual({ petition_answers: { other_ssn: null } })
    );
    patchBodies.length = 0;
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() => expect(patchBodies.length).toBeGreaterThan(0));
    for (const body of patchBodies) {
      expect(body.petition_answers).not.toHaveProperty('other_ssn');
    }
  });

  it('nine digits that are no ITIN never leave the browser', async () => {
    // PF2-U2: saved would mean it prints, and a number not starting with 9 prints blank
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await fillDebtorInfoFields();
    fireEvent.click(
      document.querySelector('input[name="itin_answer"][value="yes"]') as HTMLElement
    );
    fireEvent.change(screen.getByRole('textbox', { name: /ITIN/ }), {
      target: { value: '666-70-1234' },
    });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByText('DocumentUploadPage');
    expect(patchBodies.length).toBeGreaterThan(0);
    for (const body of patchBodies) {
      expect(body.petition_answers).not.toHaveProperty('itin');
    }
    expect(JSON.stringify(patchBodies)).not.toContain('666701234');
  });

  it('a typed ITIN is sent once and never echoed', async () => {
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await fillDebtorInfoFields();
    fireEvent.click(
      document.querySelector('input[name="itin_answer"][value="yes"]') as HTMLElement
    );
    fireEvent.change(screen.getByRole('textbox', { name: /ITIN/ }), {
      target: { value: '900-70-1234' },
    });
    const withItin = () =>
      patchBodies.filter((body) => 'itin' in (body.petition_answers as Record<string, unknown>));
    await waitFor(() => expect(withItin()).toHaveLength(1), { timeout: 5000 });
    expect((withItin()[0].petition_answers as Record<string, unknown>).itin).toBe('900701234');
    // Saved: the step says so by the server's own rule, and the next save carries no ITIN
    expect(await screen.findByText(ITIN_SAVED)).toBeInTheDocument();
    const sentWithItin = patchBodies.length;
    // Clearing the typed ITIN is no edit: past the 2 s autosave pause, nothing more goes out
    await new Promise((resolve) => setTimeout(resolve, 2500));
    expect(patchBodies.length).toBe(sentWithItin);
    fireEvent.change(screen.getByRole('textbox', { name: /first name/i }), {
      target: { value: 'Janet' },
    });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByText('DocumentUploadPage');
    expect(patchBodies.length).toBe(sentWithItin + 1);
    expect(patchBodies.at(-1)!.petition_answers).not.toHaveProperty('itin');
    expect(JSON.stringify(patchBodies.slice(sentWithItin))).not.toContain('900701234');
  });

  it('a typed other Social Security number is sent once and never echoed', async () => {
    // Form 121 line 2 prints it only once the server holds it
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await fillDebtorInfoFields();
    fireEvent.click(
      document.querySelector('input[name="other_ssn_answer"][value="yes"]') as HTMLElement
    );
    fireEvent.change(document.querySelector('input[name="other_ssn"]') as HTMLElement, {
      target: { value: '900-12-3457' },
    });
    const withOther = () =>
      patchBodies.filter(
        (body) => 'other_ssn' in (body.petition_answers as Record<string, unknown>)
      );
    await waitFor(() => expect(withOther()).toHaveLength(1), { timeout: 5000 });
    expect((withOther()[0].petition_answers as Record<string, unknown>).other_ssn).toBe(
      '900123457'
    );
    expect(await screen.findByText(OTHER_SSN_SAVED)).toBeInTheDocument();
    const sentWithOther = patchBodies.length;
    await new Promise((resolve) => setTimeout(resolve, 2500));
    expect(patchBodies.length).toBe(sentWithOther);
    fireEvent.change(screen.getByRole('textbox', { name: /first name/i }), {
      target: { value: 'Janet' },
    });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByText('DocumentUploadPage');
    expect(patchBodies.length).toBe(sentWithOther + 1);
    expect(patchBodies.at(-1)!.petition_answers).not.toHaveProperty('other_ssn');
  });

  it('a replaced ITIN shows as saved again once its save succeeds', async () => {
    // Replace opens the box; the save that carries the new number closes it again
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(savedStep1)
      )
    );
    renderWizard();
    await userEvent.click(await screen.findByRole('button', { name: REPLACE_SAVED }));
    fireEvent.change(screen.getByRole('textbox', { name: /ITIN/ }), {
      target: { value: '900-70-5678' },
    });
    await waitFor(
      () =>
        expect(
          patchBodies.some(
            (body) => (body.petition_answers as Record<string, unknown>).itin === '900705678'
          )
        ).toBe(true),
      { timeout: 5000 }
    );
    expect(await screen.findByText(ITIN_SAVED)).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: /ITIN/ })).not.toBeInTheDocument();
  });

  it('a typed name row goes without its browser key, and a blank row stays home', async () => {
    // PF2-T8-7: every `_`-prefixed key stays out of the request, and an all-blank new row out
    // of the body
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await fillDebtorInfoFields();
    fireEvent.click(
      document.querySelector('input[name="other_names_answer"][value="yes"]') as HTMLElement
    );
    await userEvent.click(screen.getByRole('button', { name: PETITION_ADD_OTHER_NAME }));
    await userEvent.click(screen.getByRole('button', { name: PETITION_ADD_OTHER_NAME }));
    fireEvent.change(document.querySelector('input[name="other_names_0_first"]') as HTMLElement, {
      target: { value: 'Demo' },
    });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByText('DocumentUploadPage');
    const petition = patchBodies.at(-1)!.petition_answers as Record<string, unknown>;
    expect(petition.other_names_answer).toBe('yes');
    expect(petition.other_names).toEqual([{ first: 'Demo' }]);
  });

  it('no spouse SSN leaves the browser', async () => {
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    expect(screen.queryByRole('option', { name: /joint/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/spouse/i)).not.toBeInTheDocument();
    await fillDebtorInfoFields();
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByText('DocumentUploadPage');
    expect(patchBodies.length).toBeGreaterThan(0);
    for (const body of patchBodies) expect(JSON.stringify(body)).not.toContain('co_debtor');
  });

  // P10 #5. The SSN is write-only, so a loaded step 1 is never complete: the filer retypes it.
  it("a session with no county shows step 1's county as needed on load", async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({
          ...sessionAtStep1,
          debtor_info: completedSession.debtor_info,
          household: null,
        })
      )
    );
    renderWizard();
    const county = await screen.findByRole('combobox', { name: /county/i });
    expect(county).toHaveValue('');
    expect(county).toBeInvalid();
    expect(county).toHaveAccessibleDescription(
      expect.stringContaining('Please choose your county')
    );
    fireEvent.change(screen.getByLabelText(/social security number/i), {
      target: { value: '900-12-3456' },
    });
    fireEvent.change(screen.getByRole('textbox', { name: /phone number/i }), {
      target: { value: '312-555-0100' },
    });
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled();
  });
});

// ===========================================================================
// A cleared expense (DIG-55)
// ===========================================================================

describe('IntakeWizard cleared expense', { timeout: 15_000 }, () => {
  const savedExpenses = {
    data_source: 'manual',
    rent_or_mortgage: '1100.00',
    real_estate_taxes: '0.00',
    home_insurance: '0.00',
    home_maintenance: '0.00',
    hoa_dues: '0.00',
    electricity_heat_gas: '0.00',
    water_sewer_garbage: '0.00',
    phone_internet_cable: '0.00',
    utilities: '180.00',
    food_and_groceries: '450.00',
    childcare: '400.00',
    clothing: '60.00',
    personal_care: '0.00',
    medical_expenses: '75.00',
    vehicle_maintenance: '40.00',
    entertainment: '0.00',
    charitable_contributions: '0.00',
    life_insurance: '0.00',
    health_insurance: '0.00',
    vehicle_insurance: '85.00',
    insurance_not_deducted: '120.00',
    taxes_not_deducted: '0.00',
    child_support_paid: '0.00',
    support_others: '0.00',
    other_property_taxes: '0.00',
    other_property_insurance: '0.00',
    other_property_upkeep: '0.00',
    other_property_hoa_dues: '0.00',
    other_expenses: '50.00',
    utilities_specify: '',
    insurance_specify: '',
    taxes_specify: '',
    support_others_specify: '',
    other_expenses_specify: '',
    expenses_include_others: 'no',
    total_monthly_expenses: 2560.0,
    created_at: '2026-10-01T10:00:00Z',
    updated_at: '2026-10-01T10:00:00Z',
  };

  /** Serve a session sitting on the Expenses step (step 4); returns the PATCH bodies. */
  function serveExpensesSession(expense_info: Record<string, unknown> | null) {
    // Line 24 is answered, so Continue waits for nothing and step 4's body carries its keys
    const savedSession = {
      ...sessionAtStep1,
      current_step: 4,
      expense_info,
      schedule_i_answers: { schedule_j_line_24_answer: 'no' },
    };
    const patchBodies: Record<string, unknown>[] = [];
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(savedSession)
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        patchBodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(savedSession);
      }),
      http.post('http://localhost:8000/api/intake/sessions/:id/update_step/', () =>
        HttpResponse.json({
          session: { ...savedSession, current_step: 5 },
          message: 'Step updated.',
        })
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
    return patchBodies;
  }

  it('saves a cleared expense box as $0, so the old amount does not stay on the server', async () => {
    const patchBodies = serveExpensesSession(savedExpenses);

    renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });
    fireEvent.change(
      screen.getByRole('spinbutton', { name: EXPENSE_LINE_WORDS.rent_or_mortgage }),
      { target: { value: '' } }
    );
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByRole('heading', { name: /assets/i, level: 2 });

    const body = patchBodies[patchBodies.length - 1];
    expect(Object.keys(body)).toEqual(['expense_info', 'schedule_i_answers']);
    const expenseInfo = body.expense_info as Record<string, unknown>;
    // The 29 amounts, the five Specify texts and line 3, in that order, and nothing else (DRF
    // drops any other name silently). The boxes the filer left alone keep their saved amounts.
    expect(Object.keys(expenseInfo)).toEqual([
      ...EXPENSE_FIELDS,
      ...EXPENSE_SPECIFY_FIELDS,
      'expenses_include_others',
    ]);
    // The server treats a 0 in either retired field as Remove, so the body never carries them
    expect(expenseInfo).not.toHaveProperty('vehicle_payment');
    expect(expenseInfo).not.toHaveProperty('other_property_mortgages');
    expect(expenseInfo).toEqual({
      rent_or_mortgage: 0,
      real_estate_taxes: 0,
      home_insurance: 0,
      home_maintenance: 0,
      hoa_dues: 0,
      electricity_heat_gas: 0,
      water_sewer_garbage: 0,
      phone_internet_cable: 0,
      utilities: 180,
      food_and_groceries: 450,
      childcare: 400,
      clothing: 60,
      personal_care: 0,
      medical_expenses: 75,
      vehicle_maintenance: 40,
      entertainment: 0,
      charitable_contributions: 0,
      life_insurance: 0,
      health_insurance: 0,
      vehicle_insurance: 85,
      insurance_not_deducted: 120,
      taxes_not_deducted: 0,
      child_support_paid: 0,
      support_others: 0,
      other_property_taxes: 0,
      other_property_insurance: 0,
      other_property_upkeep: 0,
      other_property_hoa_dues: 0,
      other_expenses: 50,
      utilities_specify: '',
      insurance_specify: '',
      taxes_specify: '',
      support_others_specify: '',
      other_expenses_specify: '',
      expenses_include_others: 'no',
    });
  });

  it('sends a blank Specify box as empty and an unanswered line 3 as null', async () => {
    const patchBodies = serveExpensesSession(null);

    renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByRole('heading', { name: /assets/i, level: 2 });

    const body = patchBodies[patchBodies.length - 1];
    expect(body.expense_info).toEqual({
      ...Object.fromEntries(EXPENSE_FIELDS.map((field) => [field, 0])),
      utilities_specify: '',
      insurance_specify: '',
      taxes_specify: '',
      support_others_specify: '',
      other_expenses_specify: '',
      expenses_include_others: null,
    });
  });

  it('showing the Expenses step again sends nothing', async () => {
    const patchBodies = serveExpensesSession(savedExpenses);

    renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    // findBy needs real timers, so the clock is faked only after the step has shown. Each
    // step of the clock is 1 s, since a timer's reply can arm the next one.
    vi.useFakeTimers();
    try {
      for (let second = 0; second < 3; second += 1) {
        await act(() => vi.advanceTimersByTimeAsync(1000));
      }
    } finally {
      vi.useRealTimers();
    }

    expect(patchBodies).toEqual([]);
  });

  it('a total saved before the split rides the body unchanged', async () => {
    const patchBodies = serveExpensesSession({
      ...savedExpenses,
      utilities: '180.00',
      utilities_specify: 'Utilities (combined)',
    });

    renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });
    expect(screen.getByText(EXPENSES_LEGACY_UTILITIES)).toBeInTheDocument();

    vi.useFakeTimers();
    try {
      for (let second = 0; second < 3; second += 1) {
        await act(() => vi.advanceTimersByTimeAsync(1000));
      }
    } finally {
      vi.useRealTimers();
    }
    // Showing the step again sends nothing
    expect(patchBodies).toEqual([]);

    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByRole('heading', { name: /assets/i, level: 2 });
    const expenseInfo = patchBodies[patchBodies.length - 1].expense_info as Record<string, unknown>;
    expect(expenseInfo.utilities).toBe(180);
    expect(expenseInfo.utilities_specify).toBe('Utilities (combined)');
    expect(expenseInfo.electricity_heat_gas).toBe(0);
  });
});

// ===========================================================================
// Schedule J line 24 on the Expenses step (4c spec §6.2)
// ===========================================================================

describe('IntakeWizard Schedule J line 24 on the Expenses step', { timeout: 30_000 }, () => {
  const stored = {
    ...sessionAtStep1,
    current_step: 4,
    expense_info: { data_source: 'manual', rent_or_mortgage: '1100.00' },
  };
  const openExpenses = () => screen.findByRole('heading', { name: /expenses/i, level: 2 });
  const statusLine = () => document.querySelector('.expense-info-step > [role="status"]');
  const continueButton = () => screen.getByRole('button', { name: 'Continue' });

  function serve(scheduleIAnswers: Record<string, unknown>) {
    const session = { ...stored, schedule_i_answers: scheduleIAnswers };
    const bodies: Record<string, unknown>[] = [];
    const stepUpdates: number[] = [];
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(session)),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(session);
      }),
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          const { current_step } = (await request.json()) as { current_step: number };
          stepUpdates.push(current_step);
          return HttpResponse.json({ session: { ...session, current_step }, message: 'ok' });
        }
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
    return { bodies, stepUpdates };
  }

  it("step 4's body carries only the line 24 keys, never inside expense_info", async () => {
    // Step 2's keys and the read-only date are on the record; none of them is step 4's to send
    const { bodies } = serve({
      employment_status: 'employed',
      employer_name: 'Demo Diner',
      line_11_answer: 'no',
      schedule_j_line_24_answer: 'yes',
      schedule_j_line_24_text: 'The car loan ends in May',
      answered_on: '2026-10-16',
    });
    renderWizard();
    await openExpenses();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('utilities'), { target: { value: '90' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    const body = bodies.at(-1) as Record<string, unknown>;
    expect(Object.keys(body)).toEqual(['expense_info', 'schedule_i_answers']);
    expect(body.schedule_i_answers).toEqual({
      schedule_j_line_24_answer: 'yes',
      schedule_j_line_24_text: 'The car loan ends in May',
    });
    const expenseInfo = body.expense_info as Record<string, unknown>;
    expect(expenseInfo).not.toHaveProperty('schedule_j_line_24_answer');
    expect(expenseInfo).not.toHaveProperty('schedule_j_line_24_text');
  });

  it('an unanswered line 24 goes as null, and a text kept under No still goes', async () => {
    const { bodies } = serve({});
    renderWizard();
    await openExpenses();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('utilities'), { target: { value: '90' } });
      await waitSeconds(3);
      expect(bodies.at(-1)?.schedule_i_answers).toEqual({
        schedule_j_line_24_answer: null,
        schedule_j_line_24_text: null,
      });

      pick('schedule_j_line_24_answer', 'yes');
      fireEvent.change(field('schedule_j_line_24_text'), { target: { value: 'Rent goes up' } });
      pick('schedule_j_line_24_answer', 'no');
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    // The browser never clears what the filer typed: only Delete does
    expect(bodies.at(-1)?.schedule_i_answers).toEqual({
      schedule_j_line_24_answer: 'no',
      schedule_j_line_24_text: 'Rent goes up',
    });
  });

  it('Continue waits for line 24 while autosave still saves typed amounts', async () => {
    const { bodies, stepUpdates } = serve({});
    renderWizard();
    await openExpenses();
    // Every box on the step is valid, so the gate alone holds Continue: the status line names it
    // before line 24 is touched, though the line is the step's last block (FR-1)
    expect(statusLine()).toHaveTextContent(SCHEDULE_I_GATE_J24);
    expect(continueButton()).toBeDisabled();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('utilities'), { target: { value: '90' } });
      await waitSeconds(3);
      expect(bodies).toHaveLength(1);
      expect((bodies[0].expense_info as Record<string, unknown>).utilities).toBe(90);
      expect(statusLine()).toHaveTextContent(SCHEDULE_I_GATE_J24);
      expect(continueButton()).toBeDisabled();

      pick('schedule_j_line_24_answer', 'no');
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(statusLine()).toBeEmptyDOMElement();
    expect(continueButton()).toBeEnabled();
    await userEvent.click(continueButton());
    await waitFor(() => expect(stepUpdates).toEqual([5]));
  });

  // While a box says why Continue is held, the gate waits its turn: it shows once focus leaves
  // line 24 unanswered
  it('the status line waits while a box holds Continue, until focus leaves line 24', async () => {
    serve({});
    renderWizard();
    await openExpenses();
    fireEvent.change(field('utilities'), { target: { value: '-5' } });
    expect(screen.getByText(AMOUNT_NEGATIVE)).toBeInTheDocument();
    expect(statusLine()).toBeEmptyDOMElement();
    expect(continueButton()).toBeDisabled();

    fireEvent.blur(field('schedule_j_line_24_answer'), { relatedTarget: field('clothing') });
    expect(statusLine()).toHaveTextContent(SCHEDULE_I_GATE_J24);
  });

  it('showing step 4 again sends nothing', async () => {
    const { bodies } = serve({
      schedule_j_line_24_answer: 'yes',
      schedule_j_line_24_text: 'The car loan ends in May',
      answered_on: '2026-10-16',
    });
    renderWizard();
    await openExpenses();

    vi.useFakeTimers();
    try {
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies).toEqual([]);
  });
});

// ===========================================================================
// The line 4 question (3c4 B48)
// ===========================================================================

describe('IntakeWizard line 4 question', { timeout: 15_000 }, () => {
  const homeRow = {
    id: 7,
    session: 1,
    ab_line: '1',
    asset_type: null,
    data_source: 'manual',
    description: '',
    current_value: '90000.00',
    entire_value: '90000.00',
    details: {
      street: '1 Demo Street',
      property_kinds: ['single_family'],
      who: 'only_you',
      lives_here: 'yes',
    },
  };
  const mortgage = {
    ...storedDebt,
    id: 11,
    creditor_name: 'Demo Mortgage Co',
    debt_type: 'mortgage',
    amount_owed: '90000.00',
    monthly_payment: '1200.00',
    is_secured: true,
    secured_by: 7,
    home_payment_line: 'first',
  };
  const savedSession = {
    ...sessionAtStep1,
    current_step: 4,
    assets: [homeRow],
    debts: [mortgage],
    expense_info: { data_source: 'manual', rent_or_mortgage: '1200.00' },
    schedule_i_answers: { schedule_j_line_24_answer: 'no' },
  };
  const sentence = fill(CLAIM_GAP_LINE_4, { typed: '1,200.00', linked: '1,200.00' });

  function serve(patchStatus = 200) {
    const patchBodies: Record<string, unknown>[] = [];
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(savedSession)
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        patchBodies.push((await request.json()) as Record<string, unknown>);
        return patchStatus === 200
          ? HttpResponse.json(savedSession)
          : HttpResponse.json({ detail: 'no' }, { status: patchStatus });
      }),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
    return patchBodies;
  }

  it('"Yes, I pay both" saves the typed figure and the question goes', async () => {
    const patchBodies = serve();
    renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });
    expect(screen.getByText(sentence)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: LINE_4_PAY_BOTH }));

    await waitFor(() => expect(screen.queryByText(sentence)).toBeNull());
    expect(patchBodies).toEqual([{ claim_answers: { line_4_both_confirmed: '1200.00' } }]);
  });

  it('a failed line 4 answer keeps the question and says so', async () => {
    serve(400);
    renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    await userEvent.click(screen.getByRole('button', { name: LINE_4_PAY_BOTH }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(NOT_SAVED_TRY_AGAIN);
    expect(screen.getByText(sentence)).toBeInTheDocument();
  });

  function serveSession(session: Record<string, unknown>) {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(session)),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
  }

  it('a returning filer whose confirmation is stored is not asked again', async () => {
    serveSession({ ...savedSession, claim_answers: { line_4_both_confirmed: '1200.00' } });
    renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    expect(screen.queryByText(sentence)).toBeNull();
    expect(screen.queryByRole('button', { name: LINE_4_PAY_BOTH })).toBeNull();
  });

  it('names the first mortgage alone, not a linked car loan beside it', async () => {
    serveSession({
      ...savedSession,
      assets: [
        homeRow,
        {
          ...homeRow,
          id: 8,
          ab_line: '3',
          current_value: '8000.00',
          entire_value: '8000.00',
          details: { make: 'Demo', who: 'only_you' },
        },
      ],
      debts: [
        mortgage,
        {
          ...storedDebt,
          id: 12,
          creditor_name: 'Demo Auto Finance',
          debt_type: 'car_loan',
          amount_owed: '8000.00',
          monthly_payment: '300.00',
          is_secured: true,
          secured_by: 8,
          home_payment_line: null,
        },
      ],
    });
    renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    expect(screen.getByText(sentence)).toBeInTheDocument();
  });

  it('step 4 sends the same keys after the answer as before it', async () => {
    const patchBodies = serve();
    renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });
    await userEvent.click(screen.getByRole('button', { name: LINE_4_PAY_BOTH }));
    await waitFor(() => expect(screen.queryByText(sentence)).toBeNull());
    patchBodies.length = 0;

    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() => expect(patchBodies.length).toBeGreaterThan(0));
    const body = patchBodies[patchBodies.length - 1];
    expect(Object.keys(body)).toEqual(['expense_info', 'schedule_i_answers']);
    expect(Object.keys(body.expense_info as object)).toEqual([
      ...EXPENSE_FIELDS,
      ...EXPENSE_SPECIFY_FIELDS,
      'expenses_include_others',
    ]);
  });
});

// ===========================================================================
// Contracts and codebtors (DIG-147, DIG-165, DIG-166)
// ===========================================================================

/**
 * The wizard's own step title. Each list step repeats it in an h2 of its own, so a heading query
 * finds two: wait on this before `vi.useFakeTimers()`.
 */
async function expectStep(title: string) {
  await waitFor(() => expect(document.querySelector('.step-title')).toHaveTextContent(title));
}

const storedLease = {
  id: 4,
  counterparty_name: 'Oak Street Apartments',
  contract_type: 'lease',
  description: 'Apartment lease',
  street_address: '1 Demo Street',
  street_2: '',
  city: 'Demo City',
  state: 'IL',
  zip_code: '60601',
  outside_us: false,
  lease_kind: 'residential',
  monthly_payment: null,
  vehicle_asset: null,
  owes_now: 'no',
  owed_debt: null,
};
const storedGym = {
  id: 5,
  counterparty_name: 'Metro Gym',
  contract_type: 'contract',
  description: '',
};
const storedCodebtor = {
  id: 3,
  name: 'Sam Doe',
  street_address: '2 Demo Avenue',
  street_2: '',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60601',
  outside_us: false,
  relationship: 'relative',
  links: [{ kind: 'debt', id: 7 }],
};

/**
 * A filer at `step` of a list step, whose `list` holds `loaded`. The list's PUT stores each row
 * as sent, a held id kept and any other row given the next id (from 10), and replies with the
 * stored list in the order sent. A session PATCH echoes the debts it was sent, so Continue from
 * step 6 works.
 */
function serveListSaves(
  list: 'contracts' | 'codebtors',
  step: number,
  loaded: Record<string, unknown>[],
  claimAnswers: Record<string, unknown> = {}
) {
  const session = {
    ...sessionAtStep1,
    current_step: step,
    debtor_info: { first_name: 'Jane', last_name: 'Doe' },
    debts: [storedDebt],
    // Every question answered, the list under test Yes: a test that adds a row needs its list's
    // answer to be Yes
    claim_answers: {
      no_debts: null,
      contracts_answer: list === 'contracts' ? 'yes' : 'no',
      codebtors_answer: list === 'codebtors' ? 'yes' : 'no',
      community_lived: 'no',
      ...claimAnswers,
    },
    petition_answers: LATER_PETITION_GATES,
  };
  const otherList = list === 'contracts' ? 'codebtors' : 'contracts';
  let held = loaded;
  let nextId = 10;
  let heldReply: Promise<void> | null = null;
  const bodies: Record<string, unknown>[][] = [];
  const patches: Record<string, unknown>[] = [];
  server.use(
    http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(session)),
    http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      patches.push(body);
      return HttpResponse.json({ ...session, debts: body.debts ?? session.debts });
    }),
    http.get(`http://localhost:8000/api/intake/sessions/:id/${list}/`, () =>
      HttpResponse.json(held)
    ),
    http.get(`http://localhost:8000/api/intake/sessions/:id/${otherList}/`, () =>
      HttpResponse.json([])
    ),
    http.put(`http://localhost:8000/api/intake/sessions/:id/${list}/`, async ({ request }) => {
      const rows = (await request.json()) as Record<string, unknown>[];
      bodies.push(rows);
      const heldIds = held.map((row) => row.id);
      held = rows.map((row) => ({
        ...row,
        id: heldIds.includes(row.id) ? row.id : nextId++,
      }));
      const reply = HttpResponse.json(held);
      if (heldReply) {
        const wait = heldReply;
        heldReply = null;
        await wait;
      }
      return reply;
    }),
    http.put(`http://localhost:8000/api/intake/sessions/:id/${otherList}/`, async ({ request }) => {
      const rows = (await request.json()) as Record<string, unknown>[];
      return HttpResponse.json(rows.map((row, index) => ({ ...row, id: row.id ?? 500 + index })));
    })
  );
  return {
    bodies,
    patches,
    stored: () => held,
    /** Keeps the next save's reply on its way until the returned function is called */
    holdNextReply: () => {
      let release = () => {};
      heldReply = new Promise<void>((resolve) => {
        release = resolve;
      });
      return release;
    },
  };
}

describe.each([
  {
    list: 'contracts' as const,
    step: 7,
    title: 'Contracts & Leases',
    nameKey: 'counterparty_name',
    // The name box carries the required mark, so its accessible name has more than the label
    nameLabel: new RegExp(`^${SCHEDULE_G_NAME_LABEL}`),
    addLabel: /add contract/i,
    stored: storedLease as Record<string, unknown>,
  },
  {
    list: 'codebtors' as const,
    step: 8,
    title: 'Codebtors',
    nameKey: 'name',
    // The name box carries the required mark too
    nameLabel: /^Full Name/ as string | RegExp,
    addLabel: /add codebtor/i,
    stored: storedCodebtor as Record<string, unknown>,
  },
])(
  'IntakeWizard $list autosave and keep one id',
  { timeout: 30_000 },
  ({ list, step, title, nameKey, nameLabel, addLabel, stored }) => {
    const nameBox = (index: number) => screen.getAllByRole('textbox', { name: nameLabel })[index];
    const idsSent = (bodies: Record<string, unknown>[][]) =>
      bodies.map((rows) => rows.map((row) => row.id));
    /** Adds a row and types its name, as the filer does */
    const addRow = (index: number, name: string) => {
      fireEvent.click(screen.getByRole('button', { name: addLabel }));
      fireEvent.change(nameBox(index), { target: { value: name } });
    };

    beforeEach(() => {
      server.use(
        http.post(
          'http://localhost:8000/api/intake/sessions/:id/update_step/',
          async ({ request }) => {
            const { current_step } = (await request.json()) as { current_step: number };
            return HttpResponse.json({
              session: { ...sessionAtStep1, current_step },
              message: 'Step updated.',
            });
          }
        ),
        http.post(
          'http://localhost:8000/api/audit/logs/',
          () => new HttpResponse(null, { status: 201 })
        )
      );
    });

    it('autosaves a new row two seconds after the filer stops typing, then saves an edit under the id it got', async () => {
      const { bodies } = serveListSaves(list, step, []);
      renderWizard();
      await expectStep(title);

      vi.useFakeTimers();
      try {
        addRow(0, 'Lakeview Storage');
        await waitSeconds(3);
        fireEvent.change(nameBox(0), { target: { value: 'Lakeview Storage Co' } });
        await waitSeconds(3);
      } finally {
        vi.useRealTimers();
      }

      expect(idsSent(bodies)).toEqual([[undefined], [10]]);
      // The browser's own key never reaches the server
      for (const rows of bodies) expect(rows[0]).not.toHaveProperty('_key');
    });

    it('shows the autosaved row after a refresh', async () => {
      const saves = serveListSaves(list, step, []);
      const { unmount } = renderWizard();
      await expectStep(title);

      vi.useFakeTimers();
      try {
        addRow(0, 'Lakeview Storage');
        await waitSeconds(3);
      } finally {
        vi.useRealTimers();
      }
      expect(saves.bodies).toHaveLength(1);

      unmount();
      renderWizard();
      await expectStep(title);

      await waitFor(() => expect(nameBox(0)).toHaveValue('Lakeview Storage'));
    });

    it('sends a stored row whose name was cleared, nameless and under its id (R17)', async () => {
      const { bodies } = serveListSaves(list, step, [stored]);
      renderWizard();
      await expectStep(title);
      await waitFor(() => expect(nameBox(0)).toHaveValue(String(stored[nameKey])));

      vi.useFakeTimers();
      try {
        fireEvent.change(nameBox(0), { target: { value: '' } });
        await waitSeconds(5);
        expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();
      } finally {
        vi.useRealTimers();
      }

      expect(idsSent(bodies)).toEqual([[stored.id]]);
      expect(bodies[0][0][nameKey]).toBe('');
    });

    // On a slow link the filer's next edit can be saved before the first save's reply brings the
    // new row's id. The wizard must settle on the id the server holds: a save carrying an id the
    // server has already replaced creates the row again, and each such save can start another.
    it('keeps the id the server holds when the filer edits while a save is on its way, without a save loop', async () => {
      const saves = serveListSaves(list, step, []);
      renderWizard();
      await expectStep(title);
      const landFirstSave = saves.holdNextReply();

      vi.useFakeTimers();
      try {
        addRow(0, 'Lakeview Storage');
        await waitSeconds(3);
        expect(saves.bodies).toHaveLength(1);

        const landSecondSave = saves.holdNextReply();
        fireEvent.change(nameBox(0), { target: { value: 'Lakeview Storage Co' } });
        await waitSeconds(3);
        // The two replies land 2.5 s apart, longer than the autosave delay
        await act(async () => landFirstSave());
        await waitSeconds(2);
        await act(() => vi.advanceTimersByTimeAsync(500));
        await act(async () => landSecondSave());
        await waitSeconds(15);

        // The next edit updates the row the server holds instead of replacing it
        fireEvent.change(nameBox(0), { target: { value: 'Lakeview Storage Center' } });
        await waitSeconds(5);
      } finally {
        vi.useRealTimers();
      }

      expect(saves.bodies.length).toBeLessThanOrEqual(3);
      const [lastSent] = saves.bodies[saves.bodies.length - 1];
      expect(lastSent.id).toBe(saves.stored()[0].id);
    });

    it('drops a row the filer removed while its save was on its way', async () => {
      const saves = serveListSaves(list, step, []);
      renderWizard();
      await expectStep(title);
      const landSave = saves.holdNextReply();

      vi.useFakeTimers();
      try {
        addRow(0, 'Lakeview Storage');
        addRow(1, 'Harbor Light Storage');
        await waitSeconds(3);
        expect(saves.bodies).toHaveLength(1);

        fireEvent.click(screen.getAllByRole('button', { name: 'Remove' })[0]);
        await act(async () => landSave());
        await waitSeconds(4);
      } finally {
        vi.useRealTimers();
      }

      expect(idsSent(saves.bodies)).toEqual([[undefined, undefined], [11]]);
      expect(saves.stored().map((row) => [row.id, row[nameKey]])).toEqual([
        [11, 'Harbor Light Storage'],
      ]);
    });

    it("fails the save, and says so, when the reply doesn't list each row sent", async () => {
      serveListSaves(list, step, [stored]);
      server.use(
        http.put(`http://localhost:8000/api/intake/sessions/:id/${list}/`, () =>
          HttpResponse.json([])
        )
      );
      renderWizard();
      await expectStep(title);
      await waitFor(() => expect(screen.getByRole('button', { name: /continue/i })).toBeEnabled());

      await userEvent.click(screen.getByRole('button', { name: /continue/i }));

      expect(await screen.findByText(/couldn't save just now/i)).toBeInTheDocument();
      expect(document.querySelector('.step-title')).toHaveTextContent(title);
    });

    it('keeps an edit made just before Go Back, and saves it when the step shows again', async () => {
      const { bodies } = serveListSaves(list, step, [stored]);
      renderWizard();
      await expectStep(title);
      await waitFor(() => expect(nameBox(0)).toHaveValue(String(stored[nameKey])));

      vi.useFakeTimers();
      try {
        fireEvent.change(nameBox(0), { target: { value: 'Renamed' } });
        await waitSeconds(1);
        fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
        await waitSeconds(1);
        expect(bodies).toEqual([]);

        // Continue saves the step before this one: step 6's debt, or step 7's empty list
        fireEvent.click(screen.getByRole('button', { name: /continue/i }));
        await waitSeconds(4);
      } finally {
        vi.useRealTimers();
      }

      await expectStep(title);
      expect(nameBox(0)).toHaveValue('Renamed');
      expect(bodies[bodies.length - 1]).toEqual([{ ...stored, [nameKey]: 'Renamed' }]);
    });
  }
);

describe('IntakeWizard contracts and codebtors', { timeout: 15_000 }, () => {
  let contractSaves: unknown[];
  let codebtorSaves: unknown[];
  let stepUpdates: unknown[];
  let sessionPatches: Record<string, unknown>[];

  /**
   * A filer who stopped at `step`, with these lists saved earlier, one stored debt and every claim
   * question answered (a Yes for each list that has rows). `claimAnswers` is laid over those.
   */
  function serveFiler(
    step: number,
    contracts: Record<string, unknown>[] = [],
    codebtors: Record<string, unknown>[] = [],
    claimAnswers: Record<string, unknown> = {},
    petitionAnswers: Record<string, unknown> = LATER_PETITION_GATES
  ) {
    const session = {
      ...sessionAtStep1,
      current_step: step,
      debtor_info: { first_name: 'Jane', last_name: 'Doe' },
      debts: [storedDebt],
      claim_answers: {
        no_debts: null,
        contracts_answer: contracts.length > 0 ? 'yes' : 'no',
        codebtors_answer: codebtors.length > 0 ? 'yes' : 'no',
        community_lived: 'no',
        ...claimAnswers,
      },
      petition_answers: petitionAnswers,
    };
    // The server gives each new row the next id, as the list save does
    let nextId = 10;
    const saveList =
      (saves: unknown[]) =>
      async ({ request }: { request: Request }) => {
        const rows = (await request.json()) as Record<string, unknown>[];
        saves.push(rows);
        return HttpResponse.json(rows.map((row) => ({ ...row, id: row.id ?? nextId++ })));
      };
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(session)),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        sessionPatches.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(session);
      }),
      http.get('http://localhost:8000/api/intake/sessions/:id/contracts/', () =>
        HttpResponse.json(contracts)
      ),
      http.get('http://localhost:8000/api/intake/sessions/:id/codebtors/', () =>
        HttpResponse.json(codebtors)
      ),
      http.put('http://localhost:8000/api/intake/sessions/:id/contracts/', saveList(contractSaves)),
      http.put('http://localhost:8000/api/intake/sessions/:id/codebtors/', saveList(codebtorSaves))
    );
  }

  /** Answers every question of the contract at `index`, as the filer does (fireEvent: fake timers) */
  const completeContract = (index: number) => {
    const set = (name: string, value: string) =>
      fireEvent.change(document.querySelector(`[name="${name}"]`)!, { target: { value } });
    set(`street_address_${index}`, '1 Demo Street');
    set(`city_${index}`, 'Demo City');
    set(`state_${index}`, 'IL');
    set(`zip_code_${index}`, '60601');
    set(`contract_type_${index}`, 'contract');
    set(`description_${index}`, 'Storage unit');
    fireEvent.click(document.querySelector(`[name="owes_now_${index}"][value="no"]`)!);
  };

  /** Answers every question of the codebtor at `index` and links the stored debt (fireEvent: fake timers) */
  const completeCodebtor = (index: number) => {
    const set = (name: string, value: string) =>
      fireEvent.change(document.querySelector(`[name="${name}"]`)!, { target: { value } });
    set(`codebtor_street_address_${index}`, '2 Demo Avenue');
    set(`codebtor_city_${index}`, 'Demo City');
    set(`codebtor_state_${index}`, 'IL');
    set(`codebtor_zip_code_${index}`, '60601');
    fireEvent.click(document.querySelector(`[name="codebtor_links_${index}"][value="debt-7"]`)!);
  };

  beforeEach(() => {
    contractSaves = [];
    codebtorSaves = [];
    stepUpdates = [];
    sessionPatches = [];
    server.use(
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          const body = (await request.json()) as { current_step: number };
          stepUpdates.push(body.current_step);
          return HttpResponse.json({
            session: { ...sessionAtStep1, current_step: body.current_step, status: 'in_progress' },
            message: 'Step updated.',
          });
        }
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
  });

  it.each([
    [7, 'Contracts & Leases'],
    [8, 'Codebtors'],
  ])('lets a filer who resumes at step %i (%s) continue', async (step, title) => {
    serveFiler(step);
    renderWizard();
    await expectStep(title);

    // The step reports itself valid just after it shows
    await waitFor(() => expect(screen.getByRole('button', { name: /continue/i })).toBeEnabled());
  });

  it('saves the whole contracts list on Continue, and sends the saved ids on the next save instead of adding rows again', async () => {
    serveFiler(7, [storedLease, storedGym]);
    renderWizard();
    await expectStep('Contracts & Leases');

    // Remove the gym, add a storage unit, and add a row the filer leaves blank. The edits and
    // Continue come on one fake clock, so no autosave fires before Continue (R14).
    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getAllByRole('button', { name: 'Remove' })[1]);
      fireEvent.click(screen.getByRole('button', { name: /add contract/i }));
      fireEvent.change(screen.getAllByPlaceholderText('e.g., Landlord Inc.')[1], {
        target: { value: 'Lakeview Storage' },
      });
      completeContract(1);
      fireEvent.click(screen.getByRole('button', { name: /add contract/i }));
      fireEvent.click(screen.getByRole('button', { name: /continue/i }));
      await waitSeconds(1);
    } finally {
      vi.useRealTimers();
    }
    await expectStep('Codebtors');

    const lakeview = {
      counterparty_name: 'Lakeview Storage',
      contract_type: 'contract',
      description: 'Storage unit',
      street_address: '1 Demo Street',
      street_2: '',
      city: 'Demo City',
      state: 'IL',
      zip_code: '60601',
      outside_us: false,
      lease_kind: null,
      monthly_payment: null,
      vehicle_asset: null,
      owes_now: 'no',
      owed_debt: null,
    };
    expect(contractSaves).toEqual([[storedLease, lakeview]]);

    // Back to Contracts and on again: the storage unit now carries the id the save returned
    await userEvent.click(screen.getByRole('button', { name: 'Go Back' }));
    await expectStep('Contracts & Leases');
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await expectStep('Codebtors');

    expect(contractSaves[1]).toEqual([storedLease, { ...lakeview, id: 10 }]);
  });

  // A second press while the first save is on its way would save the list twice, and Schedule G
  // would print each contract twice
  it('saves the contracts list once when the filer double-clicks Continue', async () => {
    serveFiler(7, [storedLease]);
    renderWizard();
    await expectStep('Contracts & Leases');
    const continueButton = screen.getByRole('button', { name: /continue/i });
    await waitFor(() => expect(continueButton).toBeEnabled());

    fireEvent.click(continueButton);
    fireEvent.click(continueButton);
    await expectStep('Codebtors');

    expect(contractSaves).toEqual([[storedLease]]);
    expect(stepUpdates).toEqual([8]);
  });

  // An empty list means the filer has none: a removed last row must not stay stored and
  // print on Schedule G or H
  it.each([
    [7, 'Contracts & Leases', 'Codebtors', [storedLease], [], () => contractSaves, {}],
    [
      8,
      'Codebtors',
      'Review & Results',
      [],
      [storedCodebtor],
      () => codebtorSaves,
      { codebtors_answer: 'no' },
    ],
  ])(
    'saves an empty list when the filer removes the last row on step %i (%s)',
    async (step, title, nextTitle, contracts, codebtors, saves, claimAnswers) => {
      // The list's answer is No, so the empty list is no gap (the answer shows at load)
      serveFiler(
        step,
        contracts,
        codebtors,
        step === 7 ? { contracts_answer: 'no' } : claimAnswers
      );
      renderWizard();
      await expectStep(title);

      vi.useFakeTimers();
      try {
        fireEvent.click(screen.getByRole('button', { name: 'Remove' }));
        fireEvent.click(screen.getByRole('button', { name: /continue/i }));
        await waitSeconds(1);
      } finally {
        vi.useRealTimers();
      }
      await expectStep(nextTitle);

      expect(saves()).toEqual([[]]);
    }
  );

  it.each([
    [7, 'Contracts & Leases', 'contracts', [storedLease], [], 'counterparty_name'],
    [8, 'Codebtors', 'codebtors', [], [storedCodebtor], 'name'],
  ])(
    'keeps the filer on step %i (%s) and says so when the list cannot be saved',
    async (step, title, list, contracts, codebtors, field) => {
      serveFiler(step, contracts, codebtors);
      server.use(
        http.put(`http://localhost:8000/api/intake/sessions/:id/${list}/`, () =>
          HttpResponse.json([{ [field]: ['This field may not be blank.'] }], {
            status: 400,
          })
        )
      );
      renderWizard();
      await expectStep(title);

      await userEvent.click(screen.getByRole('button', { name: /continue/i }));

      expect(await screen.findByText(/couldn't save just now/i)).toBeInTheDocument();
      expect(document.querySelector('.step-title')).toHaveTextContent(title);
      expect(stepUpdates).toEqual([]);
    }
  );

  it("asks for the other party's name before a contract the filer started can be saved", async () => {
    serveFiler(7, [], [], { contracts_answer: 'yes' });
    renderWizard();
    await expectStep('Contracts & Leases');

    await userEvent.click(screen.getByRole('button', { name: /add contract/i }));
    await userEvent.type(screen.getByPlaceholderText('e.g., Apartment lease, car lease'), 'Lease');

    // The wizard has a status region of its own, so the step's is found inside the step
    const step = document.querySelector('.contracts-step') as HTMLElement;
    expect(within(step).getByRole('status')).toHaveTextContent(CONTRACT_GAP_NO_NAME);
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();
  });

  it("asks for the person's name before a codebtor the filer started can be saved", async () => {
    serveFiler(8, [], [], { codebtors_answer: 'yes', community_lived: 'no' });
    renderWizard();
    await expectStep('Codebtors');

    await userEvent.click(screen.getByRole('button', { name: /add codebtor/i }));
    await userEvent.type(field('codebtor_city_0'), 'Chicago');

    // The wizard has a status region of its own, so the step's is found inside the step
    const step = document.querySelector('.codebtors-step') as HTMLElement;
    expect(within(step).getByRole('status')).toHaveTextContent(CODEBTOR_GAP_NO_NAME);
    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();
  });

  it('saves the codebtors list on Continue and lists both lists on Review', async () => {
    serveFiler(8, [storedLease], [storedCodebtor]);
    renderWizard();
    await expectStep('Codebtors');

    // Add Ana, and add a row the filer leaves blank
    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: /add codebtor/i }));
      fireEvent.change(screen.getAllByPlaceholderText('e.g., Jane Smith')[1], {
        target: { value: 'Ana Ruiz' },
      });
      completeCodebtor(1);
      fireEvent.click(screen.getByRole('button', { name: /add codebtor/i }));
      fireEvent.click(screen.getByRole('button', { name: /continue/i }));
      await waitSeconds(1);
    } finally {
      vi.useRealTimers();
    }
    await expectStep('Review & Results');

    expect(codebtorSaves).toEqual([
      [
        storedCodebtor,
        {
          name: 'Ana Ruiz',
          street_address: '2 Demo Avenue',
          street_2: '',
          city: 'Demo City',
          state: 'IL',
          zip_code: '60601',
          outside_us: false,
          relationship: '',
          links: [{ kind: 'debt', id: 7 }],
        },
      ],
    ]);
    // Review lists the rows the server holds, not the blank row the step still shows
    expect(screen.getByText('Codebtors (2)')).toBeInTheDocument();
    expect(screen.getByText(/Oak Street Apartments/)).toBeInTheDocument();
    expect(screen.getByText(/Sam Doe/)).toBeInTheDocument();
    expect(screen.getByText(/Ana Ruiz/)).toBeInTheDocument();
  });

  it('shows the saved contracts and codebtors on Review to a filer who resumes there', async () => {
    serveFiler(9, [storedLease], [storedCodebtor]);
    renderWizard();
    await expectStep('Review & Results');

    expect(screen.getByText(/Oak Street Apartments/)).toBeInTheDocument();
    expect(screen.getByText(/Sam Doe/)).toBeInTheDocument();
  });

  it('shows no step when the saved contracts cannot be read, so Continue never saves an empty list over them', async () => {
    serveFiler(7, [storedLease]);
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/contracts/', () =>
        HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
      )
    );
    renderWizard();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "We couldn't get your latest information just now. Please try again in a moment."
    );
    expect(screen.queryByRole('button', { name: /continue/i })).not.toBeInTheDocument();
    expect(contractSaves).toEqual([]);
  });

  it('shows no step when the saved codebtors cannot be read, so Continue never saves an empty list over them', async () => {
    serveFiler(8, [], [storedCodebtor]);
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/codebtors/', () =>
        HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
      )
    );
    renderWizard();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "We couldn't get your latest information just now. Please try again in a moment."
    );
    expect(screen.queryByRole('button', { name: /continue/i })).not.toBeInTheDocument();
    expect(codebtorSaves).toEqual([]);
  });

  // =========================================================================
  // What steps 6, 7 and 8 save (3c3 Task 7)
  // =========================================================================

  const onStep6 = { ...sessionAtStep1, current_step: 6, debts: [storedDebt] };
  const sentDebts = (body: unknown) => (body as { debts: Record<string, unknown>[] }).debts;
  /** True when any key, at any depth, starts with an underscore */
  const hasBrowserKey = (value: unknown): boolean =>
    typeof value === 'object' && value !== null
      ? Object.entries(value).some(([key, inner]) => key.startsWith('_') || hasBrowserKey(inner))
      : false;
  /** Step 6's Form 101 line 16 and Supp keys with nothing answered, as its body sends them */
  const NO_DEBT_NATURE_ANSWER = {
    debt_nature: null,
    debt_nature_text: null,
    disabled_veteran: null,
    debts_on_duty: null,
    reservist: null,
    called_to_duty: null,
    duty_category: null,
    duty_released_on: null,
    duty_ended_on: null,
  };

  it('saves a half-filled debt two seconds after typing stops, with its amount as 0', async () => {
    const { bodies } = serveSessionSaves({ ...sessionAtStep1, current_step: 6 });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.change(field('creditor_name_0'), { target: { value: 'Demo Card Services' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies).toHaveLength(1);
    expect(sentDebts(bodies[0])).toHaveLength(1);
    expect(sentDebts(bodies[0])[0]).toMatchObject({
      creditor_name: 'Demo Card Services',
      amount_owed: 0,
      monthly_payment: null,
    });
    expect((bodies[0] as { claim_answers: unknown }).claim_answers).toEqual({ no_debts: null });
  });

  it('shows "no amounts owed" on Review when the filer pressed it and left a blank added row', async () => {
    serveSessionSaves({
      ...sessionAtStep1,
      current_step: 6,
      claim_answers: { contracts_answer: 'no', codebtors_answer: 'no', community_lived: 'no' },
      petition_answers: LATER_PETITION_GATES,
    });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    await userEvent.click(screen.getByRole('button', { name: /add another amount owed/i }));
    await userEvent.click(screen.getByRole('button', { name: NO_DEBTS_BUTTON }));
    for (const title of ['Contracts & Leases', 'Codebtors', 'Review & Results']) {
      const next = await screen.findByRole('button', { name: 'Continue' });
      await waitFor(() => expect(next).toBeEnabled());
      await userEvent.click(next);
      await expectStep(title);
    }

    expect(screen.getByText(REVIEW_NO_DEBTS)).toBeInTheDocument();
    expect(screen.getByText('Amounts Owed (0)')).toBeInTheDocument();
  });

  it('sends a blank type for a stored debt whose type was cleared, so the server drops the old one', async () => {
    const { bodies } = serveSessionSaves(onStep6);
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.change(field('debt_type_0'), { target: { value: '' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(sentDebts(bodies[bodies.length - 1])[0]).toMatchObject({ id: 7, debt_type: '' });
  });

  it('sends a stored debt whose name was cleared, under its id', async () => {
    const { bodies } = serveSessionSaves(onStep6);
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.change(field('creditor_name_0'), { target: { value: '' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies).toHaveLength(1);
    expect(sentDebts(bodies[0])[0]).toMatchObject({ id: 7, creditor_name: '' });
  });

  it('leaves out only a new row with nothing in it', async () => {
    const { bodies } = serveSessionSaves(onStep6);
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: /add another amount owed/i }));
      fireEvent.change(field('creditor_name_0'), {
        target: { value: 'Northwind Card Services Co' },
      });
      await waitSeconds(3);
      expect(sentDebts(bodies[bodies.length - 1]).map((row) => row.id)).toEqual([7]);

      fireEvent.change(field('creditor_name_1'), { target: { value: 'Demo Clinic' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(sentDebts(bodies[bodies.length - 1]).map((row) => row.id)).toEqual([7, undefined]);
  });

  it('sends no_debts only while "I have no amounts owed" is pressed and no row is touched', async () => {
    const { bodies } = serveSessionSaves({ ...sessionAtStep1, current_step: 6 });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: 'I have no amounts owed' }));
      await waitSeconds(3);
      expect(bodies).toHaveLength(1);
      expect(bodies[0]).toEqual({
        debts: [],
        claim_answers: { no_debts: true },
        petition_answers: NO_DEBT_NATURE_ANSWER,
      });

      fireEvent.change(field('creditor_name_0'), { target: { value: 'Demo Clinic' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    const last = bodies[bodies.length - 1] as { debts: unknown[]; claim_answers: unknown };
    expect(last.debts).toHaveLength(1);
    expect(last.claim_answers).toEqual({ no_debts: null });
    expect(
      screen.queryByRole('button', { name: 'I have no amounts owed' })
    ).not.toBeInTheDocument();
  });

  it('treats a loaded row as pressed and a loaded scanned draft as unpressed', async () => {
    const draft = {
      ...storedDebt,
      id: 8,
      creditor_name: 'Demo Scan',
      debt_type: 'other',
      is_draft: true,
    };
    const { bodies } = serveSessionSaves({
      ...sessionAtStep1,
      current_step: 6,
      debts: [storedDebt, draft],
    });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.change(field('debt_type_0'), { target: { value: 'auto_loan' } });
      await waitSeconds(3);
      expect(sentDebts(bodies[bodies.length - 1])[0].is_secured).toBe(false);

      fireEvent.change(field('debt_type_1'), { target: { value: 'auto_loan' } });
      await waitSeconds(3);
      expect(sentDebts(bodies[bodies.length - 1])[1].is_secured).toBe(true);
    } finally {
      vi.useRealTimers();
    }
  });

  it('shows a stored no_debts answer beside a stored row as not pressed', async () => {
    serveSessionSaves({
      ...sessionAtStep1,
      current_step: 6,
      debts: [storedDebt],
      claim_answers: { no_debts: true },
      // Line 16 and the Supp's gates answered, so the status speaks only to the rows (4d)
      petition_answers: LATER_PETITION_GATES,
    });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    expect((field('creditor_name_0') as HTMLInputElement).value).toBe('Northwind Card Services');
    expect(
      screen.queryByRole('button', { name: 'I have no amounts owed', pressed: true })
    ).not.toBeInTheDocument();
    // The answer is not read as a contradiction the filer can't undo
    expect(document.querySelector('.debts-step [role="status"]')).toBeEmptyDOMElement();
  });

  // Form 101 line 16 and Form 122A-1Supp's questions ride in step 6's session PATCH, each key as
  // its answer or null, so a stored answer reaches the body as it was loaded (4d)
  const sentPetition = (body: unknown) =>
    (body as { petition_answers: Record<string, unknown> }).petition_answers;
  const choose = (name: string, value: string) =>
    fireEvent.click(document.querySelector(`input[name="${name}"][value="${value}"]`)!);

  it('step 6 sends every line 16 and military key, null while unanswered', async () => {
    const { bodies } = serveSessionSaves({
      ...onStep6,
      petition_answers: { hazard_answer: 'no', rents_residence: 'no' },
    });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    vi.useFakeTimers();
    try {
      choose('debt_nature', 'consumer');
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies).toHaveLength(1);
    // The step's nine keys and no other petition key: the hazard and rent answers are other steps'
    expect(sentPetition(bodies[0])).toEqual({ ...NO_DEBT_NATURE_ANSWER, debt_nature: 'consumer' });
  });

  it('step 6 still sends military answers kept under business', async () => {
    const military = {
      disabled_veteran: 'yes',
      debts_on_duty: 'no',
      reservist: 'yes',
      called_to_duty: 'yes',
      duty_category: '2',
      duty_released_on: '01/15/2025',
    };
    const { bodies } = serveSessionSaves({
      ...onStep6,
      petition_answers: { ...LATER_PETITION_GATES, debt_nature: 'consumer', ...military },
    });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    vi.useFakeTimers();
    try {
      choose('debt_nature', 'business');
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    // Business hides the military block but deletes nothing: the answers stay behind Show and
    // Delete, and a null would remove them on the server (4d-R15)
    expect(bodies).toHaveLength(1);
    expect(sentPetition(bodies[0])).toEqual({
      ...NO_DEBT_NATURE_ANSWER,
      debt_nature: 'business',
      ...military,
    });
  });

  it('autosave on step 6 sends nothing more after a save', async () => {
    const { bodies } = serveSessionSaves({
      ...onStep6,
      petition_answers: { hazard_answer: 'no', rents_residence: 'no' },
    });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    vi.useFakeTimers();
    try {
      choose('debt_nature', 'consumer');
      await waitSeconds(3);
      expect(bodies).toHaveLength(1);
      // The saved copy keeps the petition answers sent, so the next body equals it
      await waitSeconds(6);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies).toHaveLength(1);
  });

  // F0: once a step 6 save that changed line 16's or the Supp's answers has landed, the sidebar
  // works the means test out again, and that call saves the row an unfinished intake's dashboard
  // reads, so a presumption worked out before a business answer, or before an open military
  // question, never stays on show
  /** Records each means test call as the number of session PATCHes the server had by then */
  function serveCalculates(bodies: unknown[]) {
    const calls: number[] = [];
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () => {
        calls.push(bodies.length);
        return HttpResponse.json({
          means_test_result: {
            passes_means_test: true,
            cmi: 1000,
            median_income_threshold: 5000,
            outcome: 'at_or_below_median',
            tables_gap: null,
          },
          session_id: 1,
        });
      })
    );
    return calls;
  }

  it('works the means test out again once a save that changes line 16 has landed', async () => {
    const { bodies } = serveSessionSaves({
      ...onStep6,
      petition_answers: { hazard_answer: 'no', rents_residence: 'no' },
    });
    const calls = serveCalculates(bodies);
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
    // The sidebar's own first call, when the step shows
    await waitFor(() => expect(calls).toEqual([0]));

    vi.useFakeTimers();
    try {
      choose('debt_nature', 'business');
      await waitSeconds(4);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies).toHaveLength(1);
    // Exactly one more call, made after the PATCH
    expect(calls).toEqual([0, 1]);
  });

  it('works nothing out again on a visit alone, or a save that changes no line 16 answer', async () => {
    const { bodies } = serveSessionSaves({
      ...onStep6,
      petition_answers: LATER_PETITION_GATES,
    });
    const calls = serveCalculates(bodies);
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
    await waitFor(() => expect(calls).toEqual([0]));

    vi.useFakeTimers();
    try {
      // A visit alone saves nothing and works nothing out
      await waitSeconds(4);
      expect(bodies).toHaveLength(0);
      expect(calls).toEqual([0]);

      // A save of a row alone sends line 16's answers as loaded
      fireEvent.change(field('creditor_name_0'), { target: { value: 'Northwind Bank' } });
      await waitSeconds(4);
    } finally {
      vi.useRealTimers();
    }

    expect(bodies).toHaveLength(1);
    expect(calls).toEqual([0]);
  });

  it('sends a new debt that has a number but no name', async () => {
    const { bodies } = serveSessionSaves(onStep6);
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: /add another amount owed/i }));
      fireEvent.change(field('account_number_1'), { target: { value: '1234' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(sentDebts(bodies[bodies.length - 1]).map((row) => row.id)).toEqual([7, undefined]);
  });

  it('fails the contracts save when its answer does not save, and sends both again next time', async () => {
    serveFiler(7, [storedLease], [], { contracts_answer: 'yes' });
    let patchCalls = 0;
    server.use(
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        sessionPatches.push((await request.json()) as Record<string, unknown>);
        patchCalls += 1;
        // A 400, not a 5xx: withRetry retries a 5xx on a backoff that tangles with the fake clock
        if (patchCalls === 1) {
          return HttpResponse.json(
            { claim_answers: { contracts_answer: ['Check the answer for contracts_answer.'] } },
            { status: 400 }
          );
        }
        return HttpResponse.json({ ...sessionAtStep1, current_step: 7 });
      })
    );
    renderWizard();
    await expectStep('Contracts & Leases');

    vi.useFakeTimers();
    try {
      fireEvent.change(screen.getByPlaceholderText('e.g., Landlord Inc.'), {
        target: { value: 'Oak Street Apartments LLC' },
      });
      fireEvent.click(screen.getByRole('button', { name: /continue/i }));
      await waitSeconds(1);

      expect(screen.getByText(/couldn't save just now/i)).toBeInTheDocument();
      expect(document.querySelector('.step-title')).toHaveTextContent('Contracts & Leases');
      expect(stepUpdates).toEqual([]);
      expect(contractSaves).toHaveLength(1);
      expect(sessionPatches).toHaveLength(1);

      fireEvent.click(screen.getByRole('button', { name: /continue/i }));
      await waitSeconds(1);
    } finally {
      vi.useRealTimers();
    }
    await expectStep('Codebtors');

    // The ids written into the rows after the first PUT change the body, which can start one more
    // autosave, so the counts are not exact
    expect(contractSaves.length).toBeGreaterThanOrEqual(2);
    expect((contractSaves[1] as Record<string, unknown>[])[0].id).toBe(4);
    expect(sessionPatches.length).toBeGreaterThanOrEqual(2);
    // Form 101 line 11's keys ride in the same PATCH, so they are sent again with G's answer
    for (const patch of sessionPatches) {
      expect(patch).toEqual({
        claim_answers: { contracts_answer: 'yes' },
        petition_answers: { rents_residence: 'no', eviction_judgment: null, ...NO_LANDLORD },
      });
    }
  });

  // The PUT creates the new row, the claim-answers PATCH then fails: the row must hold the id the
  // server gave it, or the next save creates it a second time and a codebtor's link to the old
  // contract id reads as dead (B9)
  it.each([
    [
      7,
      'Contracts & Leases',
      'contracts_answer',
      'e.g., Landlord Inc.',
      /add contract/i,
      () => contractSaves,
    ],
    [8, 'Codebtors', 'codebtors_answer', 'e.g., Jane Smith', /add codebtor/i, () => codebtorSaves],
  ] as const)(
    'keeps the id the list save gave a new row when the answers save after it fails, on step %i (%s)',
    async (step, title, answerKey, placeholder, addButton, saves) => {
      serveFiler(step, [], [], { [answerKey]: 'yes' });
      let patchCalls = 0;
      server.use(
        http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
          sessionPatches.push((await request.json()) as Record<string, unknown>);
          patchCalls += 1;
          if (patchCalls === 1) {
            return HttpResponse.json(
              { claim_answers: { [answerKey]: ['Check the answer.'] } },
              { status: 400 }
            );
          }
          return HttpResponse.json({ ...sessionAtStep1, current_step: step });
        })
      );
      renderWizard();
      await expectStep(title);

      vi.useFakeTimers();
      try {
        fireEvent.click(screen.getByRole('button', { name: addButton }));
        const boxes = screen.getAllByPlaceholderText(placeholder);
        fireEvent.change(boxes[boxes.length - 1], { target: { value: 'Lakeview Storage' } });
        await waitSeconds(3);
        // Autosave sent the new row, the server gave it id 10 and the PATCH failed
        expect(saves()).toHaveLength(1);
        expect(patchCalls).toBeGreaterThanOrEqual(1);

        fireEvent.click(screen.getByRole('button', { name: /continue/i }));
        await waitSeconds(1);
      } finally {
        vi.useRealTimers();
      }

      const sent = saves() as Record<string, unknown>[][];
      expect(sent.length).toBeGreaterThanOrEqual(2);
      const next = sent[sent.length - 1];
      expect(next.map((row) => row.id)).toEqual([10]);
    }
  );

  // The ids go into the rows after the answers save. Written before it, the render that follows
  // sees a body unlike the copy still on its way and starts a timer that sends the same list again.
  it.each([
    [
      7,
      'Contracts & Leases',
      'contracts_answer',
      'e.g., Landlord Inc.',
      /add contract/i,
      () => contractSaves,
    ],
    [8, 'Codebtors', 'codebtors_answer', 'e.g., Jane Smith', /add codebtor/i, () => codebtorSaves],
  ] as const)(
    'sends a new row once, not again after the answers save lands, on step %i (%s)',
    async (step, title, answerKey, placeholder, addButton, saves) => {
      serveFiler(step, [], [], { [answerKey]: 'yes' });
      let patchLanded = false;
      server.use(
        http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
          sessionPatches.push((await request.json()) as Record<string, unknown>);
          await delay(600);
          patchLanded = true;
          return HttpResponse.json({ ...sessionAtStep1, current_step: step });
        })
      );
      renderWizard();
      await expectStep(title);

      fireEvent.click(screen.getByRole('button', { name: addButton }));
      const boxes = screen.getAllByPlaceholderText(placeholder);
      fireEvent.change(boxes[boxes.length - 1], { target: { value: 'Lakeview Storage' } });

      await waitFor(() => expect(patchLanded).toBe(true), { timeout: 6000 });
      // Longer than the autosave delay (2 s)
      await new Promise((resolve) => setTimeout(resolve, 3000));

      expect(saves()).toHaveLength(1);
      expect(sessionPatches).toHaveLength(1);
    }
  );

  // A claim-answers PATCH that keeps failing must not resend the list on its own: writing the
  // same ids again changes no state, so no new body and no new timer
  it.each([
    [
      7,
      'Contracts & Leases',
      'contracts_answer',
      'e.g., Landlord Inc.',
      /add contract/i,
      () => contractSaves,
    ],
    [8, 'Codebtors', 'codebtors_answer', 'e.g., Jane Smith', /add codebtor/i, () => codebtorSaves],
  ] as const)(
    'stops after one retry while the answers save keeps failing, on step %i (%s)',
    async (step, title, answerKey, placeholder, addButton, saves) => {
      serveFiler(step, [], [], { [answerKey]: 'yes' });
      server.use(
        http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
          sessionPatches.push((await request.json()) as Record<string, unknown>);
          return HttpResponse.json(
            { claim_answers: { [answerKey]: ['Check the answer.'] } },
            { status: 400 }
          );
        })
      );
      renderWizard();
      await expectStep(title);

      vi.useFakeTimers();
      try {
        fireEvent.click(screen.getByRole('button', { name: addButton }));
        const boxes = screen.getAllByPlaceholderText(placeholder);
        fireEvent.change(boxes[boxes.length - 1], { target: { value: 'Lakeview Storage' } });
        await waitSeconds(12);
      } finally {
        vi.useRealTimers();
      }

      // One save after the edit, and one more from the body the ids changed, then no more
      expect(saves()).toHaveLength(2);
      expect(sessionPatches).toHaveLength(2);
    }
  );

  it.each([6, 7, 8])('never sends a browser-only key, on step %i', async (step) => {
    if (step === 6) {
      const { bodies } = serveSessionSaves(onStep6);
      renderWizard();
      await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
      vi.useFakeTimers();
      try {
        fireEvent.change(field('creditor_name_0'), { target: { value: 'Northwind Card Co' } });
        await waitSeconds(3);
      } finally {
        vi.useRealTimers();
      }
      expect(bodies.length).toBeGreaterThan(0);
      expect(hasBrowserKey(bodies)).toBe(false);
      return;
    }
    serveFiler(step, [storedLease], [storedCodebtor]);
    renderWizard();
    await expectStep(step === 7 ? 'Contracts & Leases' : 'Codebtors');
    await waitFor(() => expect(screen.getByRole('button', { name: /continue/i })).toBeEnabled());
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() => expect(stepUpdates).toEqual([step + 1]));

    expect(contractSaves.length + codebtorSaves.length).toBeGreaterThan(0);
    expect(hasBrowserKey([contractSaves, codebtorSaves, sessionPatches])).toBe(false);
  });

  // The stored rows here are the objects written before 3c3, none of the new keys: a row built
  // from an old row must build the same body each time, or every visit would save
  it.each([
    [6, 'Amounts Owed'],
    [7, 'Contracts & Leases'],
    [8, 'Codebtors'],
  ])('sends nothing on a visit alone to step %i (%s)', async (step, title) => {
    serveFiler(step);
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({
          ...sessionAtStep1,
          current_step: step,
          debtor_info: { first_name: 'Jane', last_name: 'Doe' },
          debts: [
            {
              id: 7,
              session: 1,
              data_source: 'manual',
              creditor_name: 'Northwind Card Services',
              debt_type: 'credit_card',
              amount_owed: '2500.00',
              monthly_payment: '75.00',
              is_in_collections: false,
              is_secured: false,
              collateral_description: '',
              notes: '',
              is_draft: false,
              source_document_name: null,
            },
          ],
          claim_answers: { no_debts: null, contracts_answer: 'yes', codebtors_answer: 'yes' },
        })
      ),
      http.get('http://localhost:8000/api/intake/sessions/:id/contracts/', () =>
        HttpResponse.json([
          {
            id: 4,
            counterparty_name: 'Oak Street Apartments',
            contract_type: 'lease',
            description: 'Apartment lease',
          },
        ])
      ),
      http.get('http://localhost:8000/api/intake/sessions/:id/codebtors/', () =>
        HttpResponse.json([
          {
            id: 3,
            name: 'Sam Doe',
            street_address: '',
            city: 'Chicago',
            state: 'IL',
            zip_code: '',
            relationship: 'relative',
          },
        ])
      )
    );
    renderWizard();
    await expectStep(title);

    vi.useFakeTimers();
    try {
      await waitSeconds(6);
    } finally {
      vi.useRealTimers();
    }

    expect(contractSaves).toEqual([]);
    expect(codebtorSaves).toEqual([]);
    expect(sessionPatches).toEqual([]);
  });

  it('sends nothing on a visit alone to step 6 with every priority answer given', async () => {
    serveFiler(6);
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({
          ...sessionAtStep1,
          current_step: 6,
          debtor_info: { first_name: 'Jane', last_name: 'Doe' },
          debts: [
            {
              ...storedDebt,
              priority_answer: 'other',
              priority_other: 'Demo deposit',
              priority_amount: '10.00',
              nonpriority_amount: null,
              past_due_amount: '0.00',
            },
          ],
          claim_answers: { no_debts: null, contracts_answer: 'yes', codebtors_answer: 'yes' },
        })
      )
    );
    renderWizard();
    await expectStep('Amounts Owed');
    vi.useFakeTimers();
    try {
      await waitSeconds(6);
    } finally {
      vi.useRealTimers();
    }
    expect(sessionPatches).toEqual([]);
  });

  it.each([
    [
      7,
      'Contracts & Leases',
      { contracts_answer: 'yes' },
      () => {
        fireEvent.click(screen.getByRole('button', { name: /add contract/i }));
        fireEvent.change(screen.getByPlaceholderText('e.g., Apartment lease, car lease'), {
          target: { value: 'Lease' },
        });
      },
      () => contractSaves,
      'description',
      'Lease',
    ],
    [
      8,
      'Codebtors',
      { codebtors_answer: 'yes' },
      () => {
        fireEvent.click(screen.getByRole('button', { name: /add codebtor/i }));
        fireEvent.change(field('codebtor_city_0'), { target: { value: 'Chicago' } });
      },
      () => codebtorSaves,
      'city',
      'Chicago',
    ],
  ])(
    'autosaves step %i (%s) while the step still has a gap',
    async (step, title, answers, typeIntoNewRow, saves, typedKey, typedValue) => {
      serveFiler(step, [], [], answers);
      renderWizard();
      await expectStep(title);

      vi.useFakeTimers();
      try {
        typeIntoNewRow();
        await waitSeconds(3);
      } finally {
        vi.useRealTimers();
      }

      expect(saves()).toHaveLength(1);
      const rows = saves()[0] as Record<string, unknown>[];
      expect(rows).toHaveLength(1);
      expect(rows[0][step === 7 ? 'counterparty_name' : 'name']).toBe('');
      expect(rows[0][typedKey]).toBe(typedValue);
      expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();
    }
  );

  it("sends the loaded claim answers back with each step's list, and carries no other step's", async () => {
    serveFiler(7, [storedLease], [], {
      contracts_answer: 'yes',
      codebtors_answer: 'no',
      community_lived: 'yes',
    });
    renderWizard();
    await expectStep('Contracts & Leases');
    await waitFor(() => expect(screen.getByRole('button', { name: /continue/i })).toBeEnabled());
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() => expect(stepUpdates).toEqual([8]));

    // G's answer and Form 101 line 11's keys, in one PATCH (PF2-T9-5), and no other step's
    expect(sessionPatches).toEqual([
      {
        claim_answers: { contracts_answer: 'yes' },
        petition_answers: { rents_residence: 'no', eviction_judgment: null, ...NO_LANDLORD },
      },
    ]);
  });

  it('the Contracts body carries the rent and landlord keys and no other petition key', async () => {
    serveFiler(
      7,
      [storedLease],
      [],
      {},
      { name_suffix: 'Jr.', other_names_answer: 'no', hazard_answer: 'no' }
    );
    renderWizard();
    await expectStep('Contracts & Leases');
    const next = screen.getByRole('button', { name: /continue/i });
    // Line 11 unanswered holds Continue; once touched, the step's one region says why
    await waitFor(() =>
      expect(document.querySelector('[name="counterparty_name_0"]')).toHaveValue(
        String(storedLease.counterparty_name)
      )
    );
    expect(next).toBeDisabled();

    const pick = (name: string, value: string) =>
      userEvent.click(document.querySelector(`input[name="${name}"][value="${value}"]`)!);
    await pick('rents_residence', 'yes');
    const step = document.querySelector('.contracts-step') as HTMLElement;
    expect(within(step).getByRole('status')).toHaveTextContent(PETITION_GATE_EVICTION);
    await pick('eviction_judgment', 'no');
    await waitFor(() => expect(next).toBeEnabled());
    await userEvent.click(next);
    await waitFor(() => expect(stepUpdates).toEqual([8]));

    // Step 1's keys and the hazard stay out: each step's body names only its own (spec §5.6)
    expect(sessionPatches.length).toBeGreaterThanOrEqual(1);
    for (const patch of sessionPatches) {
      expect(Object.keys(patch.petition_answers as object)).toEqual([
        'rents_residence',
        'eviction_judgment',
        ...Object.keys(NO_LANDLORD),
      ]);
    }
    expect(sessionPatches.at(-1)).toEqual({
      claim_answers: { contracts_answer: 'yes' },
      petition_answers: { rents_residence: 'yes', eviction_judgment: 'no', ...NO_LANDLORD },
    });
  });

  it('saves Contracts & Leases once per edit, one PUT and one PATCH, and nothing on a visit', async () => {
    serveFiler(
      7,
      [],
      [],
      { contracts_answer: 'yes' },
      { rents_residence: 'yes', eviction_judgment: 'yes', ...STORED_LANDLORD }
    );
    renderWizard();
    await expectStep('Contracts & Leases');
    expect(document.querySelector('.eviction-notice')).not.toBeNull();

    vi.useFakeTimers();
    try {
      await waitSeconds(4);
      // PF2-7: the widened body is built the same way from loaded and edited answers
      expect(contractSaves).toEqual([]);
      expect(sessionPatches).toEqual([]);

      // A new row, whose id the save writes back into it, and the rent moved to No
      fireEvent.click(screen.getByRole('button', { name: /add contract/i }));
      fireEvent.change(document.querySelector('[name="counterparty_name_0"]')!, {
        target: { value: 'Lakeview Storage' },
      });
      fireEvent.click(document.querySelector('input[name="rents_residence"][value="no"]')!);
      await waitSeconds(3);
      // PF2-T9-5: the copy the save returns matches the body once the id is in the row, so no
      // second save follows
      await waitSeconds(5);
    } finally {
      vi.useRealTimers();
    }

    expect(contractSaves).toHaveLength(1);
    // A stored eviction Yes under a rent No stays stored and is sent as it is (spec §6.7), the
    // landlord answers too: a null would remove them on the server (4b2-R6)
    expect(sessionPatches).toEqual([
      {
        claim_answers: { contracts_answer: 'yes' },
        petition_answers: { rents_residence: 'no', eviction_judgment: 'yes', ...STORED_LANDLORD },
      },
    ]);
    expect(document.querySelector('.eviction-notice')).toBeNull();
  });

  it('showing Contracts & Leases again with nothing typed saves nothing', async () => {
    // A stored landlord reaches the body the same way it was loaded, so a visit alone sends nothing
    serveFiler(
      7,
      [],
      [],
      { contracts_answer: 'yes' },
      {
        rents_residence: 'yes',
        eviction_judgment: 'yes',
        landlord_name: 'Demo Property Holdings LLC',
        landlord_street: '100 Demo St',
        landlord_city: 'Chicago',
        landlord_state: 'IL',
        landlord_zip: '60601',
      }
    );
    renderWizard();
    await expectStep('Contracts & Leases');
    expect(document.querySelector('input[name="landlord_name"]')).toHaveValue(
      'Demo Property Holdings LLC'
    );
    vi.useFakeTimers();
    try {
      await waitSeconds(6);
    } finally {
      vi.useRealTimers();
    }
    expect(contractSaves).toEqual([]);
    expect(sessionPatches).toEqual([]);
  });

  it("sends every line 2 answer of Schedule H with step 8's list", async () => {
    const community = {
      codebtors_answer: 'yes',
      community_lived: 'yes',
      community_spouse_lived_with: 'yes',
      community_state: 'Demo State',
      community_spouse_name: 'Demo Spouse',
      community_spouse_street_address: '12 Demo Street',
      community_spouse_city: 'Demo City',
      community_spouse_state: 'IL',
      community_spouse_zip_code: '60601',
    };
    serveFiler(8, [storedLease], [storedCodebtor], community);
    renderWizard();
    await expectStep('Codebtors');
    await waitFor(() => expect(screen.getByRole('button', { name: /continue/i })).toBeEnabled());
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() => expect(stepUpdates).toEqual([9]));

    expect(sessionPatches).toEqual([
      {
        claim_answers: {
          ...community,
          community_spouse_street_2: null,
          community_spouse_outside_us: null,
        },
      },
    ]);
  });
});

describe('IntakeWizard Review household', { timeout: 15_000 }, () => {
  it("Review shows line 13's count from the session the wizard read", async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({
          ...sessionAtStep9,
          household: { county: 'Kane', members: [], family_size: 2, fee_waiver_household_size: 3 },
        })
      )
    );
    renderWizard();
    await screen.findByRole('heading', { name: /review & results/i, level: 2 });
    expect(
      screen.getByText('People in your home, counting you').nextElementSibling
    ).toHaveTextContent(/^2$/);
    expect(screen.getByText('County').nextElementSibling).toHaveTextContent('Kane');
  });
});

// ===========================================================================
// Businesses and rental property on the Income step (3e2 spec §4.2, §7.4)
// ===========================================================================

describe('IntakeWizard business and rental list', { timeout: 30_000 }, () => {
  const NO_BUSINESS = 'I have no business or rental income.';
  const ADD = '+ Add a business or property';
  const incomeEntries = (body: Record<string, unknown>) =>
    (body.income_info as { business_and_rental: Record<string, unknown>[] | null })
      .business_and_rental;
  const spouseEntries = (body: Record<string, unknown>) =>
    (body.spouse_income as { business_and_rental: Record<string, unknown>[] | null })
      .business_and_rental;
  const members = (body: Record<string, unknown>) =>
    (body.household as { members: Record<string, unknown>[] | null }).members;
  const openIncome = () => screen.findByRole('heading', { name: /income/i, level: 2 });

  beforeEach(() => {
    server.use(
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          const { current_step } = (await request.json()) as { current_step: number };
          return HttpResponse.json({
            session: { ...onIncome, current_step },
            message: 'Step updated.',
          });
        }
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
  });

  // An entry saved without its id is stored again as a new entry
  it("a new entry's id reaches the entry that sent it, wherever it now sits", async () => {
    const saves = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();
    const landSave = saves.holdNextReply();

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: ADD }));
      fireEvent.change(field('entry_kind_0'), { target: { value: 'business' } });
      fireEvent.click(screen.getByRole('button', { name: ADD }));
      fireEvent.change(field('entry_kind_1'), { target: { value: 'rental' } });
      await waitSeconds(3);
      expect(saves.bodies).toHaveLength(1);

      fireEvent.click(screen.getByRole('button', { name: 'Remove business or property 1' }));
      await act(async () => landSave());
      await waitSeconds(4);
    } finally {
      vi.useRealTimers();
    }

    expect(saves.bodies.map((body) => incomeEntries(body)?.map((row) => row.id))).toEqual([
      [undefined, undefined],
      [102],
    ]);
    const [rental] = incomeEntries(saves.bodies[1]) ?? [];
    expect(rental.kind).toBe('rental');
    expect(rental).not.toHaveProperty('_key');
  });

  it("an older save's reply writes no ids once a later save of the list has gone out", async () => {
    const saves = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();
    const landFirstSave = saves.holdNextReply();

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: ADD }));
      fireEvent.change(field('entry_kind_0'), { target: { value: 'business' } });
      await waitSeconds(3);
      fireEvent.change(field('entry_description_0'), { target: { value: 'Driving' } });
      await waitSeconds(3);
      expect(saves.bodies).toHaveLength(2);

      await act(async () => landFirstSave());
      await waitSeconds(4);
      // The next edit updates the entry the server holds
      fireEvent.change(field('entry_description_0'), { target: { value: 'Delivery driving' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(saves.bodies.map((body) => incomeEntries(body)?.map((row) => row.id))).toEqual([
      [undefined],
      [undefined],
      [102],
    ]);
  });

  // One reply carries both lists, and the stub numbers members first, then entries
  it('the household and the entries each keep their ids from one reply', async () => {
    const saves = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: '+ Add a person' }));
      fireEvent.change(field('relationship_0'), { target: { value: 'son' } });
      fireEvent.click(screen.getByRole('button', { name: ADD }));
      fireEvent.change(field('entry_kind_0'), { target: { value: 'business' } });
      await waitSeconds(3);
      expect(saves.bodies).toHaveLength(1);
      fireEvent.change(field('age_0'), { target: { value: '8' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(saves.bodies).toHaveLength(2);
    expect(members(saves.bodies[1])?.[0].id).toBe(101);
    expect(incomeEntries(saves.bodies[1])?.[0].id).toBe(102);
  });

  // Ids are paired by position, never guessed
  it("a reply that doesn't list each entry sent fails the save", async () => {
    // Lines 11 and 13 answered, so it is Continue's save that fails (4c-R4)
    serveSessionSaves({ ...onIncome, schedule_i_answers: LINES_11_13_NO });
    const unanswered = {
      description: null,
      gross: null,
      expenses: null,
      current_gross: null,
      current_expenses: null,
    };
    server.use(
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({
          ...onIncome,
          income_info: {
            business_and_rental: [
              { id: 101, kind: 'business', ...unanswered },
              { id: 102, kind: 'rental', ...unanswered },
            ],
          },
        })
      )
    );
    const { container } = renderWizard();
    await openIncome();

    fireEvent.click(screen.getByRole('button', { name: ADD }));
    fireEvent.change(field('entry_kind_0'), { target: { value: 'business' } });
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }));

    expect(await screen.findByText(/couldn't save just now/i)).toBeInTheDocument();
    expect(container.querySelector('.step-title')).toHaveTextContent('Income');
  });

  it('"No business" pressed sends [], and a list never answered sends null', async () => {
    const { bodies } = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('monthly_gross_wages'), { target: { value: '3200' } });
      await waitSeconds(3);
      expect(incomeEntries(bodies.at(-1) as Record<string, unknown>)).toBeNull();

      fireEvent.click(screen.getByRole('button', { name: NO_BUSINESS }));
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(incomeEntries(bodies.at(-1) as Record<string, unknown>)).toEqual([]);
  });

  // Review Focus 1: the API sends amounts as strings, and 4200.00 + 830.00 must not join as text
  it("a loaded entry's amounts add as numbers and showing the step again sends nothing", async () => {
    const saves = serveSessionSaves({
      ...onIncome,
      status: 'completed',
      current_step: 4,
      expense_info: completedSession.expense_info,
      income_info: {
        ...TEN_ZERO,
        marital_status: 'not_married',
        business_and_rental: [
          {
            id: 1,
            kind: 'business',
            description: 'Rideshare and delivery driving',
            gross: '4200.00',
            expenses: '830.00',
            current_gross: null,
            current_expenses: null,
          },
        ],
        total_monthly_income: 3370,
      },
      household: { county: 'Cook', members: [] },
    });
    const { container } = renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
      await waitSeconds(3);
      expect(container.querySelector('.step-title')).toHaveTextContent('Take-home pay');
      fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(container.querySelector('.step-title')).toHaveTextContent('Income');
    expect(screen.getByText('Net a month').closest('section')).toHaveTextContent('$3,370.00');
    expect(
      screen.getByText('Your income', { selector: 'dt' }).nextElementSibling
    ).toHaveTextContent('$3,370.00');
    expect(document.body.textContent).not.toMatch(/\$0?4200\.00830/);
    expect(saves.bodies).toEqual([]);
    expect(saves.stored().status).toBe('completed');
  });

  it("a spouse's new entry keeps the id the reply gave it", async () => {
    const saves = serveSessionSaves({
      ...priyaAtIncome,
      spouse_income: { ...priyaAtIncome.spouse_income, business_and_rental: [] },
    });
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      fireEvent.click(
        screen.getByRole('button', { name: "+ Add your spouse's business or property" })
      );
      fireEvent.change(field('spouse_entry_kind_0'), { target: { value: 'rental' } });
      await waitSeconds(3);
      expect(saves.bodies).toHaveLength(1);
      fireEvent.change(field('spouse_entry_gross_0'), { target: { value: '900' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(saves.bodies).toHaveLength(2);
    const last = saves.bodies[1];
    expect(spouseEntries(last)).toHaveLength(1);
    expect(spouseEntries(last)?.[0].id).toBe(101);
    expect(spouseEntries(last)?.[0]).not.toHaveProperty('_key');
    // The filer's own list is unchanged: never answered
    expect(incomeEntries(last)).toBeNull();
  });
});

// ===========================================================================
// "Now different" and government assistance on the Income step (3e2 spec §4.4, §4.6, §7.4)
// ===========================================================================

describe('IntakeWizard now different and assistance', { timeout: 30_000 }, () => {
  const openIncome = () => screen.findByRole('heading', { name: /income/i, level: 2 });
  const incomeInfo = (body: Record<string, unknown>) => body.income_info as Record<string, unknown>;

  beforeEach(() => {
    server.use(
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          const { current_step } = (await request.json()) as { current_step: number };
          return HttpResponse.json({
            session: { ...onIncome, current_step },
            message: 'Step updated.',
          });
        }
      )
    );
  });

  it('answering No after Yes sends no current figure and keeps them in state', async () => {
    const { bodies } = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      pick('income_now_different', 'yes');
      fireEvent.change(field('current_monthly_gross_wages'), { target: { value: '2500' } });
      await waitSeconds(3);
      expect(incomeInfo(bodies.at(-1) as Record<string, unknown>).current_monthly_gross_wages).toBe(
        2500
      );

      pick('income_now_different', 'no');
      await waitSeconds(3);
      const sent = incomeInfo(bodies.at(-1) as Record<string, unknown>);
      expect(sent.income_now_different).toBe('no');
      for (const name of CURRENT_INCOME_FIELDS) expect(sent).not.toHaveProperty(name);

      pick('income_now_different', 'yes');
    } finally {
      vi.useRealTimers();
    }
    expect(field('current_monthly_gross_wages')).toHaveValue(2500);
  });

  it('the five assistance fields are always sent', async () => {
    const { bodies } = serveSessionSaves(onIncome);
    renderWizard();
    await openIncome();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('monthly_gross_wages'), { target: { value: '100' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(incomeInfo(bodies.at(-1) as Record<string, unknown>)).toMatchObject({
      assistance_answer: null,
      cash_assistance_kind: '',
      cash_assistance_amount: null,
      noncash_assistance_kind: '',
      noncash_assistance_value: null,
      income_now_different: null,
    });
  });

  it('showing the Income step again sends nothing, with every new answer loaded', async () => {
    const loaded = {
      ...priyaAtIncome,
      status: 'completed',
      current_step: 4,
      expense_info: completedSession.expense_info,
      income_info: {
        ...priyaAtIncome.income_info,
        business_and_rental: [],
        income_now_different: 'yes',
        ...Object.fromEntries(CURRENT_INCOME_FIELDS.map((name) => [name, null])),
        current_monthly_gross_wages: '11000.00',
        assistance_answer: 'yes',
        cash_assistance_kind: '',
        cash_assistance_amount: null,
        noncash_assistance_kind: 'SNAP (food stamps)',
        noncash_assistance_value: '350.00',
      },
      spouse_income: {
        ...priyaAtIncome.spouse_income,
        business_and_rental: [],
        income_now_different: 'no',
        ...Object.fromEntries(CURRENT_INCOME_FIELDS.map((name) => [name, null])),
        assistance_answer: 'no',
        cash_assistance_kind: '',
        cash_assistance_amount: null,
        noncash_assistance_kind: '',
        noncash_assistance_value: null,
      },
    };
    const saves = serveSessionSaves(loaded);
    const { container } = renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
      await waitSeconds(3);
      expect(container.querySelector('.step-title')).toHaveTextContent('Take-home pay');
      fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(container.querySelector('.step-title')).toHaveTextContent('Income');
    expect(field('current_monthly_gross_wages')).toHaveValue(11000);
    expect(field('noncash_assistance_value')).toHaveValue(350);
    expect(saves.bodies).toEqual([]);
  });
});

// ===========================================================================
// The Take-home pay step, step 3 (3e2 spec §7.2, §7.4)
// ===========================================================================

describe('IntakeWizard take-home pay', { timeout: 30_000 }, () => {
  const openTakeHomePay = () => screen.findByRole('heading', { name: /take-home pay/i, level: 2 });
  const NULL_DEDUCTIONS = Object.fromEntries(DEDUCTION_FIELDS.map((name) => [name, null]));
  let stepUpdates: number[];

  beforeEach(() => {
    stepUpdates = [];
    server.use(
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          const { current_step } = (await request.json()) as { current_step: number };
          stepUpdates.push(current_step);
          return HttpResponse.json({
            session: { ...onIncome, current_step },
            message: 'Step updated.',
          });
        }
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
  });

  const filerOnIncome = {
    ...onIncome,
    income_info: { ...TEN_ZERO, marital_status: 'not_married' },
    household: { county: 'Cook', members: [] },
  };

  it('Continue on Income opens Take-home pay, and Continue there sends 4', async () => {
    serveSessionSaves({ ...filerOnIncome, schedule_i_answers: LINES_11_13_NO });
    const { container } = renderWizard();
    await screen.findByRole('heading', { name: /income/i, level: 2 });

    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await openTakeHomePay();
    expect(container.querySelector('.step-title')).toHaveTextContent('Take-home pay');
    expect(stepUpdates).toEqual([3]);

    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });
    expect(stepUpdates).toEqual([3, 4]);
  });

  it('the step 3 body carries only the deductions, a blank one as null', async () => {
    const saves = serveSessionSaves({
      ...filerOnIncome,
      current_step: 3,
      income_info: { ...TEN_ZERO, monthly_gross_wages: '3000.00', marital_status: 'not_married' },
    });
    renderWizard();
    await openTakeHomePay();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('payroll_tax'), { target: { value: '400' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(saves.bodies.at(-1)).toEqual({
      income_info: { ...NULL_DEDUCTIONS, payroll_tax: 400, payroll_other_specify: '' },
    });
  });

  it('showing Take-home pay again sends nothing', async () => {
    const saves = serveSessionSaves({
      ...filerOnIncome,
      status: 'completed',
      current_step: 4,
      expense_info: completedSession.expense_info,
      income_info: { ...TEN_ZERO, marital_status: 'not_married', payroll_tax: '400.00' },
    });
    const { container } = renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(container.querySelector('.step-title')).toHaveTextContent('Take-home pay');
    expect(saves.bodies).toEqual([]);
    expect(saves.stored().status).toBe('completed');
  });

  it('line 4 follows the figures Schedule I uses, averages while unanswered', async () => {
    serveSessionSaves({
      ...filerOnIncome,
      current_step: 3,
      income_info: {
        ...TEN_ZERO,
        monthly_gross_wages: '3000.00',
        marital_status: 'not_married',
        income_now_different: null,
      },
      schedule_i_answers: LINES_11_13_NO,
    });
    renderWizard();
    await openTakeHomePay();
    const line4 = () =>
      screen.getByText('4. Calculate gross income', { selector: 'dt' }).nextElementSibling;
    expect(line4()).toHaveTextContent('$3,000.00');

    fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
    await screen.findByRole('heading', { name: /income/i, level: 2 });
    pick('income_now_different', 'yes');
    fireEvent.change(field('current_monthly_gross_wages'), { target: { value: '2500' } });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await openTakeHomePay();

    expect(line4()).toHaveTextContent('$2,500.00');
  });

  it("the Income step's save never carries a deduction", async () => {
    const saves = serveSessionSaves(filerOnIncome);
    renderWizard();
    await screen.findByRole('heading', { name: /income/i, level: 2 });

    vi.useFakeTimers();
    try {
      fireEvent.change(field('monthly_gross_wages'), { target: { value: '3000' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    const sent = (saves.bodies.at(-1) as { income_info: Record<string, unknown> }).income_info;
    expect(sent.monthly_gross_wages).toBe(3000);
    for (const name of [...DEDUCTION_FIELDS, 'payroll_other_specify']) {
      expect(sent).not.toHaveProperty(name);
    }
  });

  it("the spouse's deductions join the step 3 body only for a spouse at home", async () => {
    const saves = serveSessionSaves({ ...priyaAtIncome, current_step: 3 });
    const { unmount } = renderWizard();
    await openTakeHomePay();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('spouse_payroll_tax'), { target: { value: '250' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect((saves.bodies.at(-1) as Record<string, unknown>).spouse_income).toEqual({
      ...NULL_DEDUCTIONS,
      payroll_tax: 250,
      payroll_other_specify: '',
    });
    unmount();

    const apart = serveSessionSaves({
      ...priyaAtIncome,
      current_step: 3,
      income_info: { ...priyaAtIncome.income_info, marital_status: 'married_separately' },
    });
    renderWizard();
    await openTakeHomePay();

    vi.useFakeTimers();
    try {
      fireEvent.change(field('payroll_tax'), { target: { value: '400' } });
      await waitSeconds(3);
    } finally {
      vi.useRealTimers();
    }

    expect(apart.bodies.at(-1)).not.toHaveProperty('spouse_income');
    expect(apart.bodies.at(-1)).toHaveProperty('income_info');
  });
});

describe('IntakeWizard window notice', { timeout: 30_000 }, () => {
  const MOVED = /Your income figures are your monthly average for April 1, 2026/;
  const income_window = { start: '2026-05-01', end: '2026-10-31' };
  const onIncome = {
    ...sessionAtStep1,
    current_step: 2,
    income_window,
    income_info: {
      marital_status: null,
      monthly_gross_wages: '3100.50',
      answered_window: { start: '2026-04-01', end: '2026-09-30' },
    },
    schedule_i_answers: LINES_11_13_NO,
  };

  it('Continue on the Income step clears its window notice', async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(onIncome)),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(onIncome)
      ),
      // Continue stamps the window, so the reply names the one in force
      http.post('http://localhost:8000/api/intake/sessions/:id/update_step/', () =>
        HttpResponse.json({
          session: {
            ...onIncome,
            current_step: 3,
            income_info: { ...onIncome.income_info, answered_window: income_window },
          },
          message: 'Updated to step 3',
        })
      ),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );

    renderWizard();
    await screen.findByRole('heading', { name: /income/i, level: 2 });
    expect(screen.getByText(MOVED)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByRole('heading', { name: /take-home pay/i, level: 2 });
    await userEvent.click(screen.getByRole('button', { name: 'Go Back' }));
    await screen.findByRole('heading', { name: /income/i, level: 2 });

    expect(screen.queryByText(/monthly average for/)).not.toBeInTheDocument();
  });
});

// ===========================================================================
// A stored payment the links don't cover (3c4 R9, B39)
// ===========================================================================

describe('IntakeWizard legacy payment on Amounts Owed', { timeout: 15_000 }, () => {
  const car = {
    id: 3,
    session: 1,
    ab_line: '3',
    asset_type: null,
    data_source: 'manual',
    description: '',
    current_value: '8000.00',
    entire_value: '8000.00',
    details: { make: 'Demo', model: 'Sedan', who: 'only_you' },
  };
  const carLoan = {
    ...storedDebt,
    id: 12,
    creditor_name: 'Demo Auto Finance',
    debt_type: 'car_loan',
    amount_owed: '8000.00',
    monthly_payment: '350.00',
    is_secured: true,
    secured_by: 3,
    home_payment_line: null,
  };
  const legacySession = {
    ...sessionAtStep1,
    current_step: 6,
    assets: [car],
    debts: [{ ...storedDebt }],
    legacy_payments: { vehicle_payment: '350.00', other_property_mortgages: null },
  };
  const sentence = fill(CLAIM_GAP_LEGACY_VEHICLE, { typed: '350.00', linked: '0.00' });

  function serve(session: Record<string, unknown>, patchStatus = 200) {
    const patchBodies: Record<string, unknown>[] = [];
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(session)),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        patchBodies.push((await request.json()) as Record<string, unknown>);
        return patchStatus === 200
          ? HttpResponse.json(session)
          : HttpResponse.json({ detail: 'no' }, { status: patchStatus });
      }),
      http.post(
        'http://localhost:8000/api/audit/logs/',
        () => new HttpResponse(null, { status: 201 })
      )
    );
    return patchBodies;
  }

  it('Remove sends the figure as 0 and the sentence goes', async () => {
    const patchBodies = serve(legacySession);
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
    expect(screen.getByText(sentence)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: LEGACY_REMOVE }));

    await waitFor(() => expect(screen.queryByText(sentence)).toBeNull());
    expect(patchBodies).toEqual([{ expense_info: { vehicle_payment: 0 } }]);
  });

  it('a failed Remove keeps the sentence and says so', async () => {
    serve(legacySession, 400);
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    await userEvent.click(screen.getByRole('button', { name: LEGACY_REMOVE }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(NOT_SAVED_TRY_AGAIN);
    expect(screen.getByText(sentence)).toBeInTheDocument();
  });

  it('a stored figure the links cover shows no sentence', async () => {
    serve({ ...legacySession, debts: [carLoan] });
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    expect(screen.queryByRole('button', { name: LEGACY_REMOVE })).toBeNull();
    expect(screen.queryByText(/a month for a car/)).toBeNull();
  });

  it('a stored car figure a vehicle lease covers shows no sentence', async () => {
    const carLease = {
      ...storedLease,
      id: 6,
      counterparty_name: 'Demo Auto Lease',
      lease_kind: 'vehicle',
      monthly_payment: '389.00',
      vehicle_asset: 3,
    };
    serve({
      ...legacySession,
      debts: [],
      legacy_payments: { vehicle_payment: '389.00', other_property_mortgages: null },
    });
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/contracts/', () =>
        HttpResponse.json([carLease])
      )
    );
    renderWizard();
    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });

    expect(screen.queryByRole('button', { name: LEGACY_REMOVE })).toBeNull();
    expect(screen.queryByText(/a month for a car/)).toBeNull();
  });
});
