import { useState } from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { PlansStep } from '../PlansStep';
import { fill } from '../claims/claimNames';
import * as copy from '../../../../constants/copy';
import * as formText from '../../../../constants/formText';
import {
  FORM_108_ASSUMED,
  FORM_108_CREDITOR_LABEL,
  FORM_108_DEADLINE,
  FORM_108_INTENTIONS,
  FORM_108_LESSOR_LABEL,
  STATUTE_365_P_2,
  STATUTE_365_P_2_CITATION,
  STATUTE_521_A_2_A,
  STATUTE_521_A_2_A_CITATION,
  STATUTE_524_C,
  STATUTE_524_C_CITATION,
  STATUTE_722,
  STATUTE_722_CITATION,
} from '../../../../constants/formText';
import type { ContractRow, DebtRow, ExemptState, IntentionAnswers } from '../../../../types/api';

// Your Plans asks Form 108's questions of the rows the server asks them of, in the form's words,
// with nothing chosen for the filer and nothing that holds Continue (forms step 4e).

const car: DebtRow = {
  _key: '7',
  id: 7,
  creditor_name: 'Demo Auto Credit',
  is_secured: true,
  is_draft: false,
  collateral_description: '2019 Demo Sedan',
};
const home: DebtRow = {
  _key: '8',
  id: 8,
  creditor_name: 'Demo Home Loans',
  is_secured: true,
  is_draft: false,
  collateral_description: '12 Demo Street',
};
const card: DebtRow = { _key: '9', id: 9, creditor_name: 'Demo Card Services', is_secured: false };
const draft: DebtRow = {
  ...car,
  _key: '10',
  id: 10,
  creditor_name: 'Demo Scanned',
  is_draft: true,
};
const unsaved: DebtRow = { ...car, _key: 'new-1', id: undefined, creditor_name: 'Demo New' };

const carLease: ContractRow = {
  _key: '4',
  id: 4,
  counterparty_name: 'Demo Leasing',
  contract_type: 'lease',
  description: 'Car lease',
  lease_kind: 'vehicle',
};
const apartment: ContractRow = {
  ...carLease,
  _key: '5',
  id: 5,
  counterparty_name: 'Demo Apartments',
  description: 'Apartment lease',
  lease_kind: 'residential',
};

interface HarnessProps {
  debts?: DebtRow[];
  contracts?: ContractRow[];
  initial?: IntentionAnswers;
  exempt?: Record<string, ExemptState>;
  onAnswersChange?: (next: IntentionAnswers) => void;
  onGoToStep?: (key: string) => void;
  onValidationChange?: (valid: boolean) => void;
}

/** The wizard's part: it holds the answers */
function Harness({
  debts = [car],
  contracts = [carLease],
  initial = {},
  exempt = {},
  onAnswersChange = () => {},
  onGoToStep = () => {},
  onValidationChange = () => {},
}: HarnessProps) {
  const [answers, setAnswers] = useState<IntentionAnswers>(initial);
  return (
    <PlansStep
      debts={debts}
      contracts={contracts}
      answers={answers}
      onAnswersChange={(next) => {
        setAnswers(next);
        onAnswersChange(next);
      }}
      exempt={exempt}
      onGoToStep={onGoToStep}
      onValidationChange={onValidationChange}
    />
  );
}

const row = (name: string) => screen.getByRole('group', { name });
const radios = (name: string) =>
  Array.from(document.querySelectorAll<HTMLInputElement>(`input[type="radio"][name="${name}"]`));
const box = (name: string) => document.querySelector(`[name="${name}"]`) as HTMLTextAreaElement;
const status = () => screen.getByRole('status');
const labelOf = (input: HTMLInputElement) => input.closest('label')!.textContent!.trim();

