/**
 * The Form 122A-2 page's spouse block and each secured debt's questions (3h2 spec §8.12, lines 33
 * and 34). Business intent: the spouse's own vehicles and loans are asked in the form's words and
 * nothing is chosen for the filer; a debt's questions follow the line the filer's own vehicle
 * answers give it; a save never names a row that has gone, and a row the server names keeps what
 * the filer typed beside it.
 */
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { KESTREL, meansPage, priyaPage } from '../../test/fixtures/meansPage';
import {
  FORM_122A2_LINE_34_CURE,
  FORM_122A2_LINE_34_DEBT,
  FORM_122A2_LINE_33D_TAXES,
  FORM_122A2_PART_2_LINE_3,
  FORM_122A2_PART_2_YOU,
} from '../../constants/formText';
import {
  MEANS_DEBT_GOES_ON,
  MEANS_DEBT_WAITS,
  MEANS_GAP_SPOUSE_LOAN_SECURED_BY,
  MEANS_GAP_VEHICLE_CHOICE,
  MEANS_LETTER,
  MEANS_PAGE_SAVE_FAILED,
  MEANS_PAGE_UPDATED,
  MEANS_SIXTY_OR_MORE,
  MEANS_SPOUSE_ADD_LOAN,
  MEANS_SPOUSE_ADD_VEHICLE,
  MEANS_SPOUSE_LOAN_FROM,
  MEANS_SPOUSE_REMOVE_LOAN,
  MEANS_SPOUSE_INTRO,
  MEANS_SPOUSE_REMOVE_VEHICLE,
  MEANS_SPOUSE_TITLE,
  MEANS_SPOUSE_VEHICLE_LEGEND,
  MEANS_TOO_LONG,
} from '../../constants/copy';
import type { MeansAnswers, MeansPage, MeansSpouseLoan, MeansSpouseVehicle } from '../../types/api';
import {
  URL,
  field,
  gapRegion,
  pressContinue,
  radio,
  ready,
  renderPage,
  serve,
} from './meansTestPageHelpers';

const fill = (sentence: string, values: Record<string, string>) =>
  Object.entries(values).reduce(
    (text, [key, value]) => text.split(`{${key}}`).join(value),
    sentence
  );

const vehicleRow = (over: Partial<MeansSpouseVehicle> = {}): MeansSpouseVehicle => ({
  ref: 'spouse-1',
  description: 'Demo van',
  leased: 'no',
  claimed: null,
  ...over,
});

const loanRow = (over: Partial<MeansSpouseLoan> = {}): MeansSpouseLoan => ({
  ref: 'spouse-1',
  on_amounts_owed: 'no',
  debt: null,
  creditor: 'Demo Credit Union',
  secured_by: null,
  property: '',
  payment: null,
  payments_left: null,
  payment_changes: null,
  total_60_months: null,
  taxes_or_insurance: null,
  necessary_for_support: null,
  cure: null,
  ...over,
});

/** A married filer whose spouse has one described van and one loan, nothing else answered */
function spousePage(
  vehicles: MeansSpouseVehicle[],
  loans: MeansSpouseLoan[],
  answers: Partial<MeansAnswers> = {}
): MeansPage {
  const page = meansPage();
  page.answers = {
    ...page.answers,
    spouse_vehicles_answer: 'yes',
    spouse_vehicles: vehicles,
    spouse_loans_answer: 'yes',
    spouse_loans: loans,
    ...answers,
  };
  return page;
}

const names = (select: HTMLSelectElement) =>
  [...select.options].map((option) => option.textContent);
const selectNamed = (name: string) =>
  document.querySelector(`select[name="${name}"]`) as HTMLSelectElement;
const radiosOf = (name: string) => [
  ...document.querySelectorAll<HTMLInputElement>(`input[name="${name}"]`),
];
const region = (name: string) => screen.getByRole('region', { name });

type SentBody = {
  spouse_vehicles: { ref: string; claimed: string | null }[];
  spouse_loans: { ref: string; secured_by: string | null }[];
  vehicle_choice: (string | null)[];
  vehicle_claims: Record<string, string | null>;
  debts: { id: number; payments_left: unknown }[];
};

