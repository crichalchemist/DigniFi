/**
 * Retry utility with exponential backoff
 *
 * Only retries on 5xx server errors — client errors (4xx) are never retried
 * since the same request would produce the same result.
 */

import { APIClientError } from '../api/client';

interface RetryOptions {
  /** Maximum number of retry attempts (default: 3) */
  maxRetries?: number;
  /** Base delay in milliseconds (default: 500) */
  baseDelay?: number;
  /** Only retry when this predicate returns true */
  shouldRetry?: (error: unknown) => boolean;
}

/** Default predicate: retry only on 5xx server errors */
const isRetryableError = (error: unknown): boolean => {
  if (error instanceof APIClientError) {
    return error.statusCode >= 500 && error.statusCode < 600;
  }
  // Network errors (fetch failed) are retryable
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return true;
  }
  return false;
};

/**
 * Execute an async function with exponential backoff retry.
 *
 * Delay formula: baseDelay * 2^attempt (500ms, 1s, 2s, ...)
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {},
): Promise<T> {
  const {
    maxRetries = 3,
    baseDelay = 500,
    shouldRetry = isRetryableError,
  } = options;

  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (attempt >= maxRetries || !shouldRetry(error)) {
        throw error;
      }

      const delay = baseDelay * Math.pow(2, attempt);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  // Unreachable, but TypeScript needs it
  throw lastError;
}
