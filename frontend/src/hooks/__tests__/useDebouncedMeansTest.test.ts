import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { api } from '../../api/client';
import { useDebouncedMeansTest } from '../useDebouncedMeansTest';
import { MEANS_TEST_WAITING } from '../../constants/copy';

const CALCULATE = 'http://localhost:8000/api/intake/sessions/:id/calculate_means_test/';

const RESULT = {
  passes_means_test: null,
  cmi: 9000,
  median_income_threshold: 100000,
  family_size: 4,
  outcome: 'cannot_work_out',
  tables_gap: null,
  details: { cmi: 9000, annualized_cmi: 108000, median_income_threshold: 100000, family_size: 4 },
  means_test_id: 1,
};

describe('useDebouncedMeansTest', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('a step back to the first step drops the result it held and says it is waiting', async () => {
    const { result, rerender } = renderHook(
      ({ step }) => useDebouncedMeansTest({ sessionId: 1, currentStep: step, debounceMs: 0 }),
      { initialProps: { step: 3 } }
    );
    await waitFor(() => expect(result.current.result).not.toBeNull());

    rerender({ step: 1 });

    await waitFor(() => expect(result.current.result).toBeNull());
    expect(result.current.isCalculating).toBe(false);
    expect(result.current.statusMessage).toBe(MEANS_TEST_WAITING);
  });

  it('a step back aborts the call on its way', async () => {
    let release: () => void = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    let reached = false;
    server.use(
      http.post(CALCULATE, async () => {
        reached = true;
        await held;
        return HttpResponse.json({ means_test_result: RESULT, session_id: 1 });
      })
    );
    // The sentinel: the call the hook awaits. The hook's continuation is registered on it before
    // the test's, so once the test's await returns the hook has handled the reply.
    const original = api.intake.calculateMeansTest.bind(api.intake);
    let calls: Promise<unknown>[] = [];
    vi.spyOn(api.intake, 'calculateMeansTest').mockImplementation((id) => {
      const call = original(id);
      calls = [...calls, call];
      return call;
    });
    const { result, rerender } = renderHook(
      ({ step }) => useDebouncedMeansTest({ sessionId: 1, currentStep: step, debounceMs: 0 }),
      { initialProps: { step: 3 } }
    );
    await waitFor(() => expect(reached).toBe(true));
    expect(result.current.isCalculating).toBe(true);

    rerender({ step: 1 });
    await waitFor(() => expect(result.current.isCalculating).toBe(false));

    await act(async () => {
      release();
      await calls[0].catch(() => undefined);
    });
    expect(calls).toHaveLength(1);
    expect(result.current.result).toBeNull();
    expect(result.current.isCalculating).toBe(false);
  });
});
