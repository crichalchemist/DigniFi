import { useEffect, useState } from 'react';
import { pollDocument } from '../../api/client';
import type { UploadedDocument } from '../../types/api';

interface QueueItem {
  docId: number;
  filename: string;
  doc: UploadedDocument | null;
}

interface UploadQueueProps {
  items: QueueItem[];
  onAllComplete: (docs: UploadedDocument[]) => void;
}

export function UploadQueue({ items, onAllComplete }: UploadQueueProps) {
  const [states, setStates] = useState<Record<number, UploadedDocument | null>>({});

  useEffect(() => {
    if (!items.length) return;

    const intervals: ReturnType<typeof setInterval>[] = [];

    items.forEach((item) => {
      const interval = setInterval(async () => {
        try {
          const doc = await pollDocument(item.docId);
          if (doc.ocr_result?.status === 'completed' || doc.ocr_result?.status === 'failed') {
            clearInterval(interval);
            setStates((prev) => ({ ...prev, [item.docId]: doc }));
          }
        } catch {
          clearInterval(interval);
        }
      }, 3000);
      intervals.push(interval);
    });

    return () => intervals.forEach(clearInterval);
  }, [items]);

  useEffect(() => {
    if (!items.length) return;
    const completed = items.filter((i) => states[i.docId] !== undefined);
    if (completed.length === items.length) {
      onAllComplete(Object.values(states).filter(Boolean) as UploadedDocument[]);
    }
  }, [states, items, onAllComplete]);

  const statusLabel = (docId: number) => {
    const doc = states[docId];
    if (!doc) return 'Processing…';
    const s = doc.ocr_result?.status;
    if (s === 'completed') return '✓ Done';
    if (s === 'failed') return '✗ Failed';
    return 'Processing…';
  };

  return (
    <ul aria-label="Upload queue" className="upload-queue">
      {items.map((item) => (
        <li key={item.docId} className="upload-queue-item">
          <span>{item.filename}</span>
          <span aria-live="polite">{statusLabel(item.docId)}</span>
        </li>
      ))}
    </ul>
  );
}
