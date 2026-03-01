import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UPLDisclaimer } from '../UPLDisclaimer';
import { UPL_GENERAL_DISCLAIMER } from '../../../constants/upl';

describe('UPLDisclaimer', () => {
  // ---------------------------------------------------------------------------
  // Inline variant
  // ---------------------------------------------------------------------------

  it('renders inline variant by default', () => {
    render(<UPLDisclaimer text="Test disclaimer" />);
    const element = screen.getByRole('note');
    expect(element).toHaveClass('upl-disclaimer--inline');
    expect(element).toHaveTextContent('Test disclaimer');
  });

  it('has correct aria-label for inline', () => {
    render(<UPLDisclaimer text="test" variant="inline" />);
    expect(screen.getByRole('note')).toHaveAttribute(
      'aria-label',
      'Legal information disclaimer',
    );
  });

  it('renders info icon in inline variant', () => {
    const { container } = render(<UPLDisclaimer text="test" />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Banner variant
  // ---------------------------------------------------------------------------

  it('renders banner variant with title', () => {
    render(<UPLDisclaimer text={UPL_GENERAL_DISCLAIMER} variant="banner" />);
    const element = screen.getByRole('note');
    expect(element).toHaveClass('upl-disclaimer--banner');
    expect(screen.getByText('Legal Information Notice')).toBeInTheDocument();
    expect(element).toHaveTextContent(UPL_GENERAL_DISCLAIMER);
  });

  it('has correct aria-label for banner', () => {
    render(<UPLDisclaimer text="test" variant="banner" />);
    expect(screen.getByRole('note')).toHaveAttribute(
      'aria-label',
      'Important legal disclaimer',
    );
  });

  // ---------------------------------------------------------------------------
  // Checkbox variant
  // ---------------------------------------------------------------------------

  it('renders checkbox variant with input', () => {
    const onAcknowledge = vi.fn();
    render(
      <UPLDisclaimer
        text="I acknowledge"
        variant="checkbox"
        onAcknowledge={onAcknowledge}
      />,
    );

    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeInTheDocument();
    expect(checkbox).not.toBeChecked();
  });

  it('calls onAcknowledge when checkbox is toggled', async () => {
    const user = userEvent.setup();
    const onAcknowledge = vi.fn();
    render(
      <UPLDisclaimer
        text="I acknowledge"
        variant="checkbox"
        onAcknowledge={onAcknowledge}
      />,
    );

    await user.click(screen.getByRole('checkbox'));
    expect(onAcknowledge).toHaveBeenCalledWith(true);
  });

  it('respects controlled acknowledged prop', () => {
    render(
      <UPLDisclaimer
        text="I acknowledge"
        variant="checkbox"
        acknowledged={true}
      />,
    );
    expect(screen.getByRole('checkbox')).toBeChecked();
  });

  // ---------------------------------------------------------------------------
  // Modal variant
  // ---------------------------------------------------------------------------

  it('returns null for modal variant (use UPLConfirmationModal instead)', () => {
    const { container } = render(
      <UPLDisclaimer text="test" variant="modal" />,
    );
    expect(container.innerHTML).toBe('');
  });

  // ---------------------------------------------------------------------------
  // Custom className
  // ---------------------------------------------------------------------------

  it('applies custom className', () => {
    render(
      <UPLDisclaimer text="test" variant="banner" className="my-custom" />,
    );
    expect(screen.getByRole('note')).toHaveClass('my-custom');
  });
});
