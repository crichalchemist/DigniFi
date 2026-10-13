/**
 * useAutoSave - Debounced auto-save on field changes
 *
 * Saves data after 2 seconds of inactivity. Exposes save status
 * so the UI can show "Saving..." / "Saved" indicators.
 *
 * A save whose data equals the last saved or loaded copy (or the copy of a save still on its
 * way) is skipped, so showing a step again sends nothing. Only a real edit is saved, and on
 * the server it reopens a completed intake (forms step 2 §5.3).
 */

import { useState, useEffect, useRef, useCallback } from 'react';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface UseAutoSaveOptions<T> {
  /** The data to auto-save */
  data: T;
  /**
   * Names whose data `data` is, for a caller that shows one of several (the wizard's steps).
   * Each name keeps its own last saved copy; the first data seen under a name is its loaded copy.
   */
  dataKey?: string;
  /** Async function that persists the data */
  onSave: (data: T) => Promise<void>;
  /** Debounce delay in milliseconds (default: 2000) */
  debounceMs?: number;
  /** Whether auto-save is enabled (default: true) */
  enabled?: boolean;
}

interface UseAutoSaveReturn {
  saveStatus: SaveStatus;
  /** Manually trigger an immediate save. Resolves true on success, false on failure. */
  saveNow: () => Promise<boolean>;
  /** Last successful save timestamp */
  lastSavedAt: Date | null;
}

export function useAutoSave<T>({
  data,
  dataKey,
  onSave,
  debounceMs = 2000,
  enabled = true,
}: UseAutoSaveOptions<T>): UseAutoSaveReturn {
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dataRef = useRef(data);
  const dataKeyRef = useRef(dataKey);
  const onSaveRef = useRef(onSave);
  // The last copy saved or loaded under each name, as JSON
  const savedCopiesRef = useRef(new Map<string | undefined, string>());
  // The copy of a save still on its way, by name: once it lands, the server holds it
  const sendingCopiesRef = useRef(new Map<string | undefined, string>());

  // Keep refs current to avoid stale closures
  useEffect(() => {
    dataRef.current = data;
    dataKeyRef.current = dataKey;
    onSaveRef.current = onSave;
  });

  const executeSave = useCallback(async (): Promise<boolean> => {
    // Taken before the save, so a later edit is never recorded as saved
    const key = dataKeyRef.current;
    const copy = JSON.stringify(dataRef.current);
    sendingCopiesRef.current.set(key, copy);
    setSaveStatus('saving');
    try {
      await onSaveRef.current(dataRef.current);
      savedCopiesRef.current.set(key, copy);
      setSaveStatus('saved');
      setLastSavedAt(new Date());

      // Reset to idle after 3 seconds
      setTimeout(() => setSaveStatus((s) => (s === 'saved' ? 'idle' : s)), 3000);
      return true;
    } catch {
      setSaveStatus('error');
      return false;
    } finally {
      // Unless a later save of this name has gone out since
      if (sendingCopiesRef.current.get(key) === copy) sendingCopiesRef.current.delete(key);
    }
  }, []);

  // Debounced save on data changes
  useEffect(() => {
    const copy = JSON.stringify(data);
    const savedCopies = savedCopiesRef.current;

    // The first data seen under a name is the loaded copy, not an edit
    if (!savedCopies.has(dataKey)) {
      savedCopies.set(dataKey, copy);
      return;
    }

    // Compared with what the server will hold once a save on its way lands
    const serverCopy = sendingCopiesRef.current.get(dataKey) ?? savedCopies.get(dataKey);
    if (!enabled || copy === serverCopy) return;

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(executeSave, debounceMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [data, dataKey, debounceMs, enabled, executeSave]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const saveNow = useCallback(async (): Promise<boolean> => {
    if (timerRef.current) clearTimeout(timerRef.current);
    return executeSave();
  }, [executeSave]);

  return { saveStatus, saveNow, lastSavedAt };
}
