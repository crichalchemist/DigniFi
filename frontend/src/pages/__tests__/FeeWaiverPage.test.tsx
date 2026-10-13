import { useEffect, useRef } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider, useIntake } from '../../context/IntakeContext';
import { FeeWaiverPage } from '../FeeWaiverPage';

function renderFeeWaiver() {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter initialEntries={['/fee-waiver']}>
      <IntakeProvider>
        <Routes>
          <Route path="/fee-waiver" element={<FeeWaiverPage />} />
          <Route path="/sofa" element={<div>Statement of Financial Affairs</div>} />
          <Route path="/forms" element={<div>FormDashboard</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

// `meansTestResult` is only ever populated by calling calculateMeansTest()
// through the provider — it is never hydrated from the session GET. This tiny
// harness reproduces what the eligibility widget does upstream: once the
// session has loaded, fire the means-test calc exactly once so FeeWaiverPage
// can read the verdict from context.
function MeansTestTrigger() {
  const { session, calculateMeansTest } = useIntake();
  const fired = useRef(false);
  useEffect(() => {
    if (!session || fired.current) return;
    fired.current = true;
    calculateMeansTest().catch(() => {});
  }, [session, calculateMeansTest]);
  return null;
}

const ineligibleResult = {
  passes_means_test: true,
  qualifies_for_fee_waiver: false,
  cmi: 3500,
  median_income_threshold: 71304,
  family_size: 1,
  message: 'Based on the information you provided, you may not qualify for a fee waiver.',
  details: { cmi: 3500, annualized_cmi: 42000, median_income_threshold: 71304, family_size: 1 },
  means_test_id: 1,
};

describe('FeeWaiverPage', () => {
  it('renders the fee waiver heading', async () => {
    renderFeeWaiver();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /filing fee waiver/i })).toBeInTheDocument();
    });
  });

  it('continues to the financial history questions (SOFA), not the forms, once the application is sent', async () => {
    renderFeeWaiver();
    await waitFor(() => screen.getByRole('heading', { name: /filing fee waiver/i }));

    await userEvent.type(screen.getByLabelText(/household size/i), '1');
    await userEvent.type(screen.getByLabelText(/monthly income/i), '1200');
    await userEvent.type(screen.getByLabelText(/monthly expenses/i), '1000');

    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    // Form 107 is in every packet, so a waiver filer answers its questions before the forms (DIG-149)
    await waitFor(() => {
      expect(screen.getByText('Statement of Financial Affairs')).toBeInTheDocument();
    });
    expect(screen.queryByText('FormDashboard')).not.toBeInTheDocument();
  });

  it('shows error when submission fails', async () => {
    server.use(
      http.post('http://localhost:8000/api/intake/fee-waiver/', () =>
        HttpResponse.json({ detail: 'Server error' }, { status: 400 })
      )
    );

    renderFeeWaiver();
    await waitFor(() => screen.getByRole('heading', { name: /filing fee waiver/i }));

    await userEvent.type(screen.getByLabelText(/household size/i), '1');
    await userEvent.type(screen.getByLabelText(/monthly income/i), '1200');
    await userEvent.type(screen.getByLabelText(/monthly expenses/i), '1000');
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('pre-fills the form with the figures saved during intake', async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({
          id: 1,
          user: 1,
          district: 1,
          current_step: 6,
          status: 'in_progress',
          created_at: '2026-01-20T10:00:00Z',
          updated_at: '2026-01-20T10:00:00Z',
          completed_at: null,
          debtor_info: { household_size: 4 },
          income_info: { total_monthly_income: 2500 },
          expense_info: { total_monthly_expenses: 1800 },
          assets: [],
          debts: [],
        })
      )
    );

    renderFeeWaiver();
    await waitFor(() => screen.getByRole('heading', { name: /filing fee waiver/i }));

    // The filer only confirms numbers they already gave — they shouldn't retype.
    await waitFor(() => {
      expect(screen.getByLabelText(/household size/i)).toHaveValue(4);
    });
    expect(screen.getByLabelText(/monthly income/i)).toHaveValue(2500);
    expect(screen.getByLabelText(/monthly expenses/i)).toHaveValue(1800);
  });

  it('shows an off-ramp instead of the form when the filer is fee-waiver ineligible, and it leads on to SOFA', async () => {
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
        HttpResponse.json({ means_test_result: ineligibleResult, session_id: 1 })
      )
    );

    localStorage.setItem('current_session_id', '1');
    render(
      <MemoryRouter initialEntries={['/fee-waiver']}>
        <IntakeProvider>
          <MeansTestTrigger />
          <Routes>
            <Route path="/fee-waiver" element={<FeeWaiverPage />} />
            <Route path="/sofa" element={<div>Statement of Financial Affairs</div>} />
            <Route path="/forms" element={<div>FormDashboard</div>} />
          </Routes>
        </IntakeProvider>
      </MemoryRouter>
    );

    // Once the means test returns "no", the gentle off-ramp appears...
    await waitFor(() => {
      expect(screen.getByText(/don't appear to qualify/i)).toBeInTheDocument();
    });
    const continueButton = screen.getByRole('button', { name: /^continue$/i });

    // ...and the application form itself is hidden — no fields to fill out.
    expect(screen.queryByLabelText(/household size/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /submit waiver/i })).not.toBeInTheDocument();

    // The off-ramp leads where every filer goes next: the financial history questions
    await userEvent.click(continueButton);
    expect(await screen.findByText('Statement of Financial Affairs')).toBeInTheDocument();
    expect(screen.queryByText('FormDashboard')).not.toBeInTheDocument();
  });
});
