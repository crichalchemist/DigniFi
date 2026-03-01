import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
    <IntakeProvider>
      <FormDashboard />
    </IntakeProvider>,
  );
}

describe('FormDashboard', () => {
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
      expect(
        screen.getByText('Form 101 - Voluntary Petition'),
      ).toBeInTheDocument();
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
      <IntakeProvider>
        <FormDashboard />
      </IntakeProvider>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/no active intake session/i),
      ).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Error handling
  // ---------------------------------------------------------------------------

  it('shows error message when form loading fails', async () => {
    server.use(
      http.get('http://localhost:8000/api/forms/', () =>
        HttpResponse.json({ message: 'Server error' }, { status: 422 }),
      ),
    );

    renderFormDashboard();

    await waitFor(() => {
      expect(
        screen.getByText(/unable to load your forms/i),
      ).toBeInTheDocument();
    });

    // Retry button should be present
    expect(
      screen.getByRole('button', { name: /try again/i }),
    ).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Generate All
  // ---------------------------------------------------------------------------

  it('renders Generate All button', async () => {
    // Return empty forms list so all are "pending"
    server.use(
      http.get('http://localhost:8000/api/forms/', () =>
        HttpResponse.json([]),
      ),
    );

    renderFormDashboard();

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /generate all 13 forms/i }),
      ).toBeInTheDocument();
    });
  });
});
