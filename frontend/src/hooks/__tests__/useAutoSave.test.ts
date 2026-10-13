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

  // A save reopens a completed intake on the server, so showing a step again must not send
  // one (forms step 2 §5.3). Each step keeps its own last saved or loaded copy.
  it('sends no save when the filer steps back to a step without changing it', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(
      ({ data, dataKey }) => useAutoSave({ data, dataKey, onSave, debounceMs: 2000 }),
      { initialProps: { data: { rent: 900 }, dataKey: 'expenses' } }
    );

    // The filer changes Expenses, and the change is saved.
    rerender({ data: { rent: 950 }, dataKey: 'expenses' });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(onSave).toHaveBeenCalledTimes(1);

    // Assets opens as the server holds it, then Go Back shows Expenses again as a new object.
    rerender({ data: { assets: [] }, dataKey: 'assets' });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    rerender({ data: { rent: 950 }, dataKey: 'expenses' });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it('does not save the data a step opened with', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
      initialProps: { data: { rent: 900 } },
    });

    // The step hands the same values back as a new object when it mounts.
    rerender({ data: { rent: 900 } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(onSave).not.toHaveBeenCalled();
  });

  it('saves a change back to an earlier value, since the server holds the later one', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
      initialProps: { data: { rent: 900 } },
    });

    rerender({ data: { rent: 950 } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    rerender({ data: { rent: 900 } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    expect(onSave).toHaveBeenCalledTimes(2);
    expect(onSave).toHaveBeenLastCalledWith({ rent: 900 });
  });

  // Once the save on its way lands, the server holds 950, so a change back to 900 made
  // before the reply must still be sent.
  it('sends an edit made while the previous save was still on its way', async () => {
    let landSave = () => {};
    const onSave = vi
      .fn()
      .mockImplementationOnce(
        () =>
          new Promise<void>((resolve) => {
            landSave = resolve;
          })
      )
      .mockResolvedValue(undefined);
    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
      initialProps: { data: { rent: 900 } },
    });

    rerender({ data: { rent: 950 } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(onSave).toHaveBeenCalledTimes(1);

    // The filer changes the box back, then the 950 save lands.
    rerender({ data: { rent: 900 } });
    await act(async () => {
      landSave();
      await vi.advanceTimersByTimeAsync(10000);
    });

    expect(onSave.mock.calls).toEqual([[{ rent: 950 }], [{ rent: 900 }]]);
  });

  // On a slow connection a second save can go out before the first lands. Until the second
  // lands too, the server is about to hold its copy, not the first one.
  it('sends an edit made while a later save was still on its way', async () => {
    const landSaves: Array<() => void> = [];
    const onSave = vi.fn().mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          landSaves.push(resolve);
        })
    );
    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
      initialProps: { data: { rent: 900 } },
    });

    rerender({ data: { rent: 950 } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    rerender({ data: { rent: 1000 } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(onSave).toHaveBeenCalledTimes(2);

    // The 950 save lands, the filer changes the box back to 950, then the 1000 save lands.
    await act(async () => {
      landSaves[0]();
      await vi.advanceTimersByTimeAsync(0);
    });
    rerender({ data: { rent: 950 } });
    await act(async () => {
      landSaves[1]();
      await vi.advanceTimersByTimeAsync(10000);
    });

    expect(onSave.mock.calls).toEqual([[{ rent: 950 }], [{ rent: 1000 }], [{ rent: 950 }]]);
  });

  // A failed save leaves the server holding the earlier copy, so the same change is sent again
  // when the filer next edits the box, even if the edit ends on the value that failed.
  it('sends a change again after its save failed', async () => {
    const onSave = vi.fn().mockRejectedValueOnce(new Error('network')).mockResolvedValue(undefined);
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }),
      { initialProps: { data: { rent: 900 } } }
    );

    rerender({ data: { rent: 950 } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(result.current.saveStatus).toBe('error');

    // The filer types a digit and deletes it.
    rerender({ data: { rent: 9500 } });
    rerender({ data: { rent: 950 } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    expect(onSave.mock.calls).toEqual([[{ rent: 950 }], [{ rent: 950 }]]);
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
