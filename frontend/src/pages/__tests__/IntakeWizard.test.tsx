import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider, useIntake } from '../../context/IntakeContext';
import IntakeWizard from '../IntakeWizard';

// DebtorInfoStep reads account email via useAuth; wizard test renders without
// AuthProvider, so we stub just the user object the step needs.
vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'jane@example.com' } }),
}));

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const sessionAtStep8 = {
  id: 1,
  user: 1,
  district: 1,
  current_step: 8,
  status: 'in_progress' as const,
  created_at: '2026-01-20T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
  completed_at: null,
  debtor_info: { first_name: 'Jane', last_name: 'Doe' },
  income_info: { monthly_income: [1200, 1200, 1200, 1200, 1200, 1200] },
  expense_info: { rent_or_mortgage: 1000 },
  assets: [],
  debts: [],
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
  debtor_info: null,
  income_info: null,
  expense_info: null,
  assets: [],
  debts: [],
};

function renderWizard() {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter initialEntries={['/intake']}>
      <IntakeProvider>
        <Routes>
          <Route path="/intake" element={<IntakeWizard />} />
          <Route path="/fee-waiver" element={<div>FeeWaiverPage</div>} />
          <Route path="/forms" element={<div>FormDashboard</div>} />
          <Route path="/sofa" element={<div>Statement of Financial Affairs</div>} />
          <Route path="/documents" element={<div>DocumentUploadPage</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

// ---------------------------------------------------------------------------
// Helpers: fill every required field in DebtorInfoStep
// ---------------------------------------------------------------------------

/**
 * Fill all required DebtorInfoStep fields so that onValidationChange(true) fires.
 * Must be called after the wizard has rendered and the step is visible.
 */
async function fillDebtorInfoFields() {
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
  fireEvent.change(screen.getByRole('spinbutton', { name: /household size/i }), {
    target: { value: '2' },
  });
  fireEvent.change(screen.getByRole('combobox', { name: /filing type/i }), {
    target: { value: 'individual' },
  });
}

// ===========================================================================
// Existing tests — handleComplete routing
// ===========================================================================

describe('IntakeWizard handleComplete routing', { timeout: 30_000 }, () => {
  beforeEach(() => {
    // POST (createSession) return step 8 (Review & Results — the last step)
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep8)
      ),
      http.post('http://localhost:8000/api/intake/sessions/', () =>
        HttpResponse.json({ session: sessionAtStep8, message: 'Session created.' }, { status: 201 })
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep8)
      )
    );
  });

  it('navigates to /fee-waiver when qualifies_for_fee_waiver is true', async () => {
    renderWizard();
    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });

    // Register AFTER the session GET resolves (wizard is at step 8). Registering
    // before renderWizard() races with the GET under system load in the full suite.
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
        HttpResponse.json({
          means_test_result: {
            passes_means_test: true,
            qualifies_for_fee_waiver: true,
            cmi: 1000,
            median_income_threshold: 5000,
          },
          session_id: 1,
        })
      )
    );

    await userEvent.click(completeBtn);

    await waitFor(() => {
      expect(screen.getByText('FeeWaiverPage')).toBeInTheDocument();
    });
  });

  it('navigates to /sofa when qualifies_for_fee_waiver is false', async () => {
    renderWizard();
    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
    await userEvent.click(completeBtn);

    await waitFor(() => {
      expect(screen.getByText('Statement of Financial Affairs')).toBeInTheDocument();
    });
  });

  // DIG-150: the dashboard can't prepare forms from an unfinished intake, and it never showed
  // why the filer had landed there. The reason belongs on Review, where they can act on it.
  it('keeps the filer on Review with the reason when Complete fails', async () => {
    renderWizard();
    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
        HttpResponse.json(
          {
            errors: ['Expense information is required'],
            message: 'Please complete all required sections before finalizing',
          },
          { status: 400 }
        )
      )
    );

    await userEvent.click(completeBtn);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Please complete all required sections before finalizing'
    );
    expect(
      screen.getByRole('heading', { name: /review & results/i, level: 2 })
    ).toBeInTheDocument();
    expect(screen.queryByText('FormDashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
  });

  it('keeps the filer on Review with the reason when only the means test fails', async () => {
    renderWizard();
    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
        HttpResponse.json(
          {
            error: 'No median income data for this district',
            message:
              'Unable to calculate means test. Please ensure all income information is provided.',
          },
          { status: 400 }
        )
      )
    );

    await userEvent.click(completeBtn);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to calculate means test. Please ensure all income information is provided.'
    );
    expect(
      screen.getByRole('heading', { name: /review & results/i, level: 2 })
    ).toBeInTheDocument();
    expect(screen.queryByText('FormDashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('FeeWaiverPage')).not.toBeInTheDocument();
    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
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
  ...sessionAtStep8,
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
    household_size: 2,
    filing_type: 'individual',
  },
  income_info: {
    marital_status: 'single',
    number_of_dependents: 1,
    monthly_income: [3100, 3300, 3200, 3200, 3150, 3250],
    total_monthly_income: 3200,
  },
  expense_info: {
    data_source: 'manual',
    rent_or_mortgage: '1100.00',
    utilities: '180.10',
    home_maintenance: '0.00',
    vehicle_payment: '0.00',
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
      priority_classification: 'unsecured',
      amount_owed: '2500.00',
      monthly_payment: '75.00',
      is_in_collections: false,
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
      expect.objectContaining({ debtor_info: expect.any(Object) })
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

/** Session sitting on step 5 (Amounts Owed) with no debts yet. */
const sessionAtStep5 = {
  ...sessionAtStep1,
  current_step: 5,
  debtor_info: { first_name: 'Jane', last_name: 'Doe' },
};

/** A draft debt the document processor created from an uploaded bill. */
const debtFromUploadedBill = {
  id: 7,
  session: 1,
  data_source: 'uploaded_document',
  creditor_name: 'Lakeshore Medical Group',
  debt_type: 'medical',
  priority_classification: 'unsecured',
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
    let serverSession: Record<string, unknown> = sessionAtStep5;
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
    serverSession = { ...sessionAtStep5, debts: [debtFromUploadedBill] };
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
          : HttpResponse.json({ ...sessionAtStep1, current_step: 3 })
      ),
      http.post('http://localhost:8000/api/intake/sessions/', () => {
        sessionsCreated += 1;
        return HttpResponse.json(
          { session: sessionAtStep1, message: 'Session created.' },
          { status: 201 }
        );
      }),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({ ...sessionAtStep1, current_step: 3 })
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
});

