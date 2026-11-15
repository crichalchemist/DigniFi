/**
 * What the Form 122A-2 page holds and sends. Business intent: a save never loses an answer the
 * filer gave (the server replaces the vehicle claims whole), the browser never sends its own row
 * keys, a spouse row the server named keeps the answers typed beside it, and the browser reads the
 * spouse's loans as the server does, so the page's gaps and the result agree.
 */
import {
  adoptRefs,
  fromReply,
  gapStateOf,
  rowsInputOf,
  toPutBody,
  withLiveRefs,
} from '../pageState';
import { KESTREL, meansPage, priyaPage } from '../../../test/fixtures/meansPage';
import type { MeansPage, MeansSpouseLoan } from '../../../types/api';

function loan(number: number, over: Partial<MeansSpouseLoan> = {}): MeansSpouseLoan {
  return {
    ref: `spouse-${number}`,
    on_amounts_owed: 'no',
    debt: null,
    creditor: `Demo Lender ${number}`,
    secured_by: 'home',
    property: 'A Demo house',
    payment: '100.00',
    payments_left: 10,
    payment_changes: 'no',
    total_60_months: null,
    taxes_or_insurance: null,
    necessary_for_support: null,
    cure: null,
    ...over,
  };
}

function withLoans(loans: MeansSpouseLoan[], over: Partial<MeansPage> = {}): MeansPage {
  const page = meansPage();
  page.answers.spouse_vehicles_answer = 'yes';
  page.answers.spouse_vehicles = [
    { ref: 'spouse-1', description: 'Demo van', leased: 'no', claimed: 'yes' },
  ];
  page.answers.spouse_loans_answer = 'yes';
  page.answers.spouse_loans = loans;
  page.amounts_owed_loans = [{ id: 21, creditor: 'Demo Lender A' }];
  return { ...page, ...over };
}

describe('toPutBody', () => {
  it('sends no browser-only key and every answer, with each debt answered under its id', () => {
    const page = priyaPage();
    page.answers.line_43_answer = 'yes';
    page.answers.line_43_circumstances = [
      {
        happened: 'Demo event',
        change: '',
        choices: '',
        papers: '',
        amount: '10.00',
        explanation: 'Demo words',
      },
    ];
    const body = toPutBody(fromReply(page));
    expect(JSON.stringify(body)).not.toContain('_key');
    expect(Object.keys(body).sort()).toEqual([...Object.keys(page.answers), 'debts'].sort());
    expect(body.line_3_rows).toEqual([
      { purpose: 'His payroll taxes withheld from his pay', amount: '250.00' },
    ]);
    expect(body.debts).toEqual([
      {
        id: 11,
        payments_left: 37,
        payment_changes: 'no',
        total_60_months: null,
        taxes_or_insurance: null,
        necessary_for_support: null,
        cure: null,
      },
    ]);
  });

  it('sends the spouse rows as loaded, so a save never drops them', () => {
    const page = withLoans([loan(1)]);
    const body = toPutBody(fromReply(page));
    expect(body.spouse_vehicles).toEqual(page.answers.spouse_vehicles);
    expect(body.spouse_loans).toEqual(page.answers.spouse_loans);
  });

  it('still sends the other vehicle claims after one claim is answered', () => {
    // The server replaces vehicle_claims whole: a claim left out of the body would be erased
    const page = meansPage();
    page.answers.vehicle_claims = { 'asset-7': 'yes' };
    const state = fromReply(page);
    state.answers.vehicle_claims = { ...state.answers.vehicle_claims, 'asset-8': 'no' };
    expect(toPutBody(state).vehicle_claims).toEqual({ 'asset-7': 'yes', 'asset-8': 'no' });
  });
});

describe('fromReply', () => {
  it('gives each loaded line 3 row and circumstance a key by its place', () => {
    const state = fromReply(priyaPage());
    expect(state.answers.line_3_rows.map((row) => row._key)).toEqual(['loaded-0']);
  });
});