describe('Your Plans', () => {
  it('lists each confirmed secured debt and each lease of personal property', () => {
    render(<Harness debts={[car, home]} contracts={[carLease]} />);
    expect(row('Demo Auto Credit')).toBeInTheDocument();
    expect(row('Demo Home Loans')).toBeInTheDocument();
    expect(row('Demo Leasing')).toBeInTheDocument();
    expect(within(row('Demo Auto Credit')).getByText(copy.PLANS_FROM_DEBTS)).toBeInTheDocument();
    expect(within(row('Demo Leasing')).getByText(copy.PLANS_FROM_CONTRACTS)).toBeInTheDocument();
  });

  it('leaves out a residential lease, an unsecured debt and a scanned draft', () => {
    render(<Harness debts={[car, card, draft, unsaved]} contracts={[carLease, apartment]} />);
    const legends = Array.from(document.querySelectorAll('fieldset > legend'));
    expect(legends.map((legend) => legend.textContent)).toEqual([
      'Demo Auto Credit',
      'Demo Leasing',
    ]);
  });

  it('shows the four choices in the form\'s order and "I haven\'t decided yet." last, none checked', () => {
    render(<Harness />);
    const choices = radios('plans_secured_0_intention');
    expect(choices.map((input) => input.value)).toEqual([
      'surrender',
      'retain_redeem',
      'retain_reaffirm',
      'retain_explain',
      'undecided',
    ]);
    expect(choices.map(labelOf)).toEqual([
      FORM_108_INTENTIONS.surrender,
      FORM_108_INTENTIONS.retain_redeem,
      FORM_108_INTENTIONS.retain_reaffirm,
      FORM_108_INTENTIONS.retain_explain,
      copy.PLANS_UNDECIDED,
    ]);
    expect(choices.filter((input) => input.checked)).toEqual([]);
  });

  it('asks for the filer\'s words only under "Retain the property and [explain]:"', async () => {
    const onAnswersChange = vi.fn();
    render(<Harness onAnswersChange={onAnswersChange} />);
    const user = userEvent.setup();
    for (const choice of ['surrender', 'retain_redeem', 'retain_reaffirm', 'undecided']) {
      await user.click(radios('plans_secured_0_intention').find((r) => r.value === choice)!);
      expect(box('plans_secured_0_explain')).toBeNull();
    }
    await user.click(
      radios('plans_secured_0_intention').find((r) => r.value === 'retain_explain')!
    );
    expect(screen.getByLabelText(copy.PLANS_EXPLAIN_LABEL)).toBe(box('plans_secured_0_explain'));
    await user.type(box('plans_secured_0_explain'), 'I keep paying.');
    expect(onAnswersChange).toHaveBeenLastCalledWith({
      secured: { 7: { intention: 'retain_explain', explain: 'I keep paying.' } },
    });
  });

  it('keeps words typed under another choice behind Show and Delete', async () => {
    const onAnswersChange = vi.fn();
    render(
      <Harness
        initial={{ secured: { 7: { intention: 'surrender', explain: 'Kept words' } } }}
        onAnswersChange={onAnswersChange}
      />
    );
    const user = userEvent.setup();
    expect(box('plans_secured_0_explain')).toBeNull();
    expect(screen.getByText(copy.HIDDEN_ANSWERS)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: copy.SHOW_HIDDEN }));
    expect(box('plans_secured_0_explain').value).toBe('Kept words');
    // A new choice hides them again; Delete removes them and keeps the choice
    await user.click(radios('plans_secured_0_intention').find((r) => r.value === 'retain_redeem')!);
    expect(box('plans_secured_0_explain')).toBeNull();
    await user.click(screen.getByRole('button', { name: copy.DELETE_HIDDEN }));
    expect(onAnswersChange).toHaveBeenLastCalledWith({
      secured: { 7: { intention: 'retain_redeem' } },
    });
    expect(screen.queryByText(copy.HIDDEN_ANSWERS)).toBeNull();
  });

  it('a too-long explanation shows its note and leaves Continue enabled', () => {
    const onValidationChange = vi.fn();
    const words = 'word '.repeat(20).trim(); // 99 characters, over Form 108's 62
    render(
      <Harness
        initial={{ secured: { 7: { intention: 'retain_explain', explain: words } } }}
        onValidationChange={onValidationChange}
      />
    );
    const note = fill(copy.SCHEDULE_I_DETAIL_TOO_LONG, {
      label: copy.CLAIM_TEXT_LABELS.explain,
      form: 'Form 108',
    });
    expect(screen.getByText(note)).toBeInTheDocument();
    expect(box('plans_secured_0_explain')).toHaveAccessibleDescription(note);
    expect(box('plans_secured_0_explain').value).toBe(words);
    expect(onValidationChange).toHaveBeenLastCalledWith(true);
    expect(onValidationChange).not.toHaveBeenCalledWith(false);
  });

  it('counts the words trimmed, so spaces around them never raise the note (T5-R1)', () => {
    const words = `   ${'a'.repeat(62)}   `;
    render(
      <Harness initial={{ secured: { 7: { intention: 'retain_explain', explain: words } } }} />
    );
    expect(screen.queryByText(/is too long for its box/)).toBeNull();
  });

  it.each<[ExemptState, string]>([
    ['listed', copy.PLANS_EXEMPT_LISTED],
    ['not_claiming', copy.PLANS_EXEMPT_NOT_CLAIMING],
    ['later', copy.PLANS_EXEMPT_LATER],
    ['not_named', copy.PLANS_EXEMPT_NOT_NAMED],
    ['no_property', copy.PLANS_EXEMPT_NO_PROPERTY],
  ])("shows one exempt sentence per row from Schedule C's answers (%s)", (state, sentence) => {
    render(<Harness debts={[car, home]} exempt={{ 7: state }} />);
    const carRow = within(row('Demo Auto Credit'));
    expect(carRow.getByText(formText.FORM_108_EXEMPT_QUESTION)).toBeInTheDocument();
    expect(carRow.getByText(sentence)).toBeInTheDocument();
    const others = Object.values({
      a: copy.PLANS_EXEMPT_LISTED,
      b: copy.PLANS_EXEMPT_NOT_CLAIMING,
      c: copy.PLANS_EXEMPT_LATER,
      d: copy.PLANS_EXEMPT_NOT_NAMED,
      e: copy.PLANS_EXEMPT_NO_PROPERTY,
    }).filter((other) => other !== sentence);
    for (const other of others) expect(screen.queryByText(other)).toBeNull();
    // A debt with no state (secured since the read) shows no exempt line
    expect(
      within(row('Demo Home Loans')).queryByText(formText.FORM_108_EXEMPT_QUESTION)
    ).toBeNull();
  });

  it('asks "Will the lease be assumed?" as No, Yes, then "I haven\'t decided yet."', async () => {
    const onAnswersChange = vi.fn();
    render(<Harness debts={[]} onAnswersChange={onAnswersChange} />);
    expect(screen.getByText(formText.FORM_108_ASSUMED_QUESTION)).toBeInTheDocument();
    expect(screen.getByText(formText.FORM_108_ASSUME_SENTENCE)).toBeInTheDocument();
    const choices = radios('plans_lease_0_assumed');
    expect(choices.map((input) => input.value)).toEqual(['no', 'yes', 'undecided']);
    expect(choices.map(labelOf)).toEqual([
      FORM_108_ASSUMED.no,
      FORM_108_ASSUMED.yes,
      copy.PLANS_UNDECIDED,
    ]);
    expect(choices.filter((input) => input.checked)).toEqual([]);
    await userEvent.setup().click(choices[1]);
    expect(onAnswersChange).toHaveBeenLastCalledWith({ leases: { 4: { assumed: 'yes' } } });
  });

  it("shows the form's deadline sentence as the form's words", () => {
    render(<Harness />);
    const sentence = screen.getByText(FORM_108_DEADLINE);
    expect(sentence.tagName).toBe('BLOCKQUOTE');
    expect(screen.getByText(copy.PLANS_DEADLINE_LABEL)).toBeInTheDocument();
  });

  it('renders each definition once per Part with its own question as its name', async () => {
    render(<Harness debts={[car, home]} contracts={[carLease]} />);
    const names = [
      copy.WHAT_DOES_SURRENDER_MEAN,
      copy.WHAT_DOES_REDEEM_MEAN,
      copy.WHAT_DOES_REAFFIRM_MEAN,
      copy.WHAT_DOES_EXPLAIN_MEAN,
      copy.WHAT_DOES_ASSUME_MEAN,
    ];
    expect(new Set(names).size).toBe(5);
    const summaries = Array.from(document.querySelectorAll('summary'));
    expect(summaries.map((summary) => summary.textContent)).toEqual(names);
    const citations: Record<string, [string, string]> = {
      [copy.WHAT_DOES_SURRENDER_MEAN]: [STATUTE_521_A_2_A_CITATION, STATUTE_521_A_2_A],
      [copy.WHAT_DOES_REDEEM_MEAN]: [STATUTE_722_CITATION, STATUTE_722],
      [copy.WHAT_DOES_REAFFIRM_MEAN]: [STATUTE_524_C_CITATION, STATUTE_524_C],
      [copy.WHAT_DOES_EXPLAIN_MEAN]: [STATUTE_521_A_2_A_CITATION, STATUTE_521_A_2_A],
      [copy.WHAT_DOES_ASSUME_MEAN]: [STATUTE_365_P_2_CITATION, STATUTE_365_P_2],
    };
    for (const summary of summaries) {
      const panel = summary.closest('details')!;
      const [citation, statute] = citations[summary.textContent!];
      const paragraphs = Array.from(panel.querySelectorAll('blockquote p'));
      expect(paragraphs.map((p) => p.textContent)).toEqual(statute.split('\n'));
      const help = Array.from(panel.querySelectorAll(':scope > p')).map((p) => p.textContent);
      // the citation, then the closing pointer (E1)
      expect(help).toEqual([citation, copy.PLANS_EFFECTS_HELP]);
    }
    // Four in Part 1 and one in Part 2, never one a row
    const [partOne, partTwo] = screen.getAllByRole('heading', { level: 4 });
    expect(partOne.parentElement!.querySelectorAll('details')).toHaveLength(4);
    expect(partTwo.parentElement!.querySelectorAll('details')).toHaveLength(1);
  });

  it('every definition starts closed', () => {
    render(<Harness />);
    const panels = Array.from(document.querySelectorAll('details'));
    expect(panels).toHaveLength(5);
    for (const panel of panels) expect(panel).not.toHaveAttribute('open');
  });

  it("the filer's words box starts empty and suggests nothing", async () => {
    render(<Harness />);
    await userEvent
      .setup()
      .click(radios('plans_secured_0_intention').find((r) => r.value === 'retain_explain')!);
    const words = box('plans_secured_0_explain');
    expect(words.value).toBe('');
    expect(words).not.toHaveAttribute('placeholder');
    expect(words.defaultValue).toBe('');
    expect(words.maxLength === -1 || words.maxLength >= 500).toBe(true);
  });

  it("shows each row's name under the form's own label", () => {
    render(<Harness />);
    expect(
      within(row('Demo Auto Credit')).getByText(FORM_108_CREDITOR_LABEL).parentElement
    ).toHaveTextContent(`${FORM_108_CREDITOR_LABEL} Demo Auto Credit`);
    expect(
      within(row('Demo Leasing')).getByText(FORM_108_LESSOR_LABEL).parentElement
    ).toHaveTextContent(`${FORM_108_LESSOR_LABEL} Demo Leasing`);
    expect(
      within(row('Demo Auto Credit')).getByText(formText.FORM_108_PROPERTY_LABEL).parentElement
    ).toHaveTextContent(`${formText.FORM_108_PROPERTY_LABEL} 2019 Demo Sedan`);
    expect(
      within(row('Demo Leasing')).getByText(formText.FORM_108_LEASED_PROPERTY_LABEL).parentElement
    ).toHaveTextContent(`${formText.FORM_108_LEASED_PROPERTY_LABEL} Car lease`);
  });

  it('lists each open row once in a status region and nothing once every row is chosen', async () => {
    render(
      <Harness debts={[car, home]} initial={{ secured: { 8: { intention: 'undecided' } } }} />
    );
    const sentences = [
      fill(copy.INTENTION_GAP_NONE, { name: 'Demo Auto Credit' }),
      fill(copy.INTENTION_GAP_UNDECIDED, { name: 'Demo Home Loans' }),
      fill(copy.LEASE_GAP_NONE, { name: 'Demo Leasing' }),
    ];
    expect(screen.queryByRole('alert')).toBeNull();
    expect(Array.from(status().querySelectorAll('p')).map((p) => p.textContent)).toEqual(sentences);
    const user = userEvent.setup();
    await user.click(radios('plans_secured_0_intention')[0]);
    await user.click(radios('plans_secured_1_intention')[1]);
    await user.click(radios('plans_lease_0_assumed')[0]);
    expect(status()).toBeEmptyDOMElement();
  });

  it("puts the step's heading under the wizard's", () => {
    render(<Harness />);
    expect(screen.getByRole('heading', { name: copy.PLANS_TITLE, level: 3 })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: formText.FORM_108_PART_1_HEADING, level: 4 })
    ).toBeInTheDocument();
  });

  it('with no secured debt or lease, states the basis and links to both steps', async () => {
    const onGoToStep = vi.fn();
    render(<Harness debts={[card, draft]} contracts={[apartment]} onGoToStep={onGoToStep} />);
    const sentence = screen.getByText((_, element) =>
      element?.tagName === 'P' ? element.textContent === copy.PLANS_NOT_APPLICABLE : false
    );
    expect(sentence).toBeInTheDocument();
    expect(screen.queryByRole('group')).toBeNull();
    expect(screen.queryByRole('status')).toBeNull();
    const user = userEvent.setup();
    await user.click(within(sentence).getByRole('button', { name: 'Amounts Owed' }));
    expect(onGoToStep).toHaveBeenLastCalledWith('debts');
    await user.click(within(sentence).getByRole('button', { name: 'Contracts & Leases' }));
    expect(onGoToStep).toHaveBeenLastCalledWith('contracts');
  });

  it('reports the step valid with every choice open', () => {
    const onValidationChange = vi.fn();
    render(<Harness debts={[car, home]} onValidationChange={onValidationChange} />);
    expect(onValidationChange).toHaveBeenCalledWith(true);
    expect(onValidationChange).not.toHaveBeenCalledWith(false);
  });

  it('passes axe', async () => {
    const full = render(
      <Harness
        debts={[car, home]}
        initial={{ secured: { 7: { intention: 'retain_explain', explain: 'x'.repeat(80) } } }}
        exempt={{ 7: 'listed', 8: 'later' }}
      />
    );
    expect(await axe(full.container)).toHaveNoViolations();
    full.unmount();
    const empty = render(<Harness debts={[]} contracts={[]} />);
    expect(await axe(empty.container)).toHaveNoViolations();
  });
});

