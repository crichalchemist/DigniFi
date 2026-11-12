/**
 * The exemptions page (3g1 spec §5.4). Business intent: the filer answers Schedule C's line 1,
 * line 3 and "not claiming" in the form's words, nothing is chosen for them, Continue waits on the
 * first gap, and a save that fails never sends them on.
 */
import { fireEvent, render, screen, within } from '@testing-library/react';
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
import { AMOUNT_NEGATIVE, AMOUNT_TOO_LARGE } from '../../constants/copy';
import {
  EXEMPTIONS_ADD_CLAIM,
  EXEMPTIONS_ANOTHER_LAW,
  EXEMPTIONS_AMOUNT_LABEL,
  EXEMPTIONS_CHOOSE_ONE,
  EXEMPTIONS_CLAIMS_HEADING,
  EXEMPTIONS_LAWS_HEADING,
  EXEMPTIONS_LAW_LABEL,
  EXEMPTIONS_NO_ITEMS,
  EXEMPTIONS_NO_TABLE,
  EXEMPTIONS_NOTE_12_1201,
  EXEMPTIONS_NOTE_DOMICILE,
  EXEMPTIONS_NOT_CLAIMING_BUTTON,
  EXEMPTIONS_PROPERTY_LABEL,
  EXEMPTIONS_READ_FAILED,
  EXEMPTIONS_REMOVE_CLAIM,
  EXEMPTIONS_SAVE_FAILED,
  EXEMPTIONS_TITLE,
  EXEMPTIONS_TOTALS_HEADING,
  EXEMPTION_DESCRIPTION_TOO_LONG,
  EXEMPTION_GAP_CHOOSE_ITEM,
  EXEMPTION_GAP_LINE_1,
  EXEMPTION_GAP_NO_ITEMS,
  EXEMPTION_ITEM_GONE,
  EXEMPTION_LAW_SUMMARIES,
  EXEMPTION_NO_LIMIT,
  EXEMPTION_TOTAL_FAIR_MARKET,
} from '../../constants/copy';
import { UPL_EXEMPTION_DISCLAIMER } from '../../constants/upl';
import type { ExemptionClaim, ExemptionItem, ExemptionLaw, Exemptions } from '../../types/api';

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
      { line_1: 'state_and_federal', line_3: 'no', line_3_1: null, no_claims: true, claims: [] },
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

// ---------------------------------------------------------------------------------------------
// Claims, the law list and the totals (3g1 task 8)
// ---------------------------------------------------------------------------------------------

const ITEMS: ExemptionItem[] = [
  { id: 11, name: 'Kestrel car', line_label: '3.1', value: '4500.00', description_fits: true },
  { id: 12, name: 'JPMorgan Chase', line_label: '17.1', value: '800.00', description_fits: true },
  { id: 13, name: 'JPMorgan Chase', line_label: '17.3', value: '120.00', description_fits: true },
  { id: 14, name: 'Laptop', line_label: '7.1', value: '300.00', description_fits: true },
  { id: 15, name: 'Wedding ring', line_label: '12.1', value: null, description_fits: true },
];

const B = 'il_735_5_12_1001_b';
const C = 'il_735_5_12_1001_c';

function claimOf(overrides: Partial<ExemptionClaim>): ExemptionClaim {
  return {
    id: 1,
    asset: 11,
    law: B,
    other_law: '',
    amount_kind: 'dollars',
    amount: '100.00',
    short_description: null,
    ...overrides,
  };
}

function fullRecord(overrides: Partial<Exemptions> = {}): Exemptions {
  const base = record();
  return {
    ...base,
    items: ITEMS,
    catalog: { ...base.catalog!, laws: LAWS },
    ...overrides,
  };
}

const answerLines = async () => {
  await userEvent.click(radio(EXEMPTIONS_LINE_1_QUESTION, EXEMPTIONS_LINE_1_WORDS.federal));
  await userEvent.click(radio(EXEMPTIONS_LINE_3_QUESTION, 'No'));
};
const optionTexts = (select: HTMLElement) =>
  Array.from((select as HTMLSelectElement).options).map((option) => option.text);

