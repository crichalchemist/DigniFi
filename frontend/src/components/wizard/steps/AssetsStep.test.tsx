import { useEffect, useState } from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, expect, it, vi } from 'vitest';
import { AssetsStep } from './AssetsStep';
import { firstIncompletePart, partIsComplete, shownLines } from './assets/assetGaps';
import { AB_PARTS, ASSET_LINES } from '../../../constants/assetLines';
import {
  LEASE_NOTE,
  NOTHING_TO_LIST_NOTE,
  VALUE_UNKNOWN_HEADING,
  VALUE_UNKNOWN_NOTE,
} from '../../../constants/copy';
import {
  AB_LINE_WORDS,
  AB_PERSONAL_INFO_QUESTION,
  AB_PROPERTY_KIND_QUESTION,
  AB_WHO_QUESTION,
} from '../../../constants/formText';
import { hydrateAmounts } from '../../../utils/parseAmount';
import type { AssetInfo, AssetLineAnswer, WizardRow } from '../../../types/api';

type Row = WizardRow<AssetInfo>;
type Answers = Record<string, AssetLineAnswer>;

/** What the step last handed its parent: the step holds no copies, so this is the filer's work */
const latest: { rows: Row[]; answers: Answers; valid: boolean | null } = {
  rows: [],
  answers: {},
  valid: null,
};

function Walk({
  part,
  rows: startRows = [],
  answers: startAnswers = {},
}: {
  part: number;
  rows?: Row[];
  answers?: Answers;
}) {
  const [rows, setRows] = useState(startRows);
  const [answers, setAnswers] = useState(startAnswers);
  useEffect(() => {
    latest.rows = rows;
    latest.answers = answers;
  }, [rows, answers]);
  return (
    <AssetsStep
      rows={rows}
      onRowsChange={setRows}
      answers={answers}
      onAnswersChange={setAnswers}
      part={part}
      onValidationChange={(valid) => {
        latest.valid = valid;
      }}
    />
  );
}

const field = (name: string) => document.querySelector(`[name="${name}"]`) as HTMLInputElement;
const radio = (key: string, value: 'yes' | 'no') =>
  document.querySelector(`input[name="line_${key}_answer"][value="${value}"]`) as HTMLInputElement;
const type = (name: string, value: string) => fireEvent.change(field(name), { target: { value } });
const say = (key: string, value: 'yes' | 'no') => fireEvent.click(radio(key, value));
const linesOf = (part: number) => ASSET_LINES.filter((line) => line.part === part);
const allNo = (part: number): Answers =>
  Object.fromEntries(linesOf(part).map((line) => [line.key, 'no' as const]));

function makeRow(overrides: Partial<Row> & { ab_line: string | null }): Row {
  return {
    _key: `row-${overrides.ab_line}-${Math.random()}`,
    description: 'Something I own',
    current_value: 100,
    entire_value: null,
    details: {},
    ...overrides,
  };
}

