import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { GapsNotice } from '../GapsNotice';
import {
  DASHBOARD_GAPS_MANY,
  DASHBOARD_GAPS_ONE,
  DASHBOARD_GATES_MANY,
  DASHBOARD_GATES_ONE,
  PETITION_DETAIL_CALLED_TO_DUTY,
  PETITION_DETAIL_DEBT_NATURE_TEXT,
  PETITION_DETAIL_DEBTS_ON_DUTY,
  PETITION_DETAIL_DUTY_CATEGORY,
  PETITION_DETAIL_DUTY_ENDED,
  PETITION_DETAIL_DUTY_RELEASED,
  PETITION_DETAIL_LANDLORD,
  PETITION_DETAIL_TOO_LONG,
  PETITION_DETAIL_TOO_LONG_101A,
  PETITION_DETAIL_TOO_LONG_ROW,
  SCHEDULE_I_DETAIL_TOO_LONG,
} from '../../../constants/copy';
import type { CompletionGap } from '../../../types/api';

function renderNotice(gaps: CompletionGap[]) {
  return render(
    <MemoryRouter>
      <GapsNotice gaps={gaps} />
    </MemoryRouter>
  );
}

const gate = (step: string, message: string): CompletionGap => ({
  message,
  step,
  kind: 'gate',
  forms: [],
});
const detail = (step: string, message: string): CompletionGap => ({
  message,
  step,
  kind: 'detail',
  forms: [],
});

