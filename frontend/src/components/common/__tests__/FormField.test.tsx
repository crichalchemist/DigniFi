import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FormField, FormTextarea, FormSelect } from '../FormField';

// =============================================================================
// FormField (input)
// =============================================================================

describe('FormField', () => {
  it('renders label and input', () => {
    render(<FormField label="First Name" name="first_name" />);
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
  });

  it('marks required fields with asterisk', () => {
    render(<FormField label="SSN" name="ssn" required />);
    const indicator = screen.getByLabelText('required');
    expect(indicator).toHaveTextContent('*');
  });

  it('sets aria-required on required fields', () => {
    render(<FormField label="SSN" name="ssn" required />);
    expect(screen.getByLabelText(/ssn/i)).toHaveAttribute('aria-required', 'true');
  });

  it('displays help text and links it via aria-describedby', () => {
    render(
      <FormField
        label="Phone"
        name="phone"
        helpText="Enter your 10-digit phone number"
      />,
    );
    const input = screen.getByLabelText(/phone/i);
    const helpText = screen.getByText(/10-digit/i);

    expect(helpText).toBeInTheDocument();
    expect(input).toHaveAttribute('aria-describedby', expect.stringContaining(helpText.id));
  });

  it('displays error message with role=alert', () => {
    render(
      <FormField
        label="Email"
        name="email"
        error="Please provide a valid email address"
      />,
    );
    const error = screen.getByRole('alert');
    expect(error).toHaveTextContent('Please provide a valid email address');
  });

  it('sets aria-invalid when error is present', () => {
    render(<FormField label="Email" name="email" error="Invalid" />);
    expect(screen.getByLabelText(/email/i)).toHaveAttribute('aria-invalid', 'true');
  });

  it('links error via aria-describedby', () => {
    render(<FormField label="Email" name="email" error="Invalid" />);
    const input = screen.getByLabelText(/email/i);
    expect(input.getAttribute('aria-describedby')).toContain('error');
  });

  it('sets aria-invalid to false when no error', () => {
    render(<FormField label="Name" name="name" />);
    expect(screen.getByLabelText(/name/i)).toHaveAttribute('aria-invalid', 'false');
  });

  it('renders icon when provided', () => {
    render(
      <FormField label="Search" name="search" icon={<span data-testid="icon">🔍</span>} />,
    );
    expect(screen.getByTestId('icon')).toBeInTheDocument();
    expect(screen.getByLabelText(/search/i)).toHaveClass('with-icon');
  });

  it('has-error class on wrapper when error present', () => {
    const { container } = render(
      <FormField label="Name" name="name" error="Required" />,
    );
    expect(container.querySelector('.form-field')).toHaveClass('has-error');
  });

  it('accepts user input', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FormField label="Name" name="name" onChange={onChange} />);

    await user.type(screen.getByLabelText(/name/i), 'Jane');
    expect(onChange).toHaveBeenCalled();
  });
});

// =============================================================================
// FormTextarea
// =============================================================================

describe('FormTextarea', () => {
  it('renders textarea with label', () => {
    render(<FormTextarea label="Notes" name="notes" />);
    const textarea = screen.getByLabelText(/notes/i);
    expect(textarea.tagName).toBe('TEXTAREA');
  });

  it('applies default rows', () => {
    render(<FormTextarea label="Notes" name="notes" />);
    expect(screen.getByLabelText(/notes/i)).toHaveAttribute('rows', '4');
  });

  it('displays error with role=alert', () => {
    render(<FormTextarea label="Notes" name="notes" error="Too short" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Too short');
  });
});

// =============================================================================
// FormSelect
// =============================================================================

describe('FormSelect', () => {
  const options = [
    { value: 'IL', label: 'Illinois' },
    { value: 'CA', label: 'California' },
  ];

  it('renders select with label and options', () => {
    render(<FormSelect label="State" name="state" options={options} />);
    const select = screen.getByLabelText(/state/i);
    expect(select.tagName).toBe('SELECT');
    expect(screen.getByText('Illinois')).toBeInTheDocument();
    expect(screen.getByText('California')).toBeInTheDocument();
  });

  it('shows placeholder option', () => {
    render(
      <FormSelect
        label="State"
        name="state"
        options={options}
        placeholder="Choose a state"
      />,
    );
    expect(screen.getByText('Choose a state')).toBeInTheDocument();
  });

  it('calls onChange with selected value', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <FormSelect label="State" name="state" options={options} onChange={onChange} />,
    );

    await user.selectOptions(screen.getByLabelText(/state/i), 'IL');
    expect(onChange).toHaveBeenCalledWith('IL');
  });

  it('displays error with role=alert', () => {
    render(
      <FormSelect
        label="State"
        name="state"
        options={options}
        error="Please select a state"
      />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Please select a state');
  });

  it('sets aria-invalid when error present', () => {
    render(
      <FormSelect label="State" name="state" options={options} error="Required" />,
    );
    expect(screen.getByLabelText(/state/i)).toHaveAttribute('aria-invalid', 'true');
  });
});
