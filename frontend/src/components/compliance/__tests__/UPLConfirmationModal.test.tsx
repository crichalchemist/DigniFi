import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UPLConfirmationModal } from '../UPLConfirmationModal';
import { UPL_FORM_GENERATION_CONFIRMATION } from '../../../constants/upl';

describe('UPLConfirmationModal', () => {
  const defaultProps = {
    isOpen: true,
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  it('renders nothing when not open', () => {
    const { container } = render(
      <UPLConfirmationModal {...defaultProps} isOpen={false} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders modal dialog when open', () => {
    render(<UPLConfirmationModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
  });

  it('shows default title', () => {
    render(<UPLConfirmationModal {...defaultProps} />);
    expect(screen.getByText('Acknowledgment Required')).toBeInTheDocument();
  });

  it('shows custom title', () => {
    render(<UPLConfirmationModal {...defaultProps} title="Custom Title" />);
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });

  it('shows default confirmation text', () => {
    render(<UPLConfirmationModal {...defaultProps} />);
    expect(screen.getByText(UPL_FORM_GENERATION_CONFIRMATION)).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Acknowledgment checkbox
  // ---------------------------------------------------------------------------

  it('has Continue button disabled until checkbox is checked', () => {
    render(<UPLConfirmationModal {...defaultProps} />);
    const continueBtn = screen.getByRole('button', { name: /continue/i });
    expect(continueBtn).toBeDisabled();
  });

  it('enables Continue after checking acknowledgment', async () => {
    const user = userEvent.setup();
    render(<UPLConfirmationModal {...defaultProps} />);

    await user.click(screen.getByRole('checkbox'));

    expect(screen.getByRole('button', { name: /continue/i })).toBeEnabled();
  });

  it('calls onConfirm when Continue is clicked after acknowledgment', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<UPLConfirmationModal {...defaultProps} onConfirm={onConfirm} />);

    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: /continue/i }));

    expect(onConfirm).toHaveBeenCalledOnce();
  });

  // ---------------------------------------------------------------------------
  // Cancel / Close
  // ---------------------------------------------------------------------------

  it('calls onCancel when Cancel is clicked', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<UPLConfirmationModal {...defaultProps} onCancel={onCancel} />);

    await user.click(screen.getByRole('button', { name: /cancel/i }));

    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('calls onCancel when close button is clicked', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<UPLConfirmationModal {...defaultProps} onCancel={onCancel} />);

    await user.click(screen.getByRole('button', { name: /close/i }));

    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('calls onCancel on Escape key', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<UPLConfirmationModal {...defaultProps} onCancel={onCancel} />);

    await user.keyboard('{Escape}');

    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('calls onCancel when clicking overlay background', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<UPLConfirmationModal {...defaultProps} onCancel={onCancel} />);

    // Click the overlay (role="presentation")
    const overlay = screen.getByRole('presentation');
    await user.click(overlay);

    expect(onCancel).toHaveBeenCalledOnce();
  });

  // ---------------------------------------------------------------------------
  // Reset state
  // ---------------------------------------------------------------------------

  it('resets checkbox when reopened', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<UPLConfirmationModal {...defaultProps} />);

    // Check the box
    await user.click(screen.getByRole('checkbox'));
    expect(screen.getByRole('checkbox')).toBeChecked();

    // Close
    rerender(<UPLConfirmationModal {...defaultProps} isOpen={false} />);

    // Reopen
    rerender(<UPLConfirmationModal {...defaultProps} isOpen={true} />);

    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });
});
