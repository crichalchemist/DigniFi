/**
 * Line 43's AI polish (3h4 spec sections 8 and 14, plan rulings R11-R13, R19, R21, R22): a filer may
 * ask an AI service to rewrite their explanation more clearly, after a consent that names the
 * vendor. Business intent: nothing is sent before the filer agrees, nothing the service wrote goes
 * with a save until the filer approves it, their own words stay beside an approved rewrite and can
 * come back, and a service that fails or is missing never blocks the guided draft.
 */
import { act, cleanup, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { server } from '../../test/mocks/server';
import {
  MEANS_EXPLANATION_TOO_LONG,
  MEANS_LINE_43_ASSEMBLE,
  MEANS_LINE_43_LABEL_HAPPENED,
  MEANS_LINE_43_LEGEND,
  MEANS_LINE_43_REMOVE,
  MEANS_POLISH_APPROVE,
  MEANS_POLISH_BLANK,
  MEANS_POLISH_CONSENT_HEADING,
  MEANS_POLISH_CONSENT_KEEP,
  MEANS_POLISH_CONSENT_RETENTION,
  MEANS_POLISH_CONSENT_WHAT,
  MEANS_POLISH_DECLINE,
  MEANS_POLISH_DISCLOSURE,
  MEANS_POLISH_HOLDS_REWRITE,
  MEANS_POLISH_IDENTIFIER,
  MEANS_POLISH_KEEP,
  MEANS_POLISH_KEPT,
  MEANS_POLISH_NO_REWRITE,
  MEANS_POLISH_PHRASE,
  MEANS_POLISH_RESTORE,
  MEANS_POLISH_REWRITE_LABEL,
  MEANS_POLISH_SEND,
  MEANS_POLISH_SENT_LABEL,
  MEANS_POLISH_TOO_MANY,
  MEANS_POLISH_UNAVAILABLE,
  MEANS_POLISH_WORKING,
  MEANS_POLISH_APPROVED,
} from '../../constants/copy';
import {
  POLISH_URL,
  circumstance,
  line43Page,
  polishName,
  pressContinue,
  radio,
  ready,
  renderPage,
  serve,
  servePolish,
} from './meansTestPageHelpers';

const area = (name: string) =>
  document.querySelector(`textarea[name="${name}"]`) as HTMLTextAreaElement;
const box = (index = 0) => area(`means_line_43_${index}_explanation`);
const line43 = () => document.getElementById('line-43') as HTMLElement;
const polishButton = (n = 1) => screen.getByRole('button', { name: polishName(n) });
const consentGroup = () => screen.queryByRole('group', { name: MEANS_POLISH_CONSENT_HEADING });
const rewriteBox = () => screen.queryByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL });
const press = (name: string) => userEvent.click(screen.getByRole('button', { name }));
const assembleName = (n: number) =>
  `${MEANS_LINE_43_ASSEMBLE} ${MEANS_LINE_43_LEGEND.split('{n}').join(String(n))}`;

/** Ask for a rewrite, agree if asked, and wait for the review to arrive */
async function polishFirstRow() {
  await userEvent.click(polishButton());
  if (consentGroup() !== null) await press(MEANS_POLISH_SEND);
  await screen.findByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL });
}

/** Let a held reply land and every state update behind it settle */
const drain = (release: () => void) =>
  act(async () => {
    release();
    await new Promise((resolve) => setTimeout(resolve, 20));
  });

const pageWith = (...rows: Parameters<typeof circumstance>[0][]) =>
  line43Page(rows.map((row) => circumstance(row)));

afterEach(() => {
  vi.restoreAllMocks();
});

