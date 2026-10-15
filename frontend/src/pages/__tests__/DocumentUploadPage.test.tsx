import { render, screen, waitFor, fireEvent, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse, delay } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { setAccessToken } from '../../api/client';
import { DocumentUploadPage } from '../DocumentUploadPage';

const API = 'http://localhost:8000/api';
const UPLOAD = `${API}/documents/upload/`;
const DOCUMENT = `${API}/documents/:id/`;

const COULD_NOT_READ =
  "We couldn't read this file. You can try again, or type the details in yourself in a later step.";
const UNCHECKED =
  "We couldn't check on this file. If we read it, what we found will still be used.";

function renderUploadPage() {
  return render(
    <MemoryRouter initialEntries={['/documents']}>
      <IntakeProvider>
        <Routes>
          <Route path="/documents" element={<DocumentUploadPage />} />
          <Route path="/intake" element={<h1>Intake wizard</h1>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

function dropZone(label: string) {
  return screen.getByRole('button', { name: `${label}: drop files here or click to upload` });
}

/** Under real timers: wait until the session exists and the area's zone takes files. */
async function readyZone(label: string) {
  await waitFor(() => expect(dropZone(label)).toHaveAttribute('aria-disabled', 'false'));
  return dropZone(label);
}

function dropFiles(zone: HTMLElement, ...files: File[]) {
  fireEvent.drop(zone, { dataTransfer: { files } });
}

function pdf(name: string) {
  return new File(['%PDF-1.4'], name, { type: 'application/pdf' });
}

// undici's request.formData() rejects jsdom's File, so read the field from the multipart text.
async function sentDocumentType(request: Request) {
  const body = await request.text();
  return /name="document_type"\r\n\r\n([^\r\n]*)/.exec(body)?.[1] ?? '';
}

type Outcome = { status: 'completed' | 'failed' | 'processing'; failure_reason?: string };

function documentReply(id: number, outcome: Outcome) {
  return HttpResponse.json({
    id,
    document_type: 'creditor_bill',
    original_filename: 'file.pdf',
    uploaded_at: '2026-01-20T10:00:00Z',
    ocr_result: {
      failure_reason: '',
      confidence_scores: {},
      overall_confidence: 0,
      user_validated: false,
      ...outcome,
    },
  });
}

/**
 * Uploads get ids 1, 2, 3, ... in the order they are sent; a document's status
 * answers with outcomes[id], or completed when it is not listed.
 * Returns the document types sent, in order.
 */
function serveDocuments(outcomes: Record<number, Outcome> = {}) {
  const sentTypes: string[] = [];
  server.use(
    http.post(UPLOAD, async ({ request }) => {
      sentTypes.push(await sentDocumentType(request));
      return HttpResponse.json({ id: sentTypes.length, status: 'processing' }, { status: 202 });
    }),
    http.get(DOCUMENT, ({ params }) => {
      const id = Number(params.id);
      return documentReply(id, outcomes[id] ?? { status: 'completed' });
    })
  );
  return sentTypes;
}

afterEach(() => {
  setAccessToken(null);
});

describe('DocumentUploadPage', () => {
  it('sends each area its own document type, so a pay stub is never filed as a bill', async () => {
    const sentTypes = serveDocuments();
    renderUploadPage();
    expect(screen.getByRole('heading', { level: 2, name: 'Pay stubs' })).toBeInTheDocument();

    dropFiles(await readyZone('Bills and statements'), pdf('electric-bill.pdf'));
    await waitFor(() => expect(sentTypes).toHaveLength(1));
    dropFiles(await readyZone('Pay stubs'), pdf('pay-stub.pdf'));
    await waitFor(() => expect(sentTypes).toHaveLength(2));
    dropFiles(await readyZone('Credit report'), pdf('credit-report.pdf'));
    await waitFor(() => expect(sentTypes).toHaveLength(3));

    expect(sentTypes).toEqual(['creditor_bill', 'pay_stub', 'credit_report']);
  });

  it('never tells the filer a pay stub fills in their pay', async () => {
    renderUploadPage();
    const payStubs = screen.getByRole('region', { name: 'Pay stubs' });

    // Schedule I prints the pay typed on the Income step; a stub supplies only the employer's name.
    expect(payStubs).toHaveTextContent(
      "Your employer's name is used for your income form (Schedule I)."
    );
    expect(payStubs).not.toHaveTextContent(/pay before taxes/i);
    await readyZone('Pay stubs');
  });

  it('counts only the files that were read in the summary, in plain words', async () => {
    serveDocuments({ 1: { status: 'failed', failure_reason: 'nothing_found' } });
    renderUploadPage();
    // The summary's live region is there, empty, before anything is read, so its text is announced.
    expect(screen.getByRole('status')).toBeEmptyDOMElement();

    dropFiles(await readyZone('Bills and statements'), pdf('cover-page.pdf'), pdf('statement.pdf'));
    await waitFor(() => expect(screen.getAllByText('✓ Done')).toHaveLength(1));
    dropFiles(await readyZone('Pay stubs'), pdf('june-stub.pdf'), pdf('july-stub.pdf'));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent(
        'We read 1 bill or statement and 2 pay stubs.'
      )
    );
  });

  it.each([
    {
      area: 'Bills and statements',
      why: 'nothing was found',
      outcome: { status: 'failed', failure_reason: 'nothing_found' },
      says: "We couldn't find the name of the company you owe in this file. You can upload a different page, or add this bill yourself in a later step.",
    },
    {
      area: 'Pay stubs',
      why: 'nothing was found',
      outcome: { status: 'failed', failure_reason: 'nothing_found' },
      says: "We couldn't find the pay amount and pay dates in this file. You can upload a different page, or type your income in yourself in a later step.",
    },
    {
      area: 'Credit report',
      why: 'nothing was found',
      outcome: { status: 'failed', failure_reason: 'nothing_found' },
      says: "We couldn't find any accounts in this file. You can upload a different file, or add your bills yourself in a later step.",
    },
    {
      area: 'Bills and statements',
      why: 'reading broke',
      outcome: { status: 'failed', failure_reason: 'processing_error' },
      says: COULD_NOT_READ,
    },
    {
      area: 'Pay stubs',
      why: 'an older failure has no reason',
      outcome: { status: 'failed', failure_reason: '' },
      says: COULD_NOT_READ,
    },
  ] as { area: string; why: string; outcome: Outcome; says: string }[])(
    'tells the filer in plain words why a file in $area was not read when $why',
    async ({ area, outcome, says }) => {
      serveDocuments({ 1: outcome });
      renderUploadPage();

      dropFiles(await readyZone(area), pdf('scan.pdf'));

      expect(await screen.findByText(says)).toBeInTheDocument();
    }
  );

  it('says a refused file did not upload, and asks for a PDF, JPEG or PNG only on a 400', async () => {
    let posts = 0;
    server.use(
      http.post(UPLOAD, () => {
        posts += 1;
        return posts === 1
          ? HttpResponse.json({ error: 'Unsupported file type' }, { status: 400 })
          : HttpResponse.json({ error: 'Bad gateway' }, { status: 502 });
      })
    );
    renderUploadPage();

    dropFiles(await readyZone('Bills and statements'), pdf('first.pdf'), pdf('second.pdf'));

    expect(
      await screen.findByText(
        "This file didn't upload. You can try again. Please use a PDF, JPEG, or PNG file."
      )
    ).toBeInTheDocument();
    expect(
      await screen.findByText("This file didn't upload. You can try again.")
    ).toBeInTheDocument();
  });

  it('lists every chosen file at once, before its upload finishes', async () => {
    let release!: () => void;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    let sent = 0;
    server.use(
      http.post(UPLOAD, async () => {
        await held;
        sent += 1;
        return HttpResponse.json({ id: sent, status: 'processing' }, { status: 202 });
      })
    );
    renderUploadPage();

    dropFiles(await readyZone('Bills and statements'), pdf('january.pdf'), pdf('february.pdf'));

    const queue = screen.getByRole('list', { name: 'Upload queue' });
    expect(within(queue).getByText('january.pdf')).toBeInTheDocument();
    expect(within(queue).getByText('february.pdf')).toBeInTheDocument();
    expect(within(queue).getByText('Reading your file…')).toBeInTheDocument();
    expect(within(queue).getByText('Waiting…')).toBeInTheDocument();
    expect(dropZone('Pay stubs')).toHaveAttribute('aria-disabled', 'true');
    expect(screen.getByRole('button', { name: 'Skip for now' })).toBeDisabled();

    release();

    await waitFor(() => expect(within(queue).getAllByText('✓ Done')).toHaveLength(2));
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled();
  });

  it('sends files one at a time and ignores a drop while a file is sending', async () => {
    let inFlight = 0;
    let maxInFlight = 0;
    let sent = 0;
    server.use(
      http.post(UPLOAD, async () => {
        sent += 1;
        inFlight += 1;
        maxInFlight = Math.max(maxInFlight, inFlight);
        await delay(30);
        inFlight -= 1;
        return HttpResponse.json({ id: sent, status: 'processing' }, { status: 202 });
      })
    );
    renderUploadPage();

    dropFiles(await readyZone('Bills and statements'), pdf('a.pdf'), pdf('b.pdf'), pdf('c.pdf'));
    dropFiles(dropZone('Pay stubs'), pdf('stub.pdf'));

    await waitFor(() => expect(screen.getAllByText('✓ Done')).toHaveLength(3));
    expect(sent).toBe(3);
    expect(maxInFlight).toBe(1);
    expect(screen.queryByText('stub.pdf')).not.toBeInTheDocument();
  });

  it('reads "Skip for now" until a file is read, then "Continue"', async () => {
    serveDocuments({ 1: { status: 'failed', failure_reason: 'nothing_found' } });
    renderUploadPage();
    expect(screen.getByRole('button', { name: 'Skip for now' })).toBeInTheDocument();

    dropFiles(await readyZone('Bills and statements'), pdf('cover-page.pdf'));
    await screen.findByText(/We couldn't find the name of the company you owe/);
    expect(screen.getByRole('button', { name: 'Skip for now' })).toBeEnabled();

    // The areas stay on the page after a batch, so the filer can send another file.
    dropFiles(await readyZone('Bills and statements'), pdf('statement.pdf'));
    await screen.findByText('✓ Done');
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: 'Skip for now' })).not.toBeInTheDocument();
  });

  it('lets the filer choose the same file again after it could not be read', async () => {
    serveDocuments({ 1: { status: 'failed', failure_reason: 'processing_error' } });
    const user = userEvent.setup();
    renderUploadPage();
    const file = pdf('bill.pdf');

    const zone = await readyZone('Bills and statements');
    const input = zone.querySelector<HTMLInputElement>('input[type="file"]')!;
    await user.upload(input, file);
    await screen.findByText(COULD_NOT_READ);

    await readyZone('Bills and statements');
    await user.upload(input, file);

    expect(await screen.findByText('✓ Done')).toBeInTheDocument();
    expect(screen.getAllByText('bill.pdf')).toHaveLength(2);
  });

  it('finishes an upload that starts after the login has expired', async () => {
    setAccessToken('expired-access-token');
    localStorage.setItem('refresh_token', 'mock-refresh-token');
    const authHeaders: (string | null)[] = [];
    server.use(
      http.post(UPLOAD, ({ request }) => {
        const auth = request.headers.get('Authorization');
        authHeaders.push(auth);
        return auth === 'Bearer refreshed-access-token'
          ? HttpResponse.json({ id: 1, status: 'processing' }, { status: 202 })
          : HttpResponse.json(
              { detail: 'Given token not valid for any token type' },
              { status: 401 }
            );
      })
    );
    renderUploadPage();

    dropFiles(await readyZone('Bills and statements'), pdf('bill.pdf'));

    expect(await screen.findByText('✓ Done')).toBeInTheDocument();
    expect(authHeaders).toEqual(['Bearer expired-access-token', 'Bearer refreshed-access-token']);
  });

  it('keeps checking on a file through a busy server instead of stranding it', async () => {
    let checks = 0;
    server.use(
      http.post(UPLOAD, () => HttpResponse.json({ id: 1, status: 'processing' }, { status: 202 })),
      http.get(DOCUMENT, ({ params }) => {
        checks += 1;
        return checks <= 2
          ? HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
          : documentReply(Number(params.id), { status: 'completed' });
      })
    );
    renderUploadPage();
    // Real timers until the page and its session are ready; findBy/waitFor hang under fake timers.
    await screen.findByRole('heading', { level: 1, name: 'Upload your documents' });
    const zone = await readyZone('Bills and statements');

    vi.useFakeTimers();
    try {
      dropFiles(zone, pdf('bill.pdf'));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(checks).toBe(1);
      expect(screen.getByText('Reading your file…')).toBeInTheDocument();

      await act(async () => {
        await vi.advanceTimersByTimeAsync(6000);
      });
      expect(checks).toBe(2);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(12000);
      });
      expect(checks).toBe(3);
      expect(screen.getByText('✓ Done')).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it('lets the filer move on when a file cannot be checked', async () => {
    server.use(
      http.post(UPLOAD, () => HttpResponse.json({ id: 1, status: 'processing' }, { status: 202 })),
      http.get(DOCUMENT, () =>
        HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
      )
    );
    renderUploadPage();
    await screen.findByRole('heading', { level: 1, name: 'Upload your documents' });
    const zone = await readyZone('Bills and statements');

    vi.useFakeTimers();
    try {
      dropFiles(zone, pdf('bill.pdf'));
      // One second at a time, so each check's reply lands before the clock moves on.
      for (let second = 0; second < 119; second += 1) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(1000);
        });
      }
      expect(screen.getByText('Reading your file…')).toBeInTheDocument();

      for (let second = 0; second < 2; second += 1) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(1000);
        });
      }
      expect(screen.getByText(UNCHECKED)).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }

    // Checking has stopped, so click under real timers: a user-event action hangs under
    // vitest fake timers, because RTL drains it with a setTimeout only a `jest` global advances.
    const button = screen.getByRole('button', { name: 'Skip for now' });
    expect(button).toBeEnabled();
    await userEvent.setup().click(button);
    expect(await screen.findByRole('heading', { name: 'Intake wizard' })).toBeInTheDocument();
  });
});
