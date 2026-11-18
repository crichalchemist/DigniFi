/**
 * Line 43's circumstances, drawn alone (3h4): a loaded row is keyed `loaded-<index>`, so a key can
 * come round again. Business intent: a consent panel that was open on a circumstance the filer
 * removed must not be waiting, open, on a later row that takes the same key, because the filer
 * never asked to send that row's words.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import {
  MEANS_LINE_43_LEGEND,
  MEANS_LINE_43_REMOVE,
  MEANS_POLISH_BUTTON,
  MEANS_POLISH_CONSENT_HEADING,
} from '../../../constants/copy';
import { priyaPage } from '../../../test/fixtures/meansPage';
import { Line43 } from '../Line43';
import { fromReply, type PageAnswers } from '../pageState';

const withRows = (explanations: string[]): PageAnswers => {
  const page = priyaPage();
  page.answers.line_43_answer = 'yes';
  page.answers.line_43_circumstances = explanations.map((explanation) => ({
    happened: '',
    change: '',
    choices: '',
    papers: '',
    amount: null,
    explanation,
    original_explanation: null,
  }));
  return fromReply(page).answers;
};

function Harness() {
  const [answers, setAnswers] = useState(withRows(['Demo first']));
  return (
    <>
      {/* a fresh load, which keys its first row `loaded-0` again */}
      <button type="button" onClick={() => setAnswers(withRows(['Demo reloaded']))}>
        Demo reload
      </button>
      <Line43
        answers={answers}
        onChange={(change) => setAnswers(change)}
        outcome="presumption"
        line39c="2188.40"
        savedAbove
        refusals={{}}
        clearRefusal={() => {}}
        nextKey={() => 'new-1'}
        legendRef={null}
        sessionId={1}
        polishAvailable
        setRefusal={() => {}}
      />
    </>
  );
}

describe('line 43 consent panel', () => {
  it('a removed circumstance leaves no open consent panel for the row that takes its key', async () => {
    render(<Harness />);
    const legend = MEANS_LINE_43_LEGEND.split('{n}').join('1');
    await userEvent.click(screen.getByRole('button', { name: `${MEANS_POLISH_BUTTON} ${legend}` }));
    expect(screen.getByRole('group', { name: MEANS_POLISH_CONSENT_HEADING })).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole('button', { name: MEANS_LINE_43_REMOVE.split('{n}').join('1') })
    );
    await userEvent.click(screen.getByRole('button', { name: 'Demo reload' }));

    expect(screen.getByRole('textbox', { name: /explanation/i })).toHaveValue('Demo reloaded');
    expect(screen.queryByRole('group', { name: MEANS_POLISH_CONSENT_HEADING })).toBeNull();
  });
});
