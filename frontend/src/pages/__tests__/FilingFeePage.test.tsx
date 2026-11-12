/**
 * The filing-fee page asks every filer Form 101 line 8 after Complete (3f spec §6). It shows the
 * court's limit and the filer's own figure as information, never a verdict, and it never decides
 * for the filer. Under the waiver it asks 103B lines 4, 5, 7 and 9.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { FilingFeePage } from '../FilingFeePage';
import { FILING_FEE_TEXT_LIMITS } from '../../constants/filingFee';
import {
  FEE_LAW_SENTENCE,
  PAYMENT_CHOICE_WORDS,
  WAIVER_LINE_4_QUESTION,
  WAIVER_LINE_5_QUESTION,
  WAIVER_LINE_7_QUESTION,
  WAIVER_LINE_9_QUESTION,
} from '../../constants/formText';
import {
  FEE_CHOICE_MISSING,
  FEE_COURT_DECIDES,
  FEE_INCOME_GAP,
  FEE_LINE_5_NOTE,
  FEE_NO_TABLE,
  FEE_OTHER_LINES_NOTE,
  FEE_READ_FAILED,
  FEE_SAVE_FAILED,
  FORM_103A_LINK,
  FORM_103A_URL,
  INSTALLMENTS_NOTICE,
} from '../../constants/copy';
import { UPL_WIZARD_DISCLAIMER } from '../../constants/upl';
import type { FilingFee, FilingFeeInformation, PaymentChoice } from '../../types/api';

const URL = 'http://localhost:8000/api/intake/sessions/:id/filing-fee/';

const GUIDELINE = {
  year: 2026,
  effective_date: '2026-01-15',
  source_url:
    'https://www.federalregister.gov/documents/2026/01/15/2026-00755/annual-update-of-the-hhs-poverty-guidelines',
};
// Sarah: a family of 1, below the limit. James: a family of 1, above it.
const SARAH: FilingFeeInformation = {
  family_size: 1,
  limit_monthly: '1995.00',
  guideline: GUIDELINE,
  family_income_monthly: '1750.00',
};
const JAMES: FilingFeeInformation = { ...SARAH, family_income_monthly: '4500.00' };

function record(overrides: Partial<FilingFee> = {}): FilingFee {
  return {
    payment_choice: null,
    income_change_answer: null,
    income_change_explanation: '',
    installments_explanation: '',
    others_covered_answer: null,
    others_covered_who: '',
    expense_change_answer: null,
    expense_change_explanation: '',
    information: SARAH,
    information_gap: null,
    ...overrides,
  };
}

/** Serves `saved` and records each body the page PUTs */
function serve(saved: FilingFee) {
  const sent: Record<string, unknown>[] = [];
  server.use(
    http.get(URL, () => HttpResponse.json(saved)),
    http.put(URL, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      sent.push(body);
      return HttpResponse.json({ ...saved, ...body });
    })
  );
  return sent;
}

