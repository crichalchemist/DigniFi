/**
 * FormCard - Per-form card with preview/download/filed actions
 *
 * Each card represents one of the 13 bankruptcy forms.
 * Renders UPL disclaimer from backend response when available.
 */

import { useState } from 'react';
import { Button } from '../common';
import { FormStatusBadge } from './FormStatusBadge';
import type { GeneratedForm, FormType } from '../../types/api';
import { FORM_TYPE_METADATA } from '../../types/api';

interface FormCardProps {
  formType: FormType;
  generatedForm?: GeneratedForm;
  onGenerate: (formType: FormType) => Promise<void>;
  onMarkDownloaded: (formId: number) => Promise<void>;
  onMarkFiled: (formId: number) => Promise<void>;
}

export function FormCard({
  formType,
  generatedForm,
  onGenerate,
  onMarkDownloaded,
  onMarkFiled,
}: FormCardProps) {
  const [isLoading, setIsLoading] = useState(false);
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
    <article className="form-card" aria-label={metadata.label}>
      <div className="form-card-header">
        <div className="form-card-info">
          <h3 className="form-card-title">{metadata.label}</h3>
          <p className="form-card-description">{metadata.description}</p>
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
          <Button
            size="sm"
            variant="primary"
            onClick={() => handleAction(() => onGenerate(formType))}
            isLoading={isLoading}
            loadingText="Generating..."
          >
            Generate
          </Button>
        )}

        {status === 'generated' && generatedForm && (
          <>
            <Button
              size="sm"
              variant="primary"
              onClick={() => handleAction(() => onMarkDownloaded(generatedForm.id))}
              isLoading={isLoading}
              loadingText="Preparing..."
            >
              Download
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleAction(() => onMarkFiled(generatedForm.id))}
            >
              Mark as Filed
            </Button>
          </>
        )}

        {status === 'downloaded' && generatedForm && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleAction(() => onMarkFiled(generatedForm.id))}
            isLoading={isLoading}
            loadingText="Updating..."
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
    </article>
  );
}
