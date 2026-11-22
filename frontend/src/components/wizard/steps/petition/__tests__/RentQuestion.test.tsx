import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { RentQuestion } from '../RentQuestion';
import { rentGap } from '../petitionGaps';
import {
  COURT_FORM_101A_URL,
  COURT_FORM_101B_URL,
  FORM_101A_LINK,
  CLERK_PHONE_WESTERN,
  DELETE_HIDDEN,
  FORM_101A_BOXES_BLANK,
  FORM_101A_DEPOSIT,
  FORM_101A_DEPOSIT_WITH_CLERK,
  LANDLORD_PICK_LABEL,
  FORM_101_LINE_11_LEAD,
  FORM_101A_SAYS,
  FORM_101B_LINK,
  FORM_101B_NOT_PREPARED,
  HIDDEN_ANSWERS,
  NOT_ANSWERED_YET,
  PETITION_GATE_EVICTION,
  PETITION_GATE_RENTS,
  SHOW_HIDDEN,
} from '../../../../../constants/copy';
import {
  FORM_101_LINE_11_EVICTION,
  FORM_101_LINE_11_NOTICE,
  FORM_101_LINE_11_RENT,
  FORM_101A_CERTIFICATION_BOX_1,
  FORM_101A_CERTIFICATION_BOX_2,
  FORM_101A_CERTIFICATION_HEADING,
  FORM_101A_CERTIFICATION_SENTENCE,
  FORM_101A_GATE_SENTENCE,
  FORM_101A_LANDLORD_ADDRESS,
  FORM_101A_LANDLORD_NAME,
  FORM_101A_SERVICE_CONDITIONS,
  FORM_101A_SERVICE_SENTENCE,
  FORM_101A_STAY_HEADING_A,
  FORM_101A_STAY_HEADING_B,
  FORM_101A_STAY_SENTENCE_A,
  FORM_101B_STAY_SENTENCE,
} from '../../../../../constants/formText';
import type { ContractRow, PetitionAnswers } from '../../../../../types/api';

function Harness({
  initial = {},
  touched = false,
  onChange,
  leaseRows = [],
  division = null,
}: {
  initial?: PetitionAnswers;
  touched?: boolean;
  onChange?: (next: PetitionAnswers) => void;
  leaseRows?: ContractRow[];
  division?: 'Eastern' | 'Western' | null;
}) {
  const [answers, setAnswers] = useState<PetitionAnswers>(initial);
  const [left, setLeft] = useState(false);
  return (
    <main>
      <RentQuestion
        answers={answers}
        onChange={(next) => {
          onChange?.(next);
          setAnswers(next);
        }}
        touched={touched || left}
        onLeave={() => setLeft(true)}
        leaseRows={leaseRows}
        division={division}
      />
      <button type="button">Somewhere else</button>
    </main>
  );
}

const radio = (name: string, value: string) =>
  document.querySelector(`input[name="${name}"][value="${value}"]`) as HTMLInputElement;

const notice = () => document.querySelector('.eviction-notice');
const notices = () => Array.from(document.querySelectorAll('.eviction-notice'));
const field = (name: string) =>
  document.querySelector(`[name="${name}"]`) as HTMLInputElement | HTMLSelectElement;

const LEASE: ContractRow = {
  _key: 'new-1',
  counterparty_name: 'Gold Coast Example Residential LLC',
  contract_type: 'lease',
  description: 'Residential lease',
  street_address: '850 N State St',
  street_2: 'c/o Management Office',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60610',
  outside_us: false,
  lease_kind: 'residential',
};
const PAIR: PetitionAnswers = { rents_residence: 'yes', eviction_judgment: 'yes' };