/** A PUT stand-in that gives each new spouse row the next id of its own list, as the server does */
function serveWithIds(saved: MeansPage) {
  const sent: SentBody[] = [];
  server.use(
    http.get(URL, () => HttpResponse.json(saved)),
    http.put(URL, async ({ request }) => {
      const body = (await request.json()) as SentBody & MeansAnswers & { debts?: unknown };
      sent.push(body);
      const answers: MeansAnswers = { ...body };
      delete (answers as Partial<typeof body>).debts;
      const renamed = new Map<string, string>();
      const give = (rows: { ref: string }[]) => {
        let next =
          Math.max(0, ...rows.map((row) => Number(row.ref.replace('spouse-', '')) || 0)) + 1;
        for (const row of rows) {
          if (row.ref.startsWith('new-')) renamed.set(row.ref, `spouse-${next++}`);
        }
      };
      give(answers.spouse_vehicles);
      give(answers.spouse_loans);
      const rename = (ref: string | null) => (ref === null ? null : (renamed.get(ref) ?? ref));
      const reply: MeansPage = {
        ...saved,
        answers: {
          ...answers,
          spouse_vehicles: answers.spouse_vehicles.map((row) => ({
            ...row,
            ref: rename(row.ref)!,
          })),
          spouse_loans: answers.spouse_loans.map((row) => ({
            ...row,
            ref: rename(row.ref)!,
            secured_by: rename(row.secured_by),
          })),
          vehicle_choice: [rename(answers.vehicle_choice[0]), rename(answers.vehicle_choice[1])],
        },
      };
      return HttpResponse.json(reply);
    })
  );
  return sent;
}

