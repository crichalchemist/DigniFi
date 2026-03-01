/**
 * Focus Management Hook — moves focus on wizard step transitions
 *
 * WCAG 2.4.3: Focus order must be logical and intuitive.
 * When the wizard step changes, focus moves to the step heading so
 * screen reader users hear the new context immediately.
 */

import { useEffect, useRef } from 'react';

/**
 * Moves focus to the step heading whenever `currentStep` changes.
 * Returns a ref to attach to the heading element that should receive focus.
 */
export function useFocusManagement(currentStep: number) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const isFirstRender = useRef(true);

  useEffect(() => {
    // Skip focus shift on initial mount — user hasn't navigated yet
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    // Small delay to ensure DOM has updated after step transition
    const timer = setTimeout(() => {
      headingRef.current?.focus();
    }, 100);

    return () => clearTimeout(timer);
  }, [currentStep]);

  return headingRef;
}
