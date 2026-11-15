import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../../test/mocks/server';
import { MeansTestPreview } from '../MeansTestPreview';
import {
  MEANS_OUTCOME_NO_PRESUMPTION,
  MEANS_OUTCOME_PRESUMPTION,
  MEANS_TABLE_MISSING,
  MEANS_TEST_UNAVAILABLE,
  MEANS_TEST_WAITING,
} from '../../../constants/copy';
import { PRESUMPTION_INSTRUCTIONS } from '../../../constants/formText';
import type { MeansOutcome } from '../../../types/api';

const CLOSING = 'A court makes the final decision.';
const GENERIC = 'Unable to calculate means test. Please ensure all income information is provided.';
const CALCULATE = 'http://localhost:8000/api/intake/sessions/:id/calculate_means_test/';

/**
 * The means test answers the preview with a 400 carrying this body; resolves once the preview
 * has shown what it makes of it.
 */
async function openPreviewRefusedWith(body: { error?: string; message: string }) {
  let answered = false;
  server.use(
    http.post(CALCULATE, () => {
      answered = true;
      return HttpResponse.json(body, { status: 400 });
    })
  );
  render(<MeansTestPreview sessionId={1} currentStep={3} />);
  await userEvent.click(screen.getByRole('button', { name: /income test/i }));
  await waitFor(() => expect(answered).toBe(true));
  await waitFor(() =>
    expect(screen.queryByText('Updating your result...')).not.toBeInTheDocument()
  );
}

/** The means test answers the preview with this result; resolves once the panel shows it. */
async function openPreviewWith(result: Record<string, unknown>) {
  server.use(
    http.post(CALCULATE, () =>
      HttpResponse.json({
        means_test_result: {
          passes_means_test: true,
          cmi: 3500,
          median_income_threshold: 71304,
          family_size: 4,
          ...result,
        },
        session_id: 1,
      })
    )
  );
  const view = render(<MeansTestPreview sessionId={1} currentStep={3} />);
  await userEvent.click(screen.getByRole('button', { name: /income test/i }));
  await screen.findByText('Monthly income for the means test');
  return view;
}

