import type { ReactNode } from 'react';
import { WHAT_DOES_THIS_MEAN } from '../../constants/copy';

interface WhatDoesThisMeanProps {
  /** Where the words come from: the statute, rule or form line */
  citation: string;
  /**
   * The summary's words in place of "What does this mean?", so two definitions on one step are
   * told apart (4d-R21); shown as they are, with no differing aria-label (WCAG 2.5.3, Ruling M)
   */
  label?: string;
  /** DigniFi's own closing sentence, after the citation, never inside the quotation (4e-R7) */
  note?: string;
  /** The statute's or the court's own words, verbatim, never a paraphrase */
  children: ReactNode;
}

// DRAFT: counsel
/**
 * A collapsed definition. The children are the statute's or the court's words verbatim, never
 * DigniFi's paraphrase of them; the citation says where they come from.
 */
export function WhatDoesThisMean({ citation, label, note, children }: WhatDoesThisMeanProps) {
  return (
    <details className="what-does-this-mean">
      <summary>{label ?? WHAT_DOES_THIS_MEAN}</summary>
      <blockquote>{children}</blockquote>
      <p className="form-help-text">{citation}</p>
      {note && <p className="form-help-text">{note}</p>}
    </details>
  );
}
