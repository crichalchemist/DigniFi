/**
 * useDebouncedMeansTest - Debounced means test calculation
 *
 * Calls the backend means test endpoint with a 500ms debounce.
 * Gracefully handles incomplete data by showing a friendly message
 * instead of propagating API errors.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import type { MeansTestResult } from '../types/api';
import { api, APIClientError } from '../api/client';

interface UseDebouncedMeansTestOptions {
  /** Session ID to calculate means test for */
  sessionId: number | null;
  /** Current wizard step — only calculates when step >= 2 (income entered) */
  currentStep: number;
  /** Debounce delay in milliseconds */
  debounceMs?: number;
}

interface UseDebouncedMeansTestReturn {
  result: MeansTestResult | null;
  isCalculating: boolean;
  /** User-friendly status message when result is unavailable */
  statusMessage: string | null;
  /** Manually trigger recalculation */
  recalculate: () => void;
}

const INCOMPLETE_DATA_MESSAGE =
  "We'll estimate your eligibility once you provide income and expense information.";

export function useDebouncedMeansTest({
  sessionId,
  currentStep,
  debounceMs = 500,
}: UseDebouncedMeansTestOptions): UseDebouncedMeansTestReturn {
  const [result, setResult] = useState<MeansTestResult | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(INCOMPLETE_DATA_MESSAGE);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const calculate = useCallback(async () => {
    if (!sessionId || currentStep < 2) {
      setStatusMessage(INCOMPLETE_DATA_MESSAGE);
      return;
    }

    // Cancel any in-flight request
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setIsCalculating(true);

    try {
      const response = await api.intake.calculateMeansTest(sessionId);
      // Only update if this request wasn't aborted
      if (!abortRef.current.signal.aborted) {
        setResult(response.means_test_result);
        setStatusMessage(null);
      }
    } catch (err) {
      if (abortRef.current?.signal.aborted) return;

      // Gracefully handle incomplete data errors
      if (err instanceof APIClientError && err.statusCode === 400) {
        setStatusMessage(INCOMPLETE_DATA_MESSAGE);
      } else {
        setStatusMessage('Unable to estimate eligibility right now. This is not an error with your information.');
      }
    } finally {
      if (!abortRef.current?.signal.aborted) {
        setIsCalculating(false);
      }
    }
  }, [sessionId, currentStep]);

  // Debounced recalculation on step changes
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(calculate, debounceMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [calculate, debounceMs]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const recalculate = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    calculate();
  }, [calculate]);

  return { result, isCalculating, statusMessage, recalculate };
}