describe('MeansTestPreview when the means test refuses', () => {
  // T1 review M2: during a gap between median tables, asking for income the filer already gave
  // sends them back to a step that can't help
  it.each([
    [
      'no median table is in force',
      "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your forms. Please try again later.",
    ],
    ['income was not entered by source', 'Enter your income by source on the Income step.'],
  ])('says what stands in the way when %s', async (_, sentence) => {
    await openPreviewRefusedWith({ error: sentence, message: GENERIC });

    expect(screen.getByText(sentence)).toBeInTheDocument();
    expect(screen.queryByText(MEANS_TEST_WAITING)).not.toBeInTheDocument();
  });

  it('waits for income when the refusal carries no sentence for the filer', async () => {
    // A new filer on the Income step has no income saved yet
    await openPreviewRefusedWith({ message: GENERIC });

    expect(screen.getByText(MEANS_TEST_WAITING)).toBeInTheDocument();
    expect(screen.queryByText(GENERIC)).not.toBeInTheDocument();
    expect(screen.queryByText(CLOSING)).not.toBeInTheDocument();
  });

  it('says it cannot show the result, with no closing sentence, when the call fails', async () => {
    let answered = false;
    server.use(
      http.post(CALCULATE, () => {
        answered = true;
        return HttpResponse.json({ detail: 'boom' }, { status: 500 });
      })
    );
    render(<MeansTestPreview sessionId={1} currentStep={3} />);
    await userEvent.click(screen.getByRole('button', { name: /income test/i }));
    await waitFor(() => expect(answered).toBe(true));

    expect(await screen.findByText(MEANS_TEST_UNAVAILABLE)).toBeInTheDocument();
    expect(screen.queryByText(CLOSING)).not.toBeInTheDocument();
  });

  // An old "Form 122A-2 doesn't apply to you" beside a failure is the owner's harm direction, and
  // the closing sentence never shows without the current outcome (§7.4)
  it.each<[string, number, Record<string, string>, string]>([
    [
      'a 400',
      400,
      { error: 'Enter your income by source on the Income step.', message: GENERIC },
      'Enter your income by source on the Income step.',
    ],
    ['a 500', 500, { detail: 'boom' }, MEANS_TEST_UNAVAILABLE],
  ])(
    'drops an earlier result and its closing sentence when a later call answers with %s',
    async (_, status, body, sentence) => {
      let calls = 0;
      server.use(
        http.post(CALCULATE, () => {
          calls += 1;
          if (calls === 1) {
            return HttpResponse.json({
              means_test_result: {
                passes_means_test: true,
                cmi: 3500,
                median_income_threshold: 71304,
                family_size: 1,
                outcome: 'at_or_below_median',
                tables_gap: null,
              },
              session_id: 1,
            });
          }
          // Every later call fails, so a 500's retries can't bring a result back
          return HttpResponse.json(body, { status });
        })
      );
      const { container, rerender } = render(<MeansTestPreview sessionId={1} currentStep={3} />);
      await userEvent.click(screen.getByRole('button', { name: /income test/i }));
      expect(await screen.findByText(CLOSING)).toBeInTheDocument();
      expect(container.textContent).toContain('at or below the median');

      // A later step asks for the result again
      rerender(<MeansTestPreview sessionId={1} currentStep={4} />);

      expect(await screen.findByText(sentence, {}, { timeout: 10000 })).toBeInTheDocument();
      expect(calls).toBeGreaterThan(1);
      expect(screen.queryByText(CLOSING)).not.toBeInTheDocument();
      expect(container.textContent).not.toContain('at or below the median');
      expect(screen.queryByText('Monthly income for the means test')).not.toBeInTheDocument();
    },
    20000
  );
});

