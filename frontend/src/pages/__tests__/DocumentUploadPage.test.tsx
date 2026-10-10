import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { DocumentUploadPage } from '../DocumentUploadPage';

const API = 'http://localhost:8000/api';

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

// undici's request.formData() rejects jsdom's File, so read the field from the multipart text.
async function sentDocumentType(request: Request) {
  const body = await request.text();
  return /name="document_type"\r\n\r\n([^\r\n]*)/.exec(body)?.[1] ?? '';
}

function pdf(name: string) {
  return new File(['%PDF-1.4'], name, { type: 'application/pdf' });
}

describe('DocumentUploadPage', () => {
  it('sends each area its own document type, so a pay stub is never filed as a bill', async () => {
    const sentTypes: string[] = [];
    server.use(
      http.post(`${API}/documents/upload/`, async ({ request }) => {
        sentTypes.push(await sentDocumentType(request));
        return HttpResponse.json({ id: sentTypes.length, status: 'processing' }, { status: 202 });
      }),
      // Every file stays "being read", so this test sees only what each area sent.
      http.get(`${API}/documents/:id/`, ({ params }) =>
        HttpResponse.json({
          id: Number(params.id),
          document_type: 'creditor_bill',
          original_filename: 'file.pdf',
          uploaded_at: '2026-01-20T10:00:00Z',
          ocr_result: {
            status: 'processing',
            failure_reason: '',
            confidence_scores: {},
            overall_confidence: 0,
            user_validated: false,
          },
        })
      )
    );

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
});
