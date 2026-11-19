import type { ReactNode } from 'react';

/** One line that says why the court asks a question, drawn above it */
export function FramingLine({ children }: { children: ReactNode }) {
  return <p className="form-help-text framing-line">{children}</p>;
}
