/**
 * GapsNotice - What the server finds missing from the intake, above Generate All
 *
 * A `gate` is an answer the forms can't be prepared without, so it is named as missing. A `detail`
 * is one Complete lets through: a missing answer, which the forms print blank and the count names
 * as blank, a too-long answer, listed with its words but never counted as blank (isTooLong), or
 * a missing answer whose form is refused whole (Form 101A's landlord), also never counted as blank
 * (isRefusedForm).
 * Each affected step gets its messages and one way to it.
 */

import { Link } from 'react-router-dom';
import {
  DASHBOARD_GAPS_MANY,
  DASHBOARD_GAPS_ONE,
  DASHBOARD_GATES_MANY,
  DASHBOARD_GATES_ONE,
  PETITION_DETAIL_LANDLORD,
  PETITION_DETAIL_TOO_LONG,
  PETITION_DETAIL_TOO_LONG_101A,
  PETITION_DETAIL_TOO_LONG_ROW,
  SCHEDULE_I_DETAIL_TOO_LONG,
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
  patternOf(PETITION_DETAIL_TOO_LONG_101A),
  patternOf(PETITION_DETAIL_TOO_LONG_ROW),
  patternOf(SCHEDULE_I_DETAIL_TOO_LONG),
];

/**
 * A too-long answer never prints blank: Generate refuses the form whose box can't take it (Form
 * 101, Form 101A, Form 103B, Schedule I or Schedule J; a row's {forms} names Form 101 or Form 103B,
 * and Form 101A's, Schedule I's and Schedule J's own sentences name them; Form 101A, like 103B, is
 * measured only while it is in the packet), and a text over its character cap that its box still
 * takes prints whole. So the blank count leaves it out
 */
function isTooLong(gap: CompletionGap): boolean {
  return TOO_LONG_SENTENCES.some((pattern) => pattern.test(gap.message));
}

/**
 * A missing landlord is no blank box: Form 101A is refused whole while it is missing, never
 * printed with an empty block (4b2-R12). Matched by its exact sentence, as the too-long ones are
 * by their patterns
 */
function isRefusedForm(gap: CompletionGap): boolean {
  return gap.message === PETITION_DETAIL_LANDLORD;
}

export function GapsNotice({ gaps }: { gaps: CompletionGap[] }) {
  const gateCount = gaps.filter((gap) => gap.kind === 'gate').length;
  const detailCount = gaps.filter(
    (gap) => gap.kind === 'detail' && !isTooLong(gap) && !isRefusedForm(gap)
  ).length;

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
