import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { GapsNotice } from '../GapsNotice';
import {
  DASHBOARD_GAPS_MANY,
  DASHBOARD_GAPS_ONE,
  DASHBOARD_GATES_MANY,
  DASHBOARD_GATES_ONE,
} from '../../../constants/copy';
import type { CompletionGap } from '../../../types/api';

function renderNotice(gaps: CompletionGap[]) {
  return render(
    <MemoryRouter>
      <GapsNotice gaps={gaps} />
    </MemoryRouter>
  );
}

const gate = (step: string, message: string): CompletionGap => ({ message, step, kind: 'gate' });
const detail = (step: string, message: string): CompletionGap => ({
  message,
  step,
  kind: 'detail',
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
