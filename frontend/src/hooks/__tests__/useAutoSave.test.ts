import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAutoSave } from '../useAutoSave';

describe('useAutoSave', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('debounces multiple rapid changes into a single save', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
      initialProps: { data: { a: 0 } },
    });

    // Two rapid changes within the debounce window...
    rerender({ data: { a: 1 } });
    rerender({ data: { a: 2 } });
    expect(onSave).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    // ...collapse into exactly one save.
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it('does not autosave when disabled', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, enabled: false }), {
      initialProps: { data: { a: 0 } },
    });
    rerender({ data: { a: 1 } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(onSave).not.toHaveBeenCalled();
  });

  it('saveNow returns true on success and false on failure', async () => {
    const onSave = vi
      .fn()
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error('network'));
    const { result } = renderHook(() => useAutoSave({ data: { a: 1 }, onSave }));

    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.saveNow();
    });
    expect(ok).toBe(true);
    expect(result.current.saveStatus).toBe('saved');

    await act(async () => {
      ok = await result.current.saveNow();
    });
    expect(ok).toBe(false);
    expect(result.current.saveStatus).toBe('error');
  });
});
