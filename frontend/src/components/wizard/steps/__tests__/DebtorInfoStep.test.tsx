import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { DebtorInfoStep } from '../DebtorInfoStep';
import { ILND_COUNTIES } from '../../../../constants/counties';
import {
  COUNSELING_REQUIREMENT_INTRO,
  COUNTY_OUTSIDE_DISTRICT,
  HOME_ZIP_ERROR,
  SSN_SAVED,
} from '../../../../constants/copy';
import type { DebtorInfo, PetitionAnswers } from '../../../../types/api';
import { firstPetitionGap } from '../petition/petitionGaps';

// DebtorInfoStep locks the contact email to the authenticated user's address
// (note 9). Stub useAuth so the step has a logged-in user to read from.
vi.mock('../../../../context/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'jane@example.com' } }),
}));

const noop = () => {};

// Form 101's seven yes/noes, all answered No
const EVERY_GATE_NO: PetitionAnswers = {
  other_names_answer: 'no',
  itin_answer: 'no',
  other_ssn_answer: 'no',
  mailing_answer: 'no',
  prior_bankruptcy_answer: 'no',
  pending_case_answer: 'no',
  sole_proprietor_answer: 'no',
};

// A step 1 loaded from the server: every field but the SSN, which never comes back
const LOADED: Partial<DebtorInfo> = {
  first_name: 'Demo',
  last_name: 'Filer',
  date_of_birth: '1985-06-15',
  street_address: '1 Demo Street',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60601',
  phone: '312-555-0100',
  email: 'jane@example.com',
};

function renderStep({
  initialData = {},
  county = null,
  petition = {},
  onValidationChange = noop,
}: {
  initialData?: Partial<DebtorInfo>;
  county?: string | null;
  petition?: PetitionAnswers;
  onValidationChange?: (isValid: boolean) => void;
} = {}) {
  return render(
    <DebtorInfoStep
      initialData={initialData}
      onDataChange={noop}
      onValidationChange={onValidationChange}
      county={county}
      onCountyChange={noop}
      petition={petition}
      onPetitionChange={noop}
      pendingSecrets={{}}
      onSecretChange={noop}
      division={null}
    />
  );
}

describe('DebtorInfoStep email lock', () => {
  it('pre-fills the email from the authenticated user and makes it read-only', () => {
    renderStep();

    const email = screen.getByLabelText(/email address/i) as HTMLInputElement;
    expect(email).toHaveValue('jane@example.com');
    expect(email.readOnly).toBe(true);
  });

  it('overrides a stale initialData email with the authenticated address', () => {
    // A user cannot change their sign-in identity mid-intake, so a different
    // email carried in from saved data must be replaced, not kept.
    renderStep({ initialData: { email: 'old@example.com' } });

    expect(screen.getByLabelText(/email address/i)).toHaveValue('jane@example.com');
  });
});