describe("the spouse's vehicles and loans", () => {
  it("the spouse's block shows only for a filer married and living together", async () => {
    serve(meansPage());
    const { unmount } = renderPage();
    await ready();
    expect(screen.getByRole('heading', { level: 2, name: MEANS_SPOUSE_TITLE })).toBeInTheDocument();
    unmount();

    serve({ ...meansPage(), married_together: false });
    renderPage();
    await ready();
    expect(screen.queryByRole('heading', { name: MEANS_SPOUSE_TITLE })).toBeNull();
    expect(radio('means_spouse_vehicles', 'yes')).toBeNull();
  });

  it("nothing in the spouse's block is selected on load", async () => {
    serve(meansPage());
    renderPage();
    await ready();
    expect(radio('means_spouse_vehicles', 'yes')).not.toBeChecked();
    expect(radio('means_spouse_vehicles', 'no')).not.toBeChecked();
    expect(radio('means_spouse_loans', 'yes')).not.toBeChecked();
    expect(radio('means_spouse_loans', 'no')).not.toBeChecked();
    // No row is drawn until the filer says Yes and adds one
    expect(field('means_spouse_vehicle_0_name')).toBeNull();
    expect(field('means_spouse_loan_0_creditor')).toBeNull();
  });

  it('what secures the loan lists your home, every vehicle by name and other property', async () => {
    serve(
      spousePage(
        [vehicleRow(), vehicleRow({ ref: 'spouse-2', description: '' })],
        [loanRow({ on_amounts_owed: 'no' })]
      )
    );
    renderPage();
    await ready();
    const radios = radiosOf('means_spouse_loan_0_secured_by');
    // A spouse row with no description is on no list
    expect(radios.map((input) => input.value)).toEqual(['home', 'asset-7', 'spouse-1', 'other']);
    expect(radios.map((input) => input.closest('label')?.textContent)).toEqual([
      'Your home',
      'Honda CR-V EX 2021',
      'Demo van',
      'Other property',
    ]);
    expect(radios.some((input) => input.checked)).toBe(false);
  });

  it("an Amounts Owed loan lists only the spouse's vehicles", async () => {
    serve(spousePage([vehicleRow()], [loanRow({ on_amounts_owed: 'yes', creditor: '' })]));
    renderPage();
    await ready();
    expect(radiosOf('means_spouse_loan_0_secured_by').map((input) => input.value)).toEqual([
      'home',
      'spouse-1',
      'other',
    ]);
  });

  it('which loan it is lists only the Amounts Owed debts not listed as secured, each once', async () => {
    const page = spousePage(
      [],
      [
        loanRow({ ref: 'spouse-1', on_amounts_owed: 'yes', creditor: '' }),
        loanRow({ ref: 'spouse-2', on_amounts_owed: 'yes', creditor: '' }),
      ],
      { spouse_vehicles_answer: 'no' }
    );
    page.amounts_owed_loans = [
      { id: 21, creditor: 'Demo Lender A' },
      { id: 22, creditor: 'Demo Lender B' },
    ];
    serve(page);
    renderPage();
    await ready();
    const first = selectNamed('means_spouse_loan_0_debt');
    const second = selectNamed('means_spouse_loan_1_debt');
    expect(names(first)).toEqual(['', 'Demo Lender A', 'Demo Lender B']);
    expect(first.value).toBe('');

    await userEvent.selectOptions(second, '21');
    // Debt 21 is named by row 2, so row 1 no longer offers it; row 2 still shows its own
    expect(names(first)).toEqual(['', 'Demo Lender B']);
    expect(names(second)).toEqual(['', 'Demo Lender A', 'Demo Lender B']);
    expect(second.value).toBe('21');
  });

  it('describe the property shows under your home and other property', async () => {
    serve(spousePage([vehicleRow()], [loanRow()]));
    renderPage();
    await ready();
    expect(field('means_spouse_loan_0_property')).toBeNull();
    await userEvent.click(radio('means_spouse_loan_0_secured_by', 'home'));
    expect(field('means_spouse_loan_0_property')).toBeInTheDocument();
    await userEvent.click(radio('means_spouse_loan_0_secured_by', 'spouse-1'));
    expect(field('means_spouse_loan_0_property')).toBeNull();
    await userEvent.click(radio('means_spouse_loan_0_secured_by', 'other'));
    expect(field('means_spouse_loan_0_property')).toBeInTheDocument();
  });

  it('a spouse vehicle joins line 11 once described, and its claim travels with its row', async () => {
    const sent = serve(spousePage([vehicleRow({ description: '' })], []));
    renderPage();
    await ready();
    expect(radio('means_vehicle_spouse_1_claimed', 'yes')).toBeNull();

    fireEvent.change(field('means_spouse_vehicle_0_name'), { target: { value: 'Demo van' } });
    await userEvent.click(radio('means_vehicle_spouse_1_claimed', 'yes'));
    await pressContinue();
    await ready();
    const body = sent[0] as unknown as SentBody;
    expect(body.spouse_vehicles).toEqual([
      { ref: 'spouse-1', description: 'Demo van', leased: 'no', claimed: 'yes' },
    ]);
    // The claim is on the row, never in the filer's own claims
    expect(body.vehicle_claims).not.toHaveProperty('spouse-1');
  });

  it("a filer whose only vehicle is the spouse's sees line 11", async () => {
    const page = spousePage([vehicleRow()], []);
    page.vehicles = [];
    page.debts = [];
    page.debt_lines = {};
    serve(page);
    renderPage();
    await ready();
    expect(radio('means_vehicle_spouse_1_claimed', 'yes')).toBeInTheDocument();
  });

  it("a new spouse row's id follows the reply", async () => {
    const sent = serveWithIds(meansPage());
    renderPage();
    await ready();
    await userEvent.click(radio('means_spouse_vehicles', 'yes'));
    await userEvent.click(screen.getByRole('button', { name: MEANS_SPOUSE_ADD_VEHICLE }));
    fireEvent.change(field('means_spouse_vehicle_0_name'), { target: { value: 'Demo van' } });
    await userEvent.click(radio('means_spouse_vehicle_0_leased', 'no'));
    await userEvent.click(radio('means_vehicle_new_1_claimed', 'yes'));

    await userEvent.click(radio('means_spouse_loans', 'yes'));
    await userEvent.click(screen.getByRole('button', { name: MEANS_SPOUSE_ADD_LOAN }));
    await userEvent.click(radio('means_spouse_loan_0_on_amounts_owed', 'no'));
    fireEvent.change(field('means_spouse_loan_0_creditor'), { target: { value: 'Demo Credit' } });
    await userEvent.click(radio('means_spouse_loan_0_secured_by', 'new-1'));
    fireEvent.change(field('means_spouse_loan_0_payment'), { target: { value: '450' } });
    expect(selectNamed('means_spouse_debt_new_2_payments_left')).toBeTruthy();

    await pressContinue();
    await screen.findByRole('region', {
      name: fill(MEANS_SPOUSE_LOAN_FROM, { name: 'Demo Credit' }),
    });
    expect(sent[0].spouse_vehicles[0].ref).toBe('new-1');
    expect(sent[0].spouse_loans[0]).toMatchObject({ ref: 'new-2', secured_by: 'new-1' });
    // The row keeps its place on screen, and its questions take the new id
    expect(await screen.findByDisplayValue('Demo van')).toBeInTheDocument();
    expect(selectNamed('means_spouse_debt_1_payments_left')).toBeTruthy();
    expect(selectNamed('means_spouse_debt_new_2_payments_left')).toBeNull();
    expect(field('means_spouse_loan_0_payment').value).toBe('450');

    await pressContinue();
    await screen.findByRole('button', { name: 'Continue' });
    expect(sent).toHaveLength(2);
    expect(sent[1].spouse_vehicles[0].ref).toBe('spouse-1');
    expect(sent[1].spouse_loans[0]).toMatchObject({ ref: 'spouse-1', secured_by: 'spouse-1' });
  });

  /** A loan secured by the spouse's first van and Vehicle 2 set to it; the filer then removes the van */
  async function removeTheVanThatTheLoanNames() {
    const page = spousePage(
      [
        vehicleRow({ claimed: 'yes', leased: 'yes' }),
        vehicleRow({ ref: 'spouse-2', description: 'Demo pickup', claimed: 'yes', leased: 'yes' }),
      ],
      [loanRow({ secured_by: 'spouse-1', payment: '100.00' })],
      {
        vehicle_claims: { 'asset-7': 'yes', 'asset-8': 'yes', 'asset-9': 'yes' },
        vehicle_choice: ['asset-7', 'spouse-1'],
      }
    );
    page.vehicles = [
      { ref: 'asset-7', name: 'Honda CR-V EX 2021', leased: true },
      { ref: 'asset-8', name: 'Demo leased car', leased: true },
      { ref: 'asset-9', name: 'Demo leased truck', leased: true },
    ];
    page.debts = [];
    page.debt_lines = {};
    const sent = serve(page);
    renderPage();
    await ready();
    expect(selectNamed('means_vehicle_2').value).toBe('spouse-1');

    await userEvent.click(
      screen.getByRole('button', { name: fill(MEANS_SPOUSE_REMOVE_VEHICLE, { n: '1' }) })
    );
    // Line 3 is the page's first question; answering it lets the gap region reach the rest
    await userEvent.click(radio('means_line_3', 'no'));
    return sent;
  }

  it('a removed spouse vehicle is named by no loan and no Vehicle choice in the next save', async () => {
    const sent = await removeTheVanThatTheLoanNames();
    // The page's own gap region asks the loan's question again
    expect(gapRegion()).toHaveTextContent(
      fill(MEANS_GAP_SPOUSE_LOAN_SECURED_BY, { name: 'Demo Credit Union' })
    );
    await pressContinue();
    await ready();
    const body = sent[0] as unknown as SentBody;
    expect(body.spouse_loans[0].secured_by).toBeNull();
    expect(body.vehicle_choice).toEqual(['asset-7', null]);
  });

  it('once the loan of a removed vehicle is answered, the page asks for Vehicle 1 and 2 again', async () => {
    await removeTheVanThatTheLoanNames();
    // The slots wait while a loan is unplaced, so the choice is asked only after the loan is
    await userEvent.click(radio('means_spouse_loan_0_secured_by', 'home'));
    await userEvent.type(field('means_spouse_loan_0_property'), 'Demo house');
    expect(gapRegion()).toHaveTextContent(MEANS_GAP_VEHICLE_CHOICE);
  });

  it("two rows added in one press of the keys both stay in the spouse's lists", async () => {
    serve(spousePage([], []));
    renderPage();
    await ready();
    const addVehicle = screen.getByRole('button', { name: MEANS_SPOUSE_ADD_VEHICLE });
    const addLoan = screen.getByRole('button', { name: MEANS_SPOUSE_ADD_LOAN });
    act(() => {
      addVehicle.click();
      addVehicle.click();
      addLoan.click();
      addLoan.click();
    });
    expect(field('means_spouse_vehicle_0_name')).not.toBeNull();
    expect(field('means_spouse_vehicle_1_name')).not.toBeNull();
    for (const n of ['1', '2']) {
      expect(
        screen.getByRole('button', { name: fill(MEANS_SPOUSE_REMOVE_LOAN, { n }) })
      ).toBeInTheDocument();
    }
  });

  it("a filer's own vehicle chosen before the loan was marked as on the Amounts Owed step goes as unanswered", async () => {
    const sent = serve(
      spousePage([], [loanRow({ secured_by: 'asset-7' })], { spouse_vehicles_answer: 'no' })
    );
    renderPage();
    await ready();
    expect(radio('means_spouse_loan_0_secured_by', 'asset-7')).toBeChecked();
    await userEvent.click(radio('means_spouse_loan_0_on_amounts_owed', 'yes'));
    expect(radio('means_spouse_loan_0_secured_by', 'asset-7')).toBeNull();
    await pressContinue();
    await ready();
    expect((sent[0] as unknown as SentBody).spouse_loans[0].secured_by).toBeNull();
  });

  it('a spouse description too long for its box shows the sentence beside it', async () => {
    serve(spousePage([vehicleRow()], []), {
      status: 400,
      body: { spouse_vehicles: { '0': { description: [MEANS_TOO_LONG] } } },
    });
    renderPage();
    await ready();
    expect(field('means_spouse_vehicle_0_name').maxLength).toBe(200);
    await pressContinue();
    const boxRow = field('means_spouse_vehicle_0_name').closest('.form-field') as HTMLElement;
    expect(await within(boxRow).findByText(MEANS_TOO_LONG)).toBeInTheDocument();
    expect(screen.queryByText(MEANS_PAGE_SAVE_FAILED)).toBeNull();
  });

  it('a letter the form cannot print, and words too long, are each said beside the box', async () => {
    for (const sentence of [MEANS_LETTER, MEANS_TOO_LONG]) {
      serve(spousePage([], [loanRow({ secured_by: 'home' })]), {
        status: 400,
        body: { spouse_loans: { '0': { creditor: [sentence] } } },
      });
      const { unmount } = renderPage();
      await ready();
      await pressContinue();
      const boxRow = field('means_spouse_loan_0_creditor').closest('.form-field') as HTMLElement;
      expect(await within(boxRow).findByText(sentence)).toBeInTheDocument();
      expect(screen.queryByText(MEANS_PAGE_SAVE_FAILED)).toBeNull();
      unmount();
    }
  });

  it('a refusal of a box the page is not drawing says the save failed', async () => {
    const hidden: [MeansPage, Record<string, unknown>][] = [
      [
        spousePage([vehicleRow()], [], { spouse_vehicles_answer: 'no' }),
        { spouse_vehicles: { '0': { description: [MEANS_TOO_LONG] } } },
      ],
      [
        spousePage([], [loanRow({ on_amounts_owed: 'yes', secured_by: 'home' })]),
        { spouse_loans: { '0': { creditor: [MEANS_TOO_LONG] } } },
      ],
      [
        spousePage([vehicleRow()], [loanRow({ secured_by: 'spouse-1', property: 'Demo' })]),
        { spouse_loans: { '0': { property: [MEANS_LETTER] } } },
      ],
    ];
    for (const [page, body] of hidden) {
      serve(page, { status: 400, body });
      const { unmount } = renderPage();
      await ready();
      await pressContinue();
      expect(await screen.findByRole('alert')).toHaveTextContent(MEANS_PAGE_SAVE_FAILED);
      unmount();
    }
  });

  it('a mistaken No on the spouse vehicles keeps the loan and Vehicle 1 and 2 naming the row in the save', async () => {
    const page = spousePage(
      [vehicleRow({ leased: 'yes', claimed: 'yes' })],
      [loanRow({ secured_by: 'spouse-1' })],
      {
        vehicle_claims: { 'asset-7': 'yes', 'asset-8': 'yes' },
        vehicle_choice: ['asset-8', 'spouse-1'],
      }
    );
    page.vehicles = [
      { ref: 'asset-7', name: 'Honda CR-V EX 2021', leased: false },
      { ref: 'asset-8', name: 'Demo sedan', leased: true },
    ];
    const sent = serve(page);
    renderPage();
    await ready();
    await userEvent.click(radio('means_spouse_vehicles', 'no'));
    await pressContinue();
    await ready();
    const body = sent[0] as unknown as SentBody;
    expect(body.spouse_vehicles.map((row) => row.ref)).toEqual(['spouse-1']);
    expect(body.spouse_loans[0].secured_by).toBe('spouse-1');
    expect(body.vehicle_choice).toEqual(['asset-8', 'spouse-1']);
  });

  it('a spouse vehicle link survives a No, a reload and a save', async () => {
    // the server keeps the typed row and the loan's link under No (DIG-513): the GET hands both back
    const page = spousePage(
      [vehicleRow()],
      [loanRow({ secured_by: 'spouse-1', payment: '100.00' })],
      { spouse_vehicles_answer: 'no' }
    );
    const sent = serve(page);
    renderPage();
    await ready();
    await pressContinue();
    await ready();

    const body = sent[0] as unknown as SentBody;
    expect(body.spouse_loans[0]).toMatchObject({ ref: 'spouse-1', secured_by: 'spouse-1' });
    expect(body.spouse_vehicles.map((row) => row.ref)).toEqual(['spouse-1']);
  });

  it('a save refused for a spouse vehicle another tab removed sends it as new, so the next save names no gone row', async () => {
    const first = spousePage(
      [vehicleRow({ ref: 'spouse-2', leased: 'yes', claimed: 'yes' })],
      [loanRow({ secured_by: 'spouse-2' })],
      { vehicle_choice: ['asset-7', 'spouse-2'] }
    );
    // Another tab removed the spouse's van, so the server stores no spouse-2
    const latest = spousePage([], [loanRow({ secured_by: null })]);
    const sent: SentBody[] = [];
    let reads = 0;
    server.use(
      http.get(URL, () => {
        reads += 1;
        return HttpResponse.json(reads === 1 ? first : latest);
      }),
      http.put(URL, async ({ request }) => {
        sent.push((await request.json()) as SentBody);
        return sent.length === 1
          ? HttpResponse.json(
              {
                spouse_loans: {
                  '0': { secured_by: ["This isn't one of the vehicles on line 11."] },
                },
              },
              { status: 400 }
            )
          : HttpResponse.json(latest);
      })
    );
    renderPage();
    await ready();
    await pressContinue();
    expect(await within(gapRegion()).findByText(MEANS_PAGE_UPDATED)).toBeInTheDocument();
    await pressContinue();
    await waitFor(() => expect(sent).toHaveLength(2));
    const body = sent[1];
    const vanRef = body.spouse_vehicles[0].ref;
    expect(vanRef).toMatch(/^new-/);
    expect(body.spouse_loans[0].secured_by).toBe(vanRef);
    expect(body.vehicle_choice).toEqual(['asset-7', vanRef]);
  });

  it("the spouse's block opens with the form's Part 2 sentences, which show twice only with the block", async () => {
    serve(spousePage([], []));
    const { unmount } = renderPage();
    await ready();
    const block = screen.getByRole('heading', { name: MEANS_SPOUSE_TITLE })
      .parentElement as HTMLElement;
    const paragraphs = [...block.querySelectorAll(':scope > p')].map((p) => p.textContent);
    expect(paragraphs.slice(0, 3)).toEqual([
      FORM_122A2_PART_2_YOU,
      FORM_122A2_PART_2_LINE_3,
      MEANS_SPOUSE_INTRO,
    ]);
    expect(screen.getAllByText(FORM_122A2_PART_2_YOU)).toHaveLength(2);
    expect(screen.getAllByText(FORM_122A2_PART_2_LINE_3)).toHaveLength(2);
    unmount();

    const alone = meansPage();
    alone.married_together = false;
    serve(alone);
    renderPage();
    await ready();
    expect(screen.queryByText(FORM_122A2_PART_2_YOU)).toBeNull();
    expect(screen.getAllByText(FORM_122A2_PART_2_LINE_3)).toHaveLength(1);
  });
});