describe('GapsNotice', () => {
  it('shows nothing for an empty list', () => {
    renderNotice([]);
    // The status region is there, with nothing in it
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });

  // A live region announces only what is added to a region already on the page
  it('keeps one status region from before the gaps arrive, so a screen reader reads them out', () => {
    const { rerender } = renderNotice([]);
    const region = screen.getByRole('status');

    rerender(
      <MemoryRouter>
        <GapsNotice gaps={[gate('income_info', 'Enter your income.')]} />
      </MemoryRouter>
    );

    expect(screen.getByRole('status')).toBe(region);
    expect(region).toHaveTextContent('Enter your income.');
  });

  it('a gate gap is named as missing, not as blank', () => {
    renderNotice([gate('income_info', 'Enter your income.')]);

    const notice = screen.getByRole('status');
    expect(within(notice).getByText(DASHBOARD_GATES_ONE)).toBeInTheDocument();
    expect(notice).not.toHaveTextContent(/blank/i);
  });

  it('names the count and one way per affected step, in wizard order', () => {
    renderNotice([
      gate('expense_info', 'Go through the Expenses step.'),
      gate('income_info', 'Enter your income by source.'),
      gate('income_info', 'Enter your take-home pay.'),
    ]);

    const notice = screen.getByRole('status');
    expect(
      within(notice).getByText(DASHBOARD_GATES_MANY.replace('{count}', '3'))
    ).toBeInTheDocument();
    expect(
      within(notice).getByText(
        "3 answers are still missing. Your forms can't be prepared until each is given."
      )
    ).toBeInTheDocument();
    const links = within(notice).getAllByRole('link');
    expect(links.map((link) => link.textContent)).toEqual(['Go to Income', 'Go to Expenses']);
    expect(links[0]).toHaveAttribute('href', '/intake?step=income_info');
    expect(links[1]).toHaveAttribute('href', '/intake?step=expense_info');

    const [income, expenses] = within(notice).getAllByRole('listitem');
    expect(within(income).getByText('Enter your income by source.')).toBeInTheDocument();
    expect(within(income).getByText('Enter your take-home pay.')).toBeInTheDocument();
    expect(within(expenses).getByText('Go through the Expenses step.')).toBeInTheDocument();
  });

  it('a detail gap is named as blank', () => {
    renderNotice([detail('debtor_info', 'Your date of birth is blank.')]);

    expect(screen.getByText(DASHBOARD_GAPS_ONE)).toBeInTheDocument();
    expect(screen.queryByText(DASHBOARD_GATES_ONE)).not.toBeInTheDocument();
  });

  // Form 101 refuses a too-long answer; nothing prints blank, so the blank count must not hold it
  it('a too-long detail is listed with its words but never counted as blank', () => {
    const tooLong = PETITION_DETAIL_TOO_LONG.replace('{label}', 'your other name');
    const tooLongRow = PETITION_DETAIL_TOO_LONG_ROW.replace('{label}', 'the court')
      .replace('{noun}', 'case')
      .replace('{n}', '2')
      .replace('{forms}', 'Form 101');
    renderNotice([detail('debtor_info', tooLong), detail('debtor_info', tooLongRow)]);

    const notice = screen.getByRole('status');
    expect(within(notice).getByText(tooLong)).toBeInTheDocument();
    expect(within(notice).getByText(tooLongRow)).toBeInTheDocument();
    expect(notice).not.toHaveTextContent(/blank/i);
  });

  // Owner ruling Q10: a row cell's sentence names the forms whose box refuses it, in three ways
  it.each(['Form 101', 'Form 103B', 'Forms 101 and 103B'])(
    'a too-long row naming %s is never counted as blank',
    (forms) => {
      const tooLongRow = `Your answer for line 9's case number, in case 1, is too long to fit on ${forms}.`;
      renderNotice([detail('debtor_info', tooLongRow)]);

      const notice = screen.getByRole('status');
      expect(within(notice).getByText(tooLongRow)).toBeInTheDocument();
      expect(notice).not.toHaveTextContent(/blank/i);
    }
  );

  it('counts only the blank details when a too-long one stands beside them', () => {
    const tooLong = PETITION_DETAIL_TOO_LONG.replace('{label}', 'your other name');
    renderNotice([detail('debtor_info', tooLong), detail('assets', 'An asset value is blank.')]);

    expect(screen.getByText(DASHBOARD_GAPS_ONE)).toBeInTheDocument();
  });

  it('a too-long Form 101A answer is not counted as a blank one', () => {
    const tooLong = PETITION_DETAIL_TOO_LONG_101A.replace('{label}', "the landlord's name");
    renderNotice([{ ...detail('contracts', tooLong), forms: ['form_101a'] }]);

    const notice = screen.getByRole('status');
    expect(within(notice).getByText(tooLong)).toBeInTheDocument();
    expect(notice).not.toHaveTextContent(/blank/i);
  });

  it('a too-long Schedule I answer is not counted as a blank one', () => {
    const tooLong = SCHEDULE_I_DETAIL_TOO_LONG.replace('{label}', "Employer's name").replace(
      '{form}',
      'Schedule I'
    );
    const tooLongJ = SCHEDULE_I_DETAIL_TOO_LONG.replace('{label}', 'Line 24, Explain').replace(
      '{form}',
      'Schedule J'
    );
    renderNotice([
      { ...detail('income_info', tooLong), forms: ['schedule_i'] },
      { ...detail('expense_info', tooLongJ), forms: ['schedule_j'] },
    ]);

    const notice = screen.getByRole('status');
    expect(within(notice).getByText(tooLong)).toBeInTheDocument();
    expect(within(notice).getByText(tooLongJ)).toBeInTheDocument();
    expect(notice).not.toHaveTextContent(/blank/i);
  });

  // Form 101A is refused whole while its landlord is missing; it never prints a blank box (R12)
  it('a missing landlord is not counted as a blank answer', () => {
    renderNotice([{ ...detail('contracts', PETITION_DETAIL_LANDLORD), forms: ['form_101a'] }]);

    const notice = screen.getByRole('status');
    expect(within(notice).getByText(PETITION_DETAIL_LANDLORD)).toBeInTheDocument();
    expect(within(notice).getByRole('link', { name: /Contracts/ })).toBeInTheDocument();
    expect(notice).not.toHaveTextContent(/blank/i);
  });

  // 4d-R10: an open military follow-up keeps the Supp out of the packet (or holds 122A-2 above the
  // median), and a claimed exclusion's missing date refuses the Supp whole, so none of the five ever
  // leaves a blank box on a form the filer files. Line 16c's words do: Form 101 prints that box blank
  it("doesn't count a military follow-up or a service date as a blank answer", () => {
    const military = [
      PETITION_DETAIL_DEBTS_ON_DUTY,
      PETITION_DETAIL_CALLED_TO_DUTY,
      PETITION_DETAIL_DUTY_CATEGORY,
      PETITION_DETAIL_DUTY_RELEASED,
      PETITION_DETAIL_DUTY_ENDED,
    ];
    renderNotice([
      ...military.map((message) => ({ ...detail('debts', message), forms: ['form_122a1_supp'] })),
      { ...detail('debts', PETITION_DETAIL_DEBT_NATURE_TEXT), forms: ['form_101'] },
    ]);

    const notice = screen.getByRole('status');
    for (const message of military) {
      expect(within(notice).getByText(message)).toBeInTheDocument();
    }
    // Only line 16c's words are counted
    expect(within(notice).getByText(DASHBOARD_GAPS_ONE)).toBeInTheDocument();
    expect(within(notice).getAllByRole('link', { name: /Amounts Owed/ })).toHaveLength(1);
  });

  it('with both kinds the missing sentence comes first', () => {
    renderNotice([
      detail('debtor_info', 'One blank.'),
      gate('income_info', 'Enter your income.'),
      detail('assets', 'Another blank.'),
    ]);

    const missing = screen.getByText(DASHBOARD_GATES_ONE);
    const blank = screen.getByText(DASHBOARD_GAPS_MANY.replace('{count}', '2'));
    expect(missing.compareDocumentPosition(blank) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('a gap on an unknown step shows its words and no link', () => {
    renderNotice([gate('a_step_from_a_newer_server', 'Answer the new question.')]);

    expect(screen.getByText('Answer the new question.')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  // The dashboard's own accessibility scan runs against the default `{gaps: []}` handler and never
  // sees this markup
  it('has no accessibility violations with both kinds listed', async () => {
    const { container } = renderNotice([
      gate('income_info', 'Enter your income.'),
      detail('assets', 'An asset value is blank.'),
      gate('a_step_from_a_newer_server', 'Answer the new question.'),
    ]);

    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  });
});
