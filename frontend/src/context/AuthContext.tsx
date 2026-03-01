/**
 * Auth Context - Authentication state management
 *
 * Mirrors the IntakeContext pattern (useState + actions + custom hook).
 * Access token lives in memory; refresh token in localStorage for persistence.
 * On mount, attempts silent refresh to restore the session across page reloads.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import type { UserProfile, RegisterRequest } from '../types/api';
import { authAPI, APIClientError, getRefreshToken } from '../api/client';

// ============================================================================
// Context Types
// ============================================================================

interface AuthContextValue {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (username: string, password: string) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

// ============================================================================
// Create Context
// ============================================================================

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ============================================================================
// Provider Component
// ============================================================================

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true); // true on mount for silent refresh
  const [error, setError] = useState<string | null>(null);

  const isAuthenticated = user !== null;

  // =========================================================================
  // Silent refresh on mount — restore session from refresh token
  // =========================================================================

  useEffect(() => {
    const restoreSession = async () => {
      if (!getRefreshToken()) {
        setIsLoading(false);
        return;
      }

      try {
        const refreshed = await authAPI.refresh();
        if (refreshed) {
          const profile = await authAPI.me();
          setUser(profile);
        }
      } catch {
        // Silent failure — user simply isn't logged in
      } finally {
        setIsLoading(false);
      }
    };

    restoreSession();
  }, []);

  // =========================================================================
  // Actions
  // =========================================================================

  const login = useCallback(async (username: string, password: string) => {
    setIsLoading(true);
    setError(null);

    try {
      await authAPI.login({ username, password });
      const profile = await authAPI.me();
      setUser(profile);
    } catch (err) {
      const message =
        err instanceof APIClientError && err.statusCode === 401
          ? "We couldn't find that account. Please check your username and password."
          : err instanceof APIClientError
            ? err.message
            : 'Something went wrong. Please try again.';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (data: RegisterRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      await authAPI.register(data);
      // Auto-login after registration
      await authAPI.login({ username: data.username, password: data.password });
      const profile = await authAPI.me();
      setUser(profile);
    } catch (err) {
      const message =
        err instanceof APIClientError
          ? err.message
          : 'Unable to create your account. Please try again.';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    authAPI.logout();
    setUser(null);
    setError(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // =========================================================================
  // Context Value
  // =========================================================================

  const value: AuthContextValue = {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ============================================================================
// Custom Hook
// ============================================================================

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}

export default AuthContext;