function renderPage() {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter initialEntries={['/filing-fee']}>
      <IntakeProvider>
        <Routes>
          <Route path="/filing-fee" element={<FilingFeePage />} />
          <Route path="/exemptions" element={<div>The property you claim as exempt</div>} />
          <Route path="/intake" element={<div>IntakeWizard</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

const choice = (c: PaymentChoice) => screen.findByRole('radio', { name: PAYMENT_CHOICE_WORDS[c] });
const group = (legend: string) => screen.getByRole('group', { name: legend });
const pressContinue = () => userEvent.click(screen.getByRole('button', { name: 'Continue' }));

describe('FilingFeePage', () => {
  it('asks Form 101 line 8 in its own words with nothing chosen', async () => {
    serve(record());
    renderPage();
    expect(
      await screen.findByRole('heading', { level: 1, name: 'How you will pay the filing fee' })
    ).toBeInTheDocument();
    for (const c of ['pay_in_full', 'installments', 'waiver'] as const) {
      expect(await choice(c)).not.toBeChecked();
    }
    expect(screen.getByText(FEE_LAW_SENTENCE)).toBeInTheDocument();
  });

  it("every filer sees the information-not-advice disclaimer beside the court's limit", async () => {
    serve(record());
    renderPage();
    const note = await screen.findByRole('note');
    expect(note).toHaveTextContent(UPL_WIZARD_DISCLAIMER);
  });

  it("shows the court's limit and the family's own figure, and the court decides", async () => {
    serve(record());
    renderPage();
    expect(
      await screen.findByText(
        '150% of the official poverty line for a family of 1: $1,995.00 a month.'
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'This comes from the HHS poverty guidelines for 2026, published January 15, 2026.'
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Your family's income, as Form 103B counts it from your answers: $1,750.00 a month."
      )
    ).toBeInTheDocument();
    expect(screen.getByText(FEE_COURT_DECIDES)).toBeInTheDocument();
  });

  it('says the same words whether the figure is below the limit or above it', async () => {
    // [UPL] The page compares nothing for the filer: only the two amounts differ
    const words = async (information: FilingFeeInformation) => {
      serve(record({ information }));
      const { unmount } = renderPage();
      await choice('waiver');
      const text = screen.getByRole('main').textContent ?? '';
      unmount();
      return text;
    };
    const below = await words(SARAH);
    const above = await words(JAMES);
    expect(below.replace('$1,750.00', '$X')).toBe(above.replace('$4,500.00', '$X'));
    expect(below).not.toMatch(/qualif|eligib|you should/i);
  });

  it('with an Income step gap shows no figure, links to the Income step, and still saves', async () => {
    const sent = serve(record({ information: null, information_gap: 'income' }));
    renderPage();
    expect(await screen.findByText(FEE_INCOME_GAP)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go to Income' })).toHaveAttribute(
      'href',
      '/intake?step=income_info'
    );
    expect(screen.getByRole('main').textContent).not.toMatch(/\$/);
    await userEvent.click(await choice('pay_in_full'));
    await pressContinue();
    await screen.findByText('The property you claim as exempt');
    expect(sent).toEqual([{ payment_choice: 'pay_in_full' }]);
  });

  it('with no poverty table in force says so, shows no old limit, and still saves', async () => {
    const sent = serve(record({ information: null, information_gap: 'no_table' }));
    renderPage();
    expect(await screen.findByText(FEE_NO_TABLE)).toBeInTheDocument();
    expect(screen.queryByText(/poverty line for a family of/)).not.toBeInTheDocument();
    await userEvent.click(await choice('waiver'));
    await pressContinue();
    await screen.findByText('The property you claim as exempt');
    expect(sent).toHaveLength(1);
  });

  it('refuses Continue until the filer chooses, and sends nothing', async () => {
    const sent = serve(record());
    renderPage();
    await choice('pay_in_full');
    await pressContinue();
    expect(await screen.findByRole('alert')).toHaveTextContent(FEE_CHOICE_MISSING);
    expect(sent).toHaveLength(0);
    expect(screen.queryByText('The property you claim as exempt')).not.toBeInTheDocument();
  });

  it('saves the choice and goes on to the exemptions page', async () => {
    const sent = serve(record());
    renderPage();
    await userEvent.click(await choice('installments'));
    await pressContinue();
    await screen.findByText('The property you claim as exempt');
    expect(sent).toEqual([{ payment_choice: 'installments' }]);
  });

  it('under installments says where to get Form 103A, and under the other answers it does not', async () => {
    serve(record());
    renderPage();
    await userEvent.click(await choice('pay_in_full'));
    expect(screen.queryByRole('link', { name: FORM_103A_LINK })).not.toBeInTheDocument();
    await userEvent.click(await choice('installments'));
    const link = screen.getByRole('link', { name: FORM_103A_LINK });
    expect(link).toHaveAttribute('href', FORM_103A_URL);
    expect(link.closest('p')).toHaveTextContent(INSTALLMENTS_NOTICE);
    await userEvent.click(await choice('waiver'));
    expect(screen.queryByRole('link', { name: FORM_103A_LINK })).not.toBeInTheDocument();
  });

  it("asks 103B's own questions only under the waiver, with nothing answered", async () => {
    serve(record());
    renderPage();
    await userEvent.click(await choice('pay_in_full'));
    expect(screen.queryByText(WAIVER_LINE_4_QUESTION)).not.toBeInTheDocument();
    await userEvent.click(await choice('waiver'));
    for (const legend of [WAIVER_LINE_4_QUESTION, WAIVER_LINE_7_QUESTION, WAIVER_LINE_9_QUESTION]) {
      for (const radio of within(group(legend)).getAllByRole('radio'))
        expect(radio).not.toBeChecked();
    }
    expect(screen.getByLabelText(WAIVER_LINE_5_QUESTION)).toHaveValue('');
    expect(screen.getByText(FEE_LINE_5_NOTE)).toBeInTheDocument();
    expect(screen.getByText(FEE_OTHER_LINES_NOTE)).toBeInTheDocument();
  });

  it("sends the waiver's answers with the choice, and a Yes's text only under its Yes", async () => {
    const sent = serve(record());
    renderPage();
    await userEvent.click(await choice('waiver'));
    await userEvent.click(
      within(group(WAIVER_LINE_4_QUESTION)).getByRole('radio', { name: 'Yes' })
    );
    await userEvent.type(
      within(group(WAIVER_LINE_4_QUESTION)).getByLabelText('Explain.'),
      'My hours were cut in October.'
    );
    await userEvent.type(screen.getByLabelText(WAIVER_LINE_5_QUESTION), 'I have no savings.');
    await userEvent.click(within(group(WAIVER_LINE_7_QUESTION)).getByRole('radio', { name: 'No' }));
    await userEvent.click(within(group(WAIVER_LINE_9_QUESTION)).getByRole('radio', { name: 'No' }));
    await pressContinue();
    await screen.findByText('The property you claim as exempt');
    expect(sent).toEqual([
      {
        payment_choice: 'waiver',
        income_change_answer: 'yes',
        income_change_explanation: 'My hours were cut in October.',
        installments_explanation: 'I have no savings.',
        others_covered_answer: 'no',
        expense_change_answer: 'no',
      },
    ]);
  });

  it('saves a waiver with its questions unanswered, since the forms page names what is missing', async () => {
    const sent = serve(record());
    renderPage();
    await userEvent.click(await choice('waiver'));
    await pressContinue();
    await screen.findByText('The property you claim as exempt');
    expect(sent).toEqual([
      {
        payment_choice: 'waiver',
        income_change_answer: null,
        installments_explanation: '',
        others_covered_answer: null,
        expense_change_answer: null,
      },
    ]);
  });

  it('opens with the saved answers, and moving off the waiver leaves them stored', async () => {
    const saved = record({
      payment_choice: 'waiver',
      income_change_answer: 'no',
      installments_explanation: 'I have no savings.',
      others_covered_answer: 'yes',
      others_covered_who: 'My mother',
      expense_change_answer: 'no',
    });
    const sent = serve(saved);
    renderPage();
    expect(await choice('waiver')).toBeChecked();
    expect(screen.getByLabelText(WAIVER_LINE_5_QUESTION)).toHaveValue('I have no savings.');
    expect(within(group(WAIVER_LINE_7_QUESTION)).getByLabelText('Identify who')).toHaveValue(
      'My mother'
    );
    await userEvent.click(await choice('installments'));
    await pressContinue();
    await screen.findByText('The property you claim as exempt');
    expect(sent).toEqual([{ payment_choice: 'installments' }]);
  });

  it('a filer who typed waiver answers and then chooses installments sends only the choice', async () => {
    // §4: the waiver answers stay stored and come back if the filer picks the waiver again. The
    // page never clears them, so the PUT leaves out every waiver key and the server keeps them.
    const sent = serve(record());
    renderPage();
    await userEvent.click(await choice('waiver'));
    await userEvent.click(
      within(group(WAIVER_LINE_4_QUESTION)).getByRole('radio', { name: 'Yes' })
    );
    await userEvent.type(
      within(group(WAIVER_LINE_4_QUESTION)).getByLabelText('Explain.'),
      'My hours were cut in October.'
    );
    await userEvent.type(screen.getByLabelText(WAIVER_LINE_5_QUESTION), 'I have no savings.');
    await userEvent.click(await choice('installments'));
    await userEvent.click(await choice('waiver'));
    expect(within(group(WAIVER_LINE_4_QUESTION)).getByRole('radio', { name: 'Yes' })).toBeChecked();
    expect(within(group(WAIVER_LINE_4_QUESTION)).getByLabelText('Explain.')).toHaveValue(
      'My hours were cut in October.'
    );
    expect(screen.getByLabelText(WAIVER_LINE_5_QUESTION)).toHaveValue('I have no savings.');
    await userEvent.click(await choice('installments'));
    await pressContinue();
    await screen.findByText('The property you claim as exempt');
    expect(sent).toEqual([{ payment_choice: 'installments' }]);
  });

  it('a waiver picked again shows what was saved under it before', async () => {
    serve(
      record({ payment_choice: 'pay_in_full', installments_explanation: 'I have no savings.' })
    );
    renderPage();
    expect(await choice('pay_in_full')).toBeChecked();
    await userEvent.click(await choice('waiver'));
    expect(screen.getByLabelText(WAIVER_LINE_5_QUESTION)).toHaveValue('I have no savings.');
  });

  it('stops each text at the length its box on the form can print', async () => {
    serve(
      record({
        income_change_answer: 'yes',
        others_covered_answer: 'yes',
        expense_change_answer: 'yes',
      })
    );
    renderPage();
    await userEvent.click(await choice('waiver'));
    const boxes = {
      income_change_explanation: within(group(WAIVER_LINE_4_QUESTION)).getByLabelText('Explain.'),
      installments_explanation: screen.getByLabelText(WAIVER_LINE_5_QUESTION),
      others_covered_who: within(group(WAIVER_LINE_7_QUESTION)).getByLabelText('Identify who'),
      // Line 9 prints "Yes. Explain" with no period
      expense_change_explanation: within(group(WAIVER_LINE_9_QUESTION)).getByLabelText('Explain'),
    };
    for (const [key, box] of Object.entries(boxes)) {
      expect(box).toHaveAttribute(
        'maxLength',
        String(FILING_FEE_TEXT_LIMITS[key as keyof typeof FILING_FEE_TEXT_LIMITS])
      );
    }
  });

  it('shows no question until the saved answers are read, and reads them again on Try again', async () => {
    // A blank page sent over the saved answers would undo them
    let reads = 0;
    server.use(
      http.get(URL, () => {
        reads += 1;
        return reads === 1
          ? HttpResponse.json({ detail: 'Bad request' }, { status: 400 })
          : HttpResponse.json(record({ payment_choice: 'installments' }));
      })
    );
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent(FEE_READ_FAILED);
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await choice('installments')).toBeChecked();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(reads).toBe(2);
  });

  it('says so when the save fails, and keeps the filer on the page', async () => {
    serve(record());
    server.use(
      http.put(URL, () => HttpResponse.json({ payment_choice: ['bad'] }, { status: 400 }))
    );
    renderPage();
    await userEvent.click(await choice('pay_in_full'));
    await pressContinue();
    expect(await screen.findByRole('alert')).toHaveTextContent(FEE_SAVE_FAILED);
    expect(screen.queryByText('The property you claim as exempt')).not.toBeInTheDocument();
  });
});