/** Three financed, claimed cars and both spouse questions answered No, so the slots are open */
function threeCars(): MeansPage {
  const page = meansPage();
  page.answers.spouse_vehicles_answer = 'no';
  page.answers.spouse_loans_answer = 'no';
  page.vehicles = [
    { ref: 'asset-7', name: 'Honda CR-V EX 2021', leased: false },
    { ref: 'asset-8', name: 'Demo sedan', leased: false },
    { ref: 'asset-9', name: 'Demo truck', leased: false },
  ];
  page.debts = [
    { ...KESTREL },
    { ...KESTREL, id: 12, ref: 'debt-12', creditor: 'Demo Sedan Loan', secured_by: 'asset-8' },
    { ...KESTREL, id: 13, ref: 'debt-13', creditor: 'Demo Truck Loan', secured_by: 'asset-9' },
  ];
  page.debt_lines = { 'debt-11': null, 'debt-12': null, 'debt-13': null };
  return page;
}

describe('a spouse loan that changes its answer', () => {
  it('a loan switched from Yes to No lets the next loan name the debt and the save goes through', async () => {
    const page = spousePage(
      [],
      [
        loanRow({ ref: 'spouse-1', on_amounts_owed: null, creditor: '' }),
        loanRow({ ref: 'spouse-2', on_amounts_owed: null, creditor: '' }),
      ],
      { spouse_vehicles_answer: 'no' }
    );
    page.amounts_owed_loans = [{ id: 21, creditor: 'Demo Lender A' }];
    const sent = serve(page);
    renderPage();
    await ready();
    await userEvent.click(radio('means_spouse_loan_0_on_amounts_owed', 'yes'));
    await userEvent.selectOptions(selectNamed('means_spouse_loan_0_debt'), '21');
    await userEvent.click(radio('means_spouse_loan_0_on_amounts_owed', 'no'));
    await userEvent.click(radio('means_spouse_loan_1_on_amounts_owed', 'yes'));
    await userEvent.selectOptions(selectNamed('means_spouse_loan_1_debt'), '21');
    await pressContinue();
    await ready();
    const body = sent[0] as unknown as { spouse_loans: { debt: number | null }[] };
    expect(body.spouse_loans.map((row) => row.debt)).toEqual([null, 21]);
    expect(screen.queryByText(MEANS_PAGE_SAVE_FAILED)).toBeNull();
  });
});

