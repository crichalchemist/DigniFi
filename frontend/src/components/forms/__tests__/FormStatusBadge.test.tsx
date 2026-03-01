import { render, screen } from '@testing-library/react';
import { FormStatusBadge } from '../FormStatusBadge';

describe('FormStatusBadge', () => {
  it.each([
    ['pending', 'Not Generated', 'form-status-badge--pending'],
    ['generated', 'Generated', 'form-status-badge--generated'],
    ['downloaded', 'Downloaded', 'form-status-badge--downloaded'],
    ['filed', 'Filed', 'form-status-badge--filed'],
  ] as const)('renders %s status', (status, label, className) => {
    render(<FormStatusBadge status={status} />);
    const badge = screen.getByRole('status');
    expect(badge).toHaveTextContent(label);
    expect(badge).toHaveClass(className);
  });
});
