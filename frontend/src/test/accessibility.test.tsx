/**
 * Automated Accessibility Tests
 *
 * Uses axe-core via vitest-axe to scan rendered components for
 * WCAG 2.1 AA violations. No critical or serious violations allowed.
 */

import { render, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { IntakeProvider } from '../context/IntakeContext';
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { LandingPage } from '../pages/LandingPage';
import { FormDashboard } from '../pages/FormDashboard';
import { FormCard } from '../components/forms/FormCard';
import { FormStatusBadge } from '../components/forms/FormStatusBadge';
import { UPLDisclaimer } from '../components/compliance/UPLDisclaimer';
import { UPLConfirmationModal } from '../components/compliance/UPLConfirmationModal';
import { Button } from '../components/common/Button';
import { FormField, FormSelect } from '../components/common/FormField';
import { ProgressIndicator } from '../components/common/ProgressIndicator';
import { UPL_GENERAL_DISCLAIMER } from '../constants/upl';
import type { GeneratedForm } from '../types/api';

// ============================================================================
// Helpers
// ============================================================================

function withRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

function withProviders(ui: React.ReactElement) {
  return render(
    <BrowserRouter>
      <AuthProvider>{ui}</AuthProvider>
    </BrowserRouter>,
  );
}

function withIntakeProvider(ui: React.ReactElement) {
  localStorage.setItem('current_session_id', '1');
  return render(
    <BrowserRouter>
      <AuthProvider>
        <IntakeProvider>{ui}</IntakeProvider>
      </AuthProvider>
    </BrowserRouter>,
  );
}

// Exclude color-contrast rule since jsdom doesn't compute styles accurately
const axeOptions = {
  rules: {
    'color-contrast': { enabled: false },
  },
};

// ============================================================================
// Common Components
// ============================================================================

describe('Accessibility: Common Components', () => {
  it('Button has no violations', async () => {
    const { container } = render(<Button>Click me</Button>);
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('Button (loading) has no violations', async () => {
    const { container } = render(<Button isLoading loadingText="Saving...">Save</Button>);
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('FormField has no violations', async () => {
    const { container } = render(
      <FormField label="Full Name" name="full_name" required />,
    );
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('FormField with error has no violations', async () => {
    const { container } = render(
      <FormField
        label="Email"
        name="email"
        error="Please enter a valid email address"
        required
      />,
    );
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('FormSelect has no violations', async () => {
    const { container } = render(
      <FormSelect
        label="State"
        name="state"
        options={[
          { value: 'IL', label: 'Illinois' },
          { value: 'CA', label: 'California' },
        ]}
      />,
    );
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('ProgressIndicator has no violations', async () => {
    const steps = [
      { number: 1, label: 'Info', isCompleted: true, isCurrent: false },
      { number: 2, label: 'Income', isCompleted: false, isCurrent: true },
      { number: 3, label: 'Review', isCompleted: false, isCurrent: false },
    ];
    const { container } = render(
      <ProgressIndicator steps={steps} currentStep={2} />,
    );
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });
});

// ============================================================================
// Compliance Components
// ============================================================================

describe('Accessibility: Compliance Components', () => {
  it('UPLDisclaimer inline has no violations', async () => {
    const { container } = render(
      <UPLDisclaimer text={UPL_GENERAL_DISCLAIMER} variant="inline" />,
    );
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('UPLDisclaimer banner has no violations', async () => {
    const { container } = render(
      <UPLDisclaimer text={UPL_GENERAL_DISCLAIMER} variant="banner" />,
    );
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('UPLConfirmationModal has no violations', async () => {
    const { container } = render(
      <UPLConfirmationModal
        isOpen={true}
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });
});

// ============================================================================
// Form Components
// ============================================================================

describe('Accessibility: Form Components', () => {
  it('FormStatusBadge has no violations', async () => {
    const { container } = render(<FormStatusBadge status="generated" />);
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('FormCard (pending) has no violations', async () => {
    const { container } = render(
      <FormCard
        formType="form_101"
        onGenerate={async () => {}}
        onMarkDownloaded={async () => {}}
        onMarkFiled={async () => {}}
      />,
    );
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('FormCard (generated) has no violations', async () => {
    const mockForm: GeneratedForm = {
      id: 1,
      session: 1,
      form_type: 'form_101',
      form_type_display: 'Form 101',
      status: 'generated',
      status_display: 'Generated',
      form_data: {},
      pdf_file_path: '/forms/101.pdf',
      upl_disclaimer: 'Test disclaimer.',
      generated_by: 1,
      generated_at: '2026-01-20T10:00:00Z',
      updated_at: '2026-01-20T10:00:00Z',
    };
    const { container } = render(
      <FormCard
        formType="form_101"
        generatedForm={mockForm}
        onGenerate={async () => {}}
        onMarkDownloaded={async () => {}}
        onMarkFiled={async () => {}}
      />,
    );
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });
});

// ============================================================================
// Pages
// ============================================================================

describe('Accessibility: Pages', () => {
  it('LandingPage has no violations', async () => {
    const { container } = withProviders(<LandingPage />);
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('LoginPage has no violations', async () => {
    const { container } = withProviders(<LoginPage />);
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('RegisterPage has no violations', async () => {
    const { container } = withProviders(<RegisterPage />);
    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });

  it('FormDashboard has no violations after loading', async () => {
    const { container } = withIntakeProvider(<FormDashboard />);

    // Wait for data to load
    await waitFor(() => {
      expect(container.querySelector('.form-dashboard-title')).not.toBeNull();
    });

    const results = await axe(container, axeOptions);
    expect(results).toHaveNoViolations();
  });
});
