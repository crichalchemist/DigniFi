import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../../test/mocks/server';
import { MeansTestPreview } from '../MeansTestPreview';

const ESTIMATE_LATER =
  "We'll estimate your eligibility once you provide income and expense information.";
const GENERIC = 'Unable to calculate means test. Please ensure all income information is provided.';

/**
 * The means test answers the preview with a 400 carrying this body; resolves once the preview
 * has shown what it makes of it.
 */
async function openPreviewRefusedWith(body: { error?: string; message: string }) {
  let answered = false;
  server.use(
    http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () => {
      answered = true;
      return HttpResponse.json(body, { status: 400 });
    })
  );
  render(<MeansTestPreview sessionId={1} currentStep={3} />);
  await userEvent.click(screen.getByRole('button', { name: /eligibility estimate/i }));
  await waitFor(() => expect(answered).toBe(true));
  await waitFor(() => expect(screen.queryByText('Updating estimate...')).not.toBeInTheDocument());
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
    expect(screen.queryByText(ESTIMATE_LATER)).not.toBeInTheDocument();
  });

  it('waits for income and expenses when the refusal carries no sentence for the filer', async () => {
    // A new filer on the Income step has no income saved yet
    await openPreviewRefusedWith({ message: GENERIC });

    expect(screen.getByText(ESTIMATE_LATER)).toBeInTheDocument();
    expect(screen.queryByText(GENERIC)).not.toBeInTheDocument();
  });
});