describe('adoptRefs', () => {
  it("writes the reply's spouse refs into the rows sent by position and keeps typed amounts", () => {
    const page = withLoans([loan(1, { ref: 'new-1', secured_by: 'new-2', payment: '75.50' })]);
    page.answers.spouse_vehicles = [
      { ref: 'new-2', description: 'Demo van', leased: 'no', claimed: 'yes' },
    ];
    page.answers.vehicle_choice = ['new-2', null];
    const sent = fromReply(page);
    sent.answers.line_3_rows = [{ _key: 'new-3', purpose: 'Demo', amount: '5.00' }];

    const reply = withLoans([
      loan(1, { ref: 'spouse-4', secured_by: 'spouse-7', payment: '1.00' }),
    ]);
    reply.answers.spouse_vehicles = [
      { ref: 'spouse-7', description: 'Demo van', leased: 'no', claimed: 'yes' },
    ];

    const next = adoptRefs(sent, sent, reply);
    expect(next.answers.spouse_vehicles[0].ref).toBe('spouse-7');
    expect(next.answers.spouse_loans[0].ref).toBe('spouse-4');
    expect(next.answers.spouse_loans[0].secured_by).toBe('spouse-7');
    expect(next.answers.vehicle_choice).toEqual(['spouse-7', null]);
    // typed amounts stay as typed; the reply's are never taken
    expect(next.answers.spouse_loans[0].payment).toBe('75.50');
    expect(next.answers.line_3_rows[0]).toEqual({ _key: 'new-3', purpose: 'Demo', amount: '5.00' });
  });

  it('leaves every _key as it was', () => {
    const sent = fromReply(priyaPage());
    const next = adoptRefs(sent, sent, priyaPage());
    expect(next.answers.line_3_rows.map((row) => row._key)).toEqual(['loaded-0']);
  });

  it('leaves a stored ref and a property choice alone', () => {
    const page = withLoans([loan(1), loan(2, { secured_by: 'other' })]);
    const sent = fromReply(page);
    const next = adoptRefs(sent, sent, page);
    expect(next.answers.spouse_loans.map((row) => [row.ref, row.secured_by])).toEqual([
      ['spouse-1', 'home'],
      ['spouse-2', 'other'],
    ]);
  });
});

describe('rowsInputOf', () => {
  it('places a spouse loan by what secures it and what it names', () => {
    const page = withLoans([
      loan(1), // home
      loan(2, { secured_by: 'other', property: 'A Demo boat' }),
      loan(3, { secured_by: 'spouse-1', property: '' }), // a live vehicle
      loan(4, { secured_by: 'spouse-9', property: '' }), // a vehicle that has gone
      loan(5, { on_amounts_owed: 'yes', debt: 21, creditor: '', secured_by: 'other' }),
      loan(6, { on_amounts_owed: 'yes', debt: 21, creditor: '', secured_by: 'home' }), // taken
      loan(7, { on_amounts_owed: 'yes', debt: 99, creditor: '', secured_by: 'home' }), // removed
    ]);
    const rows = rowsInputOf(page, fromReply(page));
    const spouse = rows.debts.filter((debt) => debt.ref.startsWith('spouse-'));
    expect(spouse.map((debt) => [debt.ref, debt.secured_by, debt.on_home, debt.placed])).toEqual([
      ['spouse-1', null, true, true],
      ['spouse-2', null, false, true],
      ['spouse-3', 'spouse-1', false, true],
      ['spouse-4', null, false, false],
      ['spouse-5', null, false, true],
      ['spouse-6', null, true, false],
      ['spouse-7', null, true, false],
    ]);
    expect(rows.debts[0].ref).toBe('debt-11');
  });

  it("counts the spouse's rows only for a married couple filing together and under Yes", () => {
    const page = withLoans([loan(1)]);
    expect(rowsInputOf(page, fromReply(page)).vehicles.map((v) => v.ref)).toEqual([
      'asset-7',
      'spouse-1',
    ]);
    const single = { ...page, married_together: false };
    const rows = rowsInputOf(single, fromReply(single));
    expect(rows.marital_status).toBeNull();
    expect(rows.vehicles.map((v) => v.ref)).toEqual(['asset-7']);
    expect(rows.debts.map((d) => d.ref)).toEqual(['debt-11']);

    const no = withLoans([loan(1)]);
    no.answers.spouse_vehicles_answer = 'no';
    no.answers.spouse_loans_answer = 'no';
    const noRows = rowsInputOf(no, fromReply(no));
    expect(noRows.vehicles.map((v) => v.ref)).toEqual(['asset-7']);
    expect(noRows.debts.map((d) => d.ref)).toEqual(['debt-11']);
  });

  it("reads a filer vehicle's claim as unanswered until the filer gives one, and 60 or more as 60", () => {
    const page = meansPage();
    page.debts = [{ ...KESTREL, payments_left: '60_or_more' }];
    const state = fromReply(page);
    expect(rowsInputOf(page, state).vehicles[0].claimed).toBeNull();
    state.answers.vehicle_claims = { 'asset-7': 'yes' };
    const rows = rowsInputOf(page, state);
    expect(rows.vehicles[0].claimed).toBe(true);
    expect(rows.debts[0].payments_left).toBe(60);
  });

  it('holds the Vehicle 1 and 2 choice only once both are chosen', () => {
    // 'spouse-1' names a vehicle only while the spouse's row is on the page
    const page = withLoans([]);
    const state = fromReply(page);
    state.answers.vehicle_choice = ['asset-7', null];
    expect(rowsInputOf(page, state).vehicle_choice).toBeNull();
    state.answers.vehicle_choice = ['asset-7', 'spouse-1'];
    expect(rowsInputOf(page, state).vehicle_choice).toEqual(['asset-7', 'spouse-1']);
  });
});

