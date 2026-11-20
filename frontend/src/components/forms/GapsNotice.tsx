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
} from '../../constants/copy';
import { WIZARD_STEPS } from '../../constants/wizardSteps';
import type { CompletionGap } from '../../types/api';

/** The step's place in the wizard; a step this browser doesn't know goes last */
function wizardIndex(key: string): number {
  const index = WIZARD_STEPS.findIndex((step) => step.key === key);
  return index === -1 ? WIZARD_STEPS.length : index;
}

export function GapsNotice({ gaps }: { gaps: CompletionGap[] }) {
  const gateCount = gaps.filter((gap) => gap.kind === 'gate').length;
  const detailCount = gaps.filter((gap) => gap.kind === 'detail').length;

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
          {steps.map((key) => {
            const wizardStep = WIZARD_STEPS.find((step) => step.key === key);
            return (
              <li key={key}>
                {gaps
                  .filter((gap) => gap.step === key)
                  .map((gap, index) => (
                    <p key={index}>{gap.message}</p>
                  ))}
                {wizardStep && (
                  <Link to={`/intake?step=${key}`} className="button button--primary">
                    Go to {wizardStep.label}
                  </Link>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