describe("the statutes' own words (uscode.house.gov, fetched 2026-11-24)", () => {
  it('pins each provision word for word', () => {
    expect(STATUTE_521_A_2_A_CITATION).toBe('11 U.S.C. § 521(a)(2)(A)');
    expect(STATUTE_521_A_2_A).toBe(
      '(a) The debtor shall—\n[…]\n(2) if an individual debtor’s schedule of assets and liabilities includes debts which are secured by property of the estate—\n(A) within thirty days after the date of the filing of a petition under chapter 7 of this title or on or before the date of the meeting of creditors, whichever is earlier, or within such additional time as the court, for cause, within such period fixes, file with the clerk a statement of his intention with respect to the retention or surrender of such property and, if applicable, specifying that such property is claimed as exempt, that the debtor intends to redeem such property, or that the debtor intends to reaffirm debts secured by such property; and\n[…]'
    );
    expect(STATUTE_722_CITATION).toBe('11 U.S.C. § 722');
    expect(STATUTE_722).toBe(
      'An individual debtor may, whether or not the debtor has waived the right to redeem under this section, redeem tangible personal property intended primarily for personal, family, or household use, from a lien securing a dischargeable consumer debt, if such property is exempted under section 522 of this title or has been abandoned under section 554 of this title, by paying the holder of such lien the amount of the allowed secured claim of such holder that is secured by such lien in full at the time of redemption.'
    );
    expect(STATUTE_524_C_CITATION).toBe('11 U.S.C. § 524(c)');
    expect(STATUTE_524_C).toBe(
      '(c) An agreement between a holder of a claim and the debtor, the consideration for which, in whole or in part, is based on a debt that is dischargeable in a case under this title is enforceable only to any extent enforceable under applicable nonbankruptcy law, whether or not discharge of such debt is waived, only if—\n(1) such agreement was made before the granting of the discharge under section 727, 1141, 1192, 1228, or 1328 of this title;\n(2) the debtor received the disclosures described in subsection (k) at or before the time at which the debtor signed the agreement;\n(3) such agreement has been filed with the court and, if applicable, accompanied by a declaration or an affidavit of the attorney that represented the debtor during the course of negotiating an agreement under this subsection, which states that—\n(A) such agreement represents a fully informed and voluntary agreement by the debtor;\n(B) such agreement does not impose an undue hardship on the debtor or a dependent of the debtor; and\n(C) the attorney fully advised the debtor of the legal effect and consequences of—\n(i) an agreement of the kind specified in this subsection; and\n(ii) any default under such an agreement;\n(4) the debtor has not rescinded such agreement at any time prior to discharge or within sixty days after such agreement is filed with the court, whichever occurs later, by giving notice of rescission to the holder of such claim;\n(5) the provisions of subsection (d) of this section have been complied with; and\n(6) (A) in a case concerning an individual who was not represented by an attorney during the course of negotiating an agreement under this subsection, the court approves such agreement as—\n(i) not imposing an undue hardship on the debtor or a dependent of the debtor; and\n(ii) in the best interest of the debtor.\n(B) Subparagraph (A) shall not apply to the extent that such debt is a consumer debt secured by real property.'
    );
    expect(STATUTE_365_P_2_CITATION).toBe('11 U.S.C. § 365(p)(2)');
    expect(STATUTE_365_P_2).toBe(
      '(2) (A) If the debtor in a case under chapter 7 is an individual, the debtor may notify the creditor in writing that the debtor desires to assume the lease. Upon being so notified, the creditor may, at its option, notify the debtor that it is willing to have the lease assumed by the debtor and may condition such assumption on cure of any outstanding default on terms set by the contract.\n(B) If, not later than 30 days after notice is provided under subparagraph (A), the debtor notifies the lessor in writing that the lease is assumed, the liability under the lease will be assumed by the debtor and not by the estate.\n(C) The stay under section 362 and the injunction under section 524(a)(2) shall not be violated by notification of the debtor and negotiation of cure under this subsection.'
    );
  });

  it("§ 521's quote marks each part it leaves out, on its own line", () => {
    const lines = STATUTE_521_A_2_A.split('\n');
    expect(lines).toHaveLength(5);
    expect([lines[1], lines[4]]).toEqual(['[…]', '[…]']);
    expect(lines[0]).toBe('(a) The debtor shall—');
  });

  it("holds no publisher's word joiner and no non-breaking space", () => {
    for (const text of [STATUTE_521_A_2_A, STATUTE_722, STATUTE_524_C, STATUTE_365_P_2]) {
      expect(text).not.toContain('⁠');
      expect(text).not.toContain(' ');
    }
  });
});
