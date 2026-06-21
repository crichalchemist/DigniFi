import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
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
