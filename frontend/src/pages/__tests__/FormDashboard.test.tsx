import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { FormDashboard } from '../FormDashboard';
import { FORM_103A_LINK } from '../../constants/copy';
import { FORM_103A_URL } from '../../constants/copy';
import {
  MEANS_FILED_BEFORE_122A1,
  MEANS_FILED_BEFORE_122A2,
  MEANS_FILED_MISMATCH,
  MEANS_HOLD_REFUSAL,
  MEANS_OUTCOME_PRESUMPTION,
  MEANS_PAIR_NOTICE,
} from '../../constants/copy';
import { PRESUMPTION_INSTRUCTIONS } from '../../constants/formText';

/**
 * FormDashboard requires IntakeProvider with an active session.
 * We seed localStorage to trigger session loading on mount.
 */
function renderFormDashboard() {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter>
      <IntakeProvider>
        <FormDashboard />
      </IntakeProvider>
    </MemoryRouter>
  );
}

/** Forms are prepared only from an intake the server marked complete. */
const completedSession = {
  id: 1,
  user: 1,
  district: 1,
  current_step: 9,
  status: 'completed',
  created_at: '2026-01-20T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
  completed_at: '2026-01-20T11:00:00Z',
  debtor_info: null,
  income_info: null,
  expense_info: null,
  assets: [],
  debts: [],
};

