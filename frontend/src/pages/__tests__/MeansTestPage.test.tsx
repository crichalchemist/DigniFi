/**
 * The Form 122A-2 page (3h2 spec §8). Business intent: the filer answers every question the form
 * asks in the form's own words, nothing is chosen for them, the result at the top is the form's
 * arithmetic and never a verdict, Continue never leaves on a missing answer or a result that
 * changed under the filer, and a save that fails never loses what they typed.
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { MeansTestPage } from '../MeansTestPage';
import { KESTREL, meansPage, priyaPage } from '../../test/fixtures/meansPage';
import { FORM_122A2_TITLE } from '../../constants/formText';
import {
  AMOUNT_NEGATIVE,
  AMOUNT_NOT_A_NUMBER,
  MEANS_ADD_ROW,
  MEANS_GAP_LINE_3,
  MEANS_GAP_SPOUSE_VEHICLES,
  MEANS_LINE_36_LINK,
  MEANS_LINE_36_OTHER_RULES,
  MEANS_LINE_36_PRODUCT,
  MEANS_LINE_43_LINK,
  MEANS_OUTCOME_ANSWER_PAGE,
  MEANS_OUTCOME_PRESUMPTION,
  MEANS_PAGE_LOADING,
  MEANS_PAGE_READ_FAILED,
  MEANS_PAGE_SAVE_FAILED,
  MEANS_RESULT_CHANGED,
  MEANS_STALE_ANSWERS,
  MEANS_TABLE_MISSING,
  MEANS_TEST_PREVIEW_TITLE,
  MEANS_TOO_LONG,
} from '../../constants/copy';
import { UPL_MEANS_TEST_DISCLAIMER, UPL_WIZARD_DISCLAIMER } from '../../constants/upl';
import type { MeansPage } from '../../types/api';

const URL = 'http://localhost:8000/api/intake/sessions/:id/means-test/';
const SOFA = 'Statement of Financial Affairs';

type Body = Record<string, unknown>;

/** Serve `saved`; each PUT is recorded and answered with `reply` (the saved page by default) */
function serve(
  saved: MeansPage,
  options: { status?: number; reply?: MeansPage; body?: Body } = {}
) {
  const sent: Body[] = [];
  server.use(
    http.get(URL, () => HttpResponse.json(saved)),
    http.put(URL, async ({ request }) => {
      sent.push((await request.json()) as Body);
      if (options.status !== undefined && options.status !== 200) {
        return HttpResponse.json(options.body ?? { detail: 'Bad request' }, {
          status: options.status,
        });
      }
      return HttpResponse.json(options.reply ?? saved);
    })
  );
  return sent;
}

/** Hold the GET until the returned function is called */
function serveHeldRead(saved: MeansPage) {
  let release = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.get(URL, async () => {
      await held;
      return HttpResponse.json(saved);
    })
  );
  return () => release();
}

/** Serve `saved`, holding each PUT until released; the bodies that arrived are recorded */
function serveHeldSave(saved: MeansPage) {
  let release = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  const sent: Body[] = [];
  server.use(
    http.get(URL, () => HttpResponse.json(saved)),
    http.put(URL, async ({ request }) => {
      sent.push((await request.json()) as Body);
      await held;
      return HttpResponse.json(saved);
    })
  );
  return { sent, release: () => release() };
}

