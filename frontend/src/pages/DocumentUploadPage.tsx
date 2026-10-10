import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileDropZone } from '../components/documents/FileDropZone';
import { UploadQueue } from '../components/documents/UploadQueue';
import { uploadDocument } from '../api/client';
import { useIntake } from '../context/IntakeContext';
import type { UploadedDocument } from '../types/api';

const ILND_DISTRICT_ID = 1;

const UPLOAD_AREAS = [
  {
    type: 'creditor_bill',
    label: 'Bills and statements',
    help: 'Bills or statements for money you owe. What we find will show up in the Amounts Owed step, marked "From scan." You can check or change it there.',
  },
  {
    type: 'pay_stub',
    label: 'Pay stubs',
    help: "Recent pay stubs from your job. Your employer's name and your pay before taxes are used for your income form (Schedule I).",
  },
  {
    type: 'credit_report',
    label: 'Credit report',
    help: 'Accounts with a balance will show up in the Amounts Owed step, marked "From scan." If you also uploaded a bill for the same account, it may show up twice. We may miss some, so please check that list.',
  },
] as const;

type UploadType = (typeof UPLOAD_AREAS)[number]['type'];

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
    async (files: File[], documentType: UploadType) => {
      if (!session?.id) {
        setError('No active session. Please start from the beginning.');
        return;
      }
      setUploading(true);
      setError('');

      const newItems: QueuedUpload[] = [];
      for (const file of files) {
        try {
          const res = await uploadDocument(session.id, file, documentType);
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

  const areas = UPLOAD_AREAS.map((area) => (
    <section key={area.type} aria-labelledby={`upload-area-${area.type}`}>
      <h2 id={`upload-area-${area.type}`}>{area.label}</h2>
      <p>{area.help}</p>
      <FileDropZone
        label={area.label}
        onFiles={(files) => handleFiles(files, area.type)}
        disabled={uploading || !session}
      />
    </section>
  ));

  return (
    <main className="document-page">
      <h1>Upload your documents</h1>
      <p>
        Upload paystubs, creditor bills, and other supporting documents. We&apos;ll extract the
        information and pre-fill your intake forms &mdash; you can review and correct anything
        before submitting.
      </p>
      <p className="text-muted">
        To read your documents, we send them to OpenAI, an outside AI service. If you&apos;d rather
        not, you can skip this step and type your information in by hand.
      </p>

      {error && (
        <p role="alert" className="text-error">
          {error}
        </p>
      )}

      {isEmpty && areas}

      {queue.length > 0 && (
        <>
          <UploadQueue items={queue} onAllComplete={handleAllComplete} />
          {!allComplete && areas}
        </>
      )}

      {allComplete && summary && (
        <p role="status" className="text-success">
          {summary}
        </p>
      )}

      <div className="page-actions">
        <button
          onClick={() => navigate('/intake')}
          disabled={uploading}
          className="button button--primary button--md"
        >
          {allComplete ? 'Continue' : 'Skip for now'}
        </button>
      </div>
    </main>
  );
}