describe('ExemptionsPage claims', () => {
  it('lists every law once, Illinois then federal, with its summary and limit', async () => {
    serve(fullRecord());
    renderPage();
    await ready();
    const laws = within(screen.getByRole('region', { name: EXEMPTIONS_LAWS_HEADING }));
    const rows = laws.getAllByRole('listitem');
    expect(rows).toHaveLength(25);
    LAWS.forEach((law, index) => expect(rows[index]).toHaveTextContent(law.citation));
    expect(rows.slice(0, 22).every((_, i) => LAWS[i].jurisdiction === 'illinois')).toBe(true);
    expect(laws.getByRole('heading', { name: 'Illinois laws' })).toBeInTheDocument();
    expect(laws.getByRole('heading', { name: 'Federal laws' })).toBeInTheDocument();

    const vehicle = rows[LAWS.findIndex((law) => law.key === C)];
    expect(vehicle).toHaveTextContent(EXEMPTION_LAW_SUMMARIES[C]);
    expect(vehicle).toHaveTextContent('Up to $3,600 in one motor vehicle.');
    expect(vehicle).not.toHaveTextContent(EXEMPTION_NO_LIMIT);
    expect(rows[LAWS.findIndex((law) => law.key === 'il_735_5_12_1006')]).toHaveTextContent(
      EXEMPTION_NO_LIMIT
    );
  });

  it('gives every claim the same laws in the same order whatever its property', async () => {
    serve(
      fullRecord({
        claims: [
          claimOf({ id: 1, asset: 11, law: null, amount_kind: null, amount: null }),
          claimOf({ id: 2, asset: 12, law: null, amount_kind: null, amount: null }),
        ],
      })
    );
    renderPage();
    await ready();
    const selects = screen.getAllByLabelText(EXEMPTIONS_LAW_LABEL);
    expect(selects).toHaveLength(2);
    const expected = [
      EXEMPTIONS_CHOOSE_ONE,
      ...LAWS.map((law) => law.citation),
      EXEMPTIONS_ANOTHER_LAW,
    ];
    expect(optionTexts(selects[0])).toEqual(expected);
    expect(optionTexts(selects[1])).toEqual(expected);
  });

  it('starts a new claim with nothing chosen and asks for its property', async () => {
    serve(fullRecord());
    renderPage();
    await ready();
    await userEvent.click(radio(EXEMPTIONS_LINE_1_QUESTION, EXEMPTIONS_LINE_1_WORDS.federal));
    await userEvent.click(screen.getByRole('button', { name: EXEMPTIONS_ADD_CLAIM }));
    expect(screen.getByLabelText(EXEMPTIONS_PROPERTY_LABEL)).toHaveDisplayValue(
      EXEMPTIONS_CHOOSE_ONE
    );
    expect(screen.getByLabelText(EXEMPTIONS_LAW_LABEL)).toHaveDisplayValue(EXEMPTIONS_CHOOSE_ONE);
    for (const r of document.querySelectorAll('input[name="claim_0_amount_kind"]')) {
      expect(r).not.toBeChecked();
    }
    expect(screen.queryByText(EXEMPTION_ITEM_GONE)).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(EXEMPTION_GAP_CHOOSE_ITEM);
  });

  it('clears "not claiming" when a claim is added and hides the button', async () => {
    serve(fullRecord());
    renderPage();
    await ready();
    const button = screen.getByRole('button', { name: EXEMPTIONS_NOT_CLAIMING_BUTTON });
    await userEvent.click(button);
    expect(button).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(screen.getByRole('button', { name: EXEMPTIONS_ADD_CLAIM }));
    expect(
      screen.queryByRole('button', { name: EXEMPTIONS_NOT_CLAIMING_BUTTON })
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: EXEMPTIONS_REMOVE_CLAIM }));
    expect(screen.getByRole('button', { name: EXEMPTIONS_NOT_CLAIMING_BUTTON })).toHaveAttribute(
      'aria-pressed',
      'false'
    );
  });

  it("asks for a shorter description when the property's name does not fit", async () => {
    const long = {
      ...ITEMS[3],
      name: 'Bed, couch, table, kitchenware (secondhand)',
      description_fits: false,
    };
    serve(
      fullRecord({
        items: [ITEMS[0], long],
        claims: [claimOf({ id: 1, asset: 11 }), claimOf({ id: 2, asset: 14 })],
      })
    );
    renderPage();
    await ready();
    await answerLines();
    expect(screen.getAllByText(EXEMPTION_DESCRIPTION_TOO_LONG)).toHaveLength(1);
    expect(document.querySelector('input[name="claim_0_short_description"]')).toBeNull();
    const box = document.querySelector('input[name="claim_1_short_description"]') as HTMLElement;
    expect(box).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled();
    await userEvent.type(box, 'Bed, couch, table');
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled();
  });

  it('keeps the law and amount of a claim whose property left Schedule A/B, and says so', async () => {
    serve(fullRecord({ claims: [claimOf({ id: 5, asset: null })] }));
    renderPage();
    await ready();
    expect(screen.getByText(EXEMPTION_ITEM_GONE)).toBeInTheDocument();
    expect(screen.getByLabelText(EXEMPTIONS_LAW_LABEL)).toHaveValue(B);
    expect(screen.getAllByLabelText(EXEMPTIONS_AMOUNT_LABEL)[0]).toHaveValue(100);
  });

  it('says no property is listed and offers no Add a claim when there is none', async () => {
    serve(fullRecord({ items: [] }));
    renderPage();
    await ready();
    expect(screen.getByText(EXEMPTIONS_NO_ITEMS)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: EXEMPTIONS_ADD_CLAIM })).not.toBeInTheDocument();
  });

  it('tells two items with one name apart by their line', async () => {
    serve(fullRecord());
    renderPage();
    await ready();
    await userEvent.click(screen.getByRole('button', { name: EXEMPTIONS_ADD_CLAIM }));
    const options = optionTexts(screen.getByLabelText(EXEMPTIONS_PROPERTY_LABEL));
    expect(options).toContain('JPMorgan Chase (line 17.1)');
    expect(options).toContain('JPMorgan Chase (line 17.3)');
  });

  it('shows totals that look the same over and under a limit', async () => {
    serve(
      fullRecord({
        claims: [
          claimOf({ id: 1, asset: 11, law: B, amount: '5180.00' }),
          claimOf({ id: 2, asset: 12, law: C, amount: '3600.00' }),
        ],
      })
    );
    renderPage();
    await ready();
    const over = screen.getByText('Amounts entered under this law: $5,180.00');
    const under = screen.getByText('Amounts entered under this law: $3,600.00');
    expect(over.tagName).toBe(under.tagName);
    expect(over.className).toBe(under.className);
    expect(over.parentElement?.className).toBe(under.parentElement?.className);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('counts 100% claims in words and shows a typed law with no limit line', async () => {
    serve(
      fullRecord({
        claims: [
          claimOf({ id: 1, asset: 11, law: B, amount_kind: 'fair_market_value', amount: null }),
          claimOf({ id: 2, asset: 12, law: null, other_law: 'Demo Law 5', amount: '10.00' }),
        ],
      })
    );
    renderPage();
    await ready();
    const totals = within(screen.getByRole('region', { name: EXEMPTIONS_TOTALS_HEADING }));
    expect(totals.getByText(EXEMPTION_TOTAL_FAIR_MARKET.replace('{n}', '1'))).toBeInTheDocument();
    const typed = totals.getByText('Demo Law 5').closest('li') as HTMLElement;
    expect(typed).toHaveTextContent('Amounts entered under this law: $10.00');
    expect(typed).not.toHaveTextContent(EXEMPTION_NO_LIMIT);
    // The same box also shows the law's own limit for the catalog law
    expect(totals.getByText('Up to $4,000.')).toBeInTheDocument();
  });

  it('says what is wrong with an amount the server would refuse, holds Continue and leaves it out of the total', async () => {
    serve(fullRecord({ claims: [claimOf({ id: 1, asset: 11, law: C, amount: '3600.00' })] }));
    renderPage();
    await ready();
    await answerLines();
    const box = screen.getByRole('spinbutton');
    const continueButton = screen.getByRole('button', { name: 'Continue' });
    expect(continueButton).toBeEnabled();

    fireEvent.change(box, { target: { value: '-5' } });
    expect(screen.getByText(AMOUNT_NEGATIVE)).toBeInTheDocument();
    expect(continueButton).toBeDisabled();
    expect(screen.queryByText(/\$-5/)).not.toBeInTheDocument();

    fireEvent.change(box, { target: { value: '10000000000' } });
    expect(screen.getByText(AMOUNT_TOO_LARGE)).toBeInTheDocument();
    expect(continueButton).toBeDisabled();

    fireEvent.change(box, { target: { value: '100.50' } });
    expect(screen.queryByText(AMOUNT_TOO_LARGE)).not.toBeInTheDocument();
    expect(continueButton).toBeEnabled();
  });

  it('sends every claim with its id, its property, and no amount under 100%', async () => {
    const sent = serve(
      fullRecord({
        claims: [
          claimOf({ id: 7, asset: 11, law: C, amount: '3600.00' }),
          claimOf({ id: 8, asset: 12, law: B, amount_kind: 'fair_market_value', amount: null }),
        ],
      })
    );
    renderPage();
    await ready();
    await answerLines();
    await pressContinue();
    await screen.findByText('Statement of Financial Affairs');
    expect(sent[0].claims).toEqual([
      {
        id: 7,
        asset: 11,
        law: C,
        other_law: '',
        amount_kind: 'dollars',
        amount: '3600.00',
        short_description: null,
      },
      {
        id: 8,
        asset: 12,
        law: B,
        other_law: '',
        amount_kind: 'fair_market_value',
        amount: null,
        short_description: null,
      },
    ]);
    expect(sent[0].no_claims).toBe(false);
  });

  it('keeps a stored claim in the save and hides "not claiming" while it stands', async () => {
    const sent = serve(fullRecord({ claims: [claimOf({ id: 9, asset: 14, law: C })] }));
    renderPage();
    await ready();
    expect(
      screen.queryByRole('button', { name: EXEMPTIONS_NOT_CLAIMING_BUTTON })
    ).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: EXEMPTIONS_CLAIMS_HEADING })).toBeInTheDocument();
    await answerLines();
    await pressContinue();
    await screen.findByText('Statement of Financial Affairs');
    expect(sent[0].claims).toEqual([
      {
        id: 9,
        asset: 14,
        law: C,
        other_law: '',
        amount_kind: 'dollars',
        amount: '100.00',
        short_description: null,
      },
    ]);
  });
});