// ===========================================================================
// Amounts loaded from the server (DIG-2)
// ===========================================================================

/** A returning filer on Amounts Owed. DRF sends decimal amounts as strings. */
const sessionAtStep5WithDebts = {
  ...sessionAtStep1,
  current_step: 5,
  debts: [
    {
      id: 7,
      session: 1,
      data_source: 'uploaded_document',
      creditor_name: 'Chase',
      debt_type: 'credit_card',
      priority_classification: 'unsecured',
      amount_owed: '2500.00',
      monthly_payment: '75.00',
      is_in_collections: false,
      notes: '',
      is_draft: false,
      source_document_name: null,
    },
    {
      id: 8,
      session: 1,
      data_source: 'manual',
      creditor_name: 'Mercy Hospital',
      debt_type: 'medical',
      priority_classification: 'unsecured',
      amount_owed: '100.50',
      monthly_payment: null,
      is_in_collections: false,
      notes: '',
      is_draft: false,
      source_document_name: null,
    },
  ],
};

/** A returning filer on Assets. The API never sends an asset's account number. */
const sessionAtStep4WithAssets = {
  ...sessionAtStep1,
  current_step: 4,
  assets: [
    {
      id: 3,
      session: 1,
      asset_type: 'vehicle',
      data_source: 'manual',
      description: '2015 Honda Civic',
      current_value: '8000.00',
      amount_owed: '3000.00',
      equity: 5000,
      financial_institution: '',
    },
  ],
};

describe('IntakeWizard amounts a returning filer already entered', { timeout: 15_000 }, () => {
  let patchBodies: unknown[];

  beforeEach(() => {
    patchBodies = [];
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep5WithDebts)
      ),
      // Continue saves the step, even when the filer changed nothing.
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        patchBodies.push(await request.json());
        return HttpResponse.json(sessionAtStep5WithDebts);
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
        HttpResponse.json(sessionAtStep4WithAssets)
      )
    );
    renderWizard();
    await screen.findByRole('heading', { name: /assets/i, level: 2 });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));

    await waitFor(() => expect(patchBodies.length).toBeGreaterThan(0));
    const { assets } = patchBodies[0] as { assets: Record<string, unknown>[] };
    expect(assets.map((asset) => asset.id)).toEqual([3]);
    expect(assets[0].current_value).toBe(8000);
    expect(assets[0].amount_owed).toBe(3000);
  });
});

// ===========================================================================
// Income save (DIG-41)
// ===========================================================================

describe('IntakeWizard income save', { timeout: 15_000 }, () => {
  it("saves a returning filer's months exactly as stored, and nothing else, when they continue without changes", async () => {
    // What the API returns for a filer who saved income earlier through the wizard: the
    // months, their average, and the blank household fields a wizard-created row holds.
    const savedSession = {
      ...sessionAtStep1,
      current_step: 2,
      income_info: {
        marital_status: '',
        number_of_dependents: 0,
        monthly_income: [3100, 3300, 3200, 3200, 3150, 3250],
        total_monthly_income: 3200,
        created_at: '2026-10-01T10:00:00Z',
      },
    };
    const patchBodies: unknown[] = [];
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

    renderWizard();
    await screen.findByRole('heading', { name: /income/i, level: 2 });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    expect(patchBodies.length).toBeGreaterThan(0);
    for (const body of patchBodies) {
      expect(body).toEqual({
        income_info: { monthly_income: [3100, 3300, 3200, 3200, 3150, 3250] },
      });
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
      current_step: 3,
      expense_info: {
        data_source: 'manual',
        rent_or_mortgage: '1100.00',
        utilities: '180.00',
        home_maintenance: '0.00',
        vehicle_payment: '0.00',
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