describe('RentQuestion', () => {
  it('asks the eviction question only under a rent Yes', async () => {
    const user = userEvent.setup();
    const changes: PetitionAnswers[] = [];
    render(<Harness onChange={(next) => changes.push(next)} />);
    expect(screen.getByRole('group', { name: new RegExp(FORM_101_LINE_11_RENT) })).toBeVisible();
    const rent = Array.from(
      document.querySelectorAll<HTMLInputElement>('input[name="rents_residence"]')
    );
    expect(rent.map((r) => r.value)).toEqual(['no', 'yes']);
    expect(rent.some((r) => r.checked)).toBe(false);
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();

    await user.click(radio('rents_residence', 'no'));
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();

    await user.click(radio('rents_residence', 'yes'));
    expect(
      screen.getByRole('group', { name: new RegExp(FORM_101_LINE_11_EVICTION) })
    ).toBeVisible();
    const eviction = Array.from(
      document.querySelectorAll<HTMLInputElement>('input[name="eviction_judgment"]')
    );
    expect(eviction.map((r) => r.value)).toEqual(['no', 'yes']);
    expect(eviction.some((r) => r.checked)).toBe(false);
    await user.click(radio('eviction_judgment', 'no'));
    expect(changes.at(-1)).toEqual({ rents_residence: 'yes', eviction_judgment: 'no' });
  });

  it("says what is still missing in the server's words", async () => {
    // The step's one status region shows this sentence (PF2-T9-6): the block has none of its own
    expect(rentGap({})).toBe(PETITION_GATE_RENTS);
    // A stored eviction Yes under an absent rent answer is still the rent gate (PF2-T9-2)
    expect(rentGap({ eviction_judgment: 'yes' })).toBe(PETITION_GATE_RENTS);
    expect(rentGap({ rents_residence: 'yes' })).toBe(PETITION_GATE_EVICTION);
    expect(rentGap({ rents_residence: 'yes', eviction_judgment: 'no' })).toBeNull();
    expect(rentGap({ rents_residence: 'no' })).toBeNull();
    expect(rentGap({ rents_residence: 'no', eviction_judgment: 'yes' })).toBeNull();

    render(<Harness initial={{ rents_residence: 'yes' }} touched />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    // Touched, the unanswered eviction question says so under its radios
    expect(screen.getByText(NOT_ANSWERED_YET)).toBeInTheDocument();
  });

  it('the Form 101A notice shows only under rent Yes and eviction Yes', async () => {
    const user = userEvent.setup();
    // Rent No keeps a stored eviction Yes: no radios and no notice (§6.7), only the line naming the
    // hidden answer (T9-eviction-hidden)
    const { unmount } = render(
      <Harness initial={{ rents_residence: 'no', eviction_judgment: 'yes' }} />
    );
    expect(screen.getByText(HIDDEN_ANSWERS)).toBeInTheDocument();
    expect(notice()).toBeNull();
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();
    expect(screen.queryByText(FORM_101_LINE_11_NOTICE)).not.toBeInTheDocument();
    unmount();

    render(<Harness initial={{ rents_residence: 'yes' }} />);
    expect(notice()).toBeNull();
    await user.click(radio('eviction_judgment', 'no'));
    expect(notice()).toBeNull();
    await user.click(radio('eviction_judgment', 'yes'));
    // Two parts, with the landlord block between them (4b2-R4)
    const parts = notices();
    expect(parts).toHaveLength(2);
    const [head, certification] = parts;
    const piecesOf = (part: Element) =>
      Array.from(part.querySelectorAll('p, li')).map((el) => el.textContent);

    // In §6.7's order (PF2-T9-4): line 11's lead (owner ruling Q8) and Form 101's line; the lead
    // and Form 101A's opening sentence with its two conditions; the 101A link. Then the landlord
    // block. Then the lead, the gate sentence, the certification's heading, its sentence and its
    // two boxes (owner ruling Q11, so (a)'s "both boxes above" names the form's two boxes), DigniFi's
    // two sentences, the lead, the stay passage, paragraph (a) with its heading, then (b) with its
    // heading (owner ruling Q9); DigniFi's 101B sentence; the 101B link
    expect(piecesOf(head)).toEqual([
      FORM_101_LINE_11_LEAD,
      FORM_101_LINE_11_NOTICE,
      FORM_101A_SAYS,
      FORM_101A_SERVICE_SENTENCE,
      ...FORM_101A_SERVICE_CONDITIONS,
      FORM_101A_LINK,
    ]);
    expect(piecesOf(certification)).toEqual([
      FORM_101A_SAYS,
      FORM_101A_GATE_SENTENCE,
      FORM_101A_CERTIFICATION_HEADING,
      FORM_101A_CERTIFICATION_SENTENCE,
      FORM_101A_CERTIFICATION_BOX_1,
      FORM_101A_CERTIFICATION_BOX_2,
      FORM_101A_BOXES_BLANK,
      FORM_101A_DEPOSIT,
      FORM_101A_SAYS,
      FORM_101A_STAY_HEADING_A,
      FORM_101A_STAY_SENTENCE_A,
      FORM_101A_STAY_HEADING_B,
      FORM_101B_STAY_SENTENCE,
      FORM_101B_NOT_PREPARED,
      FORM_101B_LINK,
    ]);
    const name = field('landlord_name');
    expect(head.compareDocumentPosition(name) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(
      certification.compareDocumentPosition(name) & Node.DOCUMENT_POSITION_PRECEDING
    ).toBeTruthy();

    // The forms' own words are marked as quotations, and each lead sits outside its quotation
    const quotes = Array.from(document.querySelectorAll('.eviction-notice blockquote'));
    expect(quotes).toHaveLength(4);
    expect(quotes[0].textContent).toBe(FORM_101_LINE_11_NOTICE);
    expect(quotes[2].textContent).toBe(
      FORM_101A_GATE_SENTENCE +
        FORM_101A_CERTIFICATION_HEADING +
        FORM_101A_CERTIFICATION_SENTENCE +
        FORM_101A_CERTIFICATION_BOX_1 +
        FORM_101A_CERTIFICATION_BOX_2
    );
    expect(quotes[3].textContent).toBe(
      FORM_101A_STAY_HEADING_A +
        FORM_101A_STAY_SENTENCE_A +
        FORM_101A_STAY_HEADING_B +
        FORM_101B_STAY_SENTENCE
    );
    // The two boxes are a list, as the form prints them, under the certification's sentence
    const boxes = Array.from(quotes[2].querySelectorAll('li')).map((el) => el.textContent);
    expect(boxes).toEqual([FORM_101A_CERTIFICATION_BOX_1, FORM_101A_CERTIFICATION_BOX_2]);
    // `.info-box` lays its children out as one flex row, so each part's pieces sit in one child
    // and read top to bottom, not as side-by-side columns
    expect(head.children).toHaveLength(1);
    expect(certification.children).toHaveLength(1);

    const link101A = screen.getByRole('link', { name: FORM_101A_LINK });
    expect(link101A).toHaveAttribute('href', COURT_FORM_101A_URL);
    expect(link101A).toHaveAttribute('target', '_blank');
    expect(link101A).toHaveAttribute('rel', 'noopener noreferrer');
    const link101B = screen.getByRole('link', { name: FORM_101B_LINK });
    expect(link101B).toHaveAttribute('href', COURT_FORM_101B_URL);
    expect(link101B).toHaveAttribute('target', '_blank');
    expect(link101B).toHaveAttribute('rel', 'noopener noreferrer');

    // No county, no clerk's number: no telephone number anywhere in the notice
    expect(head.textContent + certification.textContent).not.toMatch(
      /\(?\d{3}\)?[\s.-]?\d{3}-\d{4}/
    );

    // Moving rent to No hides the notice and the eviction question, and keeps the answer stored
    await user.click(radio('rents_residence', 'no'));
    expect(notice()).toBeNull();
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();
    expect(screen.getByText(HIDDEN_ANSWERS)).toBeInTheDocument();
  });

  it('keeps an eviction answer under a rent No, hidden, with Show and Delete (T9-eviction-hidden)', async () => {
    const user = userEvent.setup();
    const changes: PetitionAnswers[] = [];
    const stored: PetitionAnswers = { rents_residence: 'no', eviction_judgment: 'yes' };
    // Nothing reappears unannounced (spec line 177): the stored answer is named, not shown
    const { unmount } = render(<Harness initial={stored} />);
    expect(screen.getByText(HIDDEN_ANSWERS)).toBeInTheDocument();
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();
    await user.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    expect(radio('eviction_judgment', 'yes')).toBeChecked();
    // Shown under the rent No, the answer is there to read or change; the notice stays off (§6.7)
    expect(notice()).toBeNull();
    unmount();

    render(<Harness initial={stored} onChange={(next) => changes.push(next)} />);
    await user.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
    // Delete clears the eviction answer and every landlord key (4b2-R6)
    expect(changes.at(-1)).toEqual({
      rents_residence: 'no',
      eviction_judgment: null,
      landlord_name: null,
      landlord_street: null,
      landlord_city: null,
      landlord_state: null,
      landlord_zip: null,
    });
  });

  it('a rent No with no eviction answer stored shows no hidden-answers line', async () => {
    const user = userEvent.setup();
    render(<Harness initial={{ rents_residence: 'no' }} />);
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
    // A rent moved from Yes back to No with the eviction question never answered leaves nothing
    // to hide either: no line, and no eviction radios
    await user.click(radio('rents_residence', 'yes'));
    await user.click(radio('rents_residence', 'no'));
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();
  });

  it('a rent answer changed after Show hides the eviction answer again under the next No', async () => {
    // Show opens the stored answer once: a later rent Yes then No names it again with the hidden
    // line, never leaves its radios open under the No unannounced
    const user = userEvent.setup();
    render(<Harness initial={{ rents_residence: 'no', eviction_judgment: 'yes' }} />);
    await user.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    expect(radio('eviction_judgment', 'yes')).toBeChecked();
    await user.click(radio('rents_residence', 'yes'));
    await user.click(radio('rents_residence', 'no'));
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();
    expect(screen.getByText(HIDDEN_ANSWERS)).toBeInTheDocument();
  });

  it('eviction radios shown under a rent No are not required; under a rent Yes they are', async () => {
    // Under a rent No the eviction answer asks nothing of the filer (rentGap is null), so its
    // radios must not be announced as required
    const user = userEvent.setup();
    const { unmount } = render(
      <Harness initial={{ rents_residence: 'no', eviction_judgment: 'no' }} />
    );
    await user.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    for (const value of ['no', 'yes']) {
      expect(radio('eviction_judgment', value)).not.toHaveAttribute('aria-required');
    }
    const group = screen.getByRole('group', { name: new RegExp(FORM_101_LINE_11_EVICTION) });
    expect(group.querySelector('legend .required-indicator')).toBeNull();
    unmount();

    render(<Harness initial={{ rents_residence: 'yes' }} />);
    for (const value of ['no', 'yes']) {
      expect(radio('eviction_judgment', value)).toHaveAttribute('aria-required', 'true');
    }
  });

  it('the notice says nothing about Form 101A not being prepared', () => {
    render(<Harness initial={PAIR} />);
    expect(document.body.textContent).not.toMatch(/doesn't prepare Form 101A/);
  });

  it("the deposit sentence names the division's clerk and no number before a county", () => {
    const { unmount } = render(<Harness initial={PAIR} division="Western" />);
    expect(
      screen.getByText(`${FORM_101A_DEPOSIT_WITH_CLERK} ${CLERK_PHONE_WESTERN}.`)
    ).toBeInTheDocument();
    unmount();
    render(<Harness initial={PAIR} division={null} />);
    const sentence = screen.getByText(FORM_101A_DEPOSIT);
    expect(sentence.textContent).not.toMatch(/\d/);
  });

  it("B58's sentence sits directly under the second certification box", () => {
    render(<Harness initial={PAIR} />);
    const box2 = screen.getByText(FORM_101A_CERTIFICATION_BOX_2);
    const quote = box2.closest('blockquote') as HTMLElement;
    expect(quote.lastElementChild?.lastElementChild).toBe(box2);
    expect(quote.nextElementSibling?.textContent).toBe(FORM_101A_BOXES_BLANK);
  });

  it('no pick is offered without a residential lease', () => {
    const { unmount } = render(<Harness initial={PAIR} />);
    expect(document.querySelector('select[name="landlord_pick"]')).toBeNull();
    unmount();
    render(<Harness initial={PAIR} leaseRows={[{ ...LEASE, lease_kind: 'vehicle' }]} />);
    expect(document.querySelector('select[name="landlord_pick"]')).toBeNull();
    expect(screen.getByText(FORM_101A_LANDLORD_NAME)).toBeInTheDocument();
    expect(screen.getByRole('group', { name: FORM_101A_LANDLORD_ADDRESS })).toBeVisible();
  });

  it('picking a lease fills the five boxes and the filer can change them', async () => {
    const user = userEvent.setup();
    render(<Harness initial={PAIR} leaseRows={[LEASE]} />);
    expect(screen.getByLabelText(LANDLORD_PICK_LABEL)).toBeVisible();
    await user.selectOptions(field('landlord_pick'), 'new-1');
    expect(field('landlord_name')).toHaveValue('Gold Coast Example Residential LLC');
    expect(field('landlord_street')).toHaveValue('850 N State St, c/o Management Office');
    expect(field('landlord_city')).toHaveValue('Chicago');
    expect(field('landlord_state')).toHaveValue('IL');
    expect(field('landlord_zip')).toHaveValue('60610');
    // The pick goes back to its placeholder, so the same lease can be picked again
    expect(field('landlord_pick')).toHaveValue('');

    await user.clear(field('landlord_name'));
    await user.type(field('landlord_name'), 'Demo Property Holdings LLC');
    expect(field('landlord_name')).toHaveValue('Demo Property Holdings LLC');
    expect(field('landlord_city')).toHaveValue('Chicago');
  });

  const STORED_LANDLORD: PetitionAnswers = {
    landlord_name: 'Demo Property Holdings LLC',
    landlord_street: '100 Demo St',
    landlord_city: 'Chicago',
    landlord_state: 'IL',
    landlord_zip: '60601',
  };
  const NO_LANDLORD = {
    landlord_name: null,
    landlord_street: null,
    landlord_city: null,
    landlord_state: null,
    landlord_zip: null,
  };

  it('landlord answers kept under an eviction No hide behind one line that offers Show and Delete', async () => {
    const user = userEvent.setup();
    const changes: PetitionAnswers[] = [];
    const stored: PetitionAnswers = {
      rents_residence: 'yes',
      eviction_judgment: 'no',
      ...STORED_LANDLORD,
    };
    const { unmount } = render(<Harness initial={stored} />);
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    expect(document.querySelector('input[name="landlord_name"]')).toBeNull();
    await user.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    expect(field('landlord_name')).toHaveValue('Demo Property Holdings LLC');
    expect(notice()).toBeNull();
    unmount();

    render(<Harness initial={stored} onChange={(next) => changes.push(next)} />);
    await user.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(changes.at(-1)).toEqual({
      rents_residence: 'yes',
      eviction_judgment: 'no',
      ...NO_LANDLORD,
    });
  });

  it('landlord answers kept under a rent No hide behind one line that offers Show and Delete', async () => {
    const user = userEvent.setup();
    const changes: PetitionAnswers[] = [];
    // A stale eviction Yes under a rent No: no notice, no landlord boxes, one line
    const stored: PetitionAnswers = {
      rents_residence: 'no',
      eviction_judgment: 'yes',
      ...STORED_LANDLORD,
    };
    render(<Harness initial={stored} onChange={(next) => changes.push(next)} />);
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    expect(notice()).toBeNull();
    expect(document.querySelector('input[name="landlord_name"]')).toBeNull();
    await user.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(changes.at(-1)).toEqual({
      rents_residence: 'no',
      eviction_judgment: null,
      ...NO_LANDLORD,
    });
  });

  it('has no accessibility violations with the notice open', async () => {
    const { container } = render(
      <Harness initial={{ rents_residence: 'yes', eviction_judgment: 'yes' }} touched />
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations with the landlord block open', async () => {
    const { container } = render(
      <Harness initial={{ ...PAIR, ...STORED_LANDLORD }} leaseRows={[LEASE]} division="Eastern" />
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