describe('FormDashboard', () => {
  beforeEach(() => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(completedSession)
      )
    );
  });

  // ---------------------------------------------------------------------------
  // Loading and display
  // ---------------------------------------------------------------------------

  it('renders page after session loads', async () => {
    renderFormDashboard();

    // Session loads from localStorage → then forms load
    await waitFor(() => {
      expect(screen.getByText('Your Court Forms')).toBeInTheDocument();
    });
  });

  it('renders page title and UPL banner after loading', async () => {
    renderFormDashboard();

    await waitFor(() => {
      expect(screen.getByText('Your Court Forms')).toBeInTheDocument();
    });

    // UPL banner should be visible
    expect(screen.getByText('Legal Information Notice')).toBeInTheDocument();
  });

  it('renders form cards after loading', async () => {
    renderFormDashboard();

    await waitFor(() => {
      expect(screen.getByText('Form 101 - Voluntary Petition')).toBeInTheDocument();
    });
  });

  it('shows progress bar', async () => {
    renderFormDashboard();

    await waitFor(() => {
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Empty session state
  // ---------------------------------------------------------------------------

  it('shows empty message when no session', async () => {
    localStorage.removeItem('current_session_id');

    render(
      <MemoryRouter>
        <IntakeProvider>
          <FormDashboard />
        </IntakeProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no active intake session/i)).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // An unfinished intake (forms step 2 §5.3)
  // ---------------------------------------------------------------------------

  it('asks the filer to finish their intake, with a link back, until it is complete', async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({ ...completedSession, status: 'in_progress', completed_at: null })
      )
    );

    renderFormDashboard();

    await screen.findByText('Form 101 - Voluntary Petition');
    expect(screen.getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
      'href',
      '/intake'
    );
  });

  it('does not ask a filer whose intake is complete to finish it', async () => {
    renderFormDashboard();

    await screen.findByText('Form 101 - Voluntary Petition');
    expect(screen.queryByRole('link', { name: 'Finish your intake' })).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Error handling
  // ---------------------------------------------------------------------------

  it('shows error message when form loading fails', async () => {
    server.use(
      http.get('http://localhost:8000/api/forms/', () =>
        HttpResponse.json({ message: 'Server error' }, { status: 400 })
      )
    );

    renderFormDashboard();

    // The one sentence the app uses when the forms list can't load (W-6)
    await waitFor(() => {
      expect(screen.getByText('Unable to load your forms. Please try again.')).toBeInTheDocument();
    });

    // Retry button should be present
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Generate All
  // ---------------------------------------------------------------------------

  describe('the median table notice', () => {
    const aprilTable = {
      name: 'Census median income',
      effective_date: '2026-04-01',
      valid_through: '2026-10-31',
      source_url: 'https://www.justice.gov/ust/eo/bapcpa/20260401/bci_data/median_income_table.htm',
    };

    function packetWith(tables: unknown[]) {
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'], tables })
        )
      );
    }

    it('tells the filer which figures the forms use and when to download again', async () => {
      packetWith([aprilTable]);
      renderFormDashboard();

      expect(
        await screen.findByText(
          'These forms use the median income figures the U.S. Trustee applies to cases filed on or after April 1, 2026. New figures are expected after October 31, 2026. If you file after that date, download your forms again.'
        )
      ).toBeInTheDocument();
    });

    it('says only what applies today when no newer figures are expected', async () => {
      packetWith([{ ...aprilTable, valid_through: null }]);
      renderFormDashboard();

      expect(
        await screen.findByText(
          'These forms use the median income figures the U.S. Trustee applies to cases filed on or after April 1, 2026.'
        )
      ).toBeInTheDocument();
      expect(screen.queryByText(/New figures are expected/)).not.toBeInTheDocument();
    });

    it('shows no notice when the forms used no dated table', async () => {
      packetWith([]);
      renderFormDashboard();

      await screen.findByText('Form 121 - SSN Statement');
      expect(screen.queryByText(/median income figures/)).not.toBeInTheDocument();
    });

    it('names the day the table starts, not the day before, for a filer west of UTC', async () => {
      // new Date('2026-04-01') is UTC midnight: March 31 in Chicago
      const savedTz = process.env.TZ;
      process.env.TZ = 'America/Chicago';
      try {
        packetWith([aprilTable]);
        renderFormDashboard();

        expect(await screen.findByText(/on or after April 1, 2026\./)).toBeInTheDocument();
        expect(screen.queryByText(/March 31/)).not.toBeInTheDocument();
        expect(screen.getByText(/after October 31, 2026\./)).toBeInTheDocument();
      } finally {
        if (savedTz === undefined) delete process.env.TZ;
        else process.env.TZ = savedTz;
      }
    });
  });

  describe('the income window notice', () => {
    const NOW = { start: '2026-05-01', end: '2026-10-31' };
    const MOVED =
      'Your income figures are your monthly average for April 1, 2026 through September 30, 2026. If you file now, the six months are May 1, 2026 through October 31, 2026. Check your income on the Income step.';

    function packetWith(incomePeriod?: unknown) {
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json({
            session: 1,
            form_types: ['form_101', 'form_121'],
            tables: [],
            ...(incomePeriod === undefined ? {} : { income_period: incomePeriod }),
          })
        )
      );
    }

    it('says when the six months have moved, in words, and links to the Income step', async () => {
      packetWith({ answered_for: { start: '2026-04-01', end: '2026-09-30' }, now: NOW });
      renderFormDashboard();

      expect(await screen.findByText(MOVED)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Go to Income' })).toHaveAttribute(
        'href',
        '/intake?step=income_info'
      );
    });

    it('shows no notice when the window has not moved', async () => {
      packetWith({ answered_for: NOW, now: NOW });
      renderFormDashboard();

      await screen.findByText('Form 121 - SSN Statement');
      expect(screen.queryByText(/monthly average for/)).not.toBeInTheDocument();
    });

    it('asks the filer to check a window never confirmed', async () => {
      packetWith({ answered_for: null, now: NOW });
      renderFormDashboard();

      expect(
        await screen.findByText(
          'Check that your income figures are your monthly average for May 1, 2026 through October 31, 2026.'
        )
      ).toBeInTheDocument();
    });

    it('shows no notice for a reply that carries no window', async () => {
      packetWith();
      renderFormDashboard();

      await screen.findByText('Form 121 - SSN Statement');
      expect(screen.queryByText(/monthly average for/)).not.toBeInTheDocument();
    });

    it('shows the refusal and not the notice when the packet is refused', async () => {
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json(
            { error: 'Enter your income by source on the Income step.', step: 'income_info' },
            { status: 422 }
          )
        )
      );
      renderFormDashboard();

      expect(
        await screen.findByText('Enter your income by source on the Income step.')
      ).toBeInTheDocument();
      expect(screen.queryByText(/monthly average for/)).not.toBeInTheDocument();
    });
  });

  describe('how the filer will pay the fee', () => {
    // Form 101 line 8's words, typed out (the field index's option_text for Check Box7)
    const PAY_IN_FULL = 'I will pay the entire fee when I file my petition.';
    const INSTALLMENTS = 'I need to pay the fee in installments.';
    const WAIVER = 'I request that my fee be waived';

    function packetWith(paymentChoice?: unknown) {
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json({
            session: 1,
            form_types: ['form_101', 'form_121'],
            tables: [],
            ...(paymentChoice === undefined ? {} : { payment_choice: paymentChoice }),
          })
        )
      );
    }

    async function answerBlock() {
      return screen.findByRole('region', { name: 'How you will pay the fee' });
    }

    it('shows the filer’s line 8 answer in the form’s words, with a link to change it', async () => {
      packetWith('pay_in_full');
      renderFormDashboard();

      const block = await answerBlock();
      expect(within(block).getByText(PAY_IN_FULL)).toBeInTheDocument();
      expect(
        within(block).getByRole('link', { name: 'Change how you will pay the fee' })
      ).toHaveAttribute('href', '/filing-fee');
      expect(within(block).queryByRole('link', { name: /^Choose/ })).not.toBeInTheDocument();
    });

    it('asks a filer who has not answered line 8 to choose, and shows no answer', async () => {
      packetWith(null);
      renderFormDashboard();

      const block = await answerBlock();
      expect(
        within(block).getByRole('link', { name: 'Choose how you will pay the fee' })
      ).toHaveAttribute('href', '/filing-fee');
      expect(within(block).queryByRole('link', { name: /^Change/ })).not.toBeInTheDocument();
      for (const words of [PAY_IN_FULL, INSTALLMENTS, WAIVER]) {
        expect(within(block).queryByText(words)).not.toBeInTheDocument();
      }
    });

    it('tells a filer paying in installments to get Form 103A from the court', async () => {
      packetWith('installments');
      renderFormDashboard();

      const block = await answerBlock();
      expect(within(block).getByText(INSTALLMENTS)).toBeInTheDocument();
      expect(
        within(block).getByText(/DigniFi doesn't prepare Form 103A yet\./)
      ).toBeInTheDocument();
      expect(within(block).getByRole('link', { name: FORM_103A_LINK })).toHaveAttribute(
        'href',
        FORM_103A_URL
      );
    });

    it.each([
      ['waiver', WAIVER],
      ['pay_in_full', PAY_IN_FULL],
    ])('shows no Form 103A notice for the answer %s', async (choice, words) => {
      packetWith(choice);
      renderFormDashboard();

      const block = await answerBlock();
      expect(within(block).getByText(words)).toBeInTheDocument();
      expect(screen.queryByText(/Form 103A/)).not.toBeInTheDocument();
    });

    // Guard (ruling R29): passes before the change; it keeps a block from showing beside a refusal
    it('shows no answer, and no link to choose, when the packet is refused', async () => {
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json(
            { error: 'Enter your income by source on the Income step.', step: 'income_info' },
            { status: 422 }
          )
        )
      );
      renderFormDashboard();

      await screen.findByText('Enter your income by source on the Income step.');
      expect(
        screen.queryByRole('region', { name: 'How you will pay the fee' })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('link', { name: /how you will pay the fee/ })
      ).not.toBeInTheDocument();
    });

    it('shows the answer the packet holds after Generate All reloads it', async () => {
      // The filer changed line 8 on /filing-fee in another tab; Generate All reloads the packet
      let calls = 0;
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () => {
          calls += 1;
          return HttpResponse.json({
            session: 1,
            form_types: calls === 1 ? ['form_101', 'form_103b'] : ['form_101', 'form_121'],
            tables: [],
            payment_choice: calls === 1 ? 'waiver' : 'installments',
          });
        })
      );
      renderFormDashboard();
      expect(within(await answerBlock()).getByText(WAIVER)).toBeInTheDocument();

      await userEvent.click(await screen.findByRole('button', { name: /generate all/i }));
      await userEvent.click(screen.getByRole('checkbox'));
      await userEvent.click(screen.getByRole('button', { name: /continue/i }));

      expect(await within(await answerBlock()).findByText(INSTALLMENTS)).toBeInTheDocument();
      expect(screen.queryByText(WAIVER)).not.toBeInTheDocument();
    });
  });

  it('offers only the forms in the filer’s packet', async () => {
    // A stored form that no longer applies (122A-2 after income dropped) is neither shown nor counted
    server.use(
      http.get('http://localhost:8000/api/forms/packet/', () =>
        HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
      ),
      http.get('http://localhost:8000/api/forms/', () =>
        HttpResponse.json([
          { id: 1, session: 1, form_type: 'form_101', status: 'generated' },
          { id: 2, session: 1, form_type: 'form_122a2', status: 'generated' },
        ])
      )
    );

    renderFormDashboard();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /generate all 2 forms/i })).toBeInTheDocument();
    });
    expect(screen.getByText('1 of 2 generated')).toBeInTheDocument();
    expect(screen.getByText('Form 121 - SSN Statement')).toBeInTheDocument();
    expect(screen.queryByText('Form 103B - Fee Waiver Application')).not.toBeInTheDocument();
    expect(screen.queryByText('Form 122A-2 - Means Test Expenses')).not.toBeInTheDocument();
  });

  it('keeps showing a filed form after it leaves the packet, and says so', async () => {
    // 122A-2 was filed, then income dropped below the median (forms step 2 §5.6, DIG-155)
    server.use(
      http.get('http://localhost:8000/api/forms/packet/', () =>
        HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
      ),
      http.get('http://localhost:8000/api/forms/', () =>
        HttpResponse.json([
          { id: 1, session: 1, form_type: 'form_101', status: 'generated' },
          { id: 2, session: 1, form_type: 'form_121', status: 'filed' },
          { id: 3, session: 1, form_type: 'form_122a2', status: 'filed' },
          { id: 4, session: 1, form_type: 'form_103b', status: 'generated' },
        ])
      )
    );

    renderFormDashboard();
    await screen.findByText('Form 101 - Voluntary Petition');

    // Only the filed form outside the packet carries the note; filed 121 is in the packet
    const notes = screen.queryAllByText('Filed, no longer in your current packet');
    expect(notes).toHaveLength(1);
    const leftPacket = notes[0].closest('article') as HTMLElement;
    expect(leftPacket).toHaveAttribute('aria-label', 'Form 122A-2 - Means Test Expenses');
    expect(within(leftPacket).getByRole('button', { name: /download/i })).toBeInTheDocument();
    // A form that left the packet without being filed is neither shown nor counted
    expect(screen.queryByText('Form 103B - Fee Waiver Application')).not.toBeInTheDocument();
    expect(screen.getByText(/^2 of 2 generated/)).toBeInTheDocument();
  });

  it('shows error banner when generate_all returns partial failures', async () => {
    server.use(
      http.post('http://localhost:8000/api/forms/generate_all/', () =>
        HttpResponse.json({
          generated: [],
          errors: [{ form_type: 'form_101', error: 'Missing debtor name' }],
          total_generated: 0,
          total_errors: 1,
        })
      )
    );

    renderFormDashboard();
    await waitFor(() => expect(screen.getByText('Your Court Forms')).toBeInTheDocument());

    // Click "Generate All" (shown once the packet loads) — opens UPL confirmation modal
    const generateAllBtn = await screen.findByRole('button', { name: /generate all/i });
    await userEvent.click(generateAllBtn);

    // Acknowledge the UPL disclaimer checkbox, then confirm
    const checkbox = screen.getByRole('checkbox');
    await userEvent.click(checkbox);
    const continueBtn = screen.getByRole('button', { name: /continue/i });
    await userEvent.click(continueBtn);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/1 form.*could not be generated/i)).toBeInTheDocument();
    });
    // The error names the form as its card does, never by its internal key
    const failure = within(screen.getByRole('alert')).getByRole('listitem');
    expect(failure).toHaveTextContent('Form 101 - Voluntary Petition: Missing debtor name');
    expect(failure).not.toHaveTextContent('form_101');
    // An error that names no fix leaves trying again as the filer's only move
    expect(
      screen.getByText(/You can try generating them individually below\./)
    ).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // A refusal of the whole call (forms step 2 §5.6, DIG-156)
  // ---------------------------------------------------------------------------

  describe('when Generate All or the packet list is refused', { timeout: 15_000 }, () => {
    const FINISH_INTAKE = 'Finish your intake before preparing your forms.';
    const INCOME_NOT_SPLIT = 'Enter your income by source on the Income step.';
    // The refusal as the server sends it, naming the wizard step that fixes it
    const NOT_SPLIT = { error: INCOME_NOT_SPLIT, step: 'income_info' };
    const NO_TABLE =
      "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your forms. Please try again later.";
    // The server's sentence for a 500 speaks of one form, so the dashboard never shows it
    const SERVER_FAILURE = "This form couldn't be prepared. Please try again later.";
    const GENERIC =
      'Something went wrong. Your information is safe — please try again in a moment.';
    // A single form's refusals, as the server words them (step 3a2 spec §4.5)
    const LETTER =
      "The court form can't print the letter “ą” in “Last name”. Change it to a letter without the mark.";
    const TOO_LONG =
      '“Name of Financial Institution” is too long to fit on the court form, even in small print. Shorten it.';

    /** Open Generate All and tick the UPL notice; returns the notice's Continue button. */
    async function openGenerateAll() {
      await userEvent.click(await screen.findByRole('button', { name: /generate all/i }));
      await userEvent.click(screen.getByRole('checkbox'));
      return screen.getByRole('button', { name: /continue/i });
    }

    /** A packet that gains Form 122A-2 once the means test is worked out again. */
    function packetThatGains122a2() {
      let calls = 0;
      return http.get('http://localhost:8000/api/forms/packet/', () => {
        calls += 1;
        return HttpResponse.json({
          session: 1,
          form_types:
            calls === 1 ? ['form_101', 'form_121'] : ['form_101', 'form_121', 'form_122a2'],
        });
      });
    }

    it('shows the packet list’s refusal in its own words', async () => {
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json(NOT_SPLIT, { status: 422 })
        )
      );

      renderFormDashboard();

      expect(await screen.findByText(INCOME_NOT_SPLIT)).toBeInTheDocument();
      expect(screen.queryByText(/unable to load your forms/i)).not.toBeInTheDocument();
    });

    it('offers the step that fixes it, not a retry, when the packet list is refused', async () => {
      // A completed filer whose income isn't split gets the same refusal on every reload
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json(NOT_SPLIT, { status: 422 })
        )
      );

      renderFormDashboard();

      await screen.findByText(INCOME_NOT_SPLIT);
      expect(screen.getByRole('link', { name: 'Go to Income' })).toHaveAttribute(
        'href',
        '/intake?step=income_info'
      );
      expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
    });

    // Ruling R4-b: no step of the filer's fixes a missing median table (spec §4.3)
    it('offers neither the intake nor a retry when the packet list’s refusal names no fix', async () => {
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json({ error: NO_TABLE }, { status: 422 })
        )
      );

      renderFormDashboard();

      await screen.findByText(NO_TABLE);
      expect(screen.queryByRole('link', { name: 'Finish your intake' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
    });

    it('shows generic words, never the server’s, when the packet list fails on the server', async () => {
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json({ error: SERVER_FAILURE }, { status: 500 })
        )
      );

      renderFormDashboard();

      // A 500 is tried three more times, 3.5 s of backoff, before the dashboard gives up
      expect(
        await screen.findByText(/unable to load your forms/i, {}, { timeout: 8000 })
      ).toBeInTheDocument();
      expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
    });

    it('shows Generate All’s refusal in its own words', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({ error: FINISH_INTAKE }, { status: 422 })
        )
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      expect(await screen.findByText(FINISH_INTAKE)).toBeInTheDocument();
      expect(screen.queryByText(GENERIC)).not.toBeInTheDocument();
    });

    // A run repeated behind the filer's back can start four at once (step 3a2 spec §7)
    it('sends Generate All once, and shows generic words, never the server’s, when it fails on the server', async () => {
      let generateAllCalls = 0;
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () => {
          generateAllCalls += 1;
          return HttpResponse.json({ error: SERVER_FAILURE }, { status: 500 });
        })
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      expect(await screen.findByText(GENERIC)).toBeInTheDocument();
      expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
      expect(generateAllCalls).toBe(1);
    });

    it('links a form Generate All refused to the step that fixes it, with no advice to retry', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({
            generated: [],
            errors: [{ form_type: 'form_101', error: LETTER, step: 'debtor_info' }],
            total_generated: 0,
            total_errors: 1,
          })
        )
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      const failure = within(await screen.findByRole('alert')).getByRole('listitem');
      expect(failure).toHaveTextContent(`Form 101 - Voluntary Petition: ${LETTER}`);
      expect(within(failure).getByRole('link', { name: 'Go to Your Information' })).toHaveAttribute(
        'href',
        '/intake?step=debtor_info'
      );
      expect(screen.queryByText(/try generating them individually/i)).not.toBeInTheDocument();
    });

    it('still suggests generating one at a time when any form Generate All refused names no fix', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({
            generated: [],
            errors: [
              { form_type: 'form_101', error: LETTER, step: 'debtor_info' },
              { form_type: 'form_121', error: SERVER_FAILURE },
            ],
            total_generated: 0,
            total_errors: 2,
          })
        )
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent(
        '2 forms could not be generated. You can try generating them individually below.'
      );
      const [letter, serverFailure] = within(alert).getAllByRole('listitem');
      expect(
        within(letter).getByRole('link', { name: 'Go to Your Information' })
      ).toBeInTheDocument();
      expect(within(serverFailure).queryByRole('link')).not.toBeInTheDocument();
    });

    // The words of each link go to the owner with the plan (ruling R22). Each page is one a
    // binding of that form can name: the filing-fee answers, a SOFA list (the synthetic Schedule D
    // group's), the pay stub's employer name, and Form 107's asked answers.
    it('names each page that fixes a form Generate All refused', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({
            generated: [],
            errors: [
              { form_type: 'form_103b', error: TOO_LONG, page: '/filing-fee' },
              { form_type: 'schedule_d', error: TOO_LONG, page: '/sofa' },
              { form_type: 'schedule_i', error: TOO_LONG, page: '/documents' },
              { form_type: 'form_107', error: TOO_LONG, page: '/ask/form_107' },
            ],
            total_generated: 0,
            total_errors: 4,
          })
        )
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      const alert = await screen.findByRole('alert');
      const links = within(alert)
        .getAllByRole('link')
        .map((link) => [link.textContent, link.getAttribute('href')]);
      expect(links).toEqual([
        ['Go to How you will pay the filing fee', '/filing-fee'],
        ['Go to Statement of Financial Affairs', '/sofa'],
        ['Go to Upload your documents', '/documents'],
        ['Answer the questions for Form 107 - Financial Affairs', '/ask/form_107'],
      ]);
      expect(screen.queryByText(/try generating them individually/i)).not.toBeInTheDocument();
    });

    it('links a Schedule C refusal to the exemptions page', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({
            generated: [],
            errors: [
              {
                form_type: 'schedule_c',
                error: 'Choose which set of exemptions you are claiming.',
                page: '/exemptions',
              },
            ],
            total_generated: 0,
            total_errors: 1,
          })
        )
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      const alert = await screen.findByRole('alert');
      expect(
        within(alert).getByRole('link', { name: 'Go to The property you claim as exempt' })
      ).toHaveAttribute('href', '/exemptions');
    });

    // A page is linked only by words this page has for it, never by a built-in property's name
    it('offers no link for a page it has no words for, such as /ask/constructor', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({
            generated: [],
            errors: [{ form_type: 'form_107', error: TOO_LONG, page: '/ask/constructor' }],
            total_generated: 0,
            total_errors: 1,
          })
        )
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      const alert = await screen.findByRole('alert');
      expect(within(alert).queryByRole('link')).not.toBeInTheDocument();
      expect(alert).toHaveTextContent('You can try generating them individually below.');
    });

    it('links a refused Generate All to the step that fixes it', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json(NOT_SPLIT, { status: 422 })
        )
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent(INCOME_NOT_SPLIT);
      expect(within(alert).getByRole('link', { name: 'Go to Income' })).toHaveAttribute(
        'href',
        '/intake?step=income_info'
      );
    });

    // The intake was reopened since this page loaded it as complete (step 3a1 spec §4.4)
    it('links a refused Generate All to the page that fixes it', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({ error: FINISH_INTAKE, page: '/intake' }, { status: 422 })
        )
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      await screen.findByText(FINISH_INTAKE);
      const links = screen.getAllByRole('link', { name: 'Finish your intake' });
      expect(links).toHaveLength(1);
      expect(links[0]).toHaveAttribute('href', '/intake');
    });

    // Ruling R4-a: the notice for an unfinished intake already links back to it
    it('adds no second link back to the intake when the dashboard already offers one', async () => {
      server.use(
        http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
          HttpResponse.json({ ...completedSession, status: 'in_progress', completed_at: null })
        ),
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({ error: FINISH_INTAKE, page: '/intake' }, { status: 422 })
        )
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      await screen.findByText(FINISH_INTAKE);
      expect(screen.getAllByRole('link', { name: 'Finish your intake' })).toHaveLength(1);
    });

    // This page loaded the intake as unfinished; it was completed since, elsewhere
    it('shows the words "Finish your intake" once when the packet list is refused while the unfinished-intake notice shows', async () => {
      server.use(
        http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
          HttpResponse.json({ ...completedSession, status: 'in_progress', completed_at: null })
        ),
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json(NOT_SPLIT, { status: 422 })
        )
      );

      renderFormDashboard();

      await screen.findByText(INCOME_NOT_SPLIT);
      expect(screen.getAllByRole('link', { name: 'Finish your intake' })).toHaveLength(1);
    });

    // This page loaded the intake as complete; it was reopened since, elsewhere
    it('shows the words "Finish your intake" once when both the packet list and Generate All are refused', async () => {
      let packetCalls = 0;
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () => {
          packetCalls += 1;
          return packetCalls === 1
            ? HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
            : HttpResponse.json(NOT_SPLIT, { status: 422 });
        }),
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({ error: FINISH_INTAKE, page: '/intake' }, { status: 422 })
        )
      );

      renderFormDashboard();
      // Marking a form filed reloads the packet list, which is now refused
      await userEvent.click(await screen.findByRole('button', { name: /mark as filed/i }));
      await screen.findByText(INCOME_NOT_SPLIT);
      await userEvent.click(await openGenerateAll());

      await screen.findByText(FINISH_INTAKE);
      // Generate All reloads the packet list too, and it is refused again
      await waitFor(() => expect(packetCalls).toBe(3));
      expect(screen.getAllByRole('link', { name: 'Finish your intake' })).toHaveLength(1);
    });

    it('reloads the packet after Generate All succeeds', async () => {
      server.use(packetThatGains122a2());

      renderFormDashboard();
      const continueBtn = await openGenerateAll();
      expect(screen.queryByText('Form 122A-2 - Means Test Expenses')).not.toBeInTheDocument();
      await userEvent.click(continueBtn);

      expect(await screen.findByText('Form 122A-2 - Means Test Expenses')).toBeInTheDocument();
    });

    it('reloads the packet after Generate All is refused, and a later one that succeeds clears the refusal', async () => {
      let generateAllCalls = 0;
      server.use(
        packetThatGains122a2(),
        // Refused the first time; the next one succeeds
        http.post('http://localhost:8000/api/forms/generate_all/', () => {
          generateAllCalls += 1;
          return generateAllCalls === 1
            ? HttpResponse.json({ error: FINISH_INTAKE }, { status: 422 })
            : HttpResponse.json({ generated: [], errors: [], total_generated: 0, total_errors: 0 });
        })
      );
      const survey = { name: 'Feedback survey' };

      renderFormDashboard();
      const continueBtn = await openGenerateAll();
      expect(screen.queryByText('Form 122A-2 - Means Test Expenses')).not.toBeInTheDocument();
      await userEvent.click(continueBtn);

      expect(await screen.findByText('Form 122A-2 - Means Test Expenses')).toBeInTheDocument();
      expect(screen.getByText(FINISH_INTAKE)).toBeInTheDocument();
      // A refused Generate All prepared nothing, so it asks for no feedback
      expect(screen.queryByRole('form', survey)).not.toBeInTheDocument();

      await userEvent.click(await openGenerateAll());

      expect(await screen.findByRole('form', survey)).toBeInTheDocument();
      expect(screen.queryByText(FINISH_INTAKE)).not.toBeInTheDocument();
      expect(generateAllCalls).toBe(2);
    });

    it('shows the packet list’s refusal when it reloads after Generate All', async () => {
      let calls = 0;
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () => {
          calls += 1;
          return calls === 1
            ? HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
            : HttpResponse.json(NOT_SPLIT, { status: 422 });
        })
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      expect(await screen.findByText(INCOME_NOT_SPLIT)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Go to Income' })).toHaveAttribute(
        'href',
        '/intake?step=income_info'
      );
      expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
    });

    it('still offers a retry when the reload after Generate All fails on the server', async () => {
      let calls = 0;
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () => {
          calls += 1;
          return calls === 1
            ? HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
            : HttpResponse.json({ error: SERVER_FAILURE }, { status: 500 });
        })
      );

      renderFormDashboard();
      const continueBtn = await openGenerateAll();

      // The reload's 500 is tried three more times (0.5 s, 1 s, 2 s apart) before it gives up
      vi.useFakeTimers();
      try {
        fireEvent.click(continueBtn);
        for (let second = 0; second < 5; second += 1) {
          await act(async () => {
            await vi.advanceTimersByTimeAsync(1000);
          });
        }
      } finally {
        vi.useRealTimers();
      }

      expect(await screen.findByText(/unable to load your forms/i)).toBeInTheDocument();
      expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('clears a failed reload once a later reload after Generate All succeeds', async () => {
      let calls = 0;
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () => {
          calls += 1;
          return calls === 2
            ? HttpResponse.json(NOT_SPLIT, { status: 422 })
            : HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] });
        })
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());
      await screen.findByText(INCOME_NOT_SPLIT);

      await userEvent.click(await openGenerateAll());

      await waitFor(() => expect(calls).toBe(3));
      await waitFor(() => expect(screen.queryByText(INCOME_NOT_SPLIT)).not.toBeInTheDocument());
      expect(screen.getByText('Form 121 - SSN Statement')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // A single form refused on its card (step 3a2 spec §4.5)
  // ---------------------------------------------------------------------------

  describe('when a form’s Generate or Download is refused', { timeout: 15_000 }, () => {
    const LETTER =
      "The court form can't print the letter “ą” in “Last name”. Change it to a letter without the mark.";
    const TOO_LONG =
      '“Name of Financial Institution” is too long to fit on the court form, even in small print. Shorten it.';
    const FINISH_INTAKE = 'Finish your intake before preparing your forms.';
    const INCOME_NOT_SPLIT = 'Enter your income by source on the Income step.';
    const SERVER_FAILURE = "This form couldn't be prepared. Please try again later.";
    const GENERIC =
      'Something went wrong. Your information is safe — please try again in a moment.';
    // Form 101 is generated (id 1) and Form 121 is not, in the default handlers
    const GENERATED = 'Form 101 - Voluntary Petition';
    const PENDING = 'Form 121 - SSN Statement';

    /** The card of the form with this label, once the forms have loaded */
    async function cardOf(label: string) {
      return screen.findByRole('article', { name: label });
    }

    /** Answers each download of Form 101 in turn with these responses, the last one repeated */
    function downloads(...responses: Array<() => Response>) {
      let calls = 0;
      server.use(
        http.get('http://localhost:8000/api/forms/:id/download/', () => {
          calls += 1;
          return responses[Math.min(calls, responses.length) - 1]();
        })
      );
    }

    const refused =
      (body: Record<string, string>, status = 422) =>
      () =>
        HttpResponse.json(body, { status });

    /** Open Generate All and confirm it through the UPL notice */
    async function generateAll() {
      await userEvent.click(await screen.findByRole('button', { name: /generate all/i }));
      await userEvent.click(screen.getByRole('checkbox'));
      await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    }

    /** Press one card's Generate and confirm it through the same UPL notice */
    async function generateOne(card: HTMLElement) {
      await userEvent.click(within(card).getByRole('button', { name: 'Generate' }));
      await userEvent.click(screen.getByRole('checkbox'));
      await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    }

    it('links a form whose Generate was refused to the step that fixes it', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate/', () =>
          HttpResponse.json(
            { form_type: 'form_121', error: LETTER, step: 'debtor_info' },
            { status: 422 }
          )
        )
      );

      renderFormDashboard();
      const card = await cardOf(PENDING);
      await generateOne(card);

      expect(await within(card).findByText(LETTER)).toBeInTheDocument();
      expect(within(card).getByRole('link', { name: 'Go to Your Information' })).toHaveAttribute(
        'href',
        '/intake?step=debtor_info'
      );
    });

    // An unfiled form's download works the means test out again, which needs income by source
    it('links a form whose download was refused to the step that fixes it', async () => {
      downloads(refused({ form_type: 'form_101', error: INCOME_NOT_SPLIT, step: 'income_info' }));

      renderFormDashboard();
      const card = await cardOf(GENERATED);
      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));

      expect(await within(card).findByText(INCOME_NOT_SPLIT)).toBeInTheDocument();
      expect(within(card).getByRole('link', { name: 'Go to Income' })).toHaveAttribute(
        'href',
        '/intake?step=income_info'
      );
    });

    it('links a form whose Generate was refused to the page that fixes it', async () => {
      // Line 7's "Identify who" is a filing-fee answer, which feeds Form 103B (Task 4)
      const WHO_TOO_LONG =
        '“Identify who” is too long to fit on the court form, even in small print. Shorten it.';
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json({ session: 1, form_types: ['form_101', 'form_103b'] })
        ),
        http.post('http://localhost:8000/api/forms/generate/', () =>
          HttpResponse.json(
            { form_type: 'form_103b', error: WHO_TOO_LONG, page: '/filing-fee' },
            { status: 422 }
          )
        )
      );

      renderFormDashboard();
      const card = await cardOf('Form 103B - Fee Waiver Application');
      await generateOne(card);

      expect(await within(card).findByText(WHO_TOO_LONG)).toBeInTheDocument();
      expect(
        within(card).getByRole('link', { name: 'Go to How you will pay the filing fee' })
      ).toHaveAttribute('href', '/filing-fee');
    });

    // The context says the intake is complete, so no notice links to it; the server reopened it
    it('links a form’s refusal back to the intake when nothing above it does', async () => {
      downloads(refused({ form_type: 'form_101', error: FINISH_INTAKE, page: '/intake' }));

      renderFormDashboard();
      const card = await cardOf(GENERATED);
      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));

      expect(await within(card).findByText(FINISH_INTAKE)).toBeInTheDocument();
      expect(within(card).getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
        'href',
        '/intake'
      );
      expect(screen.getAllByRole('link', { name: 'Finish your intake' })).toHaveLength(1);
    });

    // A live region announces only changes to a region already on the page
    it('shows why a download was refused, in a polite region that was on the card before it', async () => {
      // A refusal that names no fix, as a filed form's does (R46), here on a generated card
      downloads(refused({ form_type: 'form_101', error: TOO_LONG }));

      renderFormDashboard();
      const card = await cardOf(GENERATED);
      const politeRegionsBefore = Array.from(card.querySelectorAll('[aria-live="polite"]'));
      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));

      const reason = await within(card).findByText(TOO_LONG);
      expect(politeRegionsBefore).toContain(reason.closest('[aria-live="polite"]'));
      expect(within(card).queryByRole('link')).not.toBeInTheDocument();
    });

    it('shows generic words, never the server’s, when a download fails on the server', async () => {
      downloads(refused({ error: SERVER_FAILURE }, 500));

      renderFormDashboard();
      const card = await cardOf(GENERATED);
      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));

      expect(await within(card).findByText(GENERIC)).toBeInTheDocument();
      expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
    });

    it('clears a form’s refusal once its Generate succeeds', async () => {
      let generateCalls = 0;
      server.use(
        http.post('http://localhost:8000/api/forms/generate/', () => {
          generateCalls += 1;
          return generateCalls === 1
            ? HttpResponse.json(
                { form_type: 'form_121', error: LETTER, step: 'debtor_info' },
                { status: 422 }
              )
            : HttpResponse.json({
                form: { id: 2, session: 1, form_type: 'form_121', status: 'generated' },
                message: 'Form generated.',
              });
        })
      );

      renderFormDashboard();
      const card = await cardOf(PENDING);
      await generateOne(card);
      await within(card).findByText(LETTER);

      await generateOne(card);

      expect(await within(card).findByRole('button', { name: 'Download' })).toBeInTheDocument();
      expect(within(card).queryByText(LETTER)).not.toBeInTheDocument();
      expect(within(card).queryByRole('link')).not.toBeInTheDocument();
    });

    it('clears a form’s refusal once its download succeeds', async () => {
      // jsdom has no object URLs and doesn't follow a download link
      const objectUrls = {
        createObjectURL: URL.createObjectURL,
        revokeObjectURL: URL.revokeObjectURL,
      };
      URL.createObjectURL = () => 'blob:pdf';
      URL.revokeObjectURL = () => {};
      const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      downloads(
        refused({ form_type: 'form_101', error: LETTER, step: 'debtor_info' }),
        () =>
          new HttpResponse(new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d]), {
            headers: { 'Content-Type': 'application/pdf' },
          })
      );

      try {
        renderFormDashboard();
        const card = await cardOf(GENERATED);
        await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
        await within(card).findByText(LETTER);

        await userEvent.click(within(card).getByRole('button', { name: 'Download' }));

        await waitFor(() => expect(click).toHaveBeenCalled());
        // The forms reload after a download, so the card is drawn again once they have
        await waitFor(() => {
          expect(screen.queryByText('Loading your forms...')).not.toBeInTheDocument();
          expect(screen.getByRole('article', { name: GENERATED })).toBeInTheDocument();
          expect(screen.queryByText(LETTER)).not.toBeInTheDocument();
        });
        expect(
          screen.queryByRole('link', { name: 'Go to Your Information' })
        ).not.toBeInTheDocument();
      } finally {
        click.mockRestore();
        Object.assign(URL, objectUrls);
      }
    });

    // Ruling R4-a: "Finish your intake" shows at most once, on the first block that offers it
    it('adds no second link back to the intake when a form’s refusal names it', async () => {
      server.use(
        http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
          HttpResponse.json({ ...completedSession, status: 'in_progress', completed_at: null })
        )
      );
      downloads(refused({ form_type: 'form_101', error: FINISH_INTAKE, page: '/intake' }));

      renderFormDashboard();
      const card = await cardOf(GENERATED);
      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));

      expect(await within(card).findByText(FINISH_INTAKE)).toBeInTheDocument();
      expect(screen.getAllByRole('link', { name: 'Finish your intake' })).toHaveLength(1);
    });

    // Ruling R4-a, in page order: Generate All's refusal sits above every card
    it('keeps "Finish your intake" on Generate All’s refusal, not on a card below it that names it too', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({ error: FINISH_INTAKE, page: '/intake' }, { status: 422 })
        )
      );
      downloads(refused({ form_type: 'form_101', error: FINISH_INTAKE, page: '/intake' }));

      renderFormDashboard();
      await generateAll();
      const wholeCall = await screen.findByRole('alert');
      const card = await cardOf(GENERATED);
      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
      await within(card).findByText(FINISH_INTAKE);

      expect(within(wholeCall).getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
        'href',
        '/intake'
      );
      expect(within(card).queryByRole('link')).not.toBeInTheDocument();
    });

    it('clears a form’s refusal once Generate All generates it', async () => {
      // The default Generate All prepares Form 101
      downloads(refused({ form_type: 'form_101', error: LETTER, step: 'debtor_info' }));

      renderFormDashboard();
      const card = await cardOf(GENERATED);
      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
      await within(card).findByText(LETTER);

      await generateAll();

      await waitFor(() => expect(within(card).queryByText(LETTER)).not.toBeInTheDocument());
      expect(within(card).queryByRole('link')).not.toBeInTheDocument();
    });

    it('shows a form’s refusal once, in Generate All’s list, when Generate All refuses it again', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({
            generated: [],
            errors: [{ form_type: 'form_101', error: LETTER, step: 'debtor_info' }],
            total_generated: 0,
            total_errors: 1,
          })
        )
      );
      downloads(refused({ form_type: 'form_101', error: LETTER, step: 'debtor_info' }));

      renderFormDashboard();
      const card = await cardOf(GENERATED);
      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
      await within(card).findByText(LETTER);

      await generateAll();
      await screen.findByText(/1 form could not be generated/);

      // A list item reads "<form>: <refusal>", so the words are matched within it
      const shown = screen.getAllByText(LETTER, { exact: false });
      expect(shown).toHaveLength(1);
      expect(shown[0].closest('li')).not.toBeNull();
      expect(screen.getAllByRole('link', { name: 'Go to Your Information' })).toHaveLength(1);
    });

    // A refusal of the whole call checked no form, so it says nothing about the card's
    it('keeps a form’s refusal when Generate All is refused as a whole', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({ error: INCOME_NOT_SPLIT, step: 'income_info' }, { status: 422 })
        )
      );
      downloads(refused({ form_type: 'form_101', error: LETTER, step: 'debtor_info' }));

      renderFormDashboard();
      const card = await cardOf(GENERATED);
      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
      await within(card).findByText(LETTER);

      await generateAll();

      const wholeCall = await screen.findByRole('alert');
      expect(within(wholeCall).getByText(INCOME_NOT_SPLIT)).toBeInTheDocument();
      expect(within(card).getByText(LETTER)).toBeInTheDocument();
      expect(within(card).getByRole('link', { name: 'Go to Your Information' })).toHaveAttribute(
        'href',
        '/intake?step=debtor_info'
      );
    });

    it('clears a form’s refusal once it is marked filed', async () => {
      downloads(refused({ form_type: 'form_101', error: LETTER, step: 'debtor_info' }));

      renderFormDashboard();
      const card = await cardOf(GENERATED);
      await userEvent.click(within(card).getByRole('button', { name: 'Download' }));
      await within(card).findByText(LETTER);

      await userEvent.click(within(card).getByRole('button', { name: 'Mark as Filed' }));

      // Marking a form filed reloads the forms, so the card is drawn again once they have
      await waitFor(() => {
        expect(screen.queryByText('Loading your forms...')).not.toBeInTheDocument();
        expect(screen.getByRole('article', { name: GENERATED })).toBeInTheDocument();
        expect(screen.queryByText(LETTER)).not.toBeInTheDocument();
      });
    });
  });

  describe('the income test on the dashboard', { timeout: 15_000 }, () => {
    const CLOSING = 'A court makes the final decision.';
    const PAIR = ['form_101', 'form_121', 'form_122a1', 'form_122a2'];
    const RESULT = 'Income test';
    const medianTable = {
      name: 'Census median income',
      effective_date: '2026-04-01',
      valid_through: '2027-03-31',
      source_url: 'https://www.justice.gov/ust/eo/bapcpa/20260401/bci_data/median_income_table.htm',
    };
    const standardsTable = {
      name: 'IRS expense standards',
      effective_date: '2026-07-15',
      valid_through: null,
      source_url: 'https://www.justice.gov/ust/means-testing/20260715',
    };
    const section104Table = {
      name: 'Bankruptcy Code dollar amounts',
      effective_date: '2025-04-01',
      valid_through: '2028-03-31',
      source_url: 'https://www.govinfo.gov/example',
    };

    /** The packet reply: the pair by default, with whatever the test adds */
    function packetWith(extra: Record<string, unknown>, formTypes: string[] = PAIR) {
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json({ session: 1, form_types: formTypes, tables: [], ...extra })
        )
      );
    }

    function storedForm(formType: string, id: number, extra: Record<string, unknown> = {}) {
      return {
        id,
        session: 1,
        form_type: formType,
        form_type_display: formType,
        status: 'generated',
        status_display: 'Generated',
        pdf_file_path: null,
        generated_by: 1,
        generated_at: '2026-01-20T10:00:00Z',
        updated_at: '2026-01-20T10:00:00Z',
        ...extra,
      };
    }

    function formsWith(...forms: unknown[]) {
      server.use(http.get('http://localhost:8000/api/forms/', () => HttpResponse.json(forms)));
    }

    /** The income test's notice, once the packet has loaded */
    function resultRegion() {
      return screen.queryByRole('status', { name: RESULT });
    }

    async function generateAll() {
      await userEvent.click(await screen.findByRole('button', { name: /generate all/i }));
      await userEvent.click(screen.getByRole('checkbox'));
      await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    }

    it('names each table set in its own words', async () => {
      packetWith({ tables: [medianTable, standardsTable, section104Table] });
      renderFormDashboard();

      expect(
        await screen.findByText(
          'These forms use the median income figures the U.S. Trustee applies to cases filed on or after April 1, 2026. New figures are expected after March 31, 2027. If you file after that date, download your forms again.'
        )
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          'These forms use the IRS expense standards the U.S. Trustee applies to cases filed on or after July 15, 2026.'
        )
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          "These forms use the Bankruptcy Code's dollar amounts for cases filed on or after April 1, 2025. New figures are expected after March 31, 2028. If you file after that date, download your forms again."
        )
      ).toBeInTheDocument();
    });

    it('shows no sentence for a table it doesn’t know', async () => {
      packetWith({ tables: [{ ...medianTable, name: 'Some other table' }] });
      renderFormDashboard();

      await screen.findByText('Form 121 - SSN Statement');
      // UPL_FORM_DISCLAIMER also starts "These forms use", so only this notice's own words count
      expect(
        screen.queryByText(/the U\.S\. Trustee applies|dollar amounts for cases/)
      ).not.toBeInTheDocument();
    });

    it('shows the result and the pair notice when the packet holds Form 122A-2', async () => {
      packetWith({ outcome: 'presumption', family_size: 4, tables_gap: null });
      renderFormDashboard();

      await screen.findByText('Form 121 - SSN Statement');
      const region = await screen.findByRole('status', { name: RESULT });
      expect(within(region).getByText(MEANS_OUTCOME_PRESUMPTION)).toBeInTheDocument();
      expect(within(region).getByText(PRESUMPTION_INSTRUCTIONS)).toBeInTheDocument();
      expect(within(region).getAllByText(CLOSING)).toHaveLength(1);
      expect(within(region).getByText(MEANS_PAIR_NOTICE)).toBeInTheDocument();
      // The closing sentence follows the result's sentences and comes before the pair notice
      const text = region.textContent!;
      expect(text.indexOf(CLOSING)).toBeGreaterThan(text.indexOf(PRESUMPTION_INSTRUCTIONS));
      expect(text.indexOf(MEANS_PAIR_NOTICE)).toBeGreaterThan(text.indexOf(CLOSING));
    });

    it('says the household size in the result for a result that can’t be worked out yet', async () => {
      packetWith({ outcome: 'cannot_work_out', family_size: 3, tables_gap: null });
      renderFormDashboard();

      const region = await screen.findByRole('status', { name: RESULT });
      expect(
        within(region).getByText(
          'Your income is above the median for a household of 3, so Form 122A-2 applies.'
        )
      ).toBeInTheDocument();
      expect(within(region).getByText("Its result can't be worked out yet.")).toBeInTheDocument();
    });

    it('shows no result for a null outcome, and still shows the pair notice', async () => {
      packetWith({ outcome: null, family_size: null, tables_gap: null });
      renderFormDashboard();

      const region = await screen.findByRole('status', { name: RESULT });
      expect(within(region).getByText(MEANS_PAIR_NOTICE)).toBeInTheDocument();
      expect(within(region).queryByText(CLOSING)).not.toBeInTheDocument();
      expect(region.textContent).not.toMatch(/median|presumption/i);
    });

    // C8.2: a row saved before 3h1 has a family size but no outcome
    it('decides whether to show a result from the outcome alone, never from the family size', async () => {
      packetWith({ outcome: null, family_size: 4 });
      renderFormDashboard();

      const region = await screen.findByRole('status', { name: RESULT });
      expect(within(region).queryByText(CLOSING)).not.toBeInTheDocument();
      expect(region.textContent).not.toMatch(/household of 4/);
    });

    /** The packet reply: the first read says one thing, every later read another */
    function packetThen(first: Record<string, unknown>, later: () => Response) {
      let reads = 0;
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () => {
          reads += 1;
          if (reads === 1) {
            return HttpResponse.json({ session: 1, form_types: PAIR, tables: [], ...first });
          }
          return later();
        }),
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({ generated: [], errors: [], total_generated: 0, total_errors: 0 })
        )
      );
    }

    it('replaces the result with the one Generate All’s reload reports', async () => {
      packetThen({ outcome: 'presumption', family_size: 4, tables_gap: null }, () =>
        HttpResponse.json({
          session: 1,
          form_types: PAIR,
          tables: [],
          outcome: 'cannot_work_out',
          family_size: 3,
          tables_gap: null,
        })
      );
      renderFormDashboard();
      const region = await screen.findByRole('status', { name: RESULT });
      expect(within(region).getByText(MEANS_OUTCOME_PRESUMPTION)).toBeInTheDocument();

      await generateAll();

      await waitFor(() => {
        expect(
          within(screen.getByRole('status', { name: RESULT })).getByText(
            'Your income is above the median for a household of 3, so Form 122A-2 applies.'
          )
        ).toBeInTheDocument();
      });
      const after = screen.getByRole('status', { name: RESULT });
      expect(within(after).queryByText(MEANS_OUTCOME_PRESUMPTION)).not.toBeInTheDocument();
      expect(within(after).getAllByText(CLOSING)).toHaveLength(1);
    });

    it('drops the result, and its closing sentence, when Generate All’s reload fails', async () => {
      packetThen({ outcome: 'presumption', family_size: 4, tables_gap: null }, () =>
        HttpResponse.json({ detail: 'no' }, { status: 400 })
      );
      renderFormDashboard();
      const region = await screen.findByRole('status', { name: RESULT });
      expect(within(region).getByText(MEANS_OUTCOME_PRESUMPTION)).toBeInTheDocument();

      await generateAll();

      await waitFor(() => {
        expect(screen.queryByText(MEANS_OUTCOME_PRESUMPTION)).not.toBeInTheDocument();
      });
      expect(screen.queryByText(CLOSING)).not.toBeInTheDocument();
      expect(screen.queryByText(PRESUMPTION_INSTRUCTIONS)).not.toBeInTheDocument();
      expect(screen.getByText(MEANS_PAIR_NOTICE)).toBeInTheDocument();
    });

    it('shows neither the result nor the pair notice without Form 122A-2', async () => {
      packetWith({ outcome: 'at_or_below_median', family_size: 1 }, ['form_101', 'form_121']);
      renderFormDashboard();

      await screen.findByText('Form 121 - SSN Statement');
      expect(resultRegion()).toBeNull();
      expect(screen.queryByText(MEANS_PAIR_NOTICE)).not.toBeInTheDocument();
      expect(screen.queryByText(CLOSING)).not.toBeInTheDocument();
    });

    it('lists the pair’s Generate All refusals apart from the others, as information', async () => {
      const LETTER = 'The court form can’t print the letter “ą”. Change it.';
      packetWith({ outcome: 'cannot_work_out', family_size: 4 });
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({
            generated: [],
            errors: [
              { form_type: 'form_122a1', error: MEANS_HOLD_REFUSAL },
              { form_type: 'form_121', error: LETTER, step: 'debtor_info' },
              { form_type: 'form_122a2', error: MEANS_HOLD_REFUSAL },
            ],
            total_generated: 0,
            total_errors: 3,
          })
        )
      );
      renderFormDashboard();
      await generateAll();

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent(/^1 form could not be generated\./);
      expect(alert).toHaveTextContent(LETTER);
      expect(alert).not.toHaveTextContent(/Form 122A/);

      const pair = screen.getAllByText(MEANS_HOLD_REFUSAL, { exact: false });
      expect(pair).toHaveLength(2);
      const block = pair[0].closest('[role="status"]')!;
      expect(block).toBe(pair[1].closest('[role="status"]'));
      expect(block).toHaveTextContent('Form 122A-1 - Means Test');
      expect(block).toHaveTextContent('Form 122A-2 - Means Test Expenses');
      expect(block).not.toHaveTextContent(LETTER);
    });

    it('shows no alert at all when only the pair was refused', async () => {
      packetWith({ outcome: 'cannot_work_out', family_size: 4 });
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({
            generated: [],
            errors: [{ form_type: 'form_122a2', error: MEANS_HOLD_REFUSAL }],
            total_generated: 0,
            total_errors: 1,
          })
        )
      );
      renderFormDashboard();
      await generateAll();

      await screen.findByText(MEANS_HOLD_REFUSAL, { exact: false });
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('a refused Mark as Filed shows on its card', async () => {
      packetWith({ outcome: 'cannot_work_out', family_size: 4 });
      formsWith(storedForm('form_122a1', 7));
      server.use(
        http.post('http://localhost:8000/api/forms/:id/mark_filed/', () =>
          HttpResponse.json(
            { form_type: 'form_122a1', error: MEANS_HOLD_REFUSAL, page: '/exemptions' },
            { status: 422 }
          )
        )
      );
      renderFormDashboard();

      const card = await screen.findByRole('article', { name: 'Form 122A-1 - Means Test' });
      await userEvent.click(within(card).getByRole('button', { name: 'Mark as Filed' }));

      expect(await within(card).findByText(MEANS_HOLD_REFUSAL)).toBeInTheDocument();
      expect(
        within(card).getByRole('link', { name: 'Go to The property you claim as exempt' })
      ).toHaveAttribute('href', '/exemptions');
      // Still unfiled
      expect(within(card).getByRole('button', { name: 'Mark as Filed' })).toBeInTheDocument();
      expect(within(card).queryByLabelText('Filed with court')).not.toBeInTheDocument();
    });

    it.each([
      ['form_122a2', 'Form 122A-2 - Means Test Expenses', MEANS_FILED_BEFORE_122A2],
      ['form_122a1', 'Form 122A-1 - Means Test', MEANS_FILED_BEFORE_122A1],
    ])('shows a card notice for %s filed before 3h', async (formType, label, sentence) => {
      packetWith({ outcome: 'cannot_work_out', family_size: 4 });
      formsWith(storedForm(formType, 7, { status: 'filed', filed_before_means_test: true }));
      renderFormDashboard();

      const card = await screen.findByRole('article', { name: label });
      const notice = within(card).getByText(sentence);
      expect(notice).toHaveAttribute('role', 'status');
    });

    describe('the mismatch notice', () => {
      const filed122a1 = (stored_box_2: boolean | null) =>
        storedForm('form_122a1', 7, {
          status: 'filed',
          filed_before_means_test: false,
          stored_box_2,
        });

      it('shows on a filed 122A-1 that stored box 1 while Form 122A-2 applies', async () => {
        packetWith({ outcome: 'cannot_work_out', family_size: 4 });
        formsWith(filed122a1(false));
        renderFormDashboard();

        const card = await screen.findByRole('article', { name: 'Form 122A-1 - Means Test' });
        expect(within(card).getByText(MEANS_FILED_MISMATCH)).toBeInTheDocument();
      });

      it.each([
        ['stored box 2', true],
        ['stored nothing', null],
      ])('does not show for a filed 122A-1 that %s', async (_, stored) => {
        packetWith({ outcome: 'cannot_work_out', family_size: 4 });
        formsWith(filed122a1(stored));
        renderFormDashboard();

        await screen.findByRole('article', { name: 'Form 122A-1 - Means Test' });
        expect(screen.queryByText(MEANS_FILED_MISMATCH)).not.toBeInTheDocument();
      });

      it('does not show when Form 122A-2 is not in the packet', async () => {
        packetWith({ outcome: 'at_or_below_median', family_size: 1 }, [
          'form_101',
          'form_121',
          'form_122a1',
        ]);
        formsWith(filed122a1(false));
        renderFormDashboard();

        await screen.findByRole('article', { name: 'Form 122A-1 - Means Test' });
        expect(screen.queryByText(MEANS_FILED_MISMATCH)).not.toBeInTheDocument();
      });

      it('does not show on a form filed before 3h, which has its own notice', async () => {
        packetWith({ outcome: 'cannot_work_out', family_size: 4 });
        formsWith(
          storedForm('form_122a1', 7, {
            status: 'filed',
            filed_before_means_test: true,
            stored_box_2: false,
          })
        );
        renderFormDashboard();

        const card = await screen.findByRole('article', { name: 'Form 122A-1 - Means Test' });
        expect(within(card).getByText(MEANS_FILED_BEFORE_122A1)).toBeInTheDocument();
        expect(within(card).queryByText(MEANS_FILED_MISMATCH)).not.toBeInTheDocument();
      });
    });
  });
});
