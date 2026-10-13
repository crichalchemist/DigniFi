import { StrictMode } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
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

/** Opens /sofa with the forms dashboard behind it, and records every save the page sends. */
function renderSOFA() {
  const saves: Record<string, unknown>[] = [];
  server.use(
    http.patch('http://localhost:8000/api/intake/sofa-report/:sessionId/', async ({ request }) => {
      saves.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(emptyReport);
    })
  );
  localStorage.setItem('current_session_id', '1');
  render(
    <MemoryRouter initialEntries={['/sofa']}>
      <IntakeProvider>
        <Routes>
          <Route path="/sofa" element={<SOFAStepWithSession />} />
          <Route path="/forms" element={<div>FormDashboard</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
  return { saves, user: userEvent.setup() };
}

const save = () => screen.getByRole('button', { name: /save & continue/i });

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

describe('SOFAStep unfinished rows (DIG-148)', () => {
  it('names the income row and the boxes to finish, and saves nothing until they are filled', async () => {
    const { saves, user } = renderSOFA();
    await user.click(
      await screen.findByRole('checkbox', { name: /i had income in the past 3 years/i })
    );

    // Income source 1 is finished; Income source 2 has a source, but no year and no amount
    await user.type(screen.getByLabelText('Source'), 'Temp Agency');
    await user.type(screen.getByLabelText('Gross Amount'), '24000');
    await user.click(screen.getByRole('button', { name: /add another income source/i }));
    await user.clear(screen.getAllByLabelText('Year')[1]);
    await user.type(screen.getAllByLabelText('Source')[1], 'Walgreens');
    // Nothing is asked of a row while the filer is still typing it
    expect(screen.queryByText(/please fill in/i)).not.toBeInTheDocument();
    await user.click(save());

    expect(screen.getByText(/nothing has been saved yet/i)).toBeInTheDocument();
    expect(screen.getByText('Please fill in the Year for Income source 2.')).toBeInTheDocument();
    expect(
      screen.getByText('Please fill in the Gross Amount for Income source 2.')
    ).toBeInTheDocument();
    expect(screen.queryByText(/for Income source 1\./)).not.toBeInTheDocument();
    expect(screen.queryByText(/could not save/i)).not.toBeInTheDocument();
    expect(saves).toHaveLength(0);

    // Once the row is finished, the message goes and the whole page saves
    await user.type(screen.getAllByLabelText('Year')[1], '2024');
    await user.type(screen.getAllByLabelText('Gross Amount')[1], '9100.25');
    expect(screen.queryByText(/please fill in/i)).not.toBeInTheDocument();
    await user.click(save());

    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
    expect(saves).toHaveLength(1);
    expect(saves[0].prior_income).toEqual([
      expect.objectContaining({ source: 'Temp Agency', gross_amount: '24000' }),
      expect.objectContaining({ year: 2024, source: 'Walgreens', gross_amount: '9100.25' }),
    ]);
  });

  it('asks for the Source of an income row that has only an amount, and saves nothing until it is filled', async () => {
    const { saves, user } = renderSOFA();
    await user.click(
      await screen.findByRole('checkbox', { name: /i had income in the past 3 years/i })
    );

    // The page fills in the year, so only the Source is missing
    await user.type(screen.getByLabelText('Gross Amount'), '24000');
    await user.click(save());

    expect(screen.getByText(/nothing has been saved yet/i)).toBeInTheDocument();
    expect(screen.getByText('Please fill in the Source for Income source 1.')).toBeInTheDocument();
    expect(screen.queryByText(/the (Year|Gross Amount) for/)).not.toBeInTheDocument();
    expect(saves).toHaveLength(0);

    // The one save the page sends is the one after the Source is filled
    await user.type(screen.getByLabelText('Source'), 'Temp Agency');
    await user.click(save());

    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
    expect(saves).toHaveLength(1);
    expect(saves[0].prior_income).toEqual([
      expect.objectContaining({ source: 'Temp Agency', gross_amount: '24000' }),
    ]);
  });

  it('names the creditor row and the boxes to finish, counting a row with only its dates as started', async () => {
    const { saves, user } = renderSOFA();
    await user.click(
      await screen.findByRole('checkbox', { name: /payments to creditors in the past year/i })
    );

    await user.type(screen.getByLabelText('Dates of Payments'), 'Monthly Jan-Mar 2026');
    await user.click(save());

    expect(
      screen.getByText('Please fill in the Creditor Name for Creditor 1.')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Please fill in the Total Amount Paid for Creditor 1.')
    ).toBeInTheDocument();
    expect(saves).toHaveLength(0);

    await user.type(screen.getByLabelText('Creditor Name'), 'Capital One');
    await user.type(screen.getByLabelText('Total Amount Paid'), '1500');
    await user.click(save());

    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
    expect(saves).toHaveLength(1);
    expect(saves[0].creditor_payments).toEqual([
      expect.objectContaining({
        creditor_name: 'Capital One',
        total_paid: '1500',
        dates_of_payments: 'Monthly Jan-Mar 2026',
      }),
    ]);
  });

  it('leaves a blank row out of the save instead of asking the filer to finish it', async () => {
    const { saves, user } = renderSOFA();
    await user.click(
      await screen.findByRole('checkbox', { name: /i had income in the past 3 years/i })
    );

    // Income source 1 keeps only the year the page fills in; Income source 2 is finished
    await user.click(screen.getByRole('button', { name: /add another income source/i }));
    await user.type(screen.getAllByLabelText('Source')[1], 'Temp Agency');
    await user.type(screen.getAllByLabelText('Gross Amount')[1], '24000');
    await user.click(save());

    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
    expect(screen.queryByText(/please fill in/i)).not.toBeInTheDocument();
    expect(saves).toHaveLength(1);
    expect(saves[0].prior_income).toEqual([
      expect.objectContaining({ source: 'Temp Agency', gross_amount: '24000' }),
    ]);
  });

  it('saves without the rows of a section the filer switched off, even a half-filled one', async () => {
    const { saves, user } = renderSOFA();
    const priorIncome = await screen.findByRole('checkbox', {
      name: /i had income in the past 3 years/i,
    });
    await user.click(priorIncome);
    await user.type(screen.getByLabelText('Source'), 'Walgreens');
    await user.click(priorIncome);
    await user.click(save());

    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
    expect(saves).toHaveLength(1);
    expect(saves[0].has_prior_income).toBe(false);
    expect(saves[0]).not.toHaveProperty('prior_income');
  });

  it('saves without the creditor rows the filer switched off, even a half-filled one', async () => {
    const { saves, user } = renderSOFA();
    const creditorPayments = await screen.findByRole('checkbox', {
      name: /payments to creditors in the past year/i,
    });
    await user.click(creditorPayments);
    await user.type(screen.getByLabelText('Creditor Name'), 'Capital One');
    await user.click(creditorPayments);
    await user.click(save());

    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
    expect(saves).toHaveLength(1);
    expect(saves[0].has_creditor_payments).toBe(false);
    expect(saves[0]).not.toHaveProperty('creditor_payments');
  });

  it('stops a text box at the 255 characters the server stores', async () => {
    const { saves, user } = renderSOFA();
    await user.click(
      await screen.findByRole('checkbox', { name: /i had income in the past 3 years/i })
    );
    await user.click(
      await screen.findByRole('checkbox', { name: /payments to creditors in the past year/i })
    );

    await user.click(screen.getByLabelText('Source'));
    await user.paste('S'.repeat(300));
    await user.type(screen.getByLabelText('Gross Amount'), '24000');
    await user.click(screen.getByLabelText('Creditor Name'));
    await user.paste('C'.repeat(300));
    await user.click(screen.getByLabelText('Dates of Payments'));
    await user.paste('D'.repeat(300));
    await user.type(screen.getByLabelText('Total Amount Paid'), '1500');
    await user.click(save());

    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
    expect(saves[0].prior_income).toEqual([expect.objectContaining({ source: 'S'.repeat(255) })]);
    expect(saves[0].creditor_payments).toEqual([
      expect.objectContaining({
        creditor_name: 'C'.repeat(255),
        dates_of_payments: 'D'.repeat(255),
      }),
    ]);
  });
});
