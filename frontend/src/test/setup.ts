/**
 * Vitest global setup — runs before every test file.
 *
 * Extends matchers with jest-dom (toBeInTheDocument, toHaveAttribute, etc.)
 * and starts/stops the MSW server so network requests are intercepted.
 */

import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll, expect } from 'vitest';
import { cleanup } from '@testing-library/react';
import { server } from './mocks/server';
import * as matchers from 'vitest-axe/matchers';

// Register vitest-axe matchers (toHaveNoViolations)
expect.extend(matchers);

// Start MSW before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));

// Reset handlers between tests so one test's overrides don't bleed
afterEach(() => {
  cleanup();
  server.resetHandlers();
  localStorage.clear();
});

// Shut down MSW after all tests
afterAll(() => server.close());
