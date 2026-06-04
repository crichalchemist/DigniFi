import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileDropZone } from '../components/documents/FileDropZone';
import { UploadQueue } from '../components/documents/UploadQueue';
import { uploadDocument } from '../api/client';
import { useIntake } from '../context/IntakeContext';
import type { UploadedDocument } from '../types/api';

const ILND_DISTRICT_ID = 1;

interface QueuedUpload {
  docId: number;
  filename: string;
  doc: UploadedDocument | null;
}

export function DocumentUploadPage() {
  const navigate = useNavigate();
  const { session, isLoading, createSession } = useIntake();

  // Auto-create a session for new users who arrive here before the intake wizard.
  useEffect(() => {
    if (!isLoading && !session) {
      createSession(ILND_DISTRICT_ID).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading]);
  const [queue, setQueue] = useState<QueuedUpload[]>([]);
  const [uploading, setUploading] = useState(false);
  const [allComplete, setAllComplete] = useState(false);
  const [summary, setSummary] = useState<string>('');
  const [error, setError] = useState<string>('');

  const handleFiles = useCallback(
    async (files: File[]) => {
      if (!session?.id) {
        setError('No active session. Please start from the beginning.');
        return;
      }
      setUploading(true);
      setError('');

      const newItems: QueuedUpload[] = [];
      for (const file of files) {
        try {
          const res = await uploadDocument(session.id, file, 'creditor_bill');
          newItems.push({ docId: res.id, filename: file.name, doc: null });
        } catch {
          setError(`Failed to upload ${file.name}.`);
        }
      }
      setQueue((prev) => [...prev, ...newItems]);
      setUploading(false);
    },
    [session]
  );

  const handleAllComplete = useCallback((docs: UploadedDocument[]) => {
    setAllComplete(true);
    const bills = docs.filter((d) => d.document_type === 'creditor_bill').length;
    const stubs = docs.filter((d) => d.document_type === 'pay_stub').length;
    const parts: string[] = [];
    if (bills) parts.push(`${bills} creditor bill${bills > 1 ? 's' : ''}`);
    if (stubs) parts.push(`${stubs} pay stub${stubs > 1 ? 's' : ''}`);
    setSummary(parts.length ? `Found: ${parts.join(', ')}.` : 'Processing complete.');
  }, []);

  const isEmpty = queue.length === 0 && !uploading;

  return (
    <main style={{ maxWidth: 640, margin: '0 auto', padding: '2rem' }}>
      <h1>Upload your documents</h1>
      <p>
        Upload paystubs, creditor bills, and other supporting documents. We&apos;ll extract the
        information and pre-fill your intake forms &mdash; you can review and correct anything
        before submitting.
      </p>
      <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
        Your documents are processed locally and never sent to any external service.
      </p>

      {error && (
        <p role="alert" style={{ color: '#dc2626' }}>
          {error}
        </p>
      )}

      {isEmpty && <FileDropZone onFiles={handleFiles} disabled={uploading} />}

      {queue.length > 0 && (
        <>
          <UploadQueue items={queue} onAllComplete={handleAllComplete} />
          {!allComplete && <FileDropZone onFiles={handleFiles} disabled={uploading} />}
        </>
      )}

      {allComplete && summary && (
        <p role="status" style={{ color: '#16a34a', fontWeight: 600 }}>
          {summary}
        </p>
      )}

      <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
        <button
          onClick={() => navigate('/intake')}
          disabled={uploading}
          style={{ padding: '0.75rem 1.5rem', cursor: 'pointer' }}
        >
          {allComplete ? 'Continue to intake' : 'Skip for now'}
        </button>
      </div>
    </main>
  );
}
