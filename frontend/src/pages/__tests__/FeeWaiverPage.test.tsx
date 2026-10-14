import { useEffect, useRef } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider, useIntake } from '../../context/IntakeContext';
import { FeeWaiverPage } from '../FeeWaiverPage';

const API = 'http://localhost:8000/api';

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

/** A session whose intake gave a household of 4 and income and expense totals */
function sessionWithIntakeFigures() {
  return http.get(`${API}/intake/sessions/:id/`, () =>
    HttpResponse.json({
      id: 1,
      user: 1,
      district: 1,
      current_step: 8,
      status: 'completed',
      created_at: '2026-01-20T10:00:00Z',
      updated_at: '2026-01-20T10:00:00Z',
      completed_at: null,
      debtor_info: { household_size: 4 },
      income_info: { total_monthly_income: '2500.00' },
      expense_info: { total_monthly_expenses: 1800 },
      assets: [],
      debts: [],
    })
  );
}

/** The application this session already sent, as the server returns it */
function savedApplication(answers: Record<string, unknown>) {
  return {
    id: 7,
    session: 1,
    household_size: 2,
    monthly_take_home_pay: '1750.00',
    receives_noncash_assistance: true,
    benefit_types: ['SNAP (food stamps)'],
    cannot_pay_full: true,
    cannot_pay_installments: true,
    status: 'pending',
    created_at: '2026-01-20T10:00:00Z',
    updated_at: '2026-01-20T10:00:00Z',
    ...answers,
  };
}

