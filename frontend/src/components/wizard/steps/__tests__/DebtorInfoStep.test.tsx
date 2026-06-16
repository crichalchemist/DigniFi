import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { DebtorInfoStep } from '../DebtorInfoStep';

// DebtorInfoStep locks the contact email to the authenticated user's address
// (note 9). Stub useAuth so the step has a logged-in user to read from.
vi.mock('../../../../context/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'jane@example.com' } }),
}));

const noop = () => {};

describe('DebtorInfoStep email lock', () => {
  it('pre-fills the email from the authenticated user and makes it read-only', () => {
    render(<DebtorInfoStep initialData={{}} onDataChange={noop} onValidationChange={noop} />);

    const email = screen.getByLabelText(/email address/i) as HTMLInputElement;
    expect(email).toHaveValue('jane@example.com');
    expect(email.readOnly).toBe(true);
  });

  it('overrides a stale initialData email with the authenticated address', () => {
    // A user cannot change their sign-in identity mid-intake, so a different
    // email carried in from saved data must be replaced, not kept.
    render(
      <DebtorInfoStep
        initialData={{ email: 'old@example.com' }}
        onDataChange={noop}
        onValidationChange={noop}
      />
    );

    expect(screen.getByLabelText(/email address/i)).toHaveValue('jane@example.com');
  });
});