describe('AssetsStep', () => {
  it('starts with neither No nor Yes selected on any line', () => {
    for (const part of AB_PARTS) {
      const { unmount } = render(<Walk part={part} />);
      const radios = [...document.querySelectorAll<HTMLInputElement>('input[type="radio"]')];
      expect(radios.length).toBeGreaterThan(0);
      expect(radios.filter((button) => button.checked)).toEqual([]);
      unmount();
    }
  });

  it('shows the form words and examples for each line, including lines 12 to 14 and 26 to 28', () => {
    // The field index labels these lines "No". The words here are the printed form's.
    const printed: [number, string, string | null][] = [
      [3, '12. Jewelry', 'Examples: Everyday jewelry, costume jewelry'],
      [3, '13. Non-farm animals', 'Examples: Dogs, cats, birds, horses'],
      [3, '14. Any other personal and household items you did not already list', null],
      [
        4,
        '26. Patents, copyrights, trademarks, trade secrets, and other intellectual property',
        'Examples: Internet domain names',
      ],
      [4, '27. Licenses, franchises, and other general intangibles', 'Examples: Building permits'],
      [4, '28. Tax refunds owed to you', null],
    ];
    for (const [part, words, examples] of printed) {
      const { unmount } = render(<Walk part={part} />);
      expect(screen.getByText(new RegExp(`^${words}`))).toBeInTheDocument();
      if (examples) expect(screen.getByText(new RegExp(`^${examples}`))).toBeInTheDocument();
      unmount();
    }
    // Every line in the catalog has its words, shown when its Part and gate show it
    for (const part of AB_PARTS) {
      const answers: Answers = { '37': 'yes', '46': 'yes' };
      const { unmount } = render(<Walk part={part} answers={answers} />);
      for (const line of linesOf(part)) {
        const words = AB_LINE_WORDS[line.key].words;
        expect(screen.getByText(`${line.key}. ${words}`)).toBeInTheDocument();
      }
      unmount();
    }
  });

  it('reads line 1 and the gates as the form does', () => {
    const { unmount } = render(<Walk part={1} />);
    expect(screen.getByLabelText('No. Go to Part 2.')).toBeInTheDocument();
    unmount();
    const part5 = render(<Walk part={5} />);
    expect(screen.getByLabelText('No. Go to Part 6.')).toBeInTheDocument();
    expect(screen.getByLabelText('Yes. Go to line 38.')).toBeInTheDocument();
    part5.unmount();
    render(<Walk part={6} />);
    expect(screen.getByLabelText('No. Go to Part 7.')).toBeInTheDocument();
    expect(screen.getByLabelText('Yes. Go to line 47.')).toBeInTheDocument();
  });

  it('keeps Continue invalid until every shown line in the Part is answered', () => {
    render(<Walk part={3} />);
    expect(latest.valid).toBe(false);
    const keys = linesOf(3).map((line) => line.key);
    for (const key of keys.slice(0, -1)) say(key, 'no');
    expect(latest.valid).toBe(false);
    say(keys[keys.length - 1], 'no');
    expect(latest.valid).toBe(true);
  });

  it('keeps Continue invalid while a row lacks what its line requires', () => {
    render(<Walk part={3} answers={allNo(3)} />);
    expect(latest.valid).toBe(true);
    say('6', 'yes');
    expect(latest.valid).toBe(false);
    type('line_6_0_description', 'Sofa and table');
    expect(latest.valid).toBe(false);
    type('line_6_0_current_value', '150');
    expect(latest.valid).toBe(true);
  });

  it('opens one row on Yes, with Add another', () => {
    render(<Walk part={3} />);
    say('6', 'yes');
    expect(latest.rows.map((row) => row.ab_line)).toEqual(['6']);
    expect(latest.answers['6']).toBe('yes');
    fireEvent.click(screen.getByRole('button', { name: 'Add another' }));
    expect(latest.rows.map((row) => row.ab_line)).toEqual(['6', '6']);
    expect(field('line_6_1_description')).toBeInTheDocument();
  });

  it('offers no Add another on line 16, which takes one row', () => {
    render(<Walk part={4} />);
    say('16', 'yes');
    expect(latest.rows.map((row) => row.ab_line)).toEqual(['16']);
    expect(screen.queryByRole('button', { name: 'Add another' })).toBeNull();
    expect(field('line_16_0_description')).toBeNull();
  });

  it('keeps the Yes when the last row is removed, and says the line needs an item or a No', () => {
    render(<Walk part={3} />);
    say('6', 'yes');
    fireEvent.click(screen.getByRole('button', { name: 'Remove item 1 on line 6' }));
    expect(latest.rows).toEqual([]);
    expect(latest.answers['6']).toBe('yes');
    expect(radio('6', 'yes').checked).toBe(true);
    expect(screen.getByText('Add what you have, or change it to No.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Add an item' }));
    expect(latest.rows.map((row) => row.ab_line)).toEqual(['6']);
  });

  it('saves a half-filled row in the shape the server takes', () => {
    render(<Walk part={4} />);
    say('19', 'yes');
    const [opened] = latest.rows;
    expect(opened.description).toBe('');
    expect(opened.current_value).toBeNull();
    expect(opened.entire_value).toBeNull();
    expect(opened.details).toEqual({});

    type('line_19_0_percent', '25.5');
    expect(latest.rows[0].details?.percent).toBe(25.5);
    type('line_19_0_percent', '');
    expect(latest.rows[0].details?.percent).toBeNull();
    type('line_19_0_current_value', '10');
    type('line_19_0_current_value', '');
    // undefined would leave the key out of the request, and the server would keep the old figure
    expect(latest.rows[0].current_value).toBeNull();
  });

  it('treats a typed $0 as an answer and shows it as 0 after a reload', () => {
    const { unmount } = render(<Walk part={2} answers={{ '3': 'yes', '4': 'no' }} />);
    fireEvent.click(screen.getByRole('button', { name: 'Add an item' }));
    type('line_3_0_make', 'Toyota');
    fireEvent.click(radioValue('line_3_0_who', 'only_you'));
    type('line_3_0_entire_value', '0');
    type('line_3_0_current_value', '0');
    expect(latest.rows[0].current_value).toBe(0);
    expect(latest.rows[0].entire_value).toBe(0);
    expect(latest.valid).toBe(true);
    const saved = {
      ...latest.rows[0],
      current_value: '0.00',
      entire_value: '0.00',
    } as unknown as Row;
    unmount();

    // The server sends decimals as strings, and the wizard hydrates them
    const reloaded = hydrateAmounts(saved, ['current_value', 'entire_value']);
    render(<Walk part={2} answers={{ '3': 'yes', '4': 'no' }} rows={[reloaded]} />);
    expect(field('line_3_0_current_value').value).toBe('0');
    expect(field('line_3_0_entire_value').value).toBe('0');
    expect(latest.valid).toBe(true);
  });

  it('clears the figure when I do not know is pressed, and clears the flag when a figure is typed', () => {
    render(
      <Walk part={3} answers={{ ...allNo(3), '6': 'yes' }} rows={[makeRow({ ab_line: '6' })]} />
    );
    const dontKnow = () => field('line_6_0_value_unknown');

    fireEvent.click(dontKnow());
    expect(latest.rows[0].current_value).toBeNull();
    expect(latest.rows[0].details?.value_unknown).toBe(true);
    expect(dontKnow()).toHaveAttribute('aria-pressed', 'true');
    expect(field('line_6_0_current_value').value).toBe('');
    expect(screen.getByText(VALUE_UNKNOWN_NOTE)).toBeInTheDocument();
    expect(latest.valid).toBe(true);

    type('line_6_0_current_value', '75');
    expect(latest.rows[0].current_value).toBe(75);
    expect(latest.rows[0].details?.value_unknown).toBe(false);
    expect(dontKnow()).toHaveAttribute('aria-pressed', 'false');
    expect(screen.queryByText(VALUE_UNKNOWN_NOTE)).toBeNull();

    fireEvent.click(dontKnow());
    expect(latest.rows[0].current_value).toBeNull();
    expect(latest.rows[0].details?.value_unknown).toBe(true);
  });

  it('keeps the two values of a vehicle apart when one is unknown', () => {
    const row = makeRow({
      ab_line: '3',
      entire_value: 9000,
      current_value: 4500,
      details: { make: 'Ford', who: 'with_someone' },
    });
    render(<Walk part={2} answers={{ '3': 'yes', '4': 'no' }} rows={[row]} />);
    fireEvent.click(field('line_3_0_entire_unknown'));
    expect(latest.rows[0].entire_value).toBeNull();
    expect(latest.rows[0].details?.entire_unknown).toBe(true);
    expect(latest.rows[0].current_value).toBe(4500);
    expect(latest.rows[0].details?.value_unknown).toBeFalsy();
    expect(latest.valid).toBe(true);
  });

  it('keeps an amount the server would refuse out of the row, and says why', () => {
    render(
      <Walk part={3} answers={{ ...allNo(3), '6': 'yes' }} rows={[makeRow({ ab_line: '6' })]} />
    );
    type('line_6_0_current_value', '10000000000');
    expect(latest.rows[0].current_value).toBe(100);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    type('line_6_0_current_value', '-5');
    expect(latest.rows[0].current_value).toBe(100);
    type('line_6_0_current_value', '12.345');
    expect(latest.rows[0].current_value).toBe(100);
    type('line_6_0_current_value', '9999999999.99');
    expect(latest.rows[0].current_value).toBe(9999999999.99);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('keeps a share outside 0 to 100 out of the row', () => {
    render(<Walk part={4} />);
    say('19', 'yes');
    type('line_19_0_percent', '100.01');
    expect(latest.rows[0].details?.percent).toBeUndefined();
    type('line_19_0_percent', '100');
    expect(latest.rows[0].details?.percent).toBe(100);
  });

  it('opens amounts on the numeric keypad', () => {
    render(<Walk part={2} />);
    say('3', 'yes');
    expect(field('line_3_0_current_value')).toHaveAttribute('inputmode', 'decimal');
    expect(field('line_3_0_entire_value')).toHaveAttribute('inputmode', 'decimal');
  });

  // The ask counts what a No would remove, which can reach none while it shows
  it('never asks to remove 0 items', () => {
    render(<Walk part={1} rows={[makeRow({ ab_line: '1' })]} answers={{ '1': 'yes' }} />);
    say('1', 'no');
    expect(screen.getByText(/Remove 1 item/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Remove item 1 on line 1' }));

    expect(screen.queryByText(/Remove \d item/)).toBeNull();
  });

  it('asks in the page before No removes rows, and Keep them leaves rows and the Yes', () => {
    const confirmSpy = vi.spyOn(window, 'confirm');
    const rows = [makeRow({ ab_line: '6' }), makeRow({ ab_line: '6' }), makeRow({ ab_line: '7' })];
    render(<Walk part={3} answers={{ '6': 'yes', '7': 'yes' }} rows={rows} />);

    say('6', 'no');
    expect(screen.getByText('Remove 2 item(s) you listed on this line?')).toBeInTheDocument();
    expect(latest.rows).toHaveLength(3);
    expect(latest.answers['6']).toBe('yes');

    fireEvent.click(screen.getByRole('button', { name: 'Keep them' }));
    expect(screen.queryByText(/you listed on this line/)).toBeNull();
    expect(latest.rows).toHaveLength(3);
    expect(latest.answers['6']).toBe('yes');
    expect(radio('6', 'yes').checked).toBe(true);

    say('6', 'no');
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }));
    expect(latest.rows.map((row) => row.ab_line)).toEqual(['7']);
    expect(latest.answers['6']).toBe('no');
    expect(confirmSpy).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('hides lines 38 to 44 until line 37 says Yes', () => {
    render(<Walk part={5} />);
    expect(radio('38', 'no')).toBeNull();
    expect(radio('44', 'no')).toBeNull();
    say('37', 'yes');
    for (const key of ['38', '39', '40', '41', '42', '43', '44']) {
      expect(radio(key, 'no')).toBeInTheDocument();
    }
  });

  it('hides lines 47 to 51 until line 46 says Yes', () => {
    render(<Walk part={6} />);
    expect(radio('47', 'no')).toBeNull();
    say('46', 'yes');
    for (const key of ['47', '48', '49', '50', '51']) expect(radio(key, 'no')).toBeInTheDocument();
  });

  it('asks before a gate going to No removes rows, and clears the hidden answers', () => {
    const rows = [
      makeRow({ ab_line: '38' }),
      makeRow({ ab_line: '41' }),
      makeRow({ ab_line: '6' }),
    ];
    const answers: Answers = { '37': 'yes', '38': 'yes', '39': 'no', '41': 'yes', '6': 'yes' };
    render(<Walk part={5} rows={rows} answers={answers} />);

    say('37', 'no');
    expect(screen.getByText('Remove 2 item(s) you listed under this line?')).toBeInTheDocument();
    expect(latest.answers['37']).toBe('yes');
    fireEvent.click(screen.getByRole('button', { name: 'Keep them' }));
    expect(latest.rows).toHaveLength(3);
    expect(latest.answers['38']).toBe('yes');

    say('37', 'no');
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }));
    expect(latest.rows.map((row) => row.ab_line)).toEqual(['6']);
    expect(latest.answers).toEqual({ '37': 'no', '6': 'yes' });

    say('37', 'yes');
    expect(radio('38', 'yes').checked).toBe(false);
    expect(radio('38', 'no').checked).toBe(false);
    expect(radio('39', 'no').checked).toBe(false);
  });

  it('clears the hidden answers on a gate going to No even with no rows to ask about', () => {
    render(<Walk part={5} answers={{ '37': 'yes', '38': 'no', '39': 'no' }} />);
    say('37', 'no');
    expect(screen.queryByRole('button', { name: 'Keep them' })).toBeNull();
    expect(latest.answers).toEqual({ '37': 'no' });
  });

  it('shows Only you and You and someone else only on lines 1, 3 and 4', () => {
    const everyYes: Answers = Object.fromEntries(
      ASSET_LINES.map((line) => [line.key, 'yes' as const])
    );
    const everyRow = ASSET_LINES.filter((line) => line.shape !== 'gate').map((line) =>
      makeRow({ ab_line: line.key })
    );
    for (const part of AB_PARTS) {
      const { unmount } = render(<Walk part={part} rows={everyRow} answers={everyYes} />);
      const expected = part === 1 ? 1 : part === 2 ? 2 : 0;
      expect(screen.queryAllByLabelText('Only you')).toHaveLength(expected);
      expect(screen.queryAllByLabelText('You and someone else')).toHaveLength(expected);
      unmount();
    }
  });

  it('never pre-selects who, kinds or the community box', () => {
    const first = render(<Walk part={1} />);
    say('1', 'yes');
    const part1 = [...document.querySelectorAll<HTMLInputElement>('input[name^="line_1_0_"]')];
    expect(
      part1.filter((input) => input.type !== 'number' && input.type !== 'text' && input.checked)
    ).toEqual([]);
    expect(latest.rows[0].details).toEqual({});
    first.unmount();

    const second = render(<Walk part={2} />);
    say('3', 'yes');
    expect(field('line_3_0_community').checked).toBe(false);
    second.unmount();

    render(<Walk part={4} />);
    say('17', 'yes');
    expect(field('line_17_0_kind').value).toBe('');
    say('28', 'yes');
    expect(field('line_28_0_kind').value).toBe('');
  });

  it('asks a kind on lines 17, 21, 22, 28 and 29 in the form words', () => {
    const answers: Answers = { '17': 'yes', '21': 'yes', '22': 'yes', '28': 'yes', '29': 'yes' };
    const rows = ['17', '21', '22', '28', '29'].map((key) =>
      makeRow({ ab_line: key, description: '' })
    );
    render(<Walk part={4} rows={rows} answers={answers} />);
    const options = (key: string) =>
      within(field(`line_${key}_0_kind`))
        .getAllByRole('option')
        .slice(1)
        .map((option) => [(option as HTMLOptionElement).value, option.textContent]);
    expect(options('17')).toEqual([
      ['checking', 'Checking account'],
      ['savings', 'Savings account'],
      ['cd', 'Certificates of deposit'],
      ['other', 'Other financial account'],
    ]);
    expect(options('21')).toContainEqual(['401k', '401(k) or similar plan']);
    expect(options('22')).toContainEqual(['security_deposit', 'Security deposit on rental unit']);
    expect(options('28')).toEqual([
      ['federal', 'Federal'],
      ['state', 'State'],
      ['local', 'Local'],
    ]);
    expect(options('29')).toContainEqual(['divorce_settlement', 'Divorce settlement']);
    fireEvent.change(field('line_17_0_kind'), { target: { value: 'savings' } });
    expect(latest.rows[0].details?.kind).toBe('savings');
    fireEvent.change(field('line_17_0_kind'), { target: { value: '' } });
    // The server refuses a blank who or kind as a choice: an unpicked one is null
    expect(latest.rows[0].details?.kind).toBeNull();
  });

  it('asks the place questions on line 1, and clears the Other text when Other is unticked', () => {
    render(<Walk part={1} />);
    say('1', 'yes');
    type('line_1_0_street', '123 Maple St');
    type('line_1_0_street_2', 'Unit 2');
    type('line_1_0_city', 'Chicago');
    type('line_1_0_state', 'IL');
    type('line_1_0_zip', '60601');
    type('line_1_0_county', 'Cook');
    type('line_1_0_nature', 'Fee simple');
    type('line_1_0_other_info', 'PIN 12');
    expect(field('line_1_0_other_kind')).toBeNull();
    fireEvent.click(checkbox('line_1_0_property_kinds', 'other'));
    type('line_1_0_other_kind', 'Boat slip');
    expect(latest.rows[0].details?.property_kinds).toEqual(['other']);
    fireEvent.click(checkbox('line_1_0_property_kinds', 'land'));
    fireEvent.click(checkbox('line_1_0_property_kinds', 'other'));
    expect(latest.rows[0].details?.property_kinds).toEqual(['land']);
    expect(latest.rows[0].details?.other_kind).toBe('');
    fireEvent.click(field('line_1_0_community'));
    expect(latest.rows[0].details?.community).toBe(true);
    expect(latest.rows[0].details).toMatchObject({
      street: '123 Maple St',
      street_2: 'Unit 2',
      city: 'Chicago',
      state: 'IL',
      zip: '60601',
      county: 'Cook',
      nature: 'Fee simple',
      other_info: 'PIN 12',
    });
  });

  it('asks no mileage on line 4, as the form has none', () => {
    render(<Walk part={2} />);
    say('3', 'yes');
    say('4', 'yes');
    expect(field('line_3_0_mileage')).toBeInTheDocument();
    expect(field('line_4_0_mileage')).toBeNull();
    expect(field('line_4_0_year')).toBeInTheDocument();
    expect(field('line_4_0_entire_value')).toBeInTheDocument();
  });

  it('asks the insurance company and an optional beneficiary on line 31', () => {
    render(<Walk part={4} answers={{ ...allNo(4), '31': 'yes' }} />);
    fireEvent.click(screen.getByRole('button', { name: 'Add an item' }));
    expect(screen.getByLabelText(/^Company name:/)).toBe(field('line_31_0_description'));
    expect(screen.getByLabelText(/^Surrender or refund value:/)).toBe(
      field('line_31_0_current_value')
    );
    type('line_31_0_description', 'Millbrook Mutual Life');
    type('line_31_0_current_value', '0');
    expect(latest.valid).toBe(true);
    type('line_31_0_beneficiary', 'Spouse');
    expect(latest.rows[0].details?.beneficiary).toBe('Spouse');
  });

  it('asks line 43 its question, with Describe only under its Yes', () => {
    const answers: Answers = { '37': 'yes', '43': 'yes' };
    const rows = [makeRow({ ab_line: '43', description: '', current_value: null })];
    render(<Walk part={5} rows={rows} answers={answers} />);
    expect(field('line_43_0_description')).toBeNull();
    fireEvent.click(radioValue('line_43_0_has_personal_info', 'yes'));
    expect(latest.rows[0].details?.has_personal_info).toBe(true);
    type('line_43_0_description', 'Customer names');
    fireEvent.click(radioValue('line_43_0_has_personal_info', 'no'));
    expect(latest.rows[0].details?.has_personal_info).toBe(false);
    expect(field('line_43_0_description')).toBeNull();
    // The form prints what is stored, so text the filer can no longer see can't stay in the row
    expect(latest.rows[0].description).toBe('');
    expect(field('line_43_0_current_value')).toBeInTheDocument();
  });

  it('shows no amount owed, no account number and no equity', () => {
    const everyYes: Answers = Object.fromEntries(
      ASSET_LINES.map((line) => [line.key, 'yes' as const])
    );
    const everyRow = ASSET_LINES.filter((line) => line.shape !== 'gate').map((line) =>
      makeRow({ ab_line: line.key, amount_owed: 500 })
    );
    for (const part of AB_PARTS) {
      const { container, unmount } = render(
        <Walk part={part} rows={everyRow} answers={everyYes} />
      );
      expect(container.textContent).not.toMatch(/amount owed|account number|equity/i);
      expect(container.querySelector('[name*="amount_owed"]')).toBeNull();
      expect(container.querySelector('[name*="account_number"]')).toBeNull();
      unmount();
    }
  });

  it('shows the form sentence on secured claims at each value', () => {
    render(<Walk part={3} answers={{ '6': 'yes' }} rows={[makeRow({ ab_line: '6' })]} />);
    expect(screen.getByText(/^Do not deduct secured claims or exemptions\.$/)).toBeInTheDocument();
  });

  it('offers the line 3 lease note and marks no value for the filer', () => {
    const { unmount } = render(<Walk part={2} />);
    expect(screen.getByText(LEASE_NOTE)).toBeInTheDocument();
    say('3', 'yes');
    expect(field('line_3_0_current_value').value).toBe('');
    expect(field('line_3_0_entire_value').value).toBe('');
    expect(latest.rows[0].current_value).toBeNull();
    expect(latest.rows[0].entire_value).toBeNull();
    unmount();
    render(<Walk part={3} />);
    expect(screen.queryByText(LEASE_NOTE)).toBeNull();
  });

  it('shows the reassurance above Part 1 only', () => {
    const { unmount } = render(<Walk part={1} />);
    expect(screen.getByText(NOTHING_TO_LIST_NOTE)).toBeInTheDocument();
    expect(NOTHING_TO_LIST_NOTE).not.toMatch(/blank/i);
    unmount();
    render(<Walk part={2} />);
    expect(screen.queryByText(NOTHING_TO_LIST_NOTE)).toBeNull();
  });

  it('says which Part this is, in the form words', () => {
    render(<Walk part={3} />);
    expect(screen.getByText('Part 3 of 7')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Describe Your Personal and Household Items' })
    ).toBeInTheDocument();
  });

  it('keeps Continue invalid while an old row has no line', () => {
    render(<Walk part={3} answers={allNo(3)} rows={[makeRow({ ab_line: null })]} />);
    expect(latest.valid).toBe(false);
  });

  // Continue only goes grey, so the mark is how a filer tells what still holds it back
  describe('marks what Continue is waiting for, and only that', () => {
    const required = (name: string) => expect(field(name)).toHaveAttribute('aria-required', 'true');
    const optional = (name: string) =>
      expect(field(name)).toHaveAttribute('aria-required', 'false');
    const legendIsMarked = (words: string) =>
      expect(screen.getByText(words).querySelector('.required-indicator')).toBeInTheDocument();

    it('on a place: street, a kind, who and both values, not the rest of the address', () => {
      render(<Walk part={1} />);
      say('1', 'yes');
      required('line_1_0_street');
      required('line_1_0_entire_value');
      required('line_1_0_current_value');
      for (const box of ['street_2', 'city', 'state', 'zip', 'county', 'nature', 'other_info']) {
        optional(`line_1_0_${box}`);
      }
      legendIsMarked(AB_PROPERTY_KIND_QUESTION);
      legendIsMarked(AB_WHO_QUESTION);
      fireEvent.click(checkbox('line_1_0_property_kinds', 'other'));
      required('line_1_0_other_kind');
    });

    it('on a vehicle: make, who and both values, not model, year or mileage', () => {
      render(<Walk part={2} />);
      say('3', 'yes');
      required('line_3_0_make');
      required('line_3_0_entire_value');
      required('line_3_0_current_value');
      for (const box of ['model', 'year', 'mileage', 'other_info']) optional(`line_3_0_${box}`);
      legendIsMarked(AB_WHO_QUESTION);
    });

    it('on a labelled row, a share, insurance and cash', () => {
      render(<Walk part={4} />);
      say('16', 'yes');
      required('line_16_0_current_value');
      say('17', 'yes');
      required('line_17_0_kind');
      required('line_17_0_description');
      required('line_17_0_current_value');
      say('19', 'yes');
      required('line_19_0_percent');
      say('31', 'yes');
      required('line_31_0_description');
      optional('line_31_0_beneficiary');
    });

    it('on line 43: its question, its value, and Describe under its Yes', () => {
      render(<Walk part={5} answers={{ '37': 'yes', '43': 'yes' }} />);
      fireEvent.click(screen.getByRole('button', { name: 'Add an item' }));
      legendIsMarked(AB_PERSONAL_INFO_QUESTION);
      required('line_43_0_current_value');
      fireEvent.click(radioValue('line_43_0_has_personal_info', 'yes'));
      required('line_43_0_description');
    });

    it('takes the mark off a value while I do not know is pressed, since that answers it', () => {
      render(<Walk part={3} answers={{ '6': 'yes' }} rows={[makeRow({ ab_line: '6' })]} />);
      required('line_6_0_current_value');
      fireEvent.click(field('line_6_0_value_unknown'));
      optional('line_6_0_current_value');
    });
  });

  // Complete has the server's sentence for this, but the filer can't reach Complete from here
  it('says why Continue waits on a gate that says Yes with every line under it No', () => {
    render(<Walk part={5} />);
    const sentence = 'Line 37 says Yes, but every line under it says No. Change one of them.';
    say('37', 'yes');
    const under = ['38', '39', '40', '41', '42', '43', '44'];
    for (const key of under.slice(0, -1)) say(key, 'no');
    expect(screen.queryByText(sentence)).toBeNull();

    say('44', 'no');
    expect(latest.valid).toBe(false);
    const shown = screen.getByText(sentence);
    // Where the filer who just pressed the last No is looking, not back up at line 37
    expect(radio('44', 'no').compareDocumentPosition(shown)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);

    say('38', 'yes');
    expect(screen.queryByText(sentence)).toBeNull();
  });

  it('says the same of line 46, naming that line', () => {
    const answers: Answers = { '46': 'yes', '47': 'no', '48': 'no', '49': 'no', '50': 'no' };
    render(<Walk part={6} answers={answers} />);
    say('51', 'no');
    expect(
      screen.getByText('Line 46 says Yes, but every line under it says No. Change one of them.')
    ).toBeInTheDocument();
  });

  it('keeps the Review heading for unknown values in plain words', () => {
    expect(VALUE_UNKNOWN_HEADING).toBe("You said you don't know the value of these");
  });

  it('lists an old row above Part 1 only, and picking a line moves it there and answers Yes', () => {
    const old = makeRow({ ab_line: null, description: 'Blue car', asset_type: 'vehicle' });
    const { unmount } = render(<Walk part={2} rows={[old]} />);
    expect(screen.queryByText('Blue car')).toBeNull();
    unmount();

    render(<Walk part={1} rows={[old]} />);
    expect(screen.getByText('Blue car')).toBeInTheDocument();
    fireEvent.change(field('old_row_0_line'), { target: { value: '3' } });

    expect(latest.rows[0].ab_line).toBe('3');
    expect(latest.rows[0].current_value).toBe(100);
    expect(latest.rows[0].entire_value).toBeNull();
    expect(latest.answers['3']).toBe('yes');
    expect(screen.queryByText('Blue car')).toBeNull();
  });

  it('has no axe violations on the old rows', { timeout: 60_000 }, async () => {
    const old = makeRow({ ab_line: null, description: 'Blue car', asset_type: 'vehicle' });
    const { container } = render(<Walk part={1} rows={[old]} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no axe violations on each Part', { timeout: 60_000 }, async () => {
    const everyYes: Answers = Object.fromEntries(
      ASSET_LINES.map((line) => [line.key, 'yes' as const])
    );
    const everyRow = ASSET_LINES.filter((line) => line.shape !== 'gate').map((line) =>
      makeRow({ ab_line: line.key })
    );
    for (const part of AB_PARTS) {
      const blank = render(<Walk part={part} />);
      expect(await axe(blank.container)).toHaveNoViolations();
      blank.unmount();
      const filled = render(<Walk part={part} rows={everyRow} answers={everyYes} />);
      expect(await axe(filled.container)).toHaveNoViolations();
      filled.unmount();
    }
  });
});

