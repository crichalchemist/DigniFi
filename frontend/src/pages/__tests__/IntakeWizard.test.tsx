import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { IntakeWizard } from '../IntakeWizard';

// DebtorInfoStep reads the account email via useAuth; this wizard test renders
// outside an AuthProvider, so stub the hook with a logged-in user.
vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'jane@example.com' } }),
}));

const sessionAtStep6 = {
  id: 1,
  user: 1,
  district: 1,
  current_step: 6,
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

function renderWizard() {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter initialEntries={['/intake']}>
      <IntakeProvider>
        <Routes>
          <Route path="/intake" element={<IntakeWizard />} />
          <Route path="/fee-waiver" element={<div>FeeWaiverPage</div>} />
          <Route path="/forms" element={<div>FormDashboard</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

describe('IntakeWizard handleComplete routing', () => {
  beforeEach(() => {
    // Both GET (load from localStorage) and POST (createSession) return step 6
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep6)
      ),
      http.post('http://localhost:8000/api/intake/sessions/', () =>
        HttpResponse.json({ session: sessionAtStep6, message: 'Session created.' })
      ),
      // complete/ returns updated step-6 session
      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
        HttpResponse.json({ message: 'Session completed.' })
      )
    );
  });

  it('navigates to /fee-waiver when qualifies_for_fee_waiver is true', async () => {
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
        HttpResponse.json({
          means_test_result: {
            passes_means_test: true,
            qualifies_for_fee_waiver: true,
            cmi: 1200,
            median_income_threshold: 71304,
            family_size: 1,
            message: 'You qualify.',
            details: {
              cmi: 1200,
              annualized_cmi: 14400,
              median_income_threshold: 71304,
              family_size: 1,
            },
            means_test_id: 1,
          },
          session_id: 1,
        })
      )
    );

    renderWizard();
    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
    await userEvent.click(completeBtn);

    await waitFor(() => {
      expect(screen.getByText('FeeWaiverPage')).toBeInTheDocument();
    });
  });

  it('navigates to /forms when qualifies_for_fee_waiver is false', async () => {
    renderWizard();
    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
    await userEvent.click(completeBtn);

    await waitFor(() => {
      expect(screen.getByText('FormDashboard')).toBeInTheDocument();
    });
  });
});
