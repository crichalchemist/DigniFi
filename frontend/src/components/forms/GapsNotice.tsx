/**
 * GapsNotice - What the server finds missing from the intake, above Generate All
 *
 * A `gate` is an answer the forms can't be prepared without, so it is named as missing; a `detail`
 * is one the forms print blank. Each affected step gets its messages and one way to it.
 */

import { Link } from 'react-router-dom';
import {
  DASHBOARD_GAPS_MANY,
  DASHBOARD_GAPS_ONE,
  DASHBOARD_GATES_MANY,
  DASHBOARD_GATES_ONE,
  PETITION_DETAIL_TOO_LONG,
  PETITION_DETAIL_TOO_LONG_ROW,
} from '../../constants/copy';
import { WIZARD_STEPS } from '../../constants/wizardSteps';
import type { CompletionGap } from '../../types/api';

/** The step's place in the wizard; a step this browser doesn't know goes last */
function wizardIndex(key: string): number {
  const index = WIZARD_STEPS.findIndex((step) => step.key === key);
  return index === -1 ? WIZARD_STEPS.length : index;
}

/** The one way to a gap's step, "Go to {label}"; nothing for a step this browser doesn't know */
export function GapLink({ step }: { step: string }) {
  const wizardStep = WIZARD_STEPS.find((candidate) => candidate.key === step);
  if (!wizardStep) return null;
  return (
    <Link to={`/intake?step=${step}`} className="button button--primary">
      Go to {wizardStep.label}
    </Link>
  );
}

/** A sentence template as a pattern: each {placeholder} matches any text */
function patternOf(template: string): RegExp {
  const escaped = template.replace(/[.*+?^$()|[\]\\]/g, '\\$&');
  return new RegExp(`^${escaped.replace(/\{[a-z]+\}/g, '.+')}$`);
}

const TOO_LONG_SENTENCES = [
  patternOf(PETITION_DETAIL_TOO_LONG),
  patternOf(PETITION_DETAIL_TOO_LONG_ROW),
];

/** A too-long answer stops Form 101 rather than printing blank, so the blank count leaves it out */
function isTooLong(gap: CompletionGap): boolean {
  return TOO_LONG_SENTENCES.some((pattern) => pattern.test(gap.message));
}

export function GapsNotice({ gaps }: { gaps: CompletionGap[] }) {
  const gateCount = gaps.filter((gap) => gap.kind === 'gate').length;
  const detailCount = gaps.filter((gap) => gap.kind === 'detail' && !isTooLong(gap)).length;

  // One entry per distinct step, in first-seen order; the sort is stable, so unknown steps keep it
  const steps = [...new Set(gaps.map((gap) => gap.step))].sort(
    (a, b) => wizardIndex(a) - wizardIndex(b)
  );

  // A polite region from the start, empty until there is something to say, so a screen reader
  // reads out the gaps that arrive in it (the pair region on FormDashboard works the same way)
  return (
    <section className="form-dashboard-notice form-dashboard-gaps" role="status">
      {gateCount > 0 && (
        <p>
          {gateCount === 1
            ? DASHBOARD_GATES_ONE
            : DASHBOARD_GATES_MANY.replace('{count}', String(gateCount))}
        </p>
      )}
      {detailCount > 0 && (
        <p>
          {detailCount === 1
            ? DASHBOARD_GAPS_ONE
            : DASHBOARD_GAPS_MANY.replace('{count}', String(detailCount))}
        </p>
      )}
      {steps.length > 0 && (
        <ul>
          {steps.map((key) => (
            <li key={key}>
              {gaps
                .filter((gap) => gap.step === key)
                .map((gap, index) => (
                  <p key={index}>{gap.message}</p>
                ))}
              <GapLink step={key} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