describe('a spouse vehicle with no description in a slot choice', () => {
  it('is named by its legend, never by its ref', async () => {
    const page = meansPage();
    page.vehicles = [
      { ref: 'asset-7', name: 'Honda CR-V EX 2021', leased: true },
      { ref: 'asset-8', name: 'Demo sedan', leased: true },
    ];
    page.debts = [];
    page.debt_lines = {};
    page.answers = {
      ...page.answers,
      vehicle_claims: { 'asset-7': 'yes', 'asset-8': 'yes' },
      spouse_vehicles_answer: 'yes',
      spouse_vehicles: [vehicleRow({ description: '', leased: 'yes', claimed: 'yes' })],
      spouse_loans_answer: 'no',
      spouse_loans: [],
    };
    serve(page);
    renderPage();
    await ready();
    const first = selectNamed('means_vehicle_1');
    expect(names(first)).toEqual([
      '',
      'Honda CR-V EX 2021',
      'Demo sedan',
      fill(MEANS_SPOUSE_VEHICLE_LEGEND, { n: '1' }),
    ]);
    expect(names(first).join('|')).not.toContain('spouse-1');
  });
});

describe("each secured debt's questions", () => {
  it('the taxes question is asked only of a line 33d debt, and moves with Vehicle 1', async () => {
    serve(threeCars());
    renderPage();
    await ready();
    for (const pk of [7, 8, 9]) await userEvent.click(radio(`means_vehicle_${pk}_claimed`, 'yes'));
    await userEvent.selectOptions(selectNamed('means_vehicle_1'), 'asset-7');
    await userEvent.selectOptions(selectNamed('means_vehicle_2'), 'asset-8');

    // The third car's loan is on line 33d
    expect(
      within(region('Demo Truck Loan')).getByText(fill(MEANS_DEBT_GOES_ON, { line: '33d' }))
    ).toBeInTheDocument();
    expect(radio('means_debt_13_taxes', 'yes')).toBeInTheDocument();
    expect(region('Demo Truck Loan').contains(radio('means_debt_13_taxes', 'yes'))).toBe(true);
    expect(radio('means_debt_11_taxes', 'yes')).toBeNull();
    expect(radio('means_debt_12_taxes', 'yes')).toBeNull();
    expect(
      within(region('Demo Truck Loan')).getByText(FORM_122A2_LINE_33D_TAXES, { exact: false })
    ).toBeInTheDocument();

    // Vehicle 1 changes from the first car to the third: the first car's loan moves to 33d
    await userEvent.selectOptions(selectNamed('means_vehicle_1'), 'asset-9');
    expect(radio('means_debt_13_taxes', 'yes')).toBeNull();
    expect(radio('means_debt_11_taxes', 'yes')).toBeInTheDocument();
    expect(
      within(region('Kestrel Auto Finance')).getByText(fill(MEANS_DEBT_GOES_ON, { line: '33d' }))
    ).toBeInTheDocument();

    await userEvent.selectOptions(selectNamed('means_vehicle_1'), 'asset-7');
    expect(radio('means_debt_11_taxes', 'yes')).toBeNull();
    expect(radio('means_debt_13_taxes', 'yes')).toBeInTheDocument();
  });

  it('a debt waits for its line while the vehicle answers are unfinished', async () => {
    serve(meansPage());
    renderPage();
    await ready();
    const kestrel = within(region('Kestrel Auto Finance'));
    expect(kestrel.getByText(MEANS_DEBT_WAITS)).toBeInTheDocument();
    expect(kestrel.queryByText(/On Form 122A-2, this debt goes on line/)).toBeNull();
    expect(kestrel.getByText('Secured by Honda CR-V EX 2021')).toBeInTheDocument();
    expect(
      kestrel.getByText('You entered a monthly payment of $450.00 on the Amounts Owed step.')
    ).toBeInTheDocument();

    await userEvent.click(radio('means_spouse_vehicles', 'no'));
    await userEvent.click(radio('means_spouse_loans', 'no'));
    await userEvent.click(radio('means_vehicle_7_claimed', 'no'));
    expect(kestrel.queryByText(MEANS_DEBT_WAITS)).toBeNull();
    expect(kestrel.getByText(fill(MEANS_DEBT_GOES_ON, { line: '33d' }))).toBeInTheDocument();
  });

  it("line 34's per-debt question shows only under its Yes, and the cure only under that debt's Yes", async () => {
    const page = priyaPage();
    page.answers.line_34_answer = null;
    serve(page);
    renderPage();
    await ready();
    expect(radio('means_debt_11_support', 'yes')).toBeNull();

    await userEvent.click(radio('means_line_34', 'yes'));
    const support = radio('means_debt_11_support', 'yes');
    expect(support).toBeInTheDocument();
    expect(support.closest('.means-line')).toBe(
      radio('means_line_34', 'yes').closest('.means-line')
    );
    expect(
      screen.getByText(fill(FORM_122A2_LINE_34_DEBT, { name: 'Kestrel Auto Finance' }), {
        exact: false,
      })
    ).toBeInTheDocument();
    expect(field('means_debt_11_cure')).toBeNull();

    await userEvent.click(radio('means_debt_11_support', 'no'));
    expect(field('means_debt_11_cure')).toBeNull();
    await userEvent.click(radio('means_debt_11_support', 'yes'));
    expect(field('means_debt_11_cure')).toBeInTheDocument();
    expect(screen.getAllByText(FORM_122A2_LINE_34_CURE, { exact: false }).length).toBeGreaterThan(
      0
    );

    await userEvent.click(radio('means_line_34', 'no'));
    expect(radio('means_debt_11_support', 'yes')).toBeNull();
    expect(field('means_debt_11_cure')).toBeNull();
  });

  it('payments left offers 0 to 59 and 60 or more, none chosen', async () => {
    serve(meansPage());
    renderPage();
    await ready();
    const select = selectNamed('means_debt_11_payments_left');
    expect(select.value).toBe('');
    const options = [...select.options];
    expect(options[0].textContent).toBe('');
    expect(options.slice(1, 61).map((option) => option.value)).toEqual(
      Array.from({ length: 60 }, (_, count) => String(count))
    );
    expect(options[61].value).toBe('60_or_more');
    expect(options[61].textContent).toBe(MEANS_SIXTY_OR_MORE);
    expect(options).toHaveLength(62);
  });

  it('sends 60 or more as 60_or_more', async () => {
    const sent = serve(meansPage());
    renderPage();
    await ready();
    await userEvent.selectOptions(selectNamed('means_debt_11_payments_left'), '60_or_more');
    await pressContinue();
    await ready();
    expect((sent[0] as unknown as SentBody).debts[0].payments_left).toBe('60_or_more');

    await userEvent.selectOptions(selectNamed('means_debt_11_payments_left'), '37');
    await pressContinue();
    await ready();
    expect((sent[1] as unknown as SentBody).debts[0].payments_left).toBe(37);
    expect(gapRegion()).toBeInTheDocument();
  });
});
