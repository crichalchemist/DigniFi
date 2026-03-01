/**
 * UPL Disclaimer - Renders legal disclaimers in multiple formats
 *
 * Variants:
 * - inline: subtle text below content (wizard steps)
 * - banner: prominent box with icon (review step, form dashboard)
 * - modal: blocking overlay requiring acknowledgment (form generation)
 * - checkbox: inline with required checkbox (registration-style)
 */

import { useState } from 'react';
import { UPL_ARIA_LABELS, type UPLDisclaimerVariant } from '../../constants/upl';

interface UPLDisclaimerProps {
  /** The disclaimer text to display */
  text: string;
  /** Display variant */
  variant?: UPLDisclaimerVariant;
  /** For checkbox variant: callback when checked/unchecked */
  onAcknowledge?: (acknowledged: boolean) => void;
  /** For checkbox variant: external controlled state */
  acknowledged?: boolean;
  /** Optional CSS class */
  className?: string;
}

export function UPLDisclaimer({
  text,
  variant = 'inline',
  onAcknowledge,
  acknowledged,
  className = '',
}: UPLDisclaimerProps) {
  const ariaLabel = UPL_ARIA_LABELS[variant];

  if (variant === 'inline') {
    return (
      <p
        className={`upl-disclaimer upl-disclaimer--inline ${className}`}
        role="note"
        aria-label={ariaLabel}
      >
        <svg
          className="upl-disclaimer-icon"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
            clipRule="evenodd"
          />
        </svg>
        <span>{text}</span>
      </p>
    );
  }

  if (variant === 'banner') {
    return (
      <div
        className={`upl-disclaimer upl-disclaimer--banner ${className}`}
        role="note"
        aria-label={ariaLabel}
      >
        <div className="upl-disclaimer-icon-wrapper" aria-hidden="true">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="upl-disclaimer-content">
          <strong className="upl-disclaimer-title">Legal Information Notice</strong>
          <p className="upl-disclaimer-text">{text}</p>
        </div>
      </div>
    );
  }

  if (variant === 'checkbox') {
    return (
      <label
        className={`upl-disclaimer upl-disclaimer--checkbox ${className}`}
        aria-label={ariaLabel}
      >
        <input
          type="checkbox"
          className="upl-disclaimer-checkbox"
          checked={acknowledged ?? false}
          onChange={(e) => onAcknowledge?.(e.target.checked)}
          required
        />
        <span className="upl-disclaimer-text">{text}</span>
      </label>
    );
  }

  // variant === 'modal' — not rendered directly, use UPLConfirmationModal
  return null;
}

export default UPLDisclaimer;
