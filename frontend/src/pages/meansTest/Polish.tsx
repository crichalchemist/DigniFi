import { useEffect, useRef, useState } from 'react';
import { Button, FormTextarea } from '../../components/common';
import {
  MEANS_POLISH_APPROVE,
  MEANS_POLISH_APPROVED,
  MEANS_POLISH_BUTTON,
  MEANS_POLISH_CONSENT_HEADING,
  MEANS_POLISH_CONSENT_KEEP,
  MEANS_POLISH_CONSENT_RETENTION,
  MEANS_POLISH_CONSENT_WHAT,
  MEANS_POLISH_DECLINE,
  MEANS_POLISH_DISCLOSURE,
  MEANS_POLISH_HOLDS_REWRITE,
  MEANS_POLISH_KEEP,
  MEANS_POLISH_KEPT,
  MEANS_POLISH_NOTE,
  MEANS_POLISH_RESTORE,
  MEANS_POLISH_REWRITE_LABEL,
  MEANS_POLISH_SEND,
  MEANS_POLISH_SENT_LABEL,
  MEANS_POLISH_WORKING,
} from '../../constants/copy';
import type { KeyedCircumstance } from './pageState';

/** What the service sent back for a circumstance, and the words that were sent for it */
export interface Pending {
  sent: string;
  rewrite: string;
}

interface PolishProps {
  index: number;
  row: KeyedCircumstance;
  /** The id of the circumstance's legend, so each button's name says which circumstance it is */
  legendId: string;
  pending?: Pending;
  /** This circumstance's consent panel is open */
  asking: boolean;
  status: 'approved' | 'kept' | null;
  busy: boolean;
  failure: string | null;
  available: boolean;
  onRequest: () => void;
  onConsent: (agree: boolean) => void;
  onApprove: (editedRewrite: string) => void;
  onKeep: () => void;
  onRestore: () => void;
}

/** The rewrite beside what was sent: its own edit state, seeded once from the reply */
function Review({
  index,
  pending,
  onApprove,
  onKeep,
}: {
  index: number;
  pending: Pending;
  onApprove: (editedRewrite: string) => void;
  onKeep: () => void;
}) {
  const [edited, setEdited] = useState(pending.rewrite);
  // The id on arrival; a circumstance removed above this one must not pull focus back here
  const arrivedAs = useRef(`field-means_line_43_${index}_rewrite`);
  useEffect(() => {
    document.getElementById(arrivedAs.current)?.focus();
  }, []);

  return (
    <div className="polish-review">
      <FormTextarea
        label={MEANS_POLISH_SENT_LABEL}
        name={`means_line_43_${index}_sent`}
        value={pending.sent}
        rows={8}
        readOnly
      />
      <FormTextarea
        label={MEANS_POLISH_REWRITE_LABEL}
        name={`means_line_43_${index}_rewrite`}
        value={edited}
        maxLength={2000}
        rows={8}
        helpText={MEANS_POLISH_DISCLOSURE}
        onChange={(event) => setEdited(event.target.value)}
      />
      <div className="polish-review-actions">
        <Button type="button" disabled={edited.trim() === ''} onClick={() => onApprove(edited)}>
          {MEANS_POLISH_APPROVE}
        </Button>
        <Button type="button" variant="outline" onClick={onKeep}>
          {MEANS_POLISH_KEEP}
        </Button>
      </div>
    </div>
  );
}

/**
 * What sits under a line 43 explanation box for the AI polish: the note and button, the consent
 * panel, what the service is doing, a failure, the rewrite beside what was sent, and, whenever the
 * box holds an approved rewrite, the sentence that says so and the way back to the filer's words.
 * `Line43` holds every state and does every action; this draws them.
 */
export function Polish({
  index,
  row,
  legendId,
  pending,
  asking,
  status,
  busy,
  failure,
  available,
  onRequest,
  onConsent,
  onApprove,
  onKeep,
  onRestore,
}: PolishProps) {
  const buttonId = `means-line-43-${index}-polish`;
  const headingId = `means-line-43-${index}-consent`;
  const heading = useRef<HTMLHeadingElement>(null);
  // A group can't take focus, so the heading inside it does
  useEffect(() => {
    if (asking) heading.current?.focus();
  }, [asking]);

  const blank = (row.explanation ?? '').trim() === '';
  const said = busy
    ? MEANS_POLISH_WORKING
    : status === 'approved'
      ? MEANS_POLISH_APPROVED
      : status === 'kept'
        ? MEANS_POLISH_KEPT
        : '';

  return (
    <>
      {available && (
        <>
          <p className="form-help-text">{MEANS_POLISH_NOTE}</p>
          <Button
            type="button"
            variant="outline"
            id={buttonId}
            aria-labelledby={`${buttonId} ${legendId}`}
            disabled={blank || busy || pending !== undefined}
            onClick={onRequest}
          >
            {MEANS_POLISH_BUTTON}
          </Button>
        </>
      )}
      {asking && (
        <div role="group" aria-labelledby={headingId} className="polish-consent">
          <h3 id={headingId} ref={heading} tabIndex={-1}>
            {MEANS_POLISH_CONSENT_HEADING}
          </h3>
          <p>{MEANS_POLISH_CONSENT_WHAT}</p>
          <p>{MEANS_POLISH_CONSENT_RETENTION}</p>
          <p>{MEANS_POLISH_CONSENT_KEEP}</p>
          <Button type="button" onClick={() => onConsent(true)}>
            {MEANS_POLISH_SEND}
          </Button>
          <Button type="button" variant="outline" onClick={() => onConsent(false)}>
            {MEANS_POLISH_DECLINE}
          </Button>
        </div>
      )}
      <p role="status" className="form-help-text">
        {said}
      </p>
      {failure && (
        <p role="alert" className="form-error">
          {failure}
        </p>
      )}
      {pending && <Review index={index} pending={pending} onApprove={onApprove} onKeep={onKeep} />}
      {row.original_explanation != null && (
        <>
          <p className="form-help-text">{MEANS_POLISH_HOLDS_REWRITE}</p>
          {/* Held while a review is open: an approval then would record AI text as the filer's own */}
          <Button
            type="button"
            variant="outline"
            disabled={pending !== undefined}
            onClick={onRestore}
          >
            {MEANS_POLISH_RESTORE}
          </Button>
        </>
      )}
    </>
  );
}
