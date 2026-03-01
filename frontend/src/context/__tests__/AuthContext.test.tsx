import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { AuthProvider, useAuth } from '../AuthContext';
import { setRefreshToken, clearTokens } from '../../api/client';

/**
 * Test harness that renders the hook's return values as text,
 * so we can assert on them without a complex UI.
 */
function AuthConsumer() {
  const { user, isAuthenticated, isLoading, error, login, register, logout, clearError } =
    useAuth();

  // Swallow re-thrown errors so they don't become unhandled rejections.
  // The context stores errors in state, which is what tests assert on.
  const safe = <T,>(fn: () => Promise<T>) => () => fn().catch(() => {});

  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="username">{user?.username ?? 'none'}</span>
      <span data-testid="error">{error ?? 'none'}</span>

      <button onClick={safe(() => login('janedoe', 'pass123'))}>Login</button>
      <button
        onClick={safe(() =>
          register({
            email: 'jane@example.com',
            username: 'janedoe',
            password: 'pass123',
            agreed_to_upl_disclaimer: true,
            agreed_to_terms: true,
          }),
        )}
      >
        Register
      </button>
      <button onClick={logout}>Logout</button>
      <button onClick={clearError}>Clear Error</button>
    </div>
  );
}

function renderWithAuth() {
  return render(
    <AuthProvider>
      <AuthConsumer />
    </AuthProvider>,
  );
}

beforeEach(() => {
  clearTokens();
});

describe('AuthContext', () => {
  // ---------------------------------------------------------------------------
  // Initial state
  // ---------------------------------------------------------------------------

  it('starts in loading state while checking for saved session', async () => {
    renderWithAuth();
    // No refresh token → loading should resolve quickly to false
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
  });

  // ---------------------------------------------------------------------------
  // Silent refresh on mount
  // ---------------------------------------------------------------------------

  it('restores session from refresh token on mount', async () => {
    setRefreshToken('saved-refresh-token');

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    });
    expect(screen.getByTestId('username')).toHaveTextContent('janedoe');
  });

  it('clears tokens when refresh fails on mount', async () => {
    setRefreshToken('expired-token');
    server.use(
      http.post('http://localhost:8000/api/token/refresh/', () =>
        HttpResponse.json({ detail: 'Token is invalid' }, { status: 401 }),
      ),
    );

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
  });

  // ---------------------------------------------------------------------------
  // Login
  // ---------------------------------------------------------------------------

  it('logs in successfully', async () => {
    const user = userEvent.setup();
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    await act(async () => {
      await user.click(screen.getByText('Login'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    });
    expect(screen.getByTestId('username')).toHaveTextContent('janedoe');
  });

  it('shows dignity-preserving error on 401 login', async () => {
    server.use(
      http.post('http://localhost:8000/api/token/obtain/', () =>
        HttpResponse.json({ detail: 'No active account' }, { status: 401 }),
      ),
    );

    const user = userEvent.setup();
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    await act(async () => {
      await user.click(screen.getByText('Login'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent(
        /couldn.*t find that account/i,
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Register
  // ---------------------------------------------------------------------------

  it('registers and auto-logs in', async () => {
    const user = userEvent.setup();
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    await act(async () => {
      await user.click(screen.getByText('Register'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    });
    expect(screen.getByTestId('username')).toHaveTextContent('janedoe');
  });

  // ---------------------------------------------------------------------------
  // Logout
  // ---------------------------------------------------------------------------

  it('clears user on logout', async () => {
    const user = userEvent.setup();
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    // Login first
    await act(async () => {
      await user.click(screen.getByText('Login'));
    });
    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    });

    // Then logout
    await act(async () => {
      await user.click(screen.getByText('Logout'));
    });

    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('username')).toHaveTextContent('none');
  });

  // ---------------------------------------------------------------------------
  // Error clearing
  // ---------------------------------------------------------------------------

  it('clears error on clearError', async () => {
    server.use(
      http.post('http://localhost:8000/api/token/obtain/', () =>
        HttpResponse.json({ message: 'Validation error' }, { status: 422 }),
      ),
    );

    const user = userEvent.setup();
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    await act(async () => {
      await user.click(screen.getByText('Login'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('error')).not.toHaveTextContent('none');
    });

    await act(async () => {
      await user.click(screen.getByText('Clear Error'));
    });

    expect(screen.getByTestId('error')).toHaveTextContent('none');
  });

  // ---------------------------------------------------------------------------
  // Hook boundary
  // ---------------------------------------------------------------------------

  it('throws when useAuth is used outside AuthProvider', () => {
    // Suppress React error boundary console output
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => render(<AuthConsumer />)).toThrow(
      /useAuth must be used within an AuthProvider/,
    );

    spy.mockRestore();
  });
});