function renderPage(entry = '/means-test') {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <IntakeProvider>
        <Routes>
          <Route path="/means-test" element={<MeansTestPage />} />
          <Route path="/sofa" element={<div>{SOFA}</div>} />
          <Route path="/exemptions" element={<div>Exemptions</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

const ready = () => screen.findByRole('heading', { level: 1, name: FORM_122A2_TITLE });
const box = (name: string) => document.querySelector(`input[name="${name}"]`) as HTMLInputElement;
const choice = (name: string, value: string) =>
  document.querySelector(`input[name="${name}"][value="${value}"]`) as HTMLInputElement;
const lineOf = (name: string) => (box(name) ?? choice(name, 'yes')).closest('.means-line');
const gapRegion = () => document.querySelector('main > div[role="status"]') as HTMLElement;
const result = () => screen.getByRole('status', { name: MEANS_TEST_PREVIEW_TITLE });
const pressContinue = () => userEvent.click(screen.getByRole('button', { name: 'Continue' }));
const typeAmount = (name: string, value: string) =>
  fireEvent.change(box(name), { target: { value } });

describe('MeansTestPage', () => {
  it('nothing is selected on load', async () => {
    serve(meansPage());
    renderPage();
    await ready();
    expect(screen.getAllByRole('radio').length).toBeGreaterThan(0);
    expect(screen.queryAllByRole('radio', { checked: true })).toEqual([]);
    for (const input of document.querySelectorAll<HTMLInputElement>('input[type="number"]')) {
      expect(input.value).toBe('');
    }
  });

  it('line 3 shows only for a married filer living together', async () => {
    serve(meansPage());
    const { unmount } = renderPage();
    await ready();
    expect(choice('means_line_3', 'yes')).toBeInTheDocument();
    unmount();

    serve({ ...meansPage(), married_together: false });
    renderPage();
    await ready();
    expect(choice('means_line_3', 'yes')).toBeNull();
  });

  it('line 15 shows only while a vehicle is claimed', async () => {
    serve(meansPage());
    renderPage();
    await ready();
    expect(choice('means_line_15', 'yes')).toBeNull();
    await userEvent.click(choice('means_vehicle_7_claimed', 'yes'));
    expect(choice('means_line_15', 'yes')).toBeInTheDocument();
    await userEvent.click(choice('means_vehicle_7_claimed', 'no'));
    expect(choice('means_line_15', 'yes')).toBeNull();
  });

  it('the Vehicle 1 and 2 choice shows only with more than two claimed vehicles with a loan or lease', async () => {
    const page = meansPage();
    page.answers.spouse_vehicles_answer = 'no';
    page.answers.spouse_loans_answer = 'no';
    page.vehicles = [
      { ref: 'asset-7', name: 'Honda CR-V EX 2021', leased: false },
      { ref: 'asset-8', name: 'Demo leased car', leased: true },
      { ref: 'asset-9', name: 'Demo financed truck', leased: false },
    ];
    page.debts = [
      { ...KESTREL },
      { ...KESTREL, id: 12, ref: 'debt-12', creditor: 'Demo Truck Loan', secured_by: 'asset-9' },
    ];
    page.debt_lines = { 'debt-11': null, 'debt-12': null };
    serve(page);
    renderPage();
    await ready();
    // two claimed, one declined: no choice to make
    await userEvent.click(choice('means_vehicle_7_claimed', 'yes'));
    await userEvent.click(choice('means_vehicle_8_claimed', 'yes'));
    await userEvent.click(choice('means_vehicle_9_claimed', 'no'));
    expect(box('means_vehicle_1')).toBeNull();
    expect(document.querySelector('select[name="means_vehicle_1"]')).toBeNull();

    await userEvent.click(choice('means_vehicle_9_claimed', 'yes'));
    const first = document.querySelector('select[name="means_vehicle_1"]') as HTMLSelectElement;
    const second = document.querySelector('select[name="means_vehicle_2"]') as HTMLSelectElement;
    const names = (select: HTMLSelectElement) =>
      [...select.options].map((option) => option.textContent);
    expect(names(first)).toEqual([
      '',
      'Honda CR-V EX 2021',
      'Demo leased car',
      'Demo financed truck',
    ]);
    expect(first.value).toBe('');

    // Vehicle 2 leaves out the car chosen as Vehicle 1, and the reverse
    await userEvent.selectOptions(first, 'asset-8');
    expect(names(second)).toEqual(['', 'Honda CR-V EX 2021', 'Demo financed truck']);
    await userEvent.selectOptions(second, 'asset-9');
    expect(names(first)).toEqual(['', 'Honda CR-V EX 2021', 'Demo leased car']);
  });

  it("a filer the form doesn't apply to sees no heading before the page moves to /sofa", async () => {
    const headings: string[] = [];
    const observer = new MutationObserver((records) => {
      for (const record of records) {
        record.addedNodes.forEach((node) => {
          if (!(node instanceof HTMLElement)) return;
          if (node.matches('h1, h2, h3, [role="heading"]') || node.querySelector('h1, h2, h3')) {
            headings.push(node.textContent ?? '');
          }
        });
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    const release = serveHeldRead({ ...meansPage(), applies: false });
    renderPage();
    expect(await screen.findByText(MEANS_PAGE_LOADING)).toBeInTheDocument();
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    release();
    await screen.findByText(SOFA);
    observer.disconnect();
    expect(headings).toEqual([]);
  });

  it("shows why the form can't be worked out yet when the server can't say whether it applies", async () => {
    const why = 'Enter your income by source on the Income step.';
    const sent = serve({ ...meansPage(), applies: null, applies_gap: why });
    renderPage();
    await ready();
    expect(within(gapRegion()).getByText(why)).toBeInTheDocument();
    expect(screen.queryAllByRole('radio')).toEqual([]);
    await pressContinue();
    await screen.findByText(SOFA);
    expect(sent).toEqual([]);
  });

  it('a failed read offers Try again, and Try again reads again', async () => {
    server.use(http.get(URL, () => HttpResponse.json({ detail: 'Bad request' }, { status: 400 })));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent(MEANS_PAGE_READ_FAILED);
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    serve(meansPage());
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await ready()).toBeInTheDocument();
    expect(screen.queryByText(MEANS_PAGE_READ_FAILED)).not.toBeInTheDocument();
  });

  it('the information beside each line names its source', async () => {
    serve(meansPage());
    renderPage();
    await ready();
    expect(lineOf('means_line_21')).toHaveTextContent(
      'You entered $1,200.00 on Schedule J line 8.'
    );
    expect(lineOf('means_line_16')).toHaveTextContent(
      'You entered $300.00 for your spouse on Schedule I line 5a.'
    );
    expect(lineOf('means_line_30')).toHaveTextContent(
      "For 4 people, 5% of the IRS food and clothing amounts is $76.00. Line 30 can't be more than that."
    );
  });

  it('a household of one reads 1 person beside line 30', async () => {
    const page = meansPage();
    page.information = { ...page.information!, line_30_people: 1, line_30_cap: '30.00' };
    serve(page);
    renderPage();
    await ready();
    expect(lineOf('means_line_30')).toHaveTextContent(
      "For 1 person, 5% of the IRS food and clothing amounts is $30.00. Line 30 can't be more than that."
    );
    expect(document.body.textContent).not.toContain('1 people');
  });

  it('continue saves what is answered and stays on a gap', async () => {
    const sent = serve(meansPage());
    renderPage();
    await ready();
    typeAmount('means_line_16', '100');
    await pressContinue();
    await waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0].line_16).toBe('100.00');
    expect(sent[0].line_17).toBeNull();
    expect(screen.queryByText(SOFA)).not.toBeInTheDocument();
    expect(within(gapRegion()).getByText(MEANS_GAP_LINE_3)).toBeInTheDocument();
    expect(box('means_line_16').value).toBe('100');
  });

  it('a gap never disables Continue', async () => {
    serve(meansPage());
    renderPage();
    await ready();
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled();
    await userEvent.click(choice('means_line_3', 'no'));
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled();
  });

  it('with no gap and the same result, Continue goes to /sofa', async () => {
    const sent = serve(priyaPage());
    renderPage();
    await ready();
    await pressContinue();
    await screen.findByText(SOFA);
    expect(sent).toHaveLength(1);
  });

  it("a gap only the server names keeps the filer on the page and shows the server's sentence", async () => {
    const sentence = 'Enter the amount for line 16. Enter 0 if you have none.';
    serve(priyaPage(), { reply: priyaPage({ gap: sentence }) });
    renderPage();
    await ready();
    expect(gapRegion().textContent).toBe('');
    await pressContinue();
    expect(await within(gapRegion()).findByText(sentence)).toBeInTheDocument();
    expect(screen.queryByText(SOFA)).not.toBeInTheDocument();
  });

  it('shows the gap beside Continue once anything is answered', async () => {
    serve(meansPage());
    renderPage();
    await ready();
    expect(gapRegion().textContent).toBe('');
    await userEvent.click(choice('means_line_3', 'no'));
    expect(gapRegion()).toHaveTextContent(MEANS_GAP_SPOUSE_VEHICLES);
  });

  it('continue sends one save at a time', async () => {
    const { sent, release } = serveHeldSave(priyaPage());
    renderPage();
    await ready();
    const button = screen.getByRole('button', { name: 'Continue' });
    await userEvent.click(button);
    await waitFor(() => expect(sent).toHaveLength(1));
    expect(button).toBeDisabled();
    await userEvent.click(button);
    for (const radio of screen.getAllByRole('radio')) expect(radio).toBeDisabled();
    expect(sent).toHaveLength(1);
    release();
    await screen.findByText(SOFA);
    expect(sent).toHaveLength(1);
  });

  it('a refused save keeps every answer and says why', async () => {
    serve(priyaPage(), { status: 400 });
    renderPage();
    await ready();
    typeAmount('means_line_17', '5');
    await pressContinue();
    expect(await screen.findByRole('alert')).toHaveTextContent(MEANS_PAGE_SAVE_FAILED);
    expect(screen.queryByText(SOFA)).not.toBeInTheDocument();
    expect(box('means_line_16').value).toBe('2300.00');
    expect(box('means_line_17').value).toBe('5');
    expect(choice('means_line_43', 'no')).toBeChecked();
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled();
  });

  it('a refused save keeps a changed answer, and the next Continue sends what was typed', async () => {
    const sent: Body[] = [];
    let calls = 0;
    server.use(
      http.get(URL, () => HttpResponse.json(priyaPage())),
      http.put(URL, async ({ request }) => {
        sent.push((await request.json()) as Body);
        calls += 1;
        return calls === 1
          ? HttpResponse.json({ detail: 'Bad request' }, { status: 400 })
          : HttpResponse.json(priyaPage());
      })
    );
    renderPage();
    await ready();
    expect(choice('means_line_34', 'no')).toBeChecked();
    await userEvent.click(choice('means_line_34', 'yes'));
    typeAmount('means_line_17', '5');
    await pressContinue();
    expect(await screen.findByRole('alert')).toHaveTextContent(MEANS_PAGE_SAVE_FAILED);
    // The radio stays where the filer put it, not where the page was loaded
    expect(choice('means_line_34', 'yes')).toBeChecked();
    expect(choice('means_line_34', 'no')).not.toBeChecked();
    await pressContinue();
    await waitFor(() => expect(sent).toHaveLength(2));
    expect(sent[1].line_34_answer).toBe('yes');
    expect(String(sent[1].line_17)).toMatch(/^5(\.00)?$/);
  });

  it('a server error keeps every typed answer and says the save failed', async () => {
    serve(priyaPage(), { status: 500 });
    renderPage();
    await ready();
    typeAmount('means_line_17', '5');
    await userEvent.click(choice('means_line_34', 'yes'));
    await pressContinue();
    // withRetry tries four times with 0.5 s, 1 s and 2 s between them
    expect(await screen.findByRole('alert', {}, { timeout: 10000 })).toHaveTextContent(
      MEANS_PAGE_SAVE_FAILED
    );
    expect(screen.queryByText(SOFA)).not.toBeInTheDocument();
    expect(box('means_line_17').value).toBe('5');
    expect(choice('means_line_34', 'yes')).toBeChecked();
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled();
  }, 20000);

  it('a reply that says the form no longer applies moves to /sofa without showing a heading', async () => {
    serve(priyaPage(), { reply: { ...priyaPage(), applies: false } });
    renderPage();
    await ready();
    const headings: string[] = [];
    const observer = new MutationObserver((records) => {
      for (const record of records) {
        record.addedNodes.forEach((node) => {
          if (!(node instanceof HTMLElement)) return;
          if (node.matches('h1, h2, h3, [role="heading"]') || node.querySelector('h1, h2, h3')) {
            headings.push(node.textContent ?? '');
          }
        });
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    await pressContinue();
    await screen.findByText(SOFA);
    observer.disconnect();
    expect(headings).toEqual([]);
  });

  it("a reply that can't say whether the form applies shows why, and Continue goes to /sofa", async () => {
    const why = 'Enter your income by source on the Income step.';
    const sent = serve(priyaPage(), {
      reply: { ...priyaPage(), applies: null, applies_gap: why },
    });
    renderPage();
    await ready();
    await pressContinue();
    await waitFor(() => expect(within(gapRegion()).getByText(why)).toBeInTheDocument());
    expect(screen.queryByText(SOFA)).not.toBeInTheDocument();
    await pressContinue();
    await screen.findByText(SOFA);
    expect(sent).toHaveLength(1);
  });

  it('a mistaken No on line 3 sends no rows, and Yes brings the typed rows back', async () => {
    const sent = serve(priyaPage(), { status: 400 });
    renderPage();
    await ready();
    await userEvent.click(choice('means_line_3', 'no'));
    expect(box('means_line_3_0_purpose')).toBeNull();
    await pressContinue();
    await screen.findByRole('alert');
    expect(sent[0].line_3_answer).toBe('no');
    expect(sent[0].line_3_rows).toEqual([]);
    await userEvent.click(choice('means_line_3', 'yes'));
    expect(box('means_line_3_0_purpose').value).toBe('His payroll taxes withheld from his pay');
    expect(box('means_line_3_0_amount').value).toBe('250.00');
  });

  it("a vehicle's name is shown exactly, even when it holds a replace pattern", async () => {
    const page = meansPage();
    page.vehicles = [{ ref: 'asset-7', name: 'Demo $& car', leased: false }];
    serve(page);
    renderPage();
    await ready();
    expect(lineOf('means_vehicle_7_claimed')).toHaveTextContent('Demo $& car');
    expect(document.body).not.toHaveTextContent('{name}');
  });

  it('shows a box that is too long for the form beside that box', async () => {
    serve(priyaPage(), {
      status: 400,
      body: { line_3_rows: { '0': { purpose: [MEANS_TOO_LONG] } } },
    });
    renderPage();
    await ready();
    await pressContinue();
    const purpose = await waitFor(() => {
      const input = box('means_line_3_0_purpose');
      expect(input).toHaveAccessibleDescription(MEANS_TOO_LONG);
      return input;
    });
    expect(purpose.value).toBe('His payroll taxes withheld from his pay');
    expect(screen.queryByText(MEANS_PAGE_SAVE_FAILED)).not.toBeInTheDocument();

    // Changing that box takes the sentence away
    await userEvent.type(purpose, 's');
    expect(screen.queryByText(MEANS_TOO_LONG)).not.toBeInTheDocument();
  });

  it("an amount the box can't read is shown with its reason and saved as unanswered", async () => {
    const sent = serve(priyaPage(), { reply: priyaPage() });
    renderPage();
    await ready();
    const line16 = box('means_line_16');
    // jsdom never sets badInput, so the box reports it the way a browser does for a lone '-'
    Object.defineProperty(line16, 'validity', { value: { badInput: true }, configurable: true });
    fireEvent.input(line16);
    expect(within(line16.closest('.form-field')!).getByText(AMOUNT_NOT_A_NUMBER)).toBeVisible();
    await pressContinue();
    await waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0].line_16).toBeNull();
    expect(gapRegion()).toHaveTextContent(
      'Enter the amount for line 16. Enter 0 if you have none.'
    );
    expect(screen.queryByText(SOFA)).not.toBeInTheDocument();
  });

  it('a figure the server would refuse stays in its box with its reason, and goes as unanswered', async () => {
    const sent = serve(priyaPage());
    renderPage();
    await ready();
    typeAmount('means_line_16', '-5');
    expect(box('means_line_16').value).toBe('-5');
    expect(
      within(box('means_line_16').closest('.form-field')!).getByText(AMOUNT_NEGATIVE)
    ).toBeVisible();
    await pressContinue();
    await waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0].line_16).toBeNull();
  });

  it.each([
    ['.5', '0.50'],
    ['1e3', '1000.00'],
    ['100.000', '100.00'],
  ])(
    'a number the box takes, such as .5, 1e3 or 100.000, is held and saved to the cent (%s as %s)',
    async (typed, saved) => {
      const sent = serve(priyaPage());
      renderPage();
      await ready();
      typeAmount('means_line_36_payment', typed);
      expect(screen.getByText(/That is \$/)).toBeInTheDocument();
      expect(screen.getByRole('heading', { level: 1, name: FORM_122A2_TITLE })).toBeInTheDocument();
      await pressContinue();
      await waitFor(() => expect(sent).toHaveLength(1));
      expect(sent[0].line_36_payment).toBe(saved);
    }
  );

  it('line 36 shows the debt limits in whole dollars, as the spec prints them', async () => {
    serve(meansPage());
    renderPage();
    await ready();
    expect(
      screen.getByText(
        'Chapter 13 has debt limits (11 U.S.C. section 109(e)). For cases filed on or after April 1, 2025, the limits are $526,700 in unsecured debts and $1,580,125 in secured debts.'
      )
    ).toBeInTheDocument();
  });

  it('the product shows as the payment is typed', async () => {
    const page = priyaPage();
    page.information = { ...page.information!, multiplier: '6.9' };
    serve(page);
    renderPage();
    await ready();
    expect(
      screen.getByText(
        MEANS_LINE_36_PRODUCT.replace('{m}', '6.9')
          .replace('{payment}', '$1,400.00')
          .replace('{product}', '$96.60')
      )
    ).toBeInTheDocument();
    typeAmount('means_line_36_payment', '1000');
    expect(screen.getByText(/That is \$69\.00\./)).toBeInTheDocument();
  });

  it('a new result keeps the filer on the page', async () => {
    const sent = serve(priyaPage({ outcome: 'cannot_work_out' }), {
      reply: priyaPage({ outcome: 'presumption' }),
    });
    renderPage();
    await ready();
    expect(within(result()).getByText(MEANS_OUTCOME_ANSWER_PAGE)).toBeInTheDocument();
    await pressContinue();
    expect(await within(gapRegion()).findByText(MEANS_RESULT_CHANGED)).toBeInTheDocument();
    expect(screen.queryByText(SOFA)).not.toBeInTheDocument();
    expect(within(result()).queryByText(MEANS_OUTCOME_ANSWER_PAGE)).not.toBeInTheDocument();
    expect(within(result()).getByText(MEANS_OUTCOME_PRESUMPTION)).toBeInTheDocument();
    expect(within(result()).getByRole('link', { name: MEANS_LINE_43_LINK })).toBeInTheDocument();
    expect(result()).toHaveFocus();

    await pressContinue();
    await screen.findByText(SOFA);
    expect(sent).toHaveLength(2);
  });

  it('the page names the Form 122A-2 page without a link', async () => {
    serve(meansPage());
    renderPage();
    await ready();
    expect(within(result()).getByText(MEANS_OUTCOME_ANSWER_PAGE)).toBeInTheDocument();
    expect(within(result()).queryByRole('link')).not.toBeInTheDocument();
  });

  it('the link to line 43 shows only with a presumption, and #line-43 focuses its legend', async () => {
    serve(priyaPage());
    const { unmount } = renderPage();
    await ready();
    await userEvent.click(within(result()).getByRole('link', { name: MEANS_LINE_43_LINK }));
    expect(document.querySelector('#line-43 legend')).toHaveFocus();
    unmount();

    serve(priyaPage({ outcome: 'no_presumption' }));
    const second = renderPage();
    await ready();
    expect(within(result()).queryByRole('link')).not.toBeInTheDocument();
    second.unmount();

    serve(priyaPage());
    renderPage('/means-test#line-43');
    await ready();
    await waitFor(() => expect(document.querySelector('#line-43 legend')).toHaveFocus());
  });

  it('shows the stale-answers notice without a link', async () => {
    serve(priyaPage({ debts_answered_on: '2026-09-20' }));
    renderPage();
    await ready();
    const notice = within(result()).getByText(
      MEANS_STALE_ANSWERS.replace('{month}', 'September 2026')
    );
    expect(notice.querySelector('a')).toBeNull();
  });

  it('shows no stale-answers notice in the same month', async () => {
    serve(priyaPage({ debts_answered_on: '2026-10-02' }));
    renderPage();
    await ready();
    expect(
      within(result()).queryByText(/You answered the questions about your secured debts/)
    ).toBeNull();
  });

  it('closes the result with the court sentence only when there are sentences', async () => {
    serve(priyaPage());
    const { unmount } = renderPage();
    await ready();
    const block = result();
    expect(within(block).getAllByText(UPL_MEANS_TEST_DISCLAIMER)).toHaveLength(1);
    expect(block.lastElementChild).toHaveTextContent(UPL_MEANS_TEST_DISCLAIMER);
    unmount();

    serve(priyaPage({ outcome: null }));
    renderPage();
    await ready();
    expect(within(result()).queryByText(UPL_MEANS_TEST_DISCLAIMER)).not.toBeInTheDocument();
  });

  it('offers no eleventh row of line 3, which the server would refuse and the filer could not mend', async () => {
    serve(priyaPage());
    renderPage();
    await ready();
    const add = () => screen.queryByRole('button', { name: MEANS_ADD_ROW });
    for (let row = 1; row < 10; row += 1) {
      await userEvent.click(add()!);
    }
    expect(box('means_line_3_9_purpose')).toBeInTheDocument();
    expect(add()).toBeNull();
  });

  it('puts the stale-answers notice first and the court sentence last when both show', async () => {
    serve(priyaPage({ debts_answered_on: '2026-09-20' }));
    renderPage();
    await ready();
    const block = result();
    expect(block.firstElementChild).toHaveTextContent(
      MEANS_STALE_ANSWERS.replace('{month}', 'September 2026')
    );
    expect(block.lastElementChild).toHaveTextContent(UPL_MEANS_TEST_DISCLAIMER);
  });

  it('with no means test figures, the page asks every question and shows no figure beside a line', async () => {
    const page = priyaPage({
      information: null,
      information_gap: 'no_table',
      outcome: 'cannot_work_out',
      tables_gap: 'IRS expense standards',
    });
    page.answers.line_15_answer = 'yes';
    page.answers.line_15_amount = '9999.00';
    page.answers.line_30_answer = 'yes';
    page.answers.line_30_amount = '9999.00';
    serve(page);
    renderPage();
    await ready();
    expect(within(result()).getByText(MEANS_TABLE_MISSING)).toBeInTheDocument();
    const text = document.querySelector('main')!.textContent ?? '';
    expect(text).not.toMatch(/You entered .* on Schedule [IJ] line/);
    for (const absent of [
      'Your line 7 total',
      'Your line 8 amount',
      'The form allows up to',
      '5% of the IRS food and clothing',
      'public transportation is',
      'That is $',
      'Line 35 comes from',
    ]) {
      expect(text).not.toContain(absent);
    }
    // every question is still asked, and the two cap gaps are left out
    expect(choice('means_line_36', 'yes')).toBeInTheDocument();
    expect(text).toContain(MEANS_LINE_36_OTHER_RULES);
    expect(screen.getByRole('link', { name: MEANS_LINE_36_LINK })).toBeInTheDocument();
    expect(gapRegion().textContent).toBe('');
  });

  it('renders the information-not-advice disclaimer', async () => {
    serve(meansPage());
    const { unmount } = renderPage();
    await ready();
    expect(screen.getByRole('note')).toHaveTextContent(UPL_WIZARD_DISCLAIMER);
    unmount();

    serve({ ...meansPage(), applies: null, applies_gap: 'Enter your income.' });
    renderPage();
    await ready();
    expect(screen.getByRole('note')).toHaveTextContent(UPL_WIZARD_DISCLAIMER);
  });

  it('no label or aria text says overcome, rebut or rebuttal', async () => {
    serve(priyaPage());
    renderPage();
    await ready();
    const words = /overcome|rebut/i;
    // The result's block holds the form's own instructions as body text, so only its aria-label
    // counts; every label, legend and button counts by its words
    const named = [
      ...[...document.querySelectorAll('label, legend, button')].map((e) => e.textContent ?? ''),
      ...[...document.querySelectorAll('[aria-label]')].map((e) => e.getAttribute('aria-label')!),
    ];
    expect(named.length).toBeGreaterThan(10);
    for (const text of named) expect(text).not.toMatch(words);
  });
});
