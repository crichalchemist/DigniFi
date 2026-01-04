/**
 * Intake Context - State management for bankruptcy intake wizard
 *
 * Provides centralized state for multi-step intake process.
 * Uses React Context API (vs Redux) for simplicity and reduced overhead.
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { IntakeSession, MeansTestResult } from '../types/api';
import { api, APIClientError } from '../api/client';

// ============================================================================
// Context Types
// ============================================================================

interface IntakeContextValue {
  // State
  session: IntakeSession | null;
  isLoading: boolean;
  error: string | null;
  meansTestResult: MeansTestResult | null;

  // Actions
  createSession: (districtId: number) => Promise<void>;
  loadSession: (sessionId: number) => Promise<void>;
  updateCurrentStep: (step: number, data?: Partial<IntakeSession>) => Promise<void>;
  completeSession: () => Promise<void>;
  calculateMeansTest: () => Promise<MeansTestResult>;
  clearError: () => void;
}

// ============================================================================
// Create Context
// ============================================================================

const IntakeContext = createContext<IntakeContextValue | undefined>(undefined);

// ============================================================================
// Provider Component
// ============================================================================

interface IntakeProviderProps {
  children: ReactNode;
}

export function IntakeProvider({ children }: IntakeProviderProps) {
  const [session, setSession] = useState<IntakeSession | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [meansTestResult, setMeansTestResult] = useState<MeansTestResult | null>(null);

  // =========================================================================
  // Load session from localStorage on mount (persistence)
  // =========================================================================

  useEffect(() => {
    const savedSessionId = localStorage.getItem('current_session_id');
    if (savedSessionId) {
      loadSession(parseInt(savedSessionId, 10));
    }
  }, []);

  // =========================================================================
  // Save session ID to localStorage when it changes
  // =========================================================================

  useEffect(() => {
    if (session?.id) {
      localStorage.setItem('current_session_id', session.id.toString());
    }
  }, [session?.id]);

  // =========================================================================
  // Actions
  // =========================================================================

  /**
   * Create new intake session
   */
  const createSession = async (districtId: number): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.intake.createSession({
        district: districtId,
        current_step: 1,
      });

      setSession(response.session);
    } catch (err) {
      const errorMessage =
        err instanceof APIClientError
          ? err.message
          : 'Unable to start your intake session. Please try again.';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Load existing session by ID
   */
  const loadSession = async (sessionId: number): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const loadedSession = await api.intake.getSession(sessionId);
      setSession(loadedSession);
    } catch (err) {
      const errorMessage =
        err instanceof APIClientError
          ? err.message
          : 'Unable to load your session. Please try again.';
      setError(errorMessage);

      // Clear invalid session from localStorage
      localStorage.removeItem('current_session_id');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Update current wizard step
   */
  const updateCurrentStep = async (
    step: number,
    data?: Partial<IntakeSession>
  ): Promise<void> => {
    if (!session) {
      setError('No active session found. Please start a new intake.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.intake.updateStep(session.id, {
        current_step: step,
        data,
      });

      setSession(response.session);
    } catch (err) {
      const errorMessage =
        err instanceof APIClientError
          ? err.message
          : 'Unable to save your progress. Please try again.';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Complete intake session
   */
  const completeSession = async (): Promise<void> => {
    if (!session) {
      setError('No active session found. Please start a new intake.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await api.intake.completeSession(session.id);
      const updatedSession = await api.intake.getSession(session.id);
      setSession(updatedSession);
    } catch (err) {
      const errorMessage =
        err instanceof APIClientError
          ? err.message
          : 'Unable to finalize your session. Please ensure all required information is provided.';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Calculate means test for current session
   */
  const calculateMeansTest = async (): Promise<MeansTestResult> => {
    if (!session) {
      throw new Error('No active session found. Please start a new intake.');
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.intake.calculateMeansTest(session.id);
      setMeansTestResult(response.means_test_result);
      return response.means_test_result;
    } catch (err) {
      const errorMessage =
        err instanceof APIClientError
          ? err.message
          : 'Unable to calculate means test. Please ensure all income information is provided.';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Clear error state
   */
  const clearError = () => {
    setError(null);
  };

  // =========================================================================
  // Context Value
  // =========================================================================

  const value: IntakeContextValue = {
    session,
    isLoading,
    error,
    meansTestResult,
    createSession,
    loadSession,
    updateCurrentStep,
    completeSession,
    calculateMeansTest,
    clearError,
  };

  return <IntakeContext.Provider value={value}>{children}</IntakeContext.Provider>;
}

// ============================================================================
// Custom Hook
// ============================================================================

/**
 * Use intake context hook
 * Provides access to intake session state and actions
 */
export function useIntake(): IntakeContextValue {
  const context = useContext(IntakeContext);

  if (context === undefined) {
    throw new Error('useIntake must be used within an IntakeProvider');
  }

  return context;
}

export default IntakeContext;