function radioValue(name: string, value: string) {
  return document.querySelector(`input[name="${name}"][value="${value}"]`) as HTMLInputElement;
}

function checkbox(name: string, value: string) {
  return radioValue(name, value);
}

describe('what a Part needs before Continue (the server: asset_step_gaps)', () => {
  const complete = (part: number, rows: Row[], answers: Answers) =>
    partIsComplete(part, rows, answers);
  const known = { value_unknown: true };

  it.each<[string, string, Partial<Row>, boolean]>([
    ['cash needs only its value', '16', { description: '' }, true],
    ['cash with neither figure nor flag', '16', { description: '', current_value: null }, false],
    ['an item without text', '6', { description: '   ' }, false],
    ['an item with an unknown value', '6', { current_value: null, details: known }, true],
    ['$0 is a value', '6', { current_value: 0 }, true],
    ['a labelled row without a kind', '17', {}, false],
    ['a labelled row with its kind', '17', { details: { kind: 'savings' } }, true],
    ['a shared box on 28 without a kind', '28', {}, false],
    ['a shared box on 53 asks no kind', '53', {}, true],
    ['a share without its percent', '19', {}, false],
    ['a share of 0 is an answer', '19', { details: { percent: 0 } }, true],
    ['a stored share comes back as text', '19', { details: { percent: '25.00' } }, true],
    ['insurance without a beneficiary', '31', {}, true],
  ])('%s', (_name, key, overrides, expected) => {
    const line = ASSET_LINES.find((one) => one.key === key)!;
    const answers = { ...allNo(line.part), [key]: 'yes' as const };
    expect(complete(line.part, [makeRow({ ab_line: key, ...overrides })], answers)).toBe(expected);
  });

  it('holds line 43 to its value and its question', () => {
    const answers: Answers = { ...allNo(5), '37': 'yes', '43': 'yes' };
    const line43 = (overrides: Partial<Row>) => [makeRow({ ab_line: '43', ...overrides })];
    expect(complete(5, line43({ description: '' }), answers)).toBe(false);
    expect(
      complete(
        5,
        line43({ description: '', details: { has_personal_info: false }, current_value: null }),
        answers
      )
    ).toBe(false);
    expect(
      complete(5, line43({ description: '', details: { has_personal_info: false } }), answers)
    ).toBe(true);
    expect(
      complete(5, line43({ description: '', details: { has_personal_info: true } }), answers)
    ).toBe(false);
    expect(complete(5, line43({ details: { has_personal_info: true } }), answers)).toBe(true);
  });

  it('holds a place to its street, a kind, who and both values', () => {
    const answers: Answers = { '1': 'yes' };
    const place = {
      street: '1 Elm',
      property_kinds: ['land'],
      who: 'only_you',
    } as Row['details'];
    const row = (overrides: Partial<Row>) => [
      makeRow({ ab_line: '1', entire_value: 100, details: place, ...overrides }),
    ];
    expect(complete(1, row({}), answers)).toBe(true);
    expect(complete(1, row({ entire_value: null }), answers)).toBe(false);
    expect(
      complete(1, row({ entire_value: null, details: { ...place, entire_unknown: true } }), answers)
    ).toBe(true);
    expect(complete(1, row({ details: { ...place, street: ' ' } }), answers)).toBe(false);
    expect(complete(1, row({ details: { ...place, who: null } }), answers)).toBe(false);
    expect(complete(1, row({ details: { ...place, property_kinds: [] } }), answers)).toBe(false);
    expect(complete(1, row({ details: { ...place, property_kinds: ['other'] } }), answers)).toBe(
      false
    );
    expect(
      complete(
        1,
        row({ details: { ...place, property_kinds: ['other'], other_kind: 'Slip' } }),
        answers
      )
    ).toBe(true);
  });

  it('holds a vehicle to its make, who and both values, not its model, year or mileage', () => {
    const answers: Answers = { '3': 'yes', '4': 'no' };
    const row = (details: Row['details']) => [
      makeRow({ ab_line: '3', description: '', entire_value: 0, current_value: 0, details }),
    ];
    expect(complete(2, row({ make: 'Ford', who: 'only_you' }), answers)).toBe(true);
    expect(complete(2, row({ who: 'only_you' }), answers)).toBe(false);
    expect(complete(2, row({ make: 'Ford' }), answers)).toBe(false);
  });

  it('refuses a gate that says Yes with every line under it No', () => {
    const under = Object.fromEntries(
      ['38', '39', '40', '41', '42', '43', '44'].map((key) => [key, 'no' as const])
    );
    expect(complete(5, [], { '37': 'yes', ...under })).toBe(false);
    const row = makeRow({ ab_line: '38' });
    expect(complete(5, [row], { '37': 'yes', ...under, '38': 'yes' })).toBe(true);
  });

  it('refuses a No line that still has rows, a Yes line with none, and a hidden line with rows', () => {
    expect(complete(3, [makeRow({ ab_line: '6' })], allNo(3))).toBe(false);
    expect(complete(3, [], { ...allNo(3), '6': 'yes' })).toBe(false);
    expect(complete(5, [makeRow({ ab_line: '38' })], { '37': 'no' })).toBe(false);
    expect(complete(5, [makeRow({ ab_line: '37' })], { '37': 'no' })).toBe(false);
  });

  it('shows a gate its lines only under Yes', () => {
    const count = (answers: Answers) => shownLines(answers).length;
    expect(count({})).toBe(35);
    expect(count({ '37': 'no', '46': 'no' })).toBe(35);
    expect(count({ '37': 'yes' })).toBe(42);
    expect(count({ '37': 'yes', '46': 'yes' })).toBe(47);
  });

  it('opens at the first Part with something left, or Part 1 when nothing is', () => {
    const everyPart: Answers = {
      ...allNo(1),
      ...allNo(2),
      ...allNo(3),
      ...allNo(4),
      '37': 'no',
      '46': 'no',
      '53': 'no',
    };
    expect(firstIncompletePart([], everyPart)).toBe(1);
    expect(firstIncompletePart([], {})).toBe(1);
    const noLine14 = { ...everyPart };
    delete noLine14['14'];
    expect(firstIncompletePart([], noLine14)).toBe(3);
    expect(firstIncompletePart([makeRow({ ab_line: '53' })], everyPart)).toBe(7);
  });

  // Old rows hold every Part back and are listed only above Part 1, so opening anywhere else would
  // leave Continue disabled with nothing on screen to explain it
  it('opens at Part 1 while an old row has no line, even with Part 1 answered and Part 3 not', () => {
    const everyPart: Answers = {
      ...allNo(1),
      ...allNo(2),
      ...allNo(4),
      '37': 'no',
      '46': 'no',
      '53': 'no',
    };
    expect(firstIncompletePart([], everyPart)).toBe(3);
    expect(firstIncompletePart([makeRow({ ab_line: null })], everyPart)).toBe(1);
  });
});
