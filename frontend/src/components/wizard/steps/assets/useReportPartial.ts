import { useEffect } from 'react';

/** Counts this box at the step while it holds only part of a number, until it doesn't or is gone */
export function useReportPartial(partial: boolean, onPartialBox: (change: 1 | -1) => void) {
  useEffect(() => {
    if (!partial) return undefined;
    onPartialBox(1);
    return () => onPartialBox(-1);
  }, [partial, onPartialBox]);
}
