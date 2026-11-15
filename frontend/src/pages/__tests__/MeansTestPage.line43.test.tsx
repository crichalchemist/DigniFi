/**
 * The Form 122A-2 page's line 43 (3h2 spec section 8.9 and 8.12): the filer writes the special
 * circumstances in their own words, with a draft they may ask for and edit. Business intent: nothing
 * is chosen or written for the filer, the draft never replaces words they typed, the statute's
 * arithmetic beside it is shown only while it is true of what is saved, and no word of line 43 says
 * what the filer should hope for.
 */
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { meansPage, priyaPage } from '../../test/fixtures/meansPage';
import {
  MEANS_EXPLANATION_LETTER,
  MEANS_EXPLANATION_TOO_LONG,
  MEANS_LINE_43_ADD,
  MEANS_LINE_43_ASSEMBLE,
  MEANS_LINE_43_LABEL_CHANGE,
  MEANS_LINE_43_LABEL_CHOICES,
  MEANS_LINE_43_LABEL_HAPPENED,
  MEANS_LINE_43_LABEL_PAPERS,
  MEANS_LINE_43_REMOVE,
  MEANS_LINE_43_SKIPPED,
  MEANS_PAGE_SAVE_FAILED,
  MEANS_SPOUSE_ADD_VEHICLE,
} from '../../constants/copy';
import type { MeansCircumstance, MeansPage } from '../../types/api';
import { URL, field, pressContinue, radio, ready, renderPage, serve } from './meansTestPageHelpers';

const fill = (sentence: string, values: Record<string, string>) =>
  Object.entries(values).reduce(
    (text, [key, value]) => text.split(`{${key}}`).join(value),
    sentence
  );

const circumstance = (over: Partial<MeansCircumstance> = {}): MeansCircumstance => ({
  happened: '',
  change: '',
  choices: '',
  papers: '',
  amount: '400.00',
  explanation: null,
  ...over,
});

/** Priya's filled page, line 43 Yes, a presumption with line 39c, and these circumstances */
function line43Page(circumstances: MeansCircumstance[] = [circumstance()]): MeansPage {
  const page = priyaPage();
  page.answers.line_43_answer = 'yes';
  page.answers.line_43_circumstances = circumstances;
  page.information!.line_39c = '2188.40';
  return page;
}

const NOW = /Your line 39d is now/;
const area = (name: string) =>
  document.querySelector(`textarea[name="${name}"]`) as HTMLTextAreaElement;
const line43 = () => document.getElementById('line-43') as HTMLElement;
const typeIn = async (name: string, text: string) => {
  await userEvent.type(area(name), text);
};
const retype = async (name: string, text: string) => {
  await userEvent.clear(field(name));
  await userEvent.type(field(name), text);
};