// The 25 rows of districts 0007_exemption_catalog_2026's LAWS_2026
const LAWS: ExemptionLaw[] = [
  {
    key: 'il_40_5_4_135',
    citation: '40 ILCS 5/4-135',
    jurisdiction: 'illinois',
    limit_text: '',
  },
  {
    key: 'il_215_5_238',
    citation: '215 ILCS 5/238',
    jurisdiction: 'illinois',
    limit_text: '',
  },
  {
    key: 'il_305_5_11_3',
    citation: '305 ILCS 5/11-3',
    jurisdiction: 'illinois',
    limit_text: '',
  },
  {
    key: 'il_735_5_12_901',
    citation: '735 ILCS 5/12-901',
    jurisdiction: 'illinois',
    limit_text:
      'Up to $50,000 for each person. When 2 or more people own the home, each is limited to their share of $100,000, by percentage of ownership.',
  },
  {
    key: 'il_735_5_12_1001_a',
    citation: '735 ILCS 5/12-1001(a)',
    jurisdiction: 'illinois',
    limit_text:
      'No total limit. A creditor may ask the court to take any one item with a resale value over $5,000, unless another part of this section exempts it. One piece of jewelry is exempt up to $5,000.',
  },
  {
    key: 'il_735_5_12_1001_b',
    citation: '735 ILCS 5/12-1001(b)',
    jurisdiction: 'illinois',
    limit_text: 'Up to $4,000.',
  },
  {
    key: 'il_735_5_12_1001_c',
    citation: '735 ILCS 5/12-1001(c)',
    jurisdiction: 'illinois',
    limit_text: 'Up to $3,600 in one motor vehicle.',
  },
  {
    key: 'il_735_5_12_1001_d',
    citation: '735 ILCS 5/12-1001(d)',
    jurisdiction: 'illinois',
    limit_text: 'Up to $2,250.',
  },
  {
    key: 'il_735_5_12_1001_e',
    citation: '735 ILCS 5/12-1001(e)',
    jurisdiction: 'illinois',
    limit_text: '',
  },
  {
    key: 'il_735_5_12_1001_f',
    citation: '735 ILCS 5/12-1001(f)',
    jurisdiction: 'illinois',
    limit_text: '',
  },
  {
    key: 'il_735_5_12_1001_g1',
    citation: '735 ILCS 5/12-1001(g)(1)',
    jurisdiction: 'illinois',
    limit_text: '',
  },
  {
    key: 'il_735_5_12_1001_g2',
    citation: '735 ILCS 5/12-1001(g)(2)',
    jurisdiction: 'illinois',
    limit_text: '',
  },
  {
    key: 'il_735_5_12_1001_g3',
    citation: '735 ILCS 5/12-1001(g)(3)',
    jurisdiction: 'illinois',
    limit_text: '',
  },
  {
    key: 'il_735_5_12_1001_g4',
    citation: '735 ILCS 5/12-1001(g)(4)',
    jurisdiction: 'illinois',
    limit_text: 'Only what the person and their dependents reasonably need to live on.',
  },
  {
    key: 'il_735_5_12_1001_h1',
    citation: '735 ILCS 5/12-1001(h)(1)',
    jurisdiction: 'illinois',
    limit_text:
      'The right to a payment is exempt for at most 2 years after the right accrues. Property traced to the payment is exempt for at most 5 years after the payment accrues, and only up to its amount.',
  },
  {
    key: 'il_735_5_12_1001_h2',
    citation: '735 ILCS 5/12-1001(h)(2)',
    jurisdiction: 'illinois',
    limit_text:
      'Only what the person reasonably needs to live on. The right to a payment is exempt for at most 2 years after the right accrues. Property traced to the payment is exempt for at most 5 years after the payment accrues, and only up to its amount.',
  },
  {
    key: 'il_735_5_12_1001_h3',
    citation: '735 ILCS 5/12-1001(h)(3)',
    jurisdiction: 'illinois',
    limit_text:
      'Only what the person and their dependents reasonably need to live on. The right to a payment is exempt for at most 2 years after the right accrues. Property traced to the payment is exempt for at most 5 years after the payment accrues, and only up to its amount.',
  },
  {
    key: 'il_735_5_12_1001_h4',
    citation: '735 ILCS 5/12-1001(h)(4)',
    jurisdiction: 'illinois',
    limit_text:
      'Up to $22,500. The right to a payment is exempt for at most 2 years after the right accrues. Property traced to the payment is exempt for at most 5 years after the payment accrues, and only up to its amount.',
  },
  {
    key: 'il_735_5_12_1001_h5',
    citation: '735 ILCS 5/12-1001(h)(5)',
    jurisdiction: 'illinois',
    limit_text:
      'The right to a payment is exempt for at most 2 years after the right accrues. Property traced to the payment is exempt for at most 5 years after the payment accrues, and only up to its amount.',
  },
  {
    key: 'il_735_5_12_1001_i',
    citation: '735 ILCS 5/12-1001(i)',
    jurisdiction: 'illinois',
    limit_text: '',
  },
  {
    key: 'il_735_5_12_1006',
    citation: '735 ILCS 5/12-1006',
    jurisdiction: 'illinois',
    limit_text: '',
  },
  {
    key: 'il_820_305_21',
    citation: '820 ILCS 305/21',
    jurisdiction: 'illinois',
    limit_text: '',
  },
  {
    key: 'us_11_522_b3c',
    citation: '11 U.S.C. § 522(b)(3)(C)',
    jurisdiction: 'federal',
    limit_text: '',
  },
  {
    key: 'us_38_5301',
    citation: '38 U.S.C. § 5301',
    jurisdiction: 'federal',
    limit_text: '',
  },
  {
    key: 'us_42_407',
    citation: '42 U.S.C. § 407',
    jurisdiction: 'federal',
    limit_text: '',
  },
];
