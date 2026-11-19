import type { ReactNode } from 'react';
import { WHAT_DOES_THIS_MEAN } from '../../constants/copy';

interface WhatDoesThisMeanProps {
  /** Where the words come from: the statute, rule or form line */
  citation: string;
  /** The statute's or the court's own words, verbatim, never a paraphrase */
  children: ReactNode;
}

// DRAFT: counsel
/**
 * A collapsed definition. The children are the statute's or the court's words verbatim, never
 * DigniFi's paraphrase of them; the citation says where they come from.
 */
export function WhatDoesThisMean({ citation, children }: WhatDoesThisMeanProps) {
  return (
    <details className="what-does-this-mean">
      <summary>{WHAT_DOES_THIS_MEAN}</summary>
      <blockquote>{children}</blockquote>
      <p className="form-help-text">{citation}</p>
    </details>
  );
}
