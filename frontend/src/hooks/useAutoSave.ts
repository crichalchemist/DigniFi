/**
 * useAutoSave - Debounced auto-save on field changes
 *
 * Saves data after 2 seconds of inactivity. Exposes save status
 * so the UI can show "Saving..." / "Saved" indicators.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface UseAutoSaveOptions<T> {
  /** The data to auto-save */
  data: T;
  /** Async function that persists the data */
  onSave: (data: T) => Promise<void>;
  /** Debounce delay in milliseconds (default: 2000) */
  debounceMs?: number;
  /** Whether auto-save is enabled (default: true) */
  enabled?: boolean;
}

interface UseAutoSaveReturn {
  saveStatus: SaveStatus;
  /** Manually trigger an immediate save */
  saveNow: () => Promise<void>;
  /** Last successful save timestamp */
  lastSavedAt: Date | null;
}

export function useAutoSave<T>({
  data,
  onSave,
  debounceMs = 2000,
  enabled = true,
}: UseAutoSaveOptions<T>): UseAutoSaveReturn {
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dataRef = useRef(data);
  const onSaveRef = useRef(onSave);
  const isFirstRender = useRef(true);

  // Keep refs current to avoid stale closures
  dataRef.current = data;
  onSaveRef.current = onSave;

  const executeSave = useCallback(async () => {
    setSaveStatus('saving');
    try {
      await onSaveRef.current(dataRef.current);
      setSaveStatus('saved');
      setLastSavedAt(new Date());

      // Reset to idle after 3 seconds
      setTimeout(() => setSaveStatus((s) => (s === 'saved' ? 'idle' : s)), 3000);
    } catch {
      setSaveStatus('error');
    }
  }, []);

  // Debounced save on data changes
  useEffect(() => {
    // Skip first render (initial data load)
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    if (!enabled) return;

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(executeSave, debounceMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [data, debounceMs, enabled, executeSave]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const saveNow = useCallback(async () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    await executeSave();
  }, [executeSave]);

  return { saveStatus, saveNow, lastSavedAt };
}
