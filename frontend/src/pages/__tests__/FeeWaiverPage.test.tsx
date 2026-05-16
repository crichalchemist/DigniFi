import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { FeeWaiverPage } from '../FeeWaiverPage';

function renderFeeWaiver() {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter initialEntries={['/fee-waiver']}>
      <IntakeProvider>
        <Routes>
          <Route path="/fee-waiver" element={<FeeWaiverPage />} />
          <Route path="/forms" element={<div>FormDashboard</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

describe('FeeWaiverPage', () => {
  it('renders the fee waiver heading', async () => {
    renderFeeWaiver();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /filing fee waiver/i })).toBeInTheDocument();
    });
  });

  it('navigates to /forms on successful submission', async () => {
    renderFeeWaiver();
    await waitFor(() => screen.getByRole('heading', { name: /filing fee waiver/i }));

    await userEvent.type(screen.getByLabelText(/household size/i), '1');
    await userEvent.type(screen.getByLabelText(/monthly income/i), '1200');
    await userEvent.type(screen.getByLabelText(/monthly expenses/i), '1000');

    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => {
      expect(screen.getByText('FormDashboard')).toBeInTheDocument();
    });
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
});