describe('line 43', () => {
  it('nothing on line 43 is preselected', async () => {
    serve(meansPage());
    renderPage();
    await ready();
    expect(radio('means_line_43', 'yes')).not.toBeChecked();
    expect(radio('means_line_43', 'no')).not.toBeChecked();
    expect(area('means_line_43_0_happened')).toBeNull();
    expect(screen.queryByRole('button', { name: MEANS_LINE_43_ADD })).toBeNull();

    await userEvent.click(radio('means_line_43', 'yes'));
    expect(area('means_line_43_0_explanation')).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: MEANS_LINE_43_ADD }));
    expect(area('means_line_43_0_explanation')).toHaveValue('');
    expect(area('means_line_43_0_happened')).toHaveValue('');
    expect(field('means_line_43_0_amount')).toHaveValue(null);
  });

  it('the assembled draft fills the box only on a press and only while it is empty', async () => {
    serve(line43Page([]));
    renderPage();
    await ready();
    await userEvent.click(screen.getByRole('button', { name: MEANS_LINE_43_ADD }));
    await typeIn('means_line_43_0_happened', 'Demo layoff in May');
    await typeIn('means_line_43_0_change', 'Income fell');
    await typeIn('means_line_43_0_choices', 'Asked for hours');
    await typeIn('means_line_43_0_papers', 'Letter');
    expect(area('means_line_43_0_explanation')).toHaveValue('');

    await userEvent.click(screen.getByRole('button', { name: MEANS_LINE_43_ASSEMBLE }));
    const draft = [
      `${MEANS_LINE_43_LABEL_HAPPENED} Demo layoff in May`,
      `${MEANS_LINE_43_LABEL_CHANGE} Income fell`,
      `${MEANS_LINE_43_LABEL_CHOICES} Asked for hours`,
      `${MEANS_LINE_43_LABEL_PAPERS} Letter`,
    ].join('\n');
    expect(area('means_line_43_0_explanation')).toHaveValue(draft);

    await typeIn('means_line_43_0_explanation', ' My own edit');
    await typeIn('means_line_43_0_papers', ' and a bill');
    await userEvent.click(screen.getByRole('button', { name: MEANS_LINE_43_ASSEMBLE }));
    expect(area('means_line_43_0_explanation')).toHaveValue(`${draft} My own edit`);
  });

  it('each answer box takes at most 450 characters and the explanation at most 2,000', async () => {
    serve(line43Page());
    renderPage();
    await ready();
    for (const box of ['happened', 'change', 'choices', 'papers']) {
      expect(area(`means_line_43_0_${box}`).maxLength).toBe(450);
    }
    expect(area('means_line_43_0_explanation').maxLength).toBe(2000);
  });

  it('the skip note shows when the result is no presumption', async () => {
    serve({ ...line43Page(), outcome: 'no_presumption' });
    const { unmount } = renderPage();
    await ready();
    expect(within43()).toHaveTextContent(MEANS_LINE_43_SKIPPED);
    unmount();

    serve({ ...meansPage(), outcome: 'no_presumption' });
    renderPage();
    await ready();
    expect(within43()).toHaveTextContent(MEANS_LINE_43_SKIPPED);
    expect(radio('means_line_43', 'yes')).not.toBeChecked();
  });

  it('the rebuttal figure follows the amounts as they are typed', async () => {
    serve(line43Page());
    renderPage();
    await ready();
    expect(screen.getByText('Your line 39d is now $131,304.00.')).toBeInTheDocument();
    expect(
      screen.getByText(
        'If the court allowed the amounts on line 43, line 39d would be $107,304.00.'
      )
    ).toBeInTheDocument();
    expect(screen.getByText('The court decides whether to allow them.')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: MEANS_LINE_43_ADD }));
    await retype('means_line_43_1_amount', '250');
    expect(
      screen.getByText('If the court allowed the amounts on line 43, line 39d would be $92,304.00.')
    ).toBeInTheDocument();
  });

  it('the rebuttal figure hides while answers above line 43 are unsaved', async () => {
    serve(line43Page());
    renderPage();
    await ready();
    expect(screen.getByText(NOW)).toBeInTheDocument();

    // line 16 was 2300.00: the box hands over the figure to the cent, so this one changes it
    await retype('means_line_16', '2400');
    expect(screen.queryByText(NOW)).toBeNull();
    expect(screen.queryByText(/If the court allowed/)).toBeNull();
    expect(screen.queryByText(/The court decides whether to allow them/)).toBeNull();

    // typing a line 43 amount doesn't bring them back
    await retype('means_line_43_0_amount', '300');
    expect(screen.queryByText(NOW)).toBeNull();

    // a Continue that stays on a gap (the circumstance has no explanation) saves
    await pressContinue();
    expect(await screen.findByText(NOW)).toBeInTheDocument();
    expect(
      screen.getByText(
        'If the court allowed the amounts on line 43, line 39d would be $113,304.00.'
      )
    ).toBeInTheDocument();
  });

  it('the rebuttal figure comes back after a save that gives a new spouse row its id', async () => {
    const saved = line43Page();
    const sent: Record<string, unknown>[] = [];
    server.use(
      http.get(URL, () => HttpResponse.json(saved)),
      http.put(URL, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown> & {
          spouse_vehicles: { ref: string }[];
        };
        sent.push(body);
        // the server gives each new spouse vehicle the next id, in the order sent
        const spouse_vehicles = body.spouse_vehicles.map((row, index) => ({
          ...row,
          ref: row.ref.startsWith('new-') ? `spouse-${index + 1}` : row.ref,
        }));
        return HttpResponse.json({ ...saved, answers: { ...saved.answers, spouse_vehicles } });
      })
    );
    renderPage();
    await ready();
    expect(screen.getByText(NOW)).toBeInTheDocument();

    await userEvent.click(radio('means_spouse_vehicles', 'yes'));
    await userEvent.click(screen.getByRole('button', { name: MEANS_SPOUSE_ADD_VEHICLE }));
    expect(screen.queryByText(NOW)).toBeNull();

    await pressContinue();
    expect(await screen.findByText(NOW)).toBeInTheDocument();
    expect(sent).toHaveLength(1);
    expect(sent[0].spouse_vehicles).toEqual([
      { ref: expect.stringMatching(/^new-/), description: '', leased: null, claimed: null },
    ]);
  });

  it('the rebuttal figure never shows without line 39d, under No, with only a $0 amount, or without a presumption', async () => {
    const shows = async (page: MeansPage) => {
      serve(page);
      const { unmount } = renderPage();
      await ready();
      const found = screen.queryByText(NOW) !== null;
      unmount();
      return found;
    };
    // the control: all of it true
    expect(await shows(line43Page())).toBe(true);

    const noFigure = line43Page();
    noFigure.information!.line_39c = null;
    expect(await shows(noFigure)).toBe(false);

    const under = line43Page();
    under.answers.line_43_answer = 'no';
    expect(await shows(under)).toBe(false);

    expect(await shows(line43Page([circumstance({ amount: '0.00' })]))).toBe(false);
    expect(await shows(line43Page([circumstance({ amount: null })]))).toBe(false);

    for (const outcome of ['no_presumption', 'cannot_work_out', 'at_or_below_median'] as const) {
      expect(await shows({ ...line43Page(), outcome })).toBe(false);
    }
  });

  it('an explanation the server refuses shows the sentence beside its box', async () => {
    for (const sentence of [MEANS_EXPLANATION_TOO_LONG, MEANS_EXPLANATION_LETTER]) {
      serve(line43Page([circumstance({ explanation: 'Demo words' })]), {
        status: 400,
        body: { line_43_circumstances: { '0': { explanation: [sentence] } } },
      });
      const { unmount } = renderPage();
      await ready();
      await pressContinue();
      const box = area('means_line_43_0_explanation');
      expect(await screen.findByText(sentence)).toBeInTheDocument();
      expect(box.closest('.form-field')).toHaveTextContent(sentence);
      expect(screen.queryByText(MEANS_PAGE_SAVE_FAILED)).toBeNull();
      // the typed words stay
      expect(box).toHaveValue('Demo words');
      unmount();
    }

    serve(line43Page([circumstance({ explanation: 'Demo words' })]), {
      status: 400,
      body: { line_43_circumstances: { '0': { explanation: ['Something else entirely.'] } } },
    });
    renderPage();
    await ready();
    await pressContinue();
    expect(await screen.findByText(MEANS_PAGE_SAVE_FAILED)).toBeInTheDocument();
    expect(screen.queryByText('Something else entirely.')).toBeNull();
    expect(area('means_line_43_0_explanation')).toHaveValue('Demo words');
  });

  it('under line 43 No a refused stored explanation sends nothing and blocks no save, and Yes sends it back', async () => {
    const saved = line43Page([circumstance({ explanation: 'Demo words' })]);
    const sent: Record<string, unknown>[] = [];
    server.use(
      http.get(URL, () => HttpResponse.json(saved)),
      http.put(URL, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        sent.push(body);
        const rows = body.line_43_circumstances as unknown[];
        if (rows.length > 0) {
          return HttpResponse.json(
            { line_43_circumstances: { '0': { explanation: [MEANS_EXPLANATION_LETTER] } } },
            { status: 400 }
          );
        }
        // a changed result keeps the filer on the page, so the Yes press below can be made
        return HttpResponse.json({ ...saved, outcome: 'no_presumption' });
      })
    );
    renderPage();
    await ready();
    await userEvent.click(radio('means_line_43', 'no'));
    expect(area('means_line_43_0_explanation')).toBeNull();
    await pressContinue();
    await waitFor(() => expect(sent.length).toBeGreaterThan(0));
    expect(screen.queryByText(MEANS_PAGE_SAVE_FAILED)).toBeNull();
    expect(sent.length).toBeGreaterThan(0);
    for (const body of sent) expect(body.line_43_circumstances).toEqual([]);
    await userEvent.click(radio('means_line_43', 'yes'));
    expect(area('means_line_43_0_explanation')).toHaveValue('Demo words');
    const before = sent.length;
    await pressContinue();
    expect(await screen.findByText(MEANS_EXPLANATION_LETTER)).toBeInTheDocument();
    const rows = sent[before].line_43_circumstances as { explanation: string }[];
    expect(rows).toHaveLength(1);
    expect(rows[0].explanation).toBe('Demo words');
  }, 20000);

  it("a circumstance's inputs carry the names the journeys use", async () => {
    serve(line43Page([circumstance({ explanation: 'Demo words' })]));
    renderPage();
    await ready();
    for (const box of ['happened', 'change', 'choices', 'papers', 'explanation']) {
      expect(area(`means_line_43_0_${box}`)).not.toBeNull();
    }
    expect(field('means_line_43_0_amount')).toHaveValue(400);
    expect(
      screen.getByRole('button', { name: fill(MEANS_LINE_43_REMOVE, { n: '1' }) })
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: MEANS_LINE_43_ADD })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: MEANS_LINE_43_ASSEMBLE })).toBeInTheDocument();
  });

  it('nothing on line 43 says overcome, rebut, rebuttal or abuse', async () => {
    const banned = /overcome|rebut|abuse/i;
    const check = () => {
      expect(line43().textContent).not.toMatch(banned);
      for (const labelled of line43().querySelectorAll('[aria-label]')) {
        expect(labelled.getAttribute('aria-label')).not.toMatch(banned);
      }
    };
    serve(line43Page([circumstance({ amount: '400.00' })]));
    const { unmount } = renderPage();
    await ready();
    expect(screen.getByText(NOW)).toBeInTheDocument();
    check();
    unmount();

    serve({ ...line43Page([circumstance({ amount: '400.00' })]), outcome: 'no_presumption' });
    renderPage();
    await ready();
    expect(within43()).toHaveTextContent(MEANS_LINE_43_SKIPPED);
    check();
  });
});

function within43() {
  return line43();
}