describe('line 43 AI polish', () => {
  it('the polish button is drawn only when the page says the polish is available', async () => {
    servePolish();
    serve({ ...pageWith({ explanation: 'Demo words' }), polish_available: false });
    renderPage();
    await ready();
    expect(box()).not.toBeNull();
    expect(screen.queryByRole('button', { name: /Rewrite this with an AI service/ })).toBeNull();
  });

  it('the first press asks for consent and sends nothing until the filer agrees', async () => {
    const polished = servePolish();
    serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();

    await userEvent.click(polishButton());
    expect(consentGroup()).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: MEANS_POLISH_CONSENT_HEADING })).toHaveFocus();
    // The panel names the vendor, states the dated retention, and says what stays with the filer
    const panel = within(consentGroup() as HTMLElement);
    expect(panel.getByText(MEANS_POLISH_CONSENT_WHAT)).toBeInTheDocument();
    expect(panel.getByText(MEANS_POLISH_CONSENT_RETENTION)).toBeInTheDocument();
    expect(panel.getByText(MEANS_POLISH_CONSENT_KEEP)).toBeInTheDocument();
    expect(polished).toHaveLength(0);

    await press(MEANS_POLISH_DECLINE);
    expect(consentGroup()).toBeNull();
    expect(box()).toHaveValue('Demo words');
    expect(polishButton()).toHaveFocus();
    expect(polished).toHaveLength(0);
  });

  it("agreeing sends only the box's trimmed text, once", async () => {
    const polished = servePolish();
    serve(pageWith({ explanation: '  Demo words \n' }));
    renderPage();
    await ready();
    await polishFirstRow();
    expect(polished).toEqual([{ explanation: 'Demo words' }]);
  });

  it('a failed request is not sent again on its own', async () => {
    const polished = servePolish({ status: 503, body: { error: MEANS_POLISH_UNAVAILABLE } });
    serve(pageWith({ explanation: '  Demo words \n' }));
    renderPage();
    await ready();
    await userEvent.click(polishButton());
    await press(MEANS_POLISH_SEND);
    expect(await screen.findByText(MEANS_POLISH_UNAVAILABLE)).toBeInTheDocument();
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });
    expect(polished).toHaveLength(1);
  });

  it('consent given on one circumstance covers the next, and toggling line 43 to No and back asks again', async () => {
    const polished = servePolish();
    serve(pageWith({ explanation: 'Demo first' }, { explanation: 'Demo second' }));
    renderPage();
    await ready();

    await userEvent.click(polishButton(1));
    await press(MEANS_POLISH_SEND);
    await screen.findByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL });
    await press(MEANS_POLISH_KEEP);
    expect(polished).toHaveLength(1);

    await userEvent.click(polishButton(2));
    expect(consentGroup()).toBeNull();
    await screen.findByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL });
    expect(polished).toHaveLength(2);
    await press(MEANS_POLISH_KEEP);

    await userEvent.click(radio('means_line_43', 'no'));
    await userEvent.click(radio('means_line_43', 'yes'));
    await userEvent.click(polishButton(1));
    expect(consentGroup()).toBeInTheDocument();
    expect(polished).toHaveLength(2);
  });

  it('the rewrite shows beside what was sent with the disclosure, and the box is unchanged and disabled', async () => {
    servePolish();
    serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();
    await polishFirstRow();

    const sentBox = screen.getByRole('textbox', { name: MEANS_POLISH_SENT_LABEL });
    const rewrite = screen.getByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL });
    expect(sentBox).toHaveValue('Demo words');
    expect(sentBox).toHaveAttribute('readonly');
    expect(rewrite).toHaveValue('Demo rewrite words');
    const described = document.getElementById(rewrite.getAttribute('aria-describedby') ?? '');
    expect(described).toHaveTextContent(MEANS_POLISH_DISCLOSURE);
    expect(box()).toHaveValue('Demo words');
    expect(box()).toBeDisabled();
  });

  it('an unapproved rewrite never goes with a save', async () => {
    servePolish();
    const saved = serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();
    await polishFirstRow();

    await pressContinue();
    await waitFor(() => expect(saved).toHaveLength(1));
    const rows = saved[0].line_43_circumstances as Record<string, unknown>[];
    expect(rows[0].explanation).toBe('Demo words');
    expect(rows[0].original_explanation).toBeNull();
    expect(JSON.stringify(saved[0])).not.toContain('Demo rewrite words');
  });

  it("approving puts the edited rewrite in the box and keeps the filer's words beside it", async () => {
    servePolish();
    const saved = serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();
    await polishFirstRow();

    const rewrite = screen.getByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL });
    await userEvent.clear(rewrite);
    await userEvent.type(rewrite, 'Demo rewrite words, edited');
    await press(MEANS_POLISH_APPROVE);

    expect(box()).toHaveValue('Demo rewrite words, edited');
    expect(box()).toBeEnabled();
    expect(rewriteBox()).toBeNull();
    expect(screen.getByText(MEANS_POLISH_APPROVED)).toHaveAttribute('role', 'status');
    await pressContinue();
    await waitFor(() => expect(saved).toHaveLength(1));
    const rows = saved[0].line_43_circumstances as Record<string, unknown>[];
    expect(rows[0].explanation).toBe('Demo rewrite words, edited');
    expect(rows[0].original_explanation).toBe('Demo words');
  });

  it('polishing twice keeps the first original', async () => {
    servePolish();
    const saved = serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();
    await polishFirstRow();
    expect(screen.getByRole('textbox', { name: MEANS_POLISH_SENT_LABEL })).toHaveValue(
      'Demo words'
    );
    await press(MEANS_POLISH_APPROVE);

    const second = servePolish({ body: { rewrite: 'Demo second rewrite' } });
    await userEvent.click(polishButton());
    expect(consentGroup()).toBeNull();
    await screen.findByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL });
    expect(second).toEqual([{ explanation: 'Demo rewrite words' }]);
    expect(screen.getByRole('textbox', { name: MEANS_POLISH_SENT_LABEL })).toHaveValue(
      'Demo rewrite words'
    );
    await press(MEANS_POLISH_APPROVE);
    expect(box()).toHaveValue('Demo second rewrite');

    await pressContinue();
    await waitFor(() => expect(saved).toHaveLength(1));
    const rows = saved[0].line_43_circumstances as Record<string, unknown>[];
    expect(rows[0].original_explanation).toBe('Demo words');
  });

  it("my own words can't be put back while a second review is open, so approving never records AI text as mine", async () => {
    servePolish();
    const saved = serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();
    await polishFirstRow();
    await press(MEANS_POLISH_APPROVE);

    servePolish({ body: { rewrite: 'Demo second rewrite' } });
    await userEvent.click(polishButton());
    await screen.findByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL });
    const restore = screen.getByRole('button', { name: MEANS_POLISH_RESTORE });
    expect(restore).toBeDisabled();
    await userEvent.click(restore);
    expect(screen.getByText(MEANS_POLISH_HOLDS_REWRITE)).toBeInTheDocument();

    await press(MEANS_POLISH_APPROVE);
    expect(screen.getByRole('button', { name: MEANS_POLISH_RESTORE })).toBeEnabled();
    await pressContinue();
    await waitFor(() => expect(saved).toHaveLength(1));
    const rows = saved[0].line_43_circumstances as Record<string, unknown>[];
    expect(rows[0].explanation).toBe('Demo second rewrite');
    expect(rows[0].original_explanation).toBe('Demo words');
  });

  it('the page says the box holds a rewrite and puts my own words back', async () => {
    servePolish();
    const saved = serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();
    expect(screen.queryByText(MEANS_POLISH_HOLDS_REWRITE)).toBeNull();
    await polishFirstRow();
    expect(screen.queryByText(MEANS_POLISH_HOLDS_REWRITE)).toBeNull();
    await press(MEANS_POLISH_APPROVE);
    expect(screen.getByText(MEANS_POLISH_HOLDS_REWRITE)).toBeInTheDocument();

    await press(MEANS_POLISH_RESTORE);
    expect(box()).toHaveValue('Demo words');
    expect(screen.queryByText(MEANS_POLISH_HOLDS_REWRITE)).toBeNull();
    await pressContinue();
    await waitFor(() => expect(saved).toHaveLength(1));
    const rows = saved[0].line_43_circumstances as Record<string, unknown>[];
    expect(rows[0].explanation).toBe('Demo words');
    expect(rows[0].original_explanation).toBeNull();
  });

  it('keeping my words closes the review and changes nothing', async () => {
    servePolish();
    serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();
    await polishFirstRow();

    await press(MEANS_POLISH_KEEP);
    expect(rewriteBox()).toBeNull();
    expect(box()).toHaveValue('Demo words');
    expect(box()).toBeEnabled();
    expect(screen.getByText(MEANS_POLISH_KEPT)).toHaveAttribute('role', 'status');
    expect(screen.queryByText(MEANS_POLISH_HOLDS_REWRITE)).toBeNull();
    expect(polishButton()).toHaveFocus();
  });

  it('emptying the box after approval drops the stored original', async () => {
    servePolish();
    const saved = serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();
    await polishFirstRow();
    await press(MEANS_POLISH_APPROVE);
    expect(screen.getByText(MEANS_POLISH_HOLDS_REWRITE)).toBeInTheDocument();

    await userEvent.clear(box());
    expect(screen.queryByText(MEANS_POLISH_HOLDS_REWRITE)).toBeNull();
    await pressContinue();
    await waitFor(() => expect(saved).toHaveLength(1));
    const rows = saved[0].line_43_circumstances as Record<string, unknown>[];
    expect(rows[0].original_explanation).toBeNull();
  });

  it('removing a circumstance mid-request shows no stale rewrite', async () => {
    let release!: () => void;
    const hold = new Promise<void>((resolve) => {
      release = resolve;
    });
    servePolish({ hold });
    serve(pageWith({ explanation: 'Demo words' }));
    // The abort is the only thing that calls the request off; the page without it shows the same
    // empty screen, so the count is asserted, never inferred
    const abort = vi.spyOn(AbortController.prototype, 'abort');
    const error = vi.spyOn(console, 'error');
    renderPage();
    await ready();

    await userEvent.click(polishButton());
    await press(MEANS_POLISH_SEND);
    expect(screen.getByText(MEANS_POLISH_WORKING)).toHaveAttribute('role', 'status');
    const before = abort.mock.calls.length;
    await press(MEANS_LINE_43_REMOVE.split('{n}').join('1'));
    expect(abort.mock.calls.length).toBeGreaterThan(before);

    await drain(release);
    expect(rewriteBox()).toBeNull();
    expect(box()).toBeNull();
    expect(error).not.toHaveBeenCalled();
  });

  it('leaving line 43 mid-request asks for consent again and shows no rewrite', async () => {
    let release!: () => void;
    const hold = new Promise<void>((resolve) => {
      release = resolve;
    });
    const polished = servePolish({ hold });
    serve(pageWith({ explanation: 'Demo words' }));
    const abort = vi.spyOn(AbortController.prototype, 'abort');
    renderPage();
    await ready();

    await userEvent.click(polishButton());
    await press(MEANS_POLISH_SEND);
    await waitFor(() => expect(polished).toHaveLength(1));
    const before = abort.mock.calls.length;
    await userEvent.click(radio('means_line_43', 'no'));
    expect(abort.mock.calls.length).toBeGreaterThan(before);

    await drain(release);
    await userEvent.click(radio('means_line_43', 'yes'));
    expect(rewriteBox()).toBeNull();
    expect(screen.queryByText(MEANS_POLISH_WORKING)?.textContent ?? '').toBe('');
    await userEvent.click(polishButton());
    expect(consentGroup()).toBeInTheDocument();
    expect(polished).toHaveLength(1);
  });

  it('leaving the page mid-request calls the request off', async () => {
    let release!: () => void;
    const hold = new Promise<void>((resolve) => {
      release = resolve;
    });
    const polished = servePolish({ hold });
    serve(pageWith({ explanation: 'Demo words' }));
    const abort = vi.spyOn(AbortController.prototype, 'abort');
    renderPage();
    await ready();

    await userEvent.click(polishButton());
    await press(MEANS_POLISH_SEND);
    await waitFor(() => expect(polished).toHaveLength(1));
    const before = abort.mock.calls.length;
    cleanup();
    expect(abort.mock.calls.length).toBeGreaterThan(before);
    await drain(release);
  });

  // MEANS_EXPLANATION_TOO_LONG can't be reached from the browser (the box stops at 2,000), but the
  // server may say it
  it.each([
    ['holds an identifier', MEANS_POLISH_IDENTIFIER],
    ['holds a phrase that is not sent', MEANS_POLISH_PHRASE],
    ['is blank', MEANS_POLISH_BLANK],
    ['is too long', MEANS_EXPLANATION_TOO_LONG],
  ])(
    'a refused request (%s) shows its sentence beside the box and leaves the box as it was',
    async (_case, sentence) => {
      servePolish({ status: 400, body: { explanation: [sentence] } });
      serve(pageWith({ explanation: 'Demo words' }));
      renderPage();
      await ready();
      await userEvent.click(polishButton());
      await press(MEANS_POLISH_SEND);

      expect(await screen.findByText(sentence)).toBeInTheDocument();
      expect(box().closest('.form-field')).toHaveTextContent(sentence);
      expect(box()).toHaveValue('Demo words');
      expect(box()).toBeEnabled();
      expect(consentGroup()).toBeNull();
      expect(rewriteBox()).toBeNull();
      expect(screen.queryByText(MEANS_POLISH_UNAVAILABLE)).toBeNull();
    }
  );

  it.each([
    [
      'the service gave nothing to show',
      422,
      { error: MEANS_POLISH_NO_REWRITE },
      MEANS_POLISH_NO_REWRITE,
    ],
    [
      'the filer asked too quickly',
      429,
      { detail: 'Request was throttled.' },
      MEANS_POLISH_TOO_MANY,
    ],
    [
      'the service is unavailable',
      503,
      { error: MEANS_POLISH_UNAVAILABLE },
      MEANS_POLISH_UNAVAILABLE,
    ],
  ])(
    'a service failure (%s) shows one sentence and the guided draft still works',
    async (_case, status, body, sentence) => {
      servePolish({ status, body });
      const page = pageWith({ explanation: 'Demo words', happened: 'Demo layoff in May' });
      const saved = serve(page);
      renderPage();
      await ready();
      await userEvent.click(polishButton());
      await press(MEANS_POLISH_SEND);

      expect(await screen.findByText(sentence)).toBeInTheDocument();
      expect(within(line43()).getByRole('alert')).toHaveTextContent(sentence);
      expect(box()).toHaveValue('Demo words');
      expect(rewriteBox()).toBeNull();

      // the guided draft: empty the box, press the assemble button, save
      await userEvent.clear(box());
      await press(assembleName(1));
      expect(box().value).toContain(`${MEANS_LINE_43_LABEL_HAPPENED} Demo layoff in May`);
      await pressContinue();
      await waitFor(() => expect(saved).toHaveLength(1));
      const rows = saved[0].line_43_circumstances as { explanation: string }[];
      expect(rows[0].explanation).toContain('Demo layoff in May');
    }
  );

  it('focus moves to the rewrite on arrival and back to the box on approval', async () => {
    servePolish();
    serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();
    await polishFirstRow();
    await waitFor(() =>
      expect(screen.getByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL })).toHaveFocus()
    );

    await press(MEANS_POLISH_APPROVE);
    expect(box()).toHaveFocus();
  });

  it('the polish controls carry the names the journeys will use', async () => {
    servePolish();
    serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();
    expect(document.getElementById('means-line-43-0-polish')).toBe(polishButton());
    await polishFirstRow();
    expect(area('means_line_43_0_rewrite')).toBe(
      screen.getByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL })
    );
    expect(area('means_line_43_0_sent')).toBe(
      screen.getByRole('textbox', { name: MEANS_POLISH_SENT_LABEL })
    );
  });

  it('two circumstances can have rewrites pending at once and each approval touches only its row', async () => {
    server.use(
      http.post(POLISH_URL, async ({ request }) => {
        const { explanation } = (await request.json()) as { explanation: string };
        return HttpResponse.json({ rewrite: `Demo rewrite of ${explanation}` });
      })
    );
    const saved = serve(pageWith({ explanation: 'Demo first' }, { explanation: 'Demo second' }));
    renderPage();
    await ready();

    await userEvent.click(polishButton(1));
    await press(MEANS_POLISH_SEND);
    await waitFor(() => expect(rewriteBox()).not.toBeNull());
    await userEvent.click(polishButton(2));
    await waitFor(() =>
      expect(screen.getAllByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL })).toHaveLength(2)
    );
    expect(box(0)).toBeDisabled();
    expect(box(1)).toBeDisabled();

    await userEvent.click(screen.getAllByRole('button', { name: MEANS_POLISH_APPROVE })[1]);
    expect(box(1)).toHaveValue('Demo rewrite of Demo second');
    expect(box(1)).toBeEnabled();
    expect(box(0)).toHaveValue('Demo first');
    expect(box(0)).toBeDisabled();
    expect(screen.getAllByRole('textbox', { name: MEANS_POLISH_REWRITE_LABEL })).toHaveLength(1);

    await pressContinue();
    await waitFor(() => expect(saved).toHaveLength(1));
    const rows = saved[0].line_43_circumstances as Record<string, unknown>[];
    expect(rows[0]).toMatchObject({ explanation: 'Demo first', original_explanation: null });
    expect(rows[1]).toMatchObject({
      explanation: 'Demo rewrite of Demo second',
      original_explanation: 'Demo second',
    });
  });

  it('a stored original from an earlier visit shows the sentence and goes back unchanged', async () => {
    servePolish();
    const saved = serve(
      pageWith({ explanation: 'Demo rewrite words', original_explanation: 'Demo words' })
    );
    renderPage();
    await ready();
    expect(screen.getByText(MEANS_POLISH_HOLDS_REWRITE)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: MEANS_POLISH_RESTORE })).toBeInTheDocument();
    expect(screen.queryByText(MEANS_POLISH_APPROVED)).toBeNull();

    await pressContinue();
    await waitFor(() => expect(saved).toHaveLength(1));
    const rows = saved[0].line_43_circumstances as Record<string, unknown>[];
    expect(rows[0]).toMatchObject({
      explanation: 'Demo rewrite words',
      original_explanation: 'Demo words',
    });
  });

  it('a stored original still shows its sentence and its way back when no service is set up', async () => {
    servePolish();
    const saved = serve({
      ...pageWith({ explanation: 'Demo rewrite words', original_explanation: 'Demo words' }),
      polish_available: false,
    });
    renderPage();
    await ready();
    expect(screen.queryByRole('button', { name: /Rewrite this with an AI service/ })).toBeNull();
    expect(screen.getByText(MEANS_POLISH_HOLDS_REWRITE)).toBeInTheDocument();

    await press(MEANS_POLISH_RESTORE);
    expect(box()).toHaveValue('Demo words');
    expect(box()).toHaveFocus();
    expect(screen.queryByText(MEANS_POLISH_HOLDS_REWRITE)).toBeNull();
    await pressContinue();
    await waitFor(() => expect(saved).toHaveLength(1));
    const rows = saved[0].line_43_circumstances as Record<string, unknown>[];
    expect(rows[0]).toMatchObject({ explanation: 'Demo words', original_explanation: null });
  });

  it('after approval the assemble button fills nothing until the box is emptied', async () => {
    servePolish();
    serve(pageWith({ explanation: 'Demo words' }));
    renderPage();
    await ready();
    await polishFirstRow();
    await press(MEANS_POLISH_APPROVE);

    // an answer in an aid box, since the draft is empty while all four are blank
    await userEvent.type(area('means_line_43_0_happened'), 'Demo layoff in May');
    await press(assembleName(1));
    expect(box()).toHaveValue('Demo rewrite words');

    await userEvent.clear(box());
    await press(assembleName(1));
    expect(box().value).toContain('Demo layoff in May');
  });
});