describe('DebtorInfoStep county', () => {
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

describe("DebtorInfoStep and Form 101's questions", () => {
  it('names the credit counseling requirement before the questions, as information', () => {
    renderStep();
    expect(screen.getByText(COUNSELING_REQUIREMENT_INTRO)).toBeInTheDocument();
  });

  it('a loaded step with a saved SSN continues once every yes/no is answered', () => {
    // Owner ruling Q3: the filer isn't asked to type the SSN again
    const onValidationChange = vi.fn();
    const { rerender } = renderStep({
      initialData: { ...LOADED, ssn_saved: true },
      county: 'Cook',
      onValidationChange,
    });
    expect(screen.getByLabelText(/social security number/i)).toHaveValue('');
    expect(screen.getByText(SSN_SAVED)).toBeInTheDocument();
    // The gates are still open, so Continue waits
    expect(onValidationChange).toHaveBeenLastCalledWith(false);

    rerender(
      <DebtorInfoStep
        initialData={{ ...LOADED, ssn_saved: true }}
        onDataChange={noop}
        onValidationChange={onValidationChange}
        county="Cook"
        onCountyChange={noop}
        petition={EVERY_GATE_NO}
        onPetitionChange={noop}
        pendingSecrets={{}}
        onSecretChange={noop}
        division="Eastern"
      />
    );
    expect(onValidationChange).toHaveBeenLastCalledWith(true);
  });

  it('names the open Form 101 question in the status region whenever it alone holds Continue', () => {
    // F8: a returning filer whose fields above are all valid, sent here from Review, meets a held
    // Continue; the region says which question holds it before they touch the block
    const onValidationChange = vi.fn();
    const { unmount } = renderStep({
      initialData: { ...LOADED, ssn_saved: true },
      county: 'Cook',
      onValidationChange,
    });
    expect(onValidationChange).toHaveBeenLastCalledWith(false);
    expect(screen.getByRole('status')).toHaveTextContent(firstPetitionGap({}) as string);
    unmount();

    // A field above still open holds Continue itself, and its own error says so: the region
    // waits until the filer reaches the block
    renderStep({ county: 'Cook' });
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });

  it('a loaded step with no saved SSN still asks for it', () => {
    const onValidationChange = vi.fn();
    renderStep({
      initialData: { ...LOADED, ssn_saved: false },
      county: 'Cook',
      petition: EVERY_GATE_NO,
      onValidationChange,
    });
    expect(screen.queryByText(SSN_SAVED)).not.toBeInTheDocument();
    expect(onValidationChange).toHaveBeenLastCalledWith(false);
  });

  it('the home ZIP takes digits only, at most nine, typed or pasted', async () => {
    // Owner ruling Q1: Form 101 line 5 prints a ZIP+4 as nine digits; no native maxLength, so a
    // paste loses no digit to the box
    renderStep();
    const zip = screen.getByRole('textbox', { name: /zip code/i });
    expect(zip).not.toHaveAttribute('maxLength');
    await userEvent.type(zip, '60201-12345');
    expect(zip).toHaveValue('602011234');
    await userEvent.clear(zip);
    await userEvent.click(zip);
    await userEvent.paste('60201-1234');
    expect(zip).toHaveValue('602011234');
  });

  it('a home ZIP of the wrong length says what the box takes, in the approved words', async () => {
    // Owner ruling Q7
    renderStep();
    const zip = screen.getByRole('textbox', { name: /zip code/i });
    await userEvent.type(zip, '6020');
    expect(screen.getByText(HOME_ZIP_ERROR)).toBeInTheDocument();
    await userEvent.type(zip, '1');
    expect(screen.queryByText(HOME_ZIP_ERROR)).not.toBeInTheDocument();
  });

  it('a home ZIP stored with a hyphen loads valid and is saved as stored', () => {
    // PR review, reversing T8-zip-load: the ZIP is judged on its digits, so a stored ZIP+4 needs
    // no edit; the value is not rewritten on load, which would change the body and reopen a
    // completed intake
    const onValidationChange = vi.fn();
    const onDataChange = vi.fn();
    render(
      <DebtorInfoStep
        initialData={{ ...LOADED, zip_code: '60201-1234', ssn_saved: true }}
        onDataChange={onDataChange}
        onValidationChange={onValidationChange}
        county="Cook"
        onCountyChange={noop}
        petition={EVERY_GATE_NO}
        onPetitionChange={noop}
        pendingSecrets={{}}
        onSecretChange={noop}
        division={null}
      />
    );
    expect(screen.getByRole('textbox', { name: /zip code/i })).toHaveValue('60201-1234');
    expect(screen.queryByText(HOME_ZIP_ERROR)).not.toBeInTheDocument();
    expect(onValidationChange).toHaveBeenLastCalledWith(true);
    for (const [data] of onDataChange.mock.calls) {
      expect(data.zip_code).toBe('60201-1234');
    }
  });
});
