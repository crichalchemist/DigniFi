import type { Ref } from 'react';
import {
  MEANS_LINE_43_LINK,
  MEANS_STALE_ANSWERS,
  MEANS_TEST_PREVIEW_TITLE,
} from '../../constants/copy';
import { UPL_MEANS_TEST_DISCLAIMER } from '../../constants/upl';
import type { MeansPage } from '../../types/api';
import { formatMonthYear } from '../../utils/formatMonthYear';
import { meansOutcomeSentences } from '../../utils/meansOutcome';

interface MeansResultProps {
  page: MeansPage;
  /** The in-page link's click: the page focuses line 43's legend (a hash link focuses no fieldset) */
  linkToLine43: () => void;
  ref?: Ref<HTMLElement>;
}

/**
 * The result at the top of the page (F13, H21): the stale-answers notice, the outcome's sentences
 * in plain text, under a presumption the link to line 43, then the court sentence once, last.
 */
export function MeansResult({ page, linkToLine43, ref }: MeansResultProps) {
  const sentences = meansOutcomeSentences(page.outcome, page.family_size, page.tables_gap, 'page');
  const answered = page.debts_answered_on;
  // The month of both dates, read from the ISO text (never through a Date and its time zone)
  const stale = answered !== null && answered.slice(0, 7) !== page.fill_date.slice(0, 7);

  return (
    <section role="status" aria-label={MEANS_TEST_PREVIEW_TITLE} tabIndex={-1} ref={ref}>
      {stale && <p>{MEANS_STALE_ANSWERS.replace('{month}', formatMonthYear(answered))}</p>}
      {sentences.map((sentence) => (
        <p key={sentence}>{sentence}</p>
      ))}
      {page.outcome === 'presumption' && (
        <p>
          <a
            href="#line-43"
            onClick={(event) => {
              event.preventDefault();
              linkToLine43();
            }}
          >
            {MEANS_LINE_43_LINK}
          </a>
        </p>
      )}
      {sentences.length > 0 && <p>{UPL_MEANS_TEST_DISCLAIMER}</p>}
    </section>
  );
}