/** Records each application the page sends */
function captureSent() {
  const sent: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API}/intake/fee-waiver/`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      sent.push(body);
      return HttpResponse.json({ id: 1, ...body, status: 'pending' }, { status: 201 });
    })
  );
  return sent;
}

const nonCashQuestion = () => screen.findByRole('group', { name: /non-cash help/i });

describe('FeeWaiverPage', () => {
  it('renders the fee waiver heading', async () => {
    renderFeeWaiver();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /filing fee waiver/i })).toBeInTheDocument();
    });
  });

  it('continues to the financial history questions (SOFA), not the forms, once the application is sent', async () => {
    renderFeeWaiver();

    await userEvent.type(await screen.findByLabelText(/household size/i), '1');
    await userEvent.type(screen.getByLabelText(/take-home pay/i), '1200');
    await userEvent.click(screen.getByRole('radio', { name: 'No' }));

    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    // Form 107 is in every packet, so a waiver filer answers its questions before the forms (DIG-149)
    await waitFor(() => {
      expect(screen.getByText('Statement of Financial Affairs')).toBeInTheDocument();
    });
    expect(screen.queryByText('FormDashboard')).not.toBeInTheDocument();
  });

  it('shows error when submission fails', async () => {
    server.use(
      http.post(`${API}/intake/fee-waiver/`, () =>
        HttpResponse.json({ detail: 'Server error' }, { status: 400 })
      )
    );

    renderFeeWaiver();

    await userEvent.type(await screen.findByLabelText(/household size/i), '1');
    await userEvent.type(screen.getByLabelText(/take-home pay/i), '1200');
    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('fills in the household size from the intake, but never take-home pay, and no longer asks for expenses', async () => {
    server.use(sessionWithIntakeFigures());

    renderFeeWaiver();

    // The filer only confirms the household they already gave
    await waitFor(() => {
      expect(screen.getByLabelText(/household size/i)).toHaveValue(4);
    });
    // Form 103B line 2 asks for take-home pay, which the intake never asked: the box starts empty
    expect(
      screen.getByLabelText(
        'Your average monthly take-home pay (after taxes and payroll deductions)'
      )
    ).toHaveValue(null);
    expect(screen.queryByLabelText(/monthly expenses/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/means-tested public benefits/i)).not.toBeInTheDocument();
  });

  it('opens with the answers this session already sent, which win over the intake figures', async () => {
    const reads: string[] = [];
    server.use(
      sessionWithIntakeFigures(),
      http.get(`${API}/intake/fee-waiver/`, ({ request }) => {
        reads.push(new URL(request.url).searchParams.get('session') ?? '');
        return HttpResponse.json({ count: 1, results: [savedApplication({})] });
      })
    );

    renderFeeWaiver();

    // A resubmit keeps every answer, the "cannot pay" boxes included (DIG-157)
    await waitFor(() => {
      expect(screen.getByLabelText(/household size/i)).toHaveValue(2);
    });
    expect(screen.getByLabelText(/take-home pay/i)).toHaveValue(1750);
    expect(screen.getByRole('radio', { name: 'Yes' })).toBeChecked();
    expect(screen.getByLabelText('What kind?')).toHaveValue('SNAP (food stamps)');
    expect(screen.getByLabelText(/cannot pay the full filing fee/i)).toBeChecked();
    expect(screen.getByLabelText(/cannot pay the filing fee in installments/i)).toBeChecked();
    // One filer can have several sessions: the page reads this one's application
    expect(reads).toEqual(['1']);
  });

  it('shows a saved No as No', async () => {
    server.use(
      http.get(`${API}/intake/fee-waiver/`, () =>
        HttpResponse.json({
          count: 1,
          results: [savedApplication({ receives_noncash_assistance: false, benefit_types: [] })],
        })
      )
    );

    renderFeeWaiver();

    await nonCashQuestion();
    await waitFor(() => {
      expect(screen.getByRole('radio', { name: 'No' })).toBeChecked();
    });
    expect(screen.getByRole('radio', { name: 'Yes' })).not.toBeChecked();
    expect(screen.queryByLabelText('What kind?')).not.toBeInTheDocument();
  });

  it('shows neither answer for an application saved before the question was asked', async () => {
    // A stored answer is sworn on Form 103B, so an empty one stays empty until the filer picks
    server.use(
      http.get(`${API}/intake/fee-waiver/`, () =>
        HttpResponse.json({
          count: 1,
          results: [
            savedApplication({
              monthly_take_home_pay: null,
              receives_noncash_assistance: null,
              benefit_types: [],
            }),
          ],
        })
      )
    );

    renderFeeWaiver();

    await waitFor(() => {
      expect(screen.getByLabelText(/household size/i)).toHaveValue(2);
    });
    expect(screen.getByLabelText(/take-home pay/i)).toHaveValue(null);
    expect(screen.getByRole('radio', { name: 'Yes' })).not.toBeChecked();
    expect(screen.getByRole('radio', { name: 'No' })).not.toBeChecked();
  });

  it('holds the form until the saved answers are read, so nothing typed is overwritten', async () => {
    let answer: () => void = () => {};
    const read = new Promise<void>((resolve) => {
      answer = resolve;
    });
    let readStarted: () => void = () => {};
    const started = new Promise<void>((resolve) => {
      readStarted = resolve;
    });
    server.use(
      http.get(`${API}/intake/fee-waiver/`, async () => {
        readStarted();
        await read;
        return HttpResponse.json({ count: 1, results: [savedApplication({})] });
      })
    );

    renderFeeWaiver();

    await screen.findByRole('heading', { name: /filing fee waiver/i });
    // Once the session has loaded and the read has started, the form is still held back
    await started;
    expect(screen.queryByLabelText(/household size/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /submit/i })).not.toBeInTheDocument();

    answer();
    await waitFor(() => {
      expect(screen.getByLabelText(/household size/i)).toHaveValue(2);
    });
  });

  it('asks about non-cash help with neither answer picked, and only Yes asks what kind', async () => {
    renderFeeWaiver();

    const question = await nonCashQuestion();
    expect(question).toHaveAccessibleName(
      'Do you receive non-cash help from the government, such as SNAP (food stamps) or a housing subsidy?'
    );
    expect(screen.getByRole('radio', { name: 'Yes' })).not.toBeChecked();
    expect(screen.getByRole('radio', { name: 'No' })).not.toBeChecked();
    expect(screen.queryByLabelText('What kind?')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
    expect(screen.getByLabelText('What kind?')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
    expect(screen.queryByLabelText('What kind?')).not.toBeInTheDocument();
  });

  it('sends take-home pay and the non-cash answer under the names the server keeps', async () => {
    const sent = captureSent();
    renderFeeWaiver();

    await userEvent.type(await screen.findByLabelText(/household size/i), '3');
    await userEvent.type(screen.getByLabelText(/take-home pay/i), '2800');
    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
    await userEvent.click(screen.getByLabelText(/cannot pay the full filing fee/i));
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await screen.findByText('Statement of Financial Affairs');
    // The old income, expenses and benefits answers are no longer sent
    expect(sent).toEqual([
      {
        session: 1,
        household_size: 3,
        monthly_take_home_pay: '2800',
        receives_noncash_assistance: false,
        benefit_types: [],
        cannot_pay_full: true,
        cannot_pay_installments: false,
      },
    ]);
  });

  it('sends a Yes with what kind', async () => {
    const sent = captureSent();
    renderFeeWaiver();

    await userEvent.type(await screen.findByLabelText(/household size/i), '3');
    await userEvent.type(screen.getByLabelText(/take-home pay/i), '2800');
    await userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
    await userEvent.type(screen.getByLabelText('What kind?'), '  SNAP (food stamps) ');
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await screen.findByText('Statement of Financial Affairs');
    expect(sent).toHaveLength(1);
    expect(sent[0]).toMatchObject({
      receives_noncash_assistance: true,
      benefit_types: ['SNAP (food stamps)'],
    });
  });

  it('will not send the application until every question is answered', async () => {
    const sent = captureSent();
    renderFeeWaiver();

    // Household size and take-home pay given, the non-cash question left unanswered
    await userEvent.type(await screen.findByLabelText(/household size/i), '1');
    await userEvent.type(screen.getByLabelText(/take-home pay/i), '1200');
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Please fill in all required fields.'
    );

    // A Yes without saying what kind
    await userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
    await userEvent.type(screen.getByLabelText('What kind?'), '   ');
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
    expect(screen.getByRole('alert')).toHaveTextContent('Please fill in all required fields.');

    // Take-home pay cleared, the rest answered
    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
    await userEvent.clear(screen.getByLabelText(/take-home pay/i));
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
    expect(screen.getByRole('alert')).toHaveTextContent('Please fill in all required fields.');

    expect(sent).toEqual([]);
    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
  });

  // The server refuses a negative amount, and its refusal could only say to try again
  it('says a negative take-home pay cannot be, and sends nothing', async () => {
    const sent = captureSent();
    renderFeeWaiver();

    await userEvent.type(await screen.findByLabelText(/household size/i), '1');
    await userEvent.type(screen.getByLabelText(/take-home pay/i), '-50');
    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/^Amount cannot be negative$/);
    expect(sent).toEqual([]);
    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
  });

  it('shows no form when the saved answers cannot be read, and reads them again on Try again', async () => {
    // An empty form would send unticked "cannot pay" boxes over the saved ones (DIG-157)
    let reads = 0;
    server.use(
      http.get(`${API}/intake/fee-waiver/`, () => {
        reads += 1;
        if (reads === 1) return HttpResponse.json({ detail: 'Bad request' }, { status: 400 });
        return HttpResponse.json({ count: 1, results: [savedApplication({})] });
      })
    );

    renderFeeWaiver();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "We couldn't get your latest information just now. Please try again in a moment."
    );
    expect(screen.queryByLabelText(/household size/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /submit/i })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    await waitFor(() => {
      expect(screen.getByLabelText(/household size/i)).toHaveValue(2);
    });
    expect(screen.getByLabelText(/take-home pay/i)).toHaveValue(1750);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(reads).toBe(2);
  });

  it('shows an off-ramp instead of the form when the filer is fee-waiver ineligible, and it leads on to SOFA', async () => {
    server.use(
      http.post(`${API}/intake/sessions/:id/calculate_means_test/`, () =>
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
