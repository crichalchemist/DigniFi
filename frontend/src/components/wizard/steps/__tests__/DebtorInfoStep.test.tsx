import { render, screen, within } from '@testing-library/react';
import { vi } from 'vitest';
import { DebtorInfoStep } from '../DebtorInfoStep';
import { ILND_COUNTIES } from '../../../../constants/counties';
import { COUNTY_OUTSIDE_DISTRICT } from '../../../../constants/copy';

// DebtorInfoStep locks the contact email to the authenticated user's address
// (note 9). Stub useAuth so the step has a logged-in user to read from.
vi.mock('../../../../context/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'jane@example.com' } }),
}));

const noop = () => {};

describe('DebtorInfoStep email lock', () => {
  it('pre-fills the email from the authenticated user and makes it read-only', () => {
    render(
      <DebtorInfoStep
        initialData={{}}
        onDataChange={noop}
        onValidationChange={noop}
        county={null}
        onCountyChange={noop}
      />
    );

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
        county={null}
        onCountyChange={noop}
      />
    );

    expect(screen.getByLabelText(/email address/i)).toHaveValue('jane@example.com');
  });
});

describe('DebtorInfoStep county', () => {
  const renderStep = () =>
    render(
      <DebtorInfoStep
        initialData={{}}
        onDataChange={noop}
        onValidationChange={noop}
        county={null}
        onCountyChange={noop}
      />
    );

  it('step 1 no longer asks household size or filing type', () => {
    renderStep();
    expect(screen.queryByLabelText(/household size/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/filing type/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/household & filing information/i)).not.toBeInTheDocument();
  });

  it('a filer outside the district sees why no county fits', () => {
    renderStep();
    const options = within(screen.getByRole('combobox', { name: /county/i })).getAllByRole(
      'option'
    );
    expect(options.map((option) => option.getAttribute('value'))).toEqual(['', ...ILND_COUNTIES]);
    expect(screen.getByText(COUNTY_OUTSIDE_DISTRICT)).toBeInTheDocument();
    expect(COUNTY_OUTSIDE_DISTRICT).toContain('Northern District of Illinois');
    expect(COUNTY_OUTSIDE_DISTRICT).not.toMatch(/\bfile\b|\bshould\b/i);
  });
});
