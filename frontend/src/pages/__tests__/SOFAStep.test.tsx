import { StrictMode } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse, delay } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider, useIntake } from '../../context/IntakeContext';
import { SOFAStep } from '../SOFAStep';

const emptyReport = {
  id: 1,
  session: 1,
  has_prior_income: false,
  has_creditor_payments: false,
  has_business: false,
  prior_income: [],
  creditor_payments: [],
};

/** The filer arrives from the wizard, so the session is already loaded when the page mounts. */
function SOFAStepWithSession() {
  const { session } = useIntake();
  return session ? <SOFAStep /> : null;
}

describe('SOFAStep', () => {
  it('keeps a section the filer ticked when an earlier load replies late', async () => {
    // StrictMode mounts the page twice, so the report is read twice; the first read replies last.
    let reads = 0;
    server.use(
      http.get('http://localhost:8000/api/intake/sofa-report/:sessionId/', async () => {
        reads += 1;
        if (reads === 1) await delay(300);
        return HttpResponse.json(emptyReport);
      })
    );
    localStorage.setItem('current_session_id', '1');

    render(
      <StrictMode>
        <MemoryRouter>
          <IntakeProvider>
            <SOFAStepWithSession />
          </IntakeProvider>
        </MemoryRouter>
      </StrictMode>
    );

    const priorIncome = { name: /i had income in the past 3 years/i };
    await userEvent.click(await screen.findByRole('checkbox', priorIncome));
    await new Promise((resolve) => setTimeout(resolve, 400));

    expect(reads).toBe(2);
    expect(screen.getByRole('checkbox', priorIncome)).toBeChecked();
  });
});