describe('MeansTestPreview with a result', () => {
  // The figure includes a spouse's income once the filer lives with them (3e1 spec §8.2)
  it('the means-test preview calls its figure Monthly income for the means test', async () => {
    await openPreviewWith({
      passes_means_test: null,
      cmi: 13800,
      median_income_threshold: 137902,
      family_size: 4,
      outcome: 'cannot_work_out',
      tables_gap: null,
    });

    expect(screen.getByText('Monthly income for the means test')).toBeInTheDocument();
    expect(screen.getByText('Median for Household of 4')).toBeInTheDocument();
    expect(screen.queryByText('Your Monthly Income')).not.toBeInTheDocument();
  });

  // The means test answers § 707(b) only; the court decides a fee waiver, and the filing-fee
  // page shows its figures as information (3f spec §9). An old server's key changes nothing.
  it('the means-test preview gives no fee-waiver verdict, even for a very low income', async () => {
    await openPreviewWith({
      qualifies_for_fee_waiver: true,
      cmi: 1500,
      family_size: 1,
      outcome: 'at_or_below_median',
    });

    expect(screen.getByText('Monthly income for the means test')).toBeInTheDocument();
    expect(screen.queryByText(/fee waiver/i)).not.toBeInTheDocument();
  });

  it.each<[MeansOutcome, boolean | null, string[]]>([
    [
      'at_or_below_median',
      true,
      [
        "Your income is at or below the median for a household of 4 in Illinois. Form 122A-2 doesn't apply to you.",
      ],
    ],
    [
      'cannot_work_out',
      null,
      [
        'Your income is above the median for a household of 4, so Form 122A-2 applies.',
        "Its result can't be worked out until you answer the questions on the Form 122A-2 page, once you finish your intake.",
        "Being above the median doesn't mean a presumption of abuse applies.",
      ],
    ],
    ['no_presumption', true, [MEANS_OUTCOME_NO_PRESUMPTION]],
    ['presumption', false, [MEANS_OUTCOME_PRESUMPTION, PRESUMPTION_INSTRUCTIONS]],
  ])(
    'shows the %s result in the form’s words, then the closing sentence once',
    async (outcome, passes, sentences) => {
      const { container } = await openPreviewWith({ outcome, passes_means_test: passes });

      const text = container.querySelector('.means-test-preview-indicator-text');
      expect(container.querySelectorAll('.means-test-preview-indicator-text')).toHaveLength(1);
      expect(text?.textContent).toBe(sentences.join(' '));
      // An exact-text count can't see the closing sentence inside the joined paragraph
      expect(text?.textContent).not.toContain(CLOSING);
      const closing = screen.getAllByText(CLOSING);
      expect(closing).toHaveLength(1);
      expect(
        text!.compareDocumentPosition(closing[0]) & Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy();
    }
  );

  it('puts the closing sentence after the instructions for a presumption', async () => {
    const { container } = await openPreviewWith({
      outcome: 'presumption',
      passes_means_test: false,
    });

    const body = container.querySelector('.means-test-preview-indicator')!.textContent!;
    expect(body.indexOf(PRESUMPTION_INSTRUCTIONS)).toBeGreaterThanOrEqual(0);
    expect(body.indexOf(CLOSING)).toBeGreaterThan(body.indexOf(PRESUMPTION_INSTRUCTIONS));
  });

  it.each<[MeansOutcome, boolean | null]>([
    ['at_or_below_median', true],
    ['cannot_work_out', null],
    ['no_presumption', true],
    ['presumption', false],
  ])('uses the same markup, with no icon or verdict class, for %s', async (outcome, passes) => {
    const { container } = await openPreviewWith({ outcome, passes_means_test: passes });

    const indicator = container.querySelector('.means-test-preview-indicator')!;
    expect([...indicator.classList]).toEqual(['means-test-preview-indicator']);
    // The inline disclaimer's own info icon is allowed
    expect(indicator.querySelector('svg:not(.upl-disclaimer-icon)')).toBeNull();
  });

  it.each<[MeansOutcome, boolean | null]>([
    ['at_or_below_median', true],
    ['cannot_work_out', null],
    ['no_presumption', true],
    ['presumption', false],
  ])('never says eligible or estimate for %s', async (outcome, passes) => {
    const { container } = await openPreviewWith({ outcome, passes_means_test: passes });

    expect(container.textContent).not.toMatch(/eligib|estimate/i);
  });

  it('says the means test figures are missing under a table gap, still not implying a presumption', async () => {
    const { container } = await openPreviewWith({
      outcome: 'cannot_work_out',
      passes_means_test: null,
      tables_gap: 'IRS expense standards',
    });

    const text = container.querySelector('.means-test-preview-indicator-text')!.textContent!;
    expect(text).toContain(MEANS_TABLE_MISSING);
    expect(text).not.toContain("Its result can't be worked out until you answer");
    expect(text).toContain("doesn't mean a presumption of abuse applies");
  });

  it('shows no outcome words and no closing sentence for a null outcome', async () => {
    const { container } = await openPreviewWith({ outcome: null, passes_means_test: null });

    expect(container.querySelector('.means-test-preview-indicator')).toBeNull();
    expect(screen.queryByText(CLOSING)).not.toBeInTheDocument();
    expect(container.textContent).not.toMatch(/eligib|further review|presumption/i);
  });

  it('shows no outcome words for a reply that has no outcome key at all (an older server)', async () => {
    const { container } = await openPreviewWith({ passes_means_test: false });

    expect(container.querySelector('.means-test-preview-indicator')).toBeNull();
    expect(screen.queryByText(CLOSING)).not.toBeInTheDocument();
  });

  // C8.1: no screen picks its words from the truthiness of passes_means_test
  it('picks its words from the outcome, never from passes_means_test', async () => {
    const { container } = await openPreviewWith({
      outcome: 'at_or_below_median',
      passes_means_test: false,
    });

    expect(container.querySelector('.means-test-preview-indicator-text')!.textContent).toContain(
      'at or below the median'
    );
  });
});
