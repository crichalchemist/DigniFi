import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { FormDashboard } from '../FormDashboard';

/**
 * FormDashboard requires IntakeProvider with an active session.
 * We seed localStorage to trigger session loading on mount.
 */
function renderFormDashboard() {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter>
      <IntakeProvider>
        <FormDashboard />
      </IntakeProvider>
    </MemoryRouter>
  );
}

/** Forms are prepared only from an intake the server marked complete. */
const completedSession = {
  id: 1,
  user: 1,
  district: 1,
  current_step: 8,
  status: 'completed',
  created_at: '2026-01-20T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
  completed_at: '2026-01-20T11:00:00Z',
  debtor_info: null,
  income_info: null,
  expense_info: null,
  assets: [],
  debts: [],
};

describe('FormDashboard', () => {
  beforeEach(() => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(completedSession)
      )
    );
  });

  // ---------------------------------------------------------------------------
  // Loading and display
  // ---------------------------------------------------------------------------

  it('renders page after session loads', async () => {
    renderFormDashboard();

    // Session loads from localStorage → then forms load
    await waitFor(() => {
      expect(screen.getByText('Your Court Forms')).toBeInTheDocument();
    });
  });

  it('renders page title and UPL banner after loading', async () => {
    renderFormDashboard();

    await waitFor(() => {
      expect(screen.getByText('Your Court Forms')).toBeInTheDocument();
    });

    // UPL banner should be visible
    expect(screen.getByText('Legal Information Notice')).toBeInTheDocument();
  });

  it('renders form cards after loading', async () => {
    renderFormDashboard();

    await waitFor(() => {
      expect(screen.getByText('Form 101 - Voluntary Petition')).toBeInTheDocument();
    });
  });

  it('shows progress bar', async () => {
    renderFormDashboard();

    await waitFor(() => {
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Empty session state
  // ---------------------------------------------------------------------------

  it('shows empty message when no session', async () => {
    localStorage.removeItem('current_session_id');

    render(
      <MemoryRouter>
        <IntakeProvider>
          <FormDashboard />
        </IntakeProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no active intake session/i)).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // An unfinished intake (forms step 2 §5.3)
  // ---------------------------------------------------------------------------

  it('asks the filer to finish their intake, with a link back, until it is complete', async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({ ...completedSession, status: 'in_progress', completed_at: null })
      )
    );

    renderFormDashboard();

    await screen.findByText('Form 101 - Voluntary Petition');
    expect(screen.getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
      'href',
      '/intake'
    );
  });

  it('does not ask a filer whose intake is complete to finish it', async () => {
    renderFormDashboard();

    await screen.findByText('Form 101 - Voluntary Petition');
    expect(screen.queryByRole('link', { name: 'Finish your intake' })).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Error handling
  // ---------------------------------------------------------------------------

  it('shows error message when form loading fails', async () => {
    server.use(
      http.get('http://localhost:8000/api/forms/', () =>
        HttpResponse.json({ message: 'Server error' }, { status: 422 })
      )
    );

    renderFormDashboard();

    await waitFor(() => {
      expect(screen.getByText(/unable to load your forms/i)).toBeInTheDocument();
    });

    // Retry button should be present
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Generate All
  // ---------------------------------------------------------------------------

  it('offers only the forms in the filer’s packet', async () => {
    // A stored form that no longer applies (122A-2 after income dropped) is neither shown nor counted
    server.use(
      http.get('http://localhost:8000/api/forms/packet/', () =>
        HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
      ),
      http.get('http://localhost:8000/api/forms/', () =>
        HttpResponse.json([
          { id: 1, session: 1, form_type: 'form_101', status: 'generated' },
          { id: 2, session: 1, form_type: 'form_122a2', status: 'generated' },
        ])
      )
    );

    renderFormDashboard();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /generate all 2 forms/i })).toBeInTheDocument();
    });
    expect(screen.getByText('1 of 2 generated')).toBeInTheDocument();
    expect(screen.getByText('Form 121 - SSN Statement')).toBeInTheDocument();
    expect(screen.queryByText('Form 103B - Fee Waiver Application')).not.toBeInTheDocument();
    expect(screen.queryByText('Form 122A-2 - Means Test Expenses')).not.toBeInTheDocument();
  });

  it('shows error banner when generate_all returns partial failures', async () => {
    server.use(
      http.post('http://localhost:8000/api/forms/generate_all/', () =>
        HttpResponse.json({
          generated: [],
          errors: [{ form_type: 'form_101', error: 'Missing debtor name' }],
          total_generated: 0,
          total_errors: 1,
        })
      )
    );

    renderFormDashboard();
    await waitFor(() => expect(screen.getByText('Your Court Forms')).toBeInTheDocument());

    // Click "Generate All" (shown once the packet loads) — opens UPL confirmation modal
    const generateAllBtn = await screen.findByRole('button', { name: /generate all/i });
    await userEvent.click(generateAllBtn);

    // Acknowledge the UPL disclaimer checkbox, then confirm
    const checkbox = screen.getByRole('checkbox');
    await userEvent.click(checkbox);
    const continueBtn = screen.getByRole('button', { name: /continue/i });
    await userEvent.click(continueBtn);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/1 form.*could not be generated/i)).toBeInTheDocument();
    });
    // The error names the form as its card does, never by its internal key
    const failure = within(screen.getByRole('alert')).getByRole('listitem');
    expect(failure).toHaveTextContent('Form 101 - Voluntary Petition: Missing debtor name');
    expect(failure).not.toHaveTextContent('form_101');
  });
});
