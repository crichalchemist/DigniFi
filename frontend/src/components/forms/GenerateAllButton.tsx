/**
 * GenerateAllButton - Bulk form generation with progress feedback
 *
 * Triggers the backend's atomic generateAll endpoint.
 * Shows progress while generating and UPL confirmation modal before starting.
 */

import { useState } from 'react';
import { Button } from '../common';
import { UPLConfirmationModal } from '../compliance';

interface GenerateAllButtonProps {
  onGenerateAll: () => Promise<void>;
  /** Number of forms already generated */
  generatedCount: number;
  /** Total number of form types */
  totalCount: number;
  disabled?: boolean;
}

export function GenerateAllButton({
  onGenerateAll,
  generatedCount,
  totalCount,
  disabled = false,
}: GenerateAllButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);

  const allGenerated = generatedCount >= totalCount;

  const handleConfirm = async () => {
    setShowConfirmation(false);
    setIsGenerating(true);
    try {
      await onGenerateAll();
    } catch {
      // Error handled by parent
    } finally {
      setIsGenerating(false);
    }
  };

  if (allGenerated) {
    return (
      <div className="generate-all-complete" role="status">
        <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            clipRule="evenodd"
          />
        </svg>
        <span>All {totalCount} forms have been generated</span>
      </div>
    );
  }

  return (
    <>
      <Button
        variant="primary"
        size="lg"
        fullWidth
        onClick={() => setShowConfirmation(true)}
        isLoading={isGenerating}
        loadingText={`Generating ${totalCount} forms...`}
        disabled={disabled || isGenerating}
      >
        Generate All {totalCount} Forms
      </Button>

      {generatedCount > 0 && (
        <p className="generate-all-progress" aria-live="polite">
          {generatedCount} of {totalCount} forms already generated
        </p>
      )}

      <UPLConfirmationModal
        isOpen={showConfirmation}
        onConfirm={handleConfirm}
        onCancel={() => setShowConfirmation(false)}
        title="Generate Court Forms"
      />
    </>
  );
}
