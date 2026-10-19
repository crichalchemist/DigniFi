/**
 * FormCard - Per-form card with preview/download/filed actions
 *
 * Each card represents one of the 13 bankruptcy forms.
 * Renders UPL disclaimer from backend response when available.
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '../common';
import { FormStatusBadge } from './FormStatusBadge';
import type { GeneratedForm, FormType } from '../../types/api';
import { FORM_TYPE_METADATA } from '../../types/api';

/** Why this form's last Generate or Download was refused, and the link to its fix, if any */
export interface FormRefusal {
  message: string;
  link?: { to: string; label: string };
}

interface FormCardProps {
  formType: FormType;
  generatedForm?: GeneratedForm;
  /** A filed form whose type is no longer in the filer's packet */
  leftPacket?: boolean;
  refusal?: FormRefusal;
  onGenerate: (formType: FormType) => Promise<void>;
  onDownload: (formId: number) => Promise<void>;
  onMarkFiled: (formId: number) => Promise<void>;
}

export function FormCard({
  formType,
  generatedForm,
  leftPacket = false,
  refusal,
  onGenerate,
  onDownload,
  onMarkFiled,
}: FormCardProps) {
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const metadata = FORM_TYPE_METADATA[formType];
  const status = generatedForm?.status ?? 'pending';

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
              onClick={() => handleAction(() => onGenerate(formType))}
              isLoading={isLoading}
              loadingText="Generating..."
            >
              Generate
            </Button>
            <Button size="sm" variant="outline" onClick={() => navigate(`/ask/${formType}`)}>
              Answer Questions
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

        {(status === 'generated' || status === 'downloaded') && generatedForm && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleAction(() => onMarkFiled(generatedForm.id))}
          >
            Mark as Filed
          </Button>
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

      {/* A polite live region from the start, so a screen reader reads out a refusal that
          Generate or Download adds to it (step 3a2 spec §4.5) */}
      <div className="form-card-refusal" aria-live="polite">
        {refusal && (
          <>
            <p>{refusal.message}</p>
            {refusal.link && (
              <Link to={refusal.link.to} className="button button--primary">
                {refusal.link.label}
              </Link>
            )}
          </>
        )}
      </div>
    </article>
  );
}
