/**
 * UPL Confirmation Modal - Blocks form generation until acknowledged
 *
 * Accessible modal with focus trapping and keyboard support.
 * Used at critical decision points (form generation, session completion).
 */

import { useEffect, useRef, useState } from 'react';
import { Button } from '../common';
import { UPL_FORM_GENERATION_CONFIRMATION, UPL_ARIA_LABELS } from '../../constants/upl';

interface UPLConfirmationModalProps {
  /** Whether modal is visible */
  isOpen: boolean;
  /** Called when user confirms acknowledgment */
  onConfirm: () => void;
  /** Called when user cancels */
  onCancel: () => void;
  /** Optional custom confirmation text (defaults to form generation text) */
  confirmationText?: string;
  /** Optional title override */
  title?: string;
}

export function UPLConfirmationModal({
  isOpen,
  onConfirm,
  onCancel,
  confirmationText = UPL_FORM_GENERATION_CONFIRMATION,
  title = 'Acknowledgment Required',
}: UPLConfirmationModalProps) {
  const [acknowledged, setAcknowledged] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Focus management: trap focus inside modal
  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      // Small delay to ensure modal is rendered
      const timer = setTimeout(() => modalRef.current?.focus(), 50);
      return () => clearTimeout(timer);
    } else {
      setAcknowledged(false);
      previousFocusRef.current?.focus();
    }
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <div
      className="upl-modal-overlay"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        ref={modalRef}
        className="upl-modal"
        role="dialog"
        aria-modal="true"
        aria-label={UPL_ARIA_LABELS.modal}
        tabIndex={-1}
      >
        <div className="upl-modal-header">
          <h2 className="upl-modal-title">{title}</h2>
          <button
            type="button"
            className="upl-modal-close"
            onClick={onCancel}
            aria-label="Close"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>

        <div className="upl-modal-body">
          <div className="upl-modal-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          </div>

          <label className="upl-modal-acknowledgment">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="upl-modal-checkbox"
            />
            <span className="upl-modal-text">{confirmationText}</span>
          </label>
        </div>

        <div className="upl-modal-footer">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={onConfirm}
            disabled={!acknowledged}
          >
            Continue
          </Button>
        </div>
      </div>
    </div>
  );
}

export default UPLConfirmationModal;
