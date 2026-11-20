import { FormSelect } from '../../components/common';
import { FORM_122A2_LINE_33D_TAXES } from '../../constants/formText';
import {
  MEANS_DEBT_GOES_ON,
  MEANS_DEBT_PAYMENT,
  MEANS_DEBT_PROPERTY,
  MEANS_DEBT_WAITS,
  MEANS_PAYMENT_CHANGES,
  MEANS_PAYMENTS_LEFT,
  MEANS_SIXTY_MONTH_TOTAL,
  MEANS_SIXTY_OR_MORE,
} from '../../constants/copy';
import type { MeansDebtAnswers, PaymentsLeft } from '../../types/api';
import { AmountBox } from './AmountBox';
import { dollars } from './money';
import { YesNoThenDetails } from '../../components/wizard/YesNoThenDetails';

/** One secured debt as the page asks about it: a filer's debt, or a spouse loan whose identity is given */
export type DebtItem = {
  /** What the page changes the debt by: a filer debt's ref, a spouse loan's browser key */
  key: string;
  ref: string;
  /** Every question's name starts with it (`means_debt_<pk>`, `means_spouse_debt_<id>`, ...) */
  prefix: string;
  heading: string;
  property: string;
  /** The Amounts Owed payment, shown for a filer's debt; null for a spouse loan */
  monthlyPayment: string | null;
  answers: MeansDebtAnswers;
};

interface DebtQuestionsProps {
  items: DebtItem[];
  /** Each debt's line by ref (9b, 13b, 13e or 33d), null while it waits */
  lines: Record<string, string | null>;
  onChange: (key: string, change: Partial<MeansDebtAnswers>) => void;
}

const COUNTS = Array.from({ length: 60 }, (_, count) => count);
const PAYMENT_OPTIONS = [
  ...COUNTS.map((count) => ({ value: String(count), label: String(count) })),
  { value: '60_or_more', label: MEANS_SIXTY_OR_MORE },
];

// A count goes as a number, "60 or more" as its own word, a blank option as no answer
const readCount = (value: string): PaymentsLeft | null =>
  value === '' ? null : value === '60_or_more' ? '60_or_more' : Number(value);

// split/join, not replace: replace reads $& in a name as a pattern
const fill = (sentence: string, values: Record<string, string>) =>
  Object.entries(values).reduce(
    (text, [key, value]) => text.split(`{${key}}`).join(value),
    sentence
  );

/** Each secured debt's own questions: payments left, a changing payment, and taxes on line 33d */
export function DebtQuestions({ items, lines, onChange }: DebtQuestionsProps) {
  return (
    <>
      {items.map((item) => {
        const line = lines[item.ref] ?? null;
        const { answers, prefix } = item;
        const headingId = `${prefix}_heading`;
        return (
          <section key={item.key} className="means-line" aria-labelledby={headingId}>
            <h2 id={headingId}>{item.heading}</h2>
            {item.property !== '' && (
              <p className="form-help-text">
                {fill(MEANS_DEBT_PROPERTY, { property: item.property })}
              </p>
            )}
            <p className="form-help-text">
              {line === null ? MEANS_DEBT_WAITS : fill(MEANS_DEBT_GOES_ON, { line })}
            </p>
            {item.monthlyPayment !== null && (
              <p className="form-help-text">
                {fill(MEANS_DEBT_PAYMENT, { amount: dollars(item.monthlyPayment) })}
              </p>
            )}
            <FormSelect
              label={MEANS_PAYMENTS_LEFT}
              name={`${prefix}_payments_left`}
              placeholder=""
              required
              value={answers.payments_left === null ? '' : String(answers.payments_left)}
              options={PAYMENT_OPTIONS}
              onChange={(value) => onChange(item.key, { payments_left: readCount(value) })}
            />
            <YesNoThenDetails
              question={MEANS_PAYMENT_CHANGES}
              name={`${prefix}_changes`}
              value={answers.payment_changes}
              onChange={(next) => onChange(item.key, { payment_changes: next })}
            />
            {answers.payment_changes === 'yes' && (
              <AmountBox
                name={`${prefix}_total`}
                label={MEANS_SIXTY_MONTH_TOTAL}
                value={answers.total_60_months}
                onChange={(value) => onChange(item.key, { total_60_months: value })}
              />
            )}
            {line === '33d' && (
              <YesNoThenDetails
                question={FORM_122A2_LINE_33D_TAXES}
                name={`${prefix}_taxes`}
                value={answers.taxes_or_insurance}
                onChange={(next) => onChange(item.key, { taxes_or_insurance: next })}
              />
            )}
          </section>
        );
      })}
    </>
  );
}
