/**
 * FormCard - Per-form card with preview/download/filed actions
 *
 * Each card represents one of the 13 bankruptcy forms.
 * Renders UPL disclaimer from backend response when available.
 * Generate asks for the UPL acknowledgment first, as Generate All does.
 */

import { useEffect, useId, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../common';
import { UPLConfirmationModal } from '../compliance';
import { FormStatusBadge } from './FormStatusBadge';
import type { GeneratedForm, FormType } from '../../types/api';
import { FORM_TYPE_METADATA } from '../../types/api';
import {
  MEANS_PAIR_CANCEL,
  MEANS_PAIR_CONFIRM,
  MEANS_PAIR_MARK_ALONE,
  MEANS_PAIR_MARK_BOTH,
} from '../../constants/copy';

/** Why this form's last Generate or Download was refused, and the link to its fix, if any */
export interface FormRefusal {
  message: string;
  link?: { to: string; label: string };
}

/**
 * What Mark as Filed asks first on Form 122A-1 and Form 122A-2, which are filed together: `both`
 * marks the pair; `alone` shows the filed partner's notice, then marks this form only. No `pair`
 * is today's button.
 */
export type FormCardPair =
  | { kind: 'both' }
  | { kind: 'alone'; partnerLabel: string; partnerNotice: string };

interface FormCardProps {
  formType: FormType;
  generatedForm?: GeneratedForm;
  /** A filed form whose type is no longer in the filer's packet */
  leftPacket?: boolean;
  /** Information about this form, shown before any refusal (never a refusal itself) */
  notice?: string;
  /**
   * Where a pending card's Answer Questions goes; `/ask/<form type>` without one. A refusal's
   * link, and its label, come first.
   */
  answerPath?: string;
  refusal?: FormRefusal;
  onGenerate: (formType: FormType) => Promise<void>;
  onDownload: (formId: number) => Promise<void>;
  onMarkFiled: (formId: number) => Promise<void>;
  pair?: FormCardPair;
  onMarkPairFiled?: () => Promise<void>;
}

export function FormCard({
  formType,
  generatedForm,
  leftPacket = false,
  notice,
  answerPath,
  refusal,
  onGenerate,
  onDownload,
  onMarkFiled,
  pair,
  onMarkPairFiled,
}: FormCardProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [isMarkingFiled, setIsMarkingFiled] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [confirmingPair, setConfirmingPair] = useState(false);
  const confirmId = useId();
  const noticeId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const confirmButtonRef = useRef<HTMLButtonElement>(null);
  // Set when the confirm closes, so focus returns to the Mark as Filed trigger once it is back
  const returnFocus = useRef(false);
  const navigate = useNavigate();
  const metadata = FORM_TYPE_METADATA[formType];
  const status = generatedForm?.status ?? 'pending';

  // The confirm takes focus when it opens; when it closes, focus goes back to the trigger if the
  // card is still unfiled (the pattern of UPLConfirmationModal)
  useEffect(() => {
    if (confirmingPair) {
      confirmButtonRef.current?.focus();
      return;
    }
    if (returnFocus.current && !isMarkingFiled) {
      returnFocus.current = false;
      triggerRef.current?.focus();
    }
  }, [confirmingPair, isMarkingFiled, status]);

  const handleAction = async (action: () => Promise<void>) => {
    setIsLoading(true);
    try {
      await action();
    } catch {
      // Error handled by parent
    } finally {
      setIsLoading(false);
    }
  };

  // Only Mark as Filed itself says it is marking the form filed, never a download
  const handleMarkFiled = async (formId: number) => {
    setIsMarkingFiled(true);
    await handleAction(() => onMarkFiled(formId));
    setIsMarkingFiled(false);
  };

  const handleMarkPairFiled = async () => {
    returnFocus.current = true;
    setConfirmingPair(false);
    setIsMarkingFiled(true);
    await handleAction(async () => {
      await onMarkPairFiled?.();
    });
    setIsMarkingFiled(false);
  };

  return (
    <article className={`form-card form-card--${status}`} aria-label={metadata.label}>
      <div className="form-card-header">
        <div className="form-card-info">
          <h3 className="form-card-title">{metadata.label}</h3>
          <p className="form-card-description">{metadata.description}</p>
          {leftPacket && (
            <p className="form-card-description">Filed, no longer in your current packet</p>
          )}
        </div>
        <FormStatusBadge status={status} />
      </div>

      {generatedForm?.upl_disclaimer && (
        <p className="form-card-disclaimer" role="note">
          {generatedForm.upl_disclaimer}
        </p>
      )}

      <div className="form-card-actions">
        {status === 'pending' && (
          <>
            <Button
              size="sm"
              variant="primary"
              onClick={() => setShowConfirmation(true)}
              isLoading={isLoading}
              loadingText="Generating..."
            >
              Generate
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate(refusal?.link?.to ?? answerPath ?? `/ask/${formType}`)}
            >
              {refusal?.link?.label ?? 'Answer Questions'}
            </Button>
          </>
        )}

        {/* Every stored form downloads; a filed one serves what was filed */}
        {generatedForm && (
          <Button
            size="sm"
            variant="primary"
            onClick={() => handleAction(() => onDownload(generatedForm.id))}
            isLoading={isLoading}
            loadingText="Preparing..."
          >
            Download
          </Button>
        )}

        {(status === 'generated' || status === 'downloaded') &&
          generatedForm &&
          !confirmingPair && (
            <Button
              ref={triggerRef}
              size="sm"
              variant="outline"
              onClick={() => (pair ? setConfirmingPair(true) : handleMarkFiled(generatedForm.id))}
              isLoading={isMarkingFiled}
              loadingText="Marking as filed..."
            >
              Mark as Filed
            </Button>
          )}

        {confirmingPair &&
          (status === 'generated' || status === 'downloaded') &&
          pair &&
          generatedForm && (
            <div
              className="form-card-confirm"
              role="group"
              aria-labelledby={pair.kind === 'both' ? confirmId : `${confirmId} ${noticeId}`}
            >
              {pair.kind === 'both' ? (
                <p id={confirmId}>{MEANS_PAIR_CONFIRM}</p>
              ) : (
                <>
                  <p id={confirmId}>
                    <strong>{pair.partnerLabel}</strong>
                  </p>
                  <p id={noticeId}>{pair.partnerNotice}</p>
                </>
              )}
              <div className="form-card-confirm-buttons">
                <Button
                  ref={confirmButtonRef}
                  size="sm"
                  variant="primary"
                  onClick={() => {
                    if (pair.kind === 'both') return handleMarkPairFiled();
                    returnFocus.current = true;
                    setConfirmingPair(false);
                    return handleMarkFiled(generatedForm.id);
                  }}
                >
                  {pair.kind === 'both' ? MEANS_PAIR_MARK_BOTH : MEANS_PAIR_MARK_ALONE}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    returnFocus.current = true;
                    setConfirmingPair(false);
                  }}
                >
                  {MEANS_PAIR_CANCEL}
                </Button>
              </div>
            </div>
          )}

        {status === 'filed' && (
          <span className="form-card-filed-check" aria-label="Filed with court">
            <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            Filed
          </span>
        )}
      </div>

      {notice && (
        <p className="form-card-notice" role="status">
          {notice}
        </p>
      )}

      {/* A polite live region from the start, so a screen reader reads out a refusal that
          Generate or Download adds to it (step 3a2 spec §4.5) */}
      <div className="form-card-refusal" aria-live="polite">
        {refusal && (
          <>
            <p>{refusal.message}</p>
            {/* A pending card's button already goes to the same place, so one way to the fix */}
            {refusal.link && status !== 'pending' && (
              <Link to={refusal.link.to} className="button button--primary">
                {refusal.link.label}
              </Link>
            )}
          </>
        )}
      </div>

      <UPLConfirmationModal
        isOpen={showConfirmation}
        onConfirm={() => {
          setShowConfirmation(false);
          void handleAction(() => onGenerate(formType));
        }}
        onCancel={() => setShowConfirmation(false)}
        title="Generate Court Form"
      />
    </article>
  );
}
