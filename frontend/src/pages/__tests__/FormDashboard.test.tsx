import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { FormDashboard } from '../FormDashboard';

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
  current_step: 8,
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
  });

  // ---------------------------------------------------------------------------
  // A refusal of the whole call (forms step 2 §5.6, DIG-156)
  // ---------------------------------------------------------------------------

  describe('when Generate All or the packet list is refused', { timeout: 15_000 }, () => {
    const FINISH_INTAKE = 'Finish your intake before preparing your forms.';
    const INCOME_NOT_SPLIT = 'Enter your income by source on the Income step.';
    // The server's sentence for a 500 speaks of one form, so the dashboard never shows it
    const SERVER_FAILURE = "This form couldn't be prepared. Please try again later.";
    const GENERIC =
      'Something went wrong. Your information is safe — please try again in a moment.';

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
          HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 })
        )
      );

      renderFormDashboard();

      expect(await screen.findByText(INCOME_NOT_SPLIT)).toBeInTheDocument();
      expect(screen.queryByText(/unable to load your forms/i)).not.toBeInTheDocument();
    });

    it('offers the way back to the intake, not a retry, when the packet list is refused', async () => {
      // A completed filer whose income isn't split gets the same refusal on every reload
      server.use(
        http.get('http://localhost:8000/api/forms/packet/', () =>
          HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 })
        )
      );

      renderFormDashboard();

      await screen.findByText(INCOME_NOT_SPLIT);
      expect(screen.getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
        'href',
        '/intake'
      );
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

    it('shows generic words, never the server’s, when Generate All fails on the server', async () => {
      server.use(
        http.post('http://localhost:8000/api/forms/generate_all/', () =>
          HttpResponse.json({ error: SERVER_FAILURE }, { status: 500 })
        )
      );

      renderFormDashboard();
      const continueBtn = await openGenerateAll();

      // A 500 is tried three more times (0.5 s, 1 s, 2 s apart) before the dashboard gives up
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

      expect(await screen.findByText(GENERIC)).toBeInTheDocument();
      expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
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
            : HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 });
        })
      );

      renderFormDashboard();
      await userEvent.click(await openGenerateAll());

      expect(await screen.findByText(INCOME_NOT_SPLIT)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
        'href',
        '/intake'
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
            ? HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 })
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
});
