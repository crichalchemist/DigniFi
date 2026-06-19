import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DynamicFormWizard } from '../DynamicFormWizard';

import { askModulesAPI } from '../../../api/client';
import { vi } from 'vitest';

vi.mock('../../../api/client', () => ({
  askModulesAPI: {
    getUISpec: vi.fn(),
    bulkUpsertAnswers: vi.fn(),
  },
}));

const mockSession = {
  id: 1,
  sofa_report: {},
};

// Mock IntakeContext provider
vi.mock('../../../context/IntakeContext', () => ({
  useIntake: () => ({
    session: mockSession,
    refreshSession: vi.fn(),
  }),
  IntakeProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe('DynamicFormWizard', () => {
  const mockOnComplete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('handles conditionals and sends full binding strings correctly', async () => {
    const user = userEvent.setup();

    // Mock a UI spec with conditional fields and arrays
    vi.mocked(askModulesAPI.getUISpec).mockResolvedValueOnce({
      form_type: 'form_107',
      template_filename: 'test.pdf',
      template_version: '1',
      steps: [
        {
          title: 'Step 1',
          fields: [
            {
              binding: 'sofa.has_prior_income',
              prompt: 'Do you have prior income?',
              widget: 'radio',
            },
            {
              binding: 'sofa.prior_income_group',
              prompt: 'Sources of income',
              widget: 'repeat_group',
              conditional_on: 'has_prior_income',
              fields: [
                {
                  binding: 'sofa.prior_income[].source',
                  prompt: 'Source of income',
                  widget: 'text',
                },
              ],
            },
          ],
        },
      ],
    });

    render(<DynamicFormWizard formType="form_107" onComplete={mockOnComplete} />);

    // Wait for the form to load
    expect(await screen.findByText('Step 1')).toBeInTheDocument();

    // The conditional field should NOT be rendered yet because condition is not met
    expect(screen.queryByText('Source of income')).not.toBeInTheDocument();

    // Answer the radio button
    const radioYes = screen.getByLabelText('Yes');
    await user.click(radioYes);

    // Now the conditional field should appear
    expect(await screen.findByText('Sources of income')).toBeInTheDocument();

    // Fill the repeat group input
    // The current implementation changes `[]` to `[0]`
    const incomeInput = screen.getAllByRole('textbox')[0];
    await user.type(incomeInput, 'Acme Corp');

    // Submit the form
    const nextBtn = screen.getByRole('button', { name: /Next|Complete/i });
    await user.click(nextBtn);

    // Verify bulkUpsertAnswers is called with full bindings
    expect(askModulesAPI.bulkUpsertAnswers).toHaveBeenCalledWith(1, [
      { form_type: 'form_107', binding: 'sofa.has_prior_income', value: 'Yes' },
      { form_type: 'form_107', binding: 'sofa.prior_income[0].source', value: 'Acme Corp' },
    ]);
  });
});
