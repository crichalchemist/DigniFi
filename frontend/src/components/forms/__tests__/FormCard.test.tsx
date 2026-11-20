import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { FormCard } from '../FormCard';
import type { GeneratedForm } from '../../../types/api';
import {
  MEANS_FILED_BEFORE_122A2,
  MEANS_PAIR_CANCEL,
  MEANS_PAIR_CONFIRM,
  MEANS_PAIR_MARK_ALONE,
  MEANS_PAIR_MARK_BOTH,
} from '../../../constants/copy';

const mockForm: GeneratedForm = {
  id: 1,
  session: 1,
  form_type: 'form_101',
  form_type_display: 'Form 101 - Voluntary Petition',
  status: 'generated',
  status_display: 'Generated',
  pdf_file_path: '/media/forms/form_101_1.pdf',
  upl_disclaimer: 'This form was prepared using information you provided.',
  generated_by: 1,
  generated_at: '2026-01-20T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
  filed_before_means_test: false,
  stored_box_2: null,
};

describe('FormCard', () => {
  const defaultProps = {
    formType: 'form_101' as const,
    onGenerate: vi.fn().mockResolvedValue(undefined),
    onDownload: vi.fn().mockResolvedValue(undefined),
    onMarkFiled: vi.fn().mockResolvedValue(undefined),
  };

  // ---------------------------------------------------------------------------
  // Pending state (no generated form)
  // ---------------------------------------------------------------------------

  it('renders form metadata', () => {
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} />
      </MemoryRouter>
    );
    expect(screen.getByText('Form 101 - Voluntary Petition')).toBeInTheDocument();
    expect(screen.getByText('Your official petition to file for bankruptcy')).toBeInTheDocument();
  });

  it('shows Generate button when pending', () => {
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} />
      </MemoryRouter>
    );
    expect(screen.getByRole('button', { name: /generate/i })).toBeInTheDocument();
  });

  // A court form is prepared only after the filer acknowledges that DigniFi gives legal
  // information, not advice: the same confirmation Generate All asks for.
  it('asks the filer to acknowledge the legal-information notice before preparing a form', async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn().mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} onGenerate={onGenerate} />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: /generate/i }));

    expect(
      screen.getByRole('dialog', { name: 'Legal acknowledgment required' })
    ).toBeInTheDocument();
    expect(onGenerate).not.toHaveBeenCalled();
  });

  it('prepares the form only after the filer acknowledges and continues', async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn().mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} onGenerate={onGenerate} />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: /generate/i }));
    const dialog = screen.getByRole('dialog', { name: 'Legal acknowledgment required' });
    await user.click(within(dialog).getByRole('checkbox'));
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }));

    expect(onGenerate).toHaveBeenCalledWith('form_101');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('prepares nothing when the filer cancels the acknowledgment', async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn().mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} onGenerate={onGenerate} />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: /generate/i }));
    const dialog = screen.getByRole('dialog', { name: 'Legal acknowledgment required' });
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

    expect(onGenerate).not.toHaveBeenCalled();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it("a pending card's Answer Questions goes to its answerPath, and to /ask/<form type> without one", async () => {
    const user = userEvent.setup();
    function Where() {
      return <p data-testid="where">{useLocation().pathname}</p>;
    }
    const { unmount } = render(
      <MemoryRouter>
        <FormCard {...defaultProps} formType="form_122a2" answerPath="/means-test" />
        <Where />
      </MemoryRouter>
    );
    await user.click(screen.getByRole('button', { name: 'Answer Questions' }));
    expect(screen.getByTestId('where')).toHaveTextContent('/means-test');
    unmount();

    render(
      <MemoryRouter>
        <FormCard {...defaultProps} formType="form_103b" />
        <Where />
      </MemoryRouter>
    );
    await user.click(screen.getByRole('button', { name: 'Answer Questions' }));
    expect(screen.getByTestId('where')).toHaveTextContent('/ask/form_103b');
  });

  const refusal = {
    message: 'Enter your name on the Your Information step.',
    link: { to: '/intake?step=debtor_info', label: 'Go to Your Information' },
  };

  it("a pending card's button goes where its refusal points and takes its label, before answerPath", async () => {
    const user = userEvent.setup();
    function Where() {
      const { pathname, search } = useLocation();
      return <p data-testid="where">{pathname + search}</p>;
    }
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} answerPath="/means-test" refusal={refusal} />
        <Where />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: 'Go to Your Information' }));

    expect(screen.getByTestId('where')).toHaveTextContent('/intake?step=debtor_info');
  });

  it('a refused pending card offers its fix once, as the button', () => {
    const { container } = render(
      <MemoryRouter>
        <FormCard {...defaultProps} refusal={refusal} />
      </MemoryRouter>
    );

    expect(screen.queryAllByRole('link', { name: 'Go to Your Information' })).toEqual([]);
    expect(container.querySelector('.form-card-refusal')).toHaveTextContent(refusal.message);
    expect(screen.getByRole('button', { name: 'Go to Your Information' })).toBeInTheDocument();
  });

  it('a refused generated card keeps the region’s link', () => {
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} generatedForm={mockForm} refusal={refusal} />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: 'Go to Your Information' })).toHaveAttribute(
      'href',
      '/intake?step=debtor_info'
    );
  });

  // ---------------------------------------------------------------------------
  // Generated state
  // ---------------------------------------------------------------------------

  it('shows Download and Mark as Filed buttons when generated', () => {
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} generatedForm={mockForm} />
      </MemoryRouter>
    );
    expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /mark as filed/i })).toBeInTheDocument();
  });

  // On Form 122A-1 and 122A-2, Mark as Filed works the pair out again on the server, which takes
  // as long as a download, so the button shows it is working rather than looking dead
  it('shows Mark as Filed working until it answers', async () => {
    const user = userEvent.setup();
    let answer: () => void = () => {};
    const onMarkFiled = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          answer = resolve;
        })
    );
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} generatedForm={mockForm} onMarkFiled={onMarkFiled} />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: 'Mark as Filed' }));

    const working = screen.getByRole('button', { name: /Marking as filed/ });
    expect(working).toBeDisabled();
    expect(working).toHaveAttribute('aria-busy', 'true');

    await act(async () => answer());

    expect(screen.getByRole('button', { name: 'Mark as Filed' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: /Marking as filed/ })).not.toBeInTheDocument();
  });

  // A download is not a filing: while one runs, Mark as Filed never says it is marking the form filed
  it('never reads as marking the form filed while a download runs', async () => {
    const user = userEvent.setup();
    let answer: () => void = () => {};
    const onDownload = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          answer = resolve;
        })
    );
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} generatedForm={mockForm} onDownload={onDownload} />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: 'Download' }));

    expect(screen.getByRole('button', { name: /Preparing/ })).toBeInTheDocument();
    expect(screen.queryAllByText(/Marking as filed/)).toHaveLength(0);
    expect(screen.getByRole('button', { name: 'Mark as Filed' })).toBeInTheDocument();

    await act(async () => answer());
  });

  it('shows UPL disclaimer from generated form', () => {
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} generatedForm={mockForm} />
      </MemoryRouter>
    );
    expect(
      screen.getByText('This form was prepared using information you provided.')
    ).toBeInTheDocument();
  });

  it('calls onDownload with form id', async () => {
    const user = userEvent.setup();
    const onDownload = vi.fn().mockResolvedValue(undefined);
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} generatedForm={mockForm} onDownload={onDownload} />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: /download/i }));

    expect(onDownload).toHaveBeenCalledWith(1);
  });

  // ---------------------------------------------------------------------------
  // Downloaded state
  // ---------------------------------------------------------------------------

  it('keeps Download and Mark as Filed after the first download', () => {
    const downloadedForm = { ...mockForm, status: 'downloaded' as const };
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} generatedForm={downloadedForm} />
      </MemoryRouter>
    );
    expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /mark as filed/i })).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Filed state
  // ---------------------------------------------------------------------------

  it('shows Filed indicator when filed', () => {
    const filedForm = { ...mockForm, status: 'filed' as const };
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} generatedForm={filedForm} />
      </MemoryRouter>
    );
    // Status badge shows "Filed", and the filed-check also shows "Filed"
    expect(screen.getByRole('status')).toHaveTextContent('Filed');
    expect(screen.getByLabelText('Filed with court')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /generate/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /mark as filed/i })).not.toBeInTheDocument();
  });

  it('downloads a filed form, which serves what was filed', async () => {
    const user = userEvent.setup();
    const onDownload = vi.fn().mockResolvedValue(undefined);
    const filedForm = { ...mockForm, status: 'filed' as const };
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} generatedForm={filedForm} onDownload={onDownload} />
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: /download/i }));

    expect(onDownload).toHaveBeenCalledWith(1);
  });

  // ---------------------------------------------------------------------------
  // Notice
  // ---------------------------------------------------------------------------

  it('shows a notice as information when given one', () => {
    const { container } = render(
      <MemoryRouter>
        <FormCard
          {...defaultProps}
          generatedForm={{ ...mockForm, status: 'filed' as const }}
          notice="This copy shows what was stored then."
          refusal={{ message: 'A refusal.' }}
        />
      </MemoryRouter>
    );

    const notice = screen.getByText('This copy shows what was stored then.');
    expect(notice).toHaveAttribute('role', 'status');
    expect(notice).toHaveClass('form-card-notice');
    // It comes before the refusal region
    const refusal = container.querySelector('.form-card-refusal')!;
    expect(notice.compareDocumentPosition(refusal) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('shows no notice without one', () => {
    const { container } = render(
      <MemoryRouter>
        <FormCard {...defaultProps} generatedForm={mockForm} />
      </MemoryRouter>
    );

    expect(container.querySelector('.form-card-notice')).toBeNull();
  });

  // ---------------------------------------------------------------------------
  // Form 122A-1 and Form 122A-2 are marked filed together (forms step 3h3, R13)
  // ---------------------------------------------------------------------------

  describe('the pair', () => {
    const pairProps = { ...defaultProps, formType: 'form_122a1' as const };
    const pairForm: GeneratedForm = { ...mockForm, form_type: 'form_122a1' };

    it('the card asks once before marking both', async () => {
      const user = userEvent.setup();
      const onMarkFiled = vi.fn().mockResolvedValue(undefined);
      const onMarkPairFiled = vi.fn().mockResolvedValue(undefined);
      render(
        <MemoryRouter>
          <FormCard
            {...pairProps}
            generatedForm={pairForm}
            pair={{ kind: 'both' }}
            onMarkFiled={onMarkFiled}
            onMarkPairFiled={onMarkPairFiled}
          />
        </MemoryRouter>
      );

      await user.click(screen.getByRole('button', { name: 'Mark as Filed' }));

      const confirm = screen.getByRole('group', { name: MEANS_PAIR_CONFIRM });
      expect(confirm).toBeInTheDocument();
      expect(onMarkPairFiled).not.toHaveBeenCalled();
      // The trigger gives way to the confirm's own buttons
      expect(screen.queryByRole('button', { name: 'Mark as Filed' })).not.toBeInTheDocument();

      await user.click(within(confirm).getByRole('button', { name: MEANS_PAIR_MARK_BOTH }));

      expect(onMarkPairFiled).toHaveBeenCalledTimes(1);
      expect(onMarkFiled).not.toHaveBeenCalled();
    });

    it('cancel marks neither', async () => {
      const user = userEvent.setup();
      const onMarkFiled = vi.fn().mockResolvedValue(undefined);
      const onMarkPairFiled = vi.fn().mockResolvedValue(undefined);
      render(
        <MemoryRouter>
          <FormCard
            {...pairProps}
            generatedForm={pairForm}
            pair={{ kind: 'both' }}
            onMarkFiled={onMarkFiled}
            onMarkPairFiled={onMarkPairFiled}
          />
        </MemoryRouter>
      );

      await user.click(screen.getByRole('button', { name: 'Mark as Filed' }));
      await user.click(screen.getByRole('button', { name: MEANS_PAIR_CANCEL }));

      expect(screen.queryByRole('group', { name: MEANS_PAIR_CONFIRM })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Mark as Filed' })).toBeInTheDocument();
      expect(onMarkFiled).not.toHaveBeenCalled();
      expect(onMarkPairFiled).not.toHaveBeenCalled();
    });

    it('a filed partner that disagrees shows its notice before marking alone', async () => {
      const user = userEvent.setup();
      const onMarkFiled = vi.fn().mockResolvedValue(undefined);
      const onMarkPairFiled = vi.fn().mockResolvedValue(undefined);
      render(
        <MemoryRouter>
          <FormCard
            {...pairProps}
            generatedForm={pairForm}
            pair={{
              kind: 'alone',
              partnerLabel: 'Form 122A-2 - Chapter 7 Means Test Calculation',
              partnerNotice: MEANS_FILED_BEFORE_122A2,
            }}
            onMarkFiled={onMarkFiled}
            onMarkPairFiled={onMarkPairFiled}
          />
        </MemoryRouter>
      );

      await user.click(screen.getByRole('button', { name: 'Mark as Filed' }));

      const confirm = screen.getByRole('group', {
        name: `Form 122A-2 - Chapter 7 Means Test Calculation ${MEANS_FILED_BEFORE_122A2}`,
      });
      expect(within(confirm).getByText(MEANS_FILED_BEFORE_122A2)).toBeInTheDocument();
      expect(onMarkFiled).not.toHaveBeenCalled();

      await user.click(within(confirm).getByRole('button', { name: MEANS_PAIR_MARK_ALONE }));

      expect(onMarkFiled).toHaveBeenCalledTimes(1);
      expect(onMarkFiled).toHaveBeenCalledWith(pairForm.id);
      expect(onMarkPairFiled).not.toHaveBeenCalled();
    });

    // A keyboard or screen-reader filer must land in the confirm and come back to the trigger
    it('moves focus to the confirm when it opens, and back to Mark as Filed on cancel', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <FormCard
            {...pairProps}
            generatedForm={pairForm}
            pair={{ kind: 'both' }}
            onMarkPairFiled={vi.fn().mockResolvedValue(undefined)}
          />
        </MemoryRouter>
      );

      await user.click(screen.getByRole('button', { name: 'Mark as Filed' }));
      expect(screen.getByRole('button', { name: MEANS_PAIR_MARK_BOTH })).toHaveFocus();

      await user.click(screen.getByRole('button', { name: MEANS_PAIR_CANCEL }));
      expect(screen.getByRole('button', { name: 'Mark as Filed' })).toHaveFocus();
    });

    it('moves focus to the alone confirm, and back to Mark as Filed after it resolves unfiled', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <FormCard
            {...pairProps}
            generatedForm={pairForm}
            pair={{
              kind: 'alone',
              partnerLabel: 'Form 122A-2 - Chapter 7 Means Test Calculation',
              partnerNotice: MEANS_FILED_BEFORE_122A2,
            }}
          />
        </MemoryRouter>
      );

      await user.click(screen.getByRole('button', { name: 'Mark as Filed' }));
      expect(screen.getByRole('button', { name: MEANS_PAIR_MARK_ALONE })).toHaveFocus();

      await user.click(screen.getByRole('button', { name: MEANS_PAIR_MARK_ALONE }));
      // The parent refused and left the card unfiled, so the trigger is back and has focus
      expect(await screen.findByRole('button', { name: 'Mark as Filed' })).toHaveFocus();
    });

    it('moves focus back to Mark as Filed after both are marked and the card stays unfiled', async () => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <FormCard
            {...pairProps}
            generatedForm={pairForm}
            pair={{ kind: 'both' }}
            onMarkPairFiled={vi.fn().mockResolvedValue(undefined)}
          />
        </MemoryRouter>
      );

      await user.click(screen.getByRole('button', { name: 'Mark as Filed' }));
      await user.click(screen.getByRole('button', { name: MEANS_PAIR_MARK_BOTH }));

      expect(await screen.findByRole('button', { name: 'Mark as Filed' })).toHaveFocus();
    });

    it('shows no confirm once the card is no longer unfiled', async () => {
      const user = userEvent.setup();
      const props = {
        ...pairProps,
        pair: { kind: 'both' } as const,
        onMarkPairFiled: vi.fn().mockResolvedValue(undefined),
      };
      const { rerender } = render(
        <MemoryRouter>
          <FormCard {...props} generatedForm={pairForm} />
        </MemoryRouter>
      );
      await user.click(screen.getByRole('button', { name: 'Mark as Filed' }));
      expect(screen.getByRole('group')).toBeInTheDocument();

      rerender(
        <MemoryRouter>
          <FormCard {...props} generatedForm={{ ...pairForm, status: 'filed' }} />
        </MemoryRouter>
      );

      expect(screen.queryByRole('group')).not.toBeInTheDocument();
    });

    it('a filed partner that agrees marks alone with no confirm', async () => {
      const user = userEvent.setup();
      const onMarkFiled = vi.fn().mockResolvedValue(undefined);
      render(
        <MemoryRouter>
          <FormCard {...pairProps} generatedForm={pairForm} onMarkFiled={onMarkFiled} />
        </MemoryRouter>
      );

      await user.click(screen.getByRole('button', { name: 'Mark as Filed' }));

      expect(onMarkFiled).toHaveBeenCalledTimes(1);
      expect(screen.queryByRole('group')).not.toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Status badge
  // ---------------------------------------------------------------------------

  it('shows pending badge when no form', () => {
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} />
      </MemoryRouter>
    );
    expect(screen.getByRole('status')).toHaveTextContent('Not Generated');
  });

  it('shows generated badge when form exists', () => {
    render(
      <MemoryRouter>
        <FormCard {...defaultProps} generatedForm={mockForm} />
      </MemoryRouter>
    );
    expect(screen.getByRole('status')).toHaveTextContent('Generated');
  });
});
