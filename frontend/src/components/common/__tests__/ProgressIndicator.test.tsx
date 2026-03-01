import { render, screen } from '@testing-library/react';
import { ProgressIndicator } from '../ProgressIndicator';

const makeSteps = (currentStep: number) => [
  { number: 1, label: 'Personal Info', isCompleted: currentStep > 1, isCurrent: currentStep === 1 },
  { number: 2, label: 'Income', isCompleted: currentStep > 2, isCurrent: currentStep === 2 },
  { number: 3, label: 'Expenses', isCompleted: currentStep > 3, isCurrent: currentStep === 3 },
  { number: 4, label: 'Assets', isCompleted: currentStep > 4, isCurrent: currentStep === 4 },
  { number: 5, label: 'Amounts Owed', isCompleted: currentStep > 5, isCurrent: currentStep === 5 },
  { number: 6, label: 'Review', isCompleted: false, isCurrent: currentStep === 6 },
];

describe('ProgressIndicator', () => {
  it('renders all step labels', () => {
    const steps = makeSteps(1);
    render(<ProgressIndicator steps={steps} currentStep={1} />);

    expect(screen.getByText('Personal Info')).toBeInTheDocument();
    expect(screen.getByText('Income')).toBeInTheDocument();
    expect(screen.getByText('Expenses')).toBeInTheDocument();
    expect(screen.getByText('Assets')).toBeInTheDocument();
    expect(screen.getByText('Amounts Owed')).toBeInTheDocument();
    expect(screen.getByText('Review')).toBeInTheDocument();
  });

  it('marks current step with aria-current="step"', () => {
    const steps = makeSteps(3);
    render(<ProgressIndicator steps={steps} currentStep={3} />);

    const listItems = screen.getAllByRole('listitem');
    // Step 3 (index 2) should be current
    expect(listItems[2]).toHaveAttribute('aria-current', 'step');
    // Others should not
    expect(listItems[0]).not.toHaveAttribute('aria-current');
    expect(listItems[4]).not.toHaveAttribute('aria-current');
  });

  it('shows checkmark for completed steps', () => {
    const steps = makeSteps(3);
    render(<ProgressIndicator steps={steps} currentStep={3} />);

    const listItems = screen.getAllByRole('listitem');
    // Completed steps (1, 2) should have checkmark SVG
    expect(listItems[0].querySelector('.step-checkmark')).toBeInTheDocument();
    expect(listItems[1].querySelector('.step-checkmark')).toBeInTheDocument();
    // Current step (3) should show number
    expect(listItems[2].querySelector('.step-number')).toBeInTheDocument();
  });

  it('shows "Complete" text for completed steps', () => {
    const steps = makeSteps(4);
    render(<ProgressIndicator steps={steps} currentStep={4} />);

    // Steps 1-3 are completed
    const completeLabels = screen.getAllByText('Complete');
    expect(completeLabels).toHaveLength(3);
  });

  it('renders step numbers for non-completed steps', () => {
    const steps = makeSteps(1);
    render(<ProgressIndicator steps={steps} currentStep={1} />);

    // All 6 steps show numbers since only step 1 is current, none completed
    expect(screen.getByLabelText('Step 1')).toBeInTheDocument();
    expect(screen.getByLabelText('Step 6')).toBeInTheDocument();
  });

  it('renders step connectors between steps', () => {
    const steps = makeSteps(2);
    const { container } = render(
      <ProgressIndicator steps={steps} currentStep={2} />,
    );

    // 5 connectors between 6 steps
    const connectors = container.querySelectorAll('.step-connector');
    expect(connectors).toHaveLength(5);
  });

  it('marks completed connectors', () => {
    const steps = makeSteps(3);
    const { container } = render(
      <ProgressIndicator steps={steps} currentStep={3} />,
    );

    const completedConnectors = container.querySelectorAll('.step-connector.completed');
    // Steps 1 and 2 are completed, so their connectors should be completed
    expect(completedConnectors).toHaveLength(2);
  });

  it('has navigation landmark role', () => {
    const steps = makeSteps(1);
    render(<ProgressIndicator steps={steps} currentStep={1} />);
    expect(screen.getByRole('navigation', { name: /intake progress/i })).toBeInTheDocument();
  });

  it('announces progress to screen readers', () => {
    const steps = makeSteps(3);
    render(<ProgressIndicator steps={steps} currentStep={3} />);

    // sr-only region with aria-live should contain progress info
    const liveRegion = screen.getByText(/completed 2 of 6 steps/i);
    expect(liveRegion).toHaveClass('sr-only');
    expect(liveRegion).toHaveAttribute('aria-live', 'polite');
  });

  it('applies CSS classes based on step state', () => {
    const steps = makeSteps(3);
    render(<ProgressIndicator steps={steps} currentStep={3} />);

    const listItems = screen.getAllByRole('listitem');
    expect(listItems[0]).toHaveClass('completed');
    expect(listItems[2]).toHaveClass('current');
    expect(listItems[4]).toHaveClass('upcoming');
  });
});
