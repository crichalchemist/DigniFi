import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileDropZone } from '../components/documents/FileDropZone';
import { UploadQueue, type QueueItem } from '../components/documents/UploadQueue';
import { uploadDocument, APIClientError } from '../api/client';
import { useIntake } from '../context/IntakeContext';

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
    help: "Recent pay stubs from your job. Your employer's name is used for your income form (Schedule I).",
  },
  {
    type: 'credit_report',
    label: 'Credit report',
    help: 'Accounts with a balance will show up in the Amounts Owed step, marked "From scan." If you also uploaded a bill for the same account, it may show up twice. We may miss some, so please check that list.',
  },
] as const;

type UploadType = (typeof UPLOAD_AREAS)[number]['type'];

/** How the summary names what was read, as [one, many]. */
const READ_NAMES: Record<UploadType, [string, string]> = {
  creditor_bill: ['bill or statement', 'bills or statements'],
  pay_stub: ['pay stub', 'pay stubs'],
  credit_report: ['credit report', 'credit reports'],
};

/** "We read 2 bills or statements and 1 pay stub." Only files that were read count. */
function readSummary(queue: QueueItem[]): string {
  const parts = UPLOAD_AREAS.flatMap(({ type }) => {
    const count = queue.filter(
      (item) => item.documentType === type && item.status === 'done'
    ).length;
    if (!count) return [];
    const [one, many] = READ_NAMES[type];
    return [`${count} ${count === 1 ? one : many}`];
  });
  if (!parts.length) return '';
  const last = parts.pop();
  return `We read ${parts.length ? `${parts.join(', ')} and ${last}` : last}.`;
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
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [error, setError] = useState<string>('');
  const nextKey = useRef(1);

  const updateItem = useCallback((key: number, patch: Partial<QueueItem>) => {
    setQueue((prev) => prev.map((item) => (item.key === key ? { ...item, ...patch } : item)));
  }, []);

  const handleFiles = async (files: File[], documentType: UploadType) => {
    if (!session?.id) {
      setError('No active session. Please start from the beginning.');
      return;
    }
    setError('');

    // Every chosen file gets a row straight away, before anything is sent.
    const added: QueueItem[] = files.map((file) => ({
      key: nextKey.current++,
      filename: file.name,
      documentType,
      docId: null,
      status: 'waiting',
      failureReason: '',
      wrongFileType: false,
    }));
    setQueue((prev) => [...prev, ...added]);

    // One file at a time: each upload holds a server worker until the file is read.
    for (const [index, file] of files.entries()) {
      const { key } = added[index];
      updateItem(key, { status: 'uploading' });
      try {
        const res = await uploadDocument(session.id, file, documentType);
        updateItem(key, { status: 'checking', docId: res.id });
      } catch (err) {
        updateItem(key, {
          status: 'not_uploaded',
          wrongFileType: err instanceof APIClientError && err.statusCode === 400,
        });
      }
    }
  };

  const sending = queue.some((item) => item.status === 'waiting' || item.status === 'uploading');
  const settled = queue.every(
    (item) => item.status !== 'waiting' && item.status !== 'uploading' && item.status !== 'checking'
  );
  const anyRead = queue.some((item) => item.status === 'done');
  const summary = settled ? readSummary(queue) : '';

  return (
    <main className="document-page">
      <h1>Upload your documents</h1>
      <p>
        You can upload bills, pay stubs, and a credit report. We&apos;ll try to read them. This step
        is optional.
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

      {UPLOAD_AREAS.map((area) => (
        <section key={area.type} aria-labelledby={`upload-area-${area.type}`}>
          <h2 id={`upload-area-${area.type}`}>{area.label}</h2>
          <p>{area.help}</p>
          <FileDropZone
            label={area.label}
            onFiles={(files) => handleFiles(files, area.type)}
            disabled={sending || !session}
          />
        </section>
      ))}

      {queue.length > 0 && <UploadQueue items={queue} onSettled={updateItem} />}

      {/* Present from the start: screen readers can skip a live region added with its text. */}
      <p role="status" className="text-success">
        {summary}
      </p>

      <div className="page-actions">
        <button
          onClick={() => navigate('/intake')}
          disabled={sending}
          className="button button--primary button--md"
        >
          {anyRead ? 'Continue' : 'Skip for now'}
        </button>
      </div>
    </main>
  );
}