describe('gapStateOf', () => {
  it("reads each spouse loan's identity as the gaps do: blank creditor, taken debt, removed debt", () => {
    const page = withLoans([
      loan(1), // identity given
      loan(2, { creditor: '   ' }), // a blank creditor
      loan(3, { on_amounts_owed: 'yes', debt: 21, creditor: '' }), // names debt 21
      loan(4, { on_amounts_owed: 'yes', debt: 21, creditor: '' }), // debt 21 already taken
      loan(5, { on_amounts_owed: 'yes', debt: 99, creditor: '' }), // debt 99 has gone
      loan(6, { on_amounts_owed: null }), // not yet said
    ]);
    const gapState = gapStateOf(page, fromReply(page));
    const spouse = gapState.debts.filter((debt) => debt.ref.startsWith('spouse-'));
    expect(spouse.map((debt) => debt.spouseIdentityGap)).toEqual([
      false,
      true,
      false,
      true,
      true,
      true,
    ]);
    // an Amounts Owed loan is named by the debt's creditor
    expect(spouse[2].creditor).toBe('Demo Lender A');
    expect(gapState.debts.find((debt) => debt.ref === 'debt-11')?.spouseIdentityGap).toBe(false);
  });

  it('reads the line 15 and line 30 caps from the information, and none without it', () => {
    const page = meansPage();
    const gapState = gapStateOf(page, fromReply(page));
    expect([gapState.line15Cap, gapState.line30Cap, gapState.lineFive]).toEqual([
      '250.00',
      '76.00',
      4,
    ]);
    const bare = { ...page, information: null, information_gap: 'no_table' };
    const none = gapStateOf(bare, fromReply(bare));
    expect([none.line15Cap, none.line30Cap, none.lineFive]).toEqual([null, null, null]);
  });

  it("names a filer vehicle's unanswered claim and places the loan on it once claimed", () => {
    const page = meansPage();
    page.answers.spouse_vehicles_answer = 'no';
    page.answers.spouse_loans_answer = 'no';
    const state = fromReply(page);
    expect(gapStateOf(page, state).vehicles).toEqual([
      { ref: 'asset-7', name: 'Honda CR-V EX 2021', claimed: null },
    ]);
    expect(gapStateOf(page, state).lines['debt-11']).toBeNull();
    state.answers.vehicle_claims = { 'asset-7': 'yes' };
    state.debts[0].payments_left = 37;
    state.debts[0].payment_changes = 'no';
    expect(gapStateOf(page, state).lines['debt-11']).toBe('13b');
  });
});

describe('a spouse row and its references', () => {
  it('a spouse row carries a browser key that the save leaves out', () => {
    const page = withLoans([loan(1)]);
    const state = fromReply(page);
    expect(state.answers.spouse_vehicles.map((row) => row._key)).toEqual(['loaded-0']);
    expect(state.answers.spouse_loans.map((row) => row._key)).toEqual(['loaded-0']);
    expect(JSON.stringify(toPutBody(state))).not.toContain('_key');

    // The server gives a new row its id: the ref follows, the key stays, so the row isn't remounted
    state.answers.spouse_vehicles[0].ref = 'new-4';
    const reply = withLoans([loan(1)]);
    reply.answers.spouse_vehicles[0].ref = 'spouse-9';
    const next = adoptRefs(state, state, reply);
    expect(next.answers.spouse_vehicles[0]).toMatchObject({ ref: 'spouse-9', _key: 'loaded-0' });
    expect(next.answers.spouse_loans[0]._key).toBe('loaded-0');
  });

  it('a save reads every reference as the next read would give it back', () => {
    const page = withLoans([
      loan(1, { secured_by: 'home' }),
      loan(2, { secured_by: 'other' }),
      loan(3, { secured_by: 'spouse-1' }),
      loan(4, { secured_by: 'spouse-9' }),
      loan(5, { on_amounts_owed: 'yes', creditor: '', secured_by: 'asset-7' }),
      loan(6, { on_amounts_owed: 'yes', creditor: '', debt: 21, secured_by: 'spouse-1' }),
      loan(7, { on_amounts_owed: 'yes', creditor: '', debt: 99, secured_by: 'spouse-1' }),
      loan(8, { secured_by: 'asset-7' }),
    ]);
    page.answers.vehicle_choice = ['asset-7', 'spouse-9'];
    const body = toPutBody(withLiveRefs(page, fromReply(page)));
    expect(body.spouse_loans.map((row) => [row.secured_by, row.debt])).toEqual([
      ['home', null],
      ['other', null],
      ['spouse-1', null],
      // a vehicle that has gone
      [null, null],
      // a filer's own vehicle on an Amounts Owed row
      [null, null],
      // a debt that is open stays named
      ['spouse-1', 21],
      // a debt that is gone reads as none
      ['spouse-1', null],
      // a typed loan may name the filer's own vehicle
      ['asset-7', null],
    ]);
    expect(body.vehicle_choice).toEqual(['asset-7', null]);
  });
});
