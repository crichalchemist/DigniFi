import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FormCard } from '../FormCard';
import type { GeneratedForm } from '../../../types/api';

const mockForm: GeneratedForm = {
  id: 1,
  session: 1,
  form_type: 'form_101',
  form_type_display: 'Form 101 - Voluntary Petition',
  status: 'generated',
  status_display: 'Generated',
  form_data: {},
  pdf_file_path: '/media/forms/form_101_1.pdf',
  upl_disclaimer: 'This form was prepared using information you provided.',
  generated_by: 1,
  generated_at: '2026-01-20T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
};

describe('FormCard', () => {
  const defaultProps = {
    formType: 'form_101' as const,
    onGenerate: vi.fn().mockResolvedValue(undefined),
    onMarkDownloaded: vi.fn().mockResolvedValue(undefined),
    onMarkFiled: vi.fn().mockResolvedValue(undefined),
  };

  // ---------------------------------------------------------------------------
  // Pending state (no generated form)
  // ---------------------------------------------------------------------------

  it('renders form metadata', () => {
    render(<FormCard {...defaultProps} />);
    expect(
      screen.getByText('Form 101 - Voluntary Petition'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Your official petition to file for bankruptcy'),
    ).toBeInTheDocument();
  });

  it('shows Generate button when pending', () => {
    render(<FormCard {...defaultProps} />);
    expect(
      screen.getByRole('button', { name: /generate/i }),
    ).toBeInTheDocument();
  });

  it('calls onGenerate with form type', async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn().mockResolvedValue(undefined);
    render(<FormCard {...defaultProps} onGenerate={onGenerate} />);

    await user.click(screen.getByRole('button', { name: /generate/i }));

    expect(onGenerate).toHaveBeenCalledWith('form_101');
  });

  // ---------------------------------------------------------------------------
  // Generated state
  // ---------------------------------------------------------------------------

  it('shows Download and Mark as Filed buttons when generated', () => {
    render(<FormCard {...defaultProps} generatedForm={mockForm} />);
    expect(
      screen.getByRole('button', { name: /download/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /mark as filed/i }),
    ).toBeInTheDocument();
  });

  it('shows UPL disclaimer from generated form', () => {
    render(<FormCard {...defaultProps} generatedForm={mockForm} />);
    expect(
      screen.getByText('This form was prepared using information you provided.'),
    ).toBeInTheDocument();
  });

  it('calls onMarkDownloaded with form id', async () => {
    const user = userEvent.setup();
    const onMarkDownloaded = vi.fn().mockResolvedValue(undefined);
    render(
      <FormCard
        {...defaultProps}
        generatedForm={mockForm}
        onMarkDownloaded={onMarkDownloaded}
      />,
    );

    await user.click(screen.getByRole('button', { name: /download/i }));

    expect(onMarkDownloaded).toHaveBeenCalledWith(1);
  });

  // ---------------------------------------------------------------------------
  // Downloaded state
  // ---------------------------------------------------------------------------

  it('shows Mark as Filed button when downloaded', () => {
    const downloadedForm = { ...mockForm, status: 'downloaded' as const };
    render(<FormCard {...defaultProps} generatedForm={downloadedForm} />);
    expect(
      screen.getByRole('button', { name: /mark as filed/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /download/i }),
    ).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Filed state
  // ---------------------------------------------------------------------------

  it('shows Filed indicator when filed', () => {
    const filedForm = { ...mockForm, status: 'filed' as const };
    render(<FormCard {...defaultProps} generatedForm={filedForm} />);
    // Status badge shows "Filed", and the filed-check also shows "Filed"
    expect(screen.getByRole('status')).toHaveTextContent('Filed');
    expect(screen.queryByRole('button', { name: /generate/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /download/i })).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Status badge
  // ---------------------------------------------------------------------------

  it('shows pending badge when no form', () => {
    render(<FormCard {...defaultProps} />);
    expect(screen.getByRole('status')).toHaveTextContent('Not Generated');
  });

  it('shows generated badge when form exists', () => {
    render(<FormCard {...defaultProps} generatedForm={mockForm} />);
    expect(screen.getByRole('status')).toHaveTextContent('Generated');
  });
});
