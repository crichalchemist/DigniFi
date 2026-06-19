import { render, screen } from '@testing-library/react';
import { DebtExplanationsPanel } from '../DebtExplanationsPanel';

const mockData = [
  {
    debt_id: 1,
    creditor: 'Navient',
    debt_type: 'student_loan',
    dischargeable: false,
    reason: '11 U.S.C. § 523(a)(8)',
    proceeding_needed: true,
  },
  {
    debt_id: 2,
    creditor: 'Chase',
    debt_type: 'credit_card',
    dischargeable: true,
    reason: '',
    proceeding_needed: false,
  },
];

describe('DebtExplanationsPanel', () => {
  it('renders dischargeable count', () => {
    render(<DebtExplanationsPanel debts={mockData} />);
    expect(screen.getAllByText('1')).toHaveLength(2);
    expect(screen.getByText('Dischargeable amounts')).toBeInTheDocument();
  });
  it('renders non-dischargeable count', () => {
    render(<DebtExplanationsPanel debts={mockData} />);
    expect(screen.getAllByText('1')).toHaveLength(2);
    expect(screen.getByText('Non-dischargeable amounts')).toBeInTheDocument();
  });
  it('shows student loan proceeding needed', () => {
    render(<DebtExplanationsPanel debts={mockData} />);
    expect(screen.getByText('Navient')).toBeInTheDocument();
    expect(screen.getByText(/adversary proceeding/i)).toBeInTheDocument();
  });
  it('shows empty state', () => {
    render(<DebtExplanationsPanel debts={[]} />);
    expect(screen.getByText(/no amounts/i)).toBeInTheDocument();
  });
});
