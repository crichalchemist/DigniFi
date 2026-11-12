/**
 * The exemptions page (3g1 spec §5.4). Business intent: the filer answers Schedule C's line 1,
 * line 3 and "not claiming" in the form's words, nothing is chosen for them, Continue waits on the
 * first gap, and a save that fails never sends them on.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { ExemptionsPage } from '../ExemptionsPage';
import {
  EXEMPTIONS_LINE_1_QUESTION,
  EXEMPTIONS_LINE_1_WORDS,
  EXEMPTIONS_LINE_3_QUESTION,
  EXEMPTIONS_LINE_3_1_QUESTION,
} from '../../constants/formText';
import {
  EXEMPTIONS_NO_TABLE,
  EXEMPTIONS_NOTE_12_1201,
  EXEMPTIONS_NOTE_DOMICILE,
  EXEMPTIONS_NOT_CLAIMING_BUTTON,
  EXEMPTIONS_READ_FAILED,
  EXEMPTIONS_SAVE_FAILED,
  EXEMPTIONS_TITLE,
  EXEMPTION_GAP_LINE_1,
  EXEMPTION_GAP_NO_ITEMS,
} from '../../constants/copy';
import { UPL_EXEMPTION_DISCLAIMER } from '../../constants/upl';
import type { Exemptions } from '../../types/api';

const URL = 'http://localhost:8000/api/intake/sessions/:id/exemptions/';

function record(overrides: Partial<Exemptions> = {}): Exemptions {
  return {
    line_1: null,
    line_3: null,
    line_3_1: null,
    no_claims: false,
    claims: [],
    items: [],
    catalog: {
      effective_date: '2026-01-01',
      source_url: 'https://www.ilga.gov/',
      laws: [
        {
          key: 'il_735_5_12_1001_b',
          citation: '735 ILCS 5/12-1001(b)',
          jurisdiction: 'illinois',
          limit_text: 'Up to $4,000.',
        },
      ],
    },
    catalog_gap: null,
    ...overrides,
  };
}

function serve(saved: Exemptions, putStatus = 200) {
  const sent: Record<string, unknown>[] = [];
  server.use(
    http.get(URL, () => HttpResponse.json(saved)),
    http.put(URL, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      sent.push(body);
      if (putStatus !== 200) {
        return HttpResponse.json({ detail: 'Bad request' }, { status: putStatus });
      }
      return HttpResponse.json({ ...saved, ...body });
    })
  );
  return sent;
}

function renderPage() {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter initialEntries={['/exemptions']}>
      <IntakeProvider>
        <Routes>
          <Route path="/exemptions" element={<ExemptionsPage />} />
          <Route path="/sofa" element={<div>Statement of Financial Affairs</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

// The h1 shows before the read returns, so wait for a line 1 radio first
const ready = () => screen.findByRole('radio', { name: EXEMPTIONS_LINE_1_WORDS.federal });
const group = (question: string) =>
  screen.getByRole('group', { name: (name) => name.startsWith(question) });
const radio = (question: string, name: string) =>
  within(group(question)).getByRole('radio', { name });
const pressContinue = () => userEvent.click(screen.getByRole('button', { name: 'Continue' }));

describe('ExemptionsPage', () => {
  it('shows nothing to answer until the saved answers are read, and offers Try again when the read fails', async () => {
    server.use(http.get(URL, () => HttpResponse.json({ detail: 'Bad request' }, { status: 400 })));
    renderPage();
    expect(
      await screen.findByRole('heading', { level: 1, name: EXEMPTIONS_TITLE })
    ).toBeInTheDocument();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    expect(await screen.findByRole('alert')).toHaveTextContent(EXEMPTIONS_READ_FAILED);

    serve(record());
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await ready()).toBeInTheDocument();
  });

  it("asks line 1 in the form's words with neither choice selected", async () => {
    serve(record());
    renderPage();
    await ready();
    const radios = within(group(EXEMPTIONS_LINE_1_QUESTION)).getAllByRole('radio');
    expect(radios.map((r) => r.getAttribute('value'))).toEqual(['state_and_federal', 'federal']);
    for (const r of radios) {
      expect(r).not.toBeChecked();
      expect(r).toHaveAttribute('aria-required', 'true');
    }
    expect(
      radio(EXEMPTIONS_LINE_1_QUESTION, EXEMPTIONS_LINE_1_WORDS.state_and_federal)
    ).toBeTruthy();
  });

  it('shows both line 1 notes after both choices', async () => {
    serve(record());
    renderPage();
    const federal = await ready();
    for (const text of [EXEMPTIONS_NOTE_12_1201, EXEMPTIONS_NOTE_DOMICILE]) {
      const note = screen.getByText(text);
      expect(federal.compareDocumentPosition(note) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  it('shows the exemption disclaimer inline', async () => {
    serve(record());
    renderPage();
    await ready();
    expect(await screen.findByRole('note')).toHaveTextContent(UPL_EXEMPTION_DISCLAIMER);
  });

  it('presses and unpresses "not claiming"', async () => {
    serve(record());
    renderPage();
    await ready();
    const button = screen.getByRole('button', { name: EXEMPTIONS_NOT_CLAIMING_BUTTON });
    expect(button).toHaveAttribute('aria-pressed', 'false');
    await userEvent.click(button);
    expect(button).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(button);
    expect(button).toHaveAttribute('aria-pressed', 'false');
  });

  it("line 3's No hides and clears line 3-1", async () => {
    const sent = serve(record());
    renderPage();
    await ready();
    await userEvent.click(radio(EXEMPTIONS_LINE_1_QUESTION, EXEMPTIONS_LINE_1_WORDS.federal));
    await userEvent.click(screen.getByRole('button', { name: EXEMPTIONS_NOT_CLAIMING_BUTTON }));
    await userEvent.click(radio(EXEMPTIONS_LINE_3_QUESTION, 'Yes'));
    await userEvent.click(radio(EXEMPTIONS_LINE_3_1_QUESTION, 'Yes'));
    await userEvent.click(radio(EXEMPTIONS_LINE_3_QUESTION, 'No'));
    expect(
      screen.queryByRole('group', { name: (n) => n.startsWith(EXEMPTIONS_LINE_3_1_QUESTION) })
    ).not.toBeInTheDocument();
    await pressContinue();
    await screen.findByText('Statement of Financial Affairs');
    expect(sent[0].line_3_1).toBeNull();
  });

  it('holds Continue while a gap stands and names the first gap in a status region, never an alert', async () => {
    serve(record());
    renderPage();
    await ready();
    await userEvent.click(radio(EXEMPTIONS_LINE_1_QUESTION, EXEMPTIONS_LINE_1_WORDS.federal));
    const status = screen.getByRole('status');
    expect(status).toHaveTextContent(EXEMPTION_GAP_NO_ITEMS);
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('names line 1 first when only "not claiming" is pressed', async () => {
    serve(record());
    renderPage();
    await ready();
    await userEvent.click(screen.getByRole('button', { name: EXEMPTIONS_NOT_CLAIMING_BUTTON }));
    expect(screen.getByRole('status')).toHaveTextContent(EXEMPTION_GAP_LINE_1);
  });

  it('saves the answers and goes to the SOFA step', async () => {
    const sent = serve(record());
    renderPage();
    await ready();
    await userEvent.click(
      radio(EXEMPTIONS_LINE_1_QUESTION, EXEMPTIONS_LINE_1_WORDS.state_and_federal)
    );
    await userEvent.click(screen.getByRole('button', { name: EXEMPTIONS_NOT_CLAIMING_BUTTON }));
    await userEvent.click(radio(EXEMPTIONS_LINE_3_QUESTION, 'No'));
    await pressContinue();
    await screen.findByText('Statement of Financial Affairs');
    expect(sent).toEqual([
      { line_1: 'state_and_federal', line_3: 'no', line_3_1: null, no_claims: true },
    ]);
  });

  it('keeps the filer on the page when the save fails', async () => {
    serve(record(), 400);
    renderPage();
    await ready();
    await userEvent.click(radio(EXEMPTIONS_LINE_1_QUESTION, EXEMPTIONS_LINE_1_WORDS.federal));
    await userEvent.click(screen.getByRole('button', { name: EXEMPTIONS_NOT_CLAIMING_BUTTON }));
    await userEvent.click(radio(EXEMPTIONS_LINE_3_QUESTION, 'No'));
    await pressContinue();
    expect(await screen.findByRole('alert')).toHaveTextContent(EXEMPTIONS_SAVE_FAILED);
    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
  });

  it('says so in place of the laws when no list of laws is in force', async () => {
    serve(record({ catalog: null, catalog_gap: 'no_table' }));
    renderPage();
    await ready();
    expect(screen.getByText(EXEMPTIONS_NO_TABLE)).toBeInTheDocument();
  });
});
