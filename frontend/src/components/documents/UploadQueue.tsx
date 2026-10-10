import { useEffect } from 'react';
import { pollDocument, APIClientError } from '../../api/client';
import type { OCRFailureReason } from '../../types/api';

export type UploadStatus =
  | 'waiting'
  | 'uploading'
  | 'checking'
  | 'done'
  | 'failed'
  | 'not_uploaded'
  | 'unchecked';

export interface QueueItem {
  /** Client-side key: a row exists before the server gives the file an id. */
  key: number;
  filename: string;
  documentType: string;
  docId: number | null;
  status: UploadStatus;
  failureReason: OCRFailureReason | '';
  /** The upload was refused with a 400, which is how the server rejects a file type. */
  wrongFileType: boolean;
}

interface UploadQueueProps {
  items: QueueItem[];
  onSettled: (key: number, patch: Partial<QueueItem>) => void;
}

const CHECK_INTERVAL_MS = 3000;
// The upload POST returns only after the file has been read, so the first check
// is normally the final answer. This ceiling only stops a row from waiting forever.
const GIVE_UP_AFTER_MS = 120000;

const NOTHING_FOUND: Record<string, string> = {
  creditor_bill:
    "We couldn't find the name of the company you owe in this file. You can upload a different page, or add this bill yourself in a later step.",
  pay_stub:
    "We couldn't find the pay amount and pay dates in this file. You can upload a different page, or type your income in yourself in a later step.",
  credit_report:
    "We couldn't find any accounts in this file. You can upload a different file, or add your bills yourself in a later step.",
};

const COULD_NOT_READ =
  "We couldn't read this file. You can try again, or type the details in yourself in a later step.";

function statusText(item: QueueItem): string {
  switch (item.status) {
    case 'waiting':
      return 'Waiting…';
    case 'uploading':
    case 'checking':
      return 'Reading your file…';
    case 'done':
      return '✓ Done';
    case 'failed':
      return (
        (item.failureReason === 'nothing_found' && NOTHING_FOUND[item.documentType]) ||
        COULD_NOT_READ
      );
    case 'not_uploaded':
      return item.wrongFileType
        ? "This file didn't upload. You can try again. Please use a PDF, JPEG, or PNG file."
        : "This file didn't upload. You can try again.";
    case 'unchecked':
      return "We couldn't check on this file. If we read it, what we found will still be used.";
  }
}

function QueueRow({
  item,
  onSettled,
}: {
  item: QueueItem;
  onSettled: UploadQueueProps['onSettled'];
}) {
  const { key, docId, status } = item;

  // Each row checks on its own file, so adding files never restarts another row.
  useEffect(() => {
    if (status !== 'checking' || docId === null) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let busyReplies = 0;
    const startedAt = Date.now();

    const check = async () => {
      let wait = CHECK_INTERVAL_MS;
      try {
        const ocr = (await pollDocument(docId)).ocr_result;
        if (cancelled) return;
        if (ocr?.status === 'completed' || ocr?.status === 'validated') {
          onSettled(key, { status: 'done' });
          return;
        }
        if (ocr?.status === 'failed') {
          onSettled(key, { status: 'failed', failureReason: ocr.failure_reason ?? '' });
          return;
        }
        busyReplies = 0;
      } catch (err) {
        if (cancelled) return;
        const busy =
          !(err instanceof APIClientError) || err.statusCode === 429 || err.statusCode >= 500;
        if (!busy) {
          onSettled(key, { status: 'unchecked' });
          return;
        }
        // Back off on 429, 5xx and network errors: 6 s, 12 s, 24 s, ...
        busyReplies += 1;
        wait = CHECK_INTERVAL_MS * 2 ** busyReplies;
      }
      const elapsed = Date.now() - startedAt;
      if (elapsed >= GIVE_UP_AFTER_MS) {
        onSettled(key, { status: 'unchecked' });
        return;
      }
      timer = setTimeout(check, Math.min(wait, GIVE_UP_AFTER_MS - elapsed));
    };

    check();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [key, docId, status, onSettled]);

  return (
    <li className="upload-queue-item">
      <span>{item.filename}</span>
      <span aria-live="polite">{statusText(item)}</span>
    </li>
  );
}

export function UploadQueue({ items, onSettled }: UploadQueueProps) {
  return (
    <ul aria-label="Upload queue" className="upload-queue">
      {items.map((item) => (
        <QueueRow key={item.key} item={item} onSettled={onSettled} />
      ))}
    </ul>
  );
}
