import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '../Button';

describe('Button', () => {
  // ---------------------------------------------------------------------------
  // Rendering variants
  // ---------------------------------------------------------------------------

  it('renders with default props', () => {
    render(<Button>Continue</Button>);
    const button = screen.getByRole('button', { name: /continue/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute('type', 'button');
    expect(button).toHaveClass('button', 'button--primary', 'button--md');
  });

  it.each(['primary', 'secondary', 'outline', 'text'] as const)(
    'applies %s variant class',
    (variant) => {
      render(<Button variant={variant}>Click</Button>);
      expect(screen.getByRole('button')).toHaveClass(`button--${variant}`);
    },
  );

  it.each(['sm', 'md', 'lg'] as const)('applies %s size class', (size) => {
    render(<Button size={size}>Click</Button>);
    expect(screen.getByRole('button')).toHaveClass(`button--${size}`);
  });

  it('applies full-width class', () => {
    render(<Button fullWidth>Submit</Button>);
    expect(screen.getByRole('button')).toHaveClass('button--full-width');
  });

  // ---------------------------------------------------------------------------
  // Disabled state
  // ---------------------------------------------------------------------------

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-disabled', 'true');
    expect(button).toHaveClass('button--disabled');
  });

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------

  it('shows loading spinner and text when isLoading', () => {
    render(<Button isLoading loadingText="Saving...">Submit</Button>);
    const button = screen.getByRole('button');

    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
    // "Saving..." appears in both button-content and sr-only
    expect(screen.getByText('Saving...', { selector: '.button-content' })).toBeInTheDocument();

    // Spinner is present but aria-hidden
    const spinner = button.querySelector('.button-spinner');
    expect(spinner).toHaveAttribute('aria-hidden', 'true');
  });

  it('uses default loading text when none provided', () => {
    render(<Button isLoading>Submit</Button>);
    expect(screen.getByText('Loading...', { selector: '.button-content' })).toBeInTheDocument();
  });

  it('announces loading state to screen readers', () => {
    render(<Button isLoading loadingText="Processing...">Submit</Button>);
    const liveRegion = screen.getByText('Processing...', { selector: '.sr-only' });
    expect(liveRegion).toHaveAttribute('aria-live', 'polite');
  });

  // ---------------------------------------------------------------------------
  // Icon support
  // ---------------------------------------------------------------------------

  it('renders icon on the left by default', () => {
    const icon = <span data-testid="icon">★</span>;
    render(<Button icon={icon}>Star</Button>);
    const iconWrapper = screen.getByTestId('icon').parentElement;
    expect(iconWrapper).toHaveClass('button-icon--left');
    expect(iconWrapper).toHaveAttribute('aria-hidden', 'true');
  });

  it('renders icon on the right', () => {
    const icon = <span data-testid="icon">→</span>;
    render(<Button icon={icon} iconPosition="right">Next</Button>);
    const iconWrapper = screen.getByTestId('icon').parentElement;
    expect(iconWrapper).toHaveClass('button-icon--right');
  });

  it('hides icon when loading', () => {
    const icon = <span data-testid="icon">★</span>;
    render(<Button icon={icon} isLoading>Star</Button>);
    expect(screen.queryByTestId('icon')).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Click handler
  // ---------------------------------------------------------------------------

  it('calls onClick when clicked', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click me</Button>);

    await user.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('does not call onClick when disabled', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button onClick={onClick} disabled>Click me</Button>);

    await user.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
  });

  it('does not call onClick when loading', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button onClick={onClick} isLoading>Click me</Button>);

    await user.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
  });

  // ---------------------------------------------------------------------------
  // Custom className / type passthrough
  // ---------------------------------------------------------------------------

  it('merges custom className', () => {
    render(<Button className="my-custom">Custom</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('button', 'my-custom');
  });

  it('supports submit type', () => {
    render(<Button type="submit">Go</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'submit');
  });
});
