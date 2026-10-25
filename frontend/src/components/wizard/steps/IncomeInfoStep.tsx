/**
 * Income Info Step - Monthly income collection
 *
 * Trauma-informed design:
 * - Non-judgmental language about income sources
 * - Clear explanations of why each field is needed
 * - Real-time total calculation
 * - Plain language help text
 */

import { useState, useEffect, useMemo } from 'react';
import { FormField } from '../../common';
import { HouseholdList } from './HouseholdList';
import { amountError, decimalToNumber, parseAmount } from '../../../utils/parseAmount';
import { newHouseholdMember } from '../../../utils/householdRows';
import { MAX_AGE, MAX_HOUSEHOLD_ROWS } from '../../../constants/household';
import {
  LINE_1_QUESTION,
  LIVING_SEPARATELY_DECLARATION,
  MARRIAGE_ANSWER_WORDS,
  MARRIED_NOT_FILING,
} from '../../../constants/formText';
import {
  AGE_OUT_OF_RANGE,
  NOT_ANSWERED_YET,
  SPOUSE_FILING_INFO,
  SPOUSE_INCOME_HELP,
} from '../../../constants/copy';
import { INCOME_FIELDS } from '../../../types/api';
import type {
  HouseholdMember,
  IncomeInfo,
  MaritalStatus,
  SpouseIncome,
  WizardRow,
} from '../../../types/api';

interface IncomeInfoStepProps {
  initialData?: Partial<IncomeInfo>;
  onDataChange: (data: Partial<IncomeInfo>) => void;
  onValidationChange: (isValid: boolean) => void;
  /** The wizard's household rows. The step keeps no copy, so an id a save writes stays there. */
  householdRows: WizardRow<HouseholdMember>[];
  onHouseholdRowsChange: (rows: WizardRow<HouseholdMember>[]) => void;
  /** The filer said no one else lives with them or depends on them */
  noOneElse: boolean;
  onNoOneElseChange: (pressed: boolean) => void;
  initialSpouseIncome?: SpouseIncome;
  onSpouseIncomeChange: (data: SpouseIncome) => void;
}

type IncomeSource = (typeof INCOME_FIELDS)[number];

/** One amount box: the filer's, and the spouse's under the same words */
interface IncomeBox {
  field: IncomeSource;
  label: string;
  helpText?: string;
}

// The ten boxes, by section and by row as the step shows them. A row of two shares a line.
const INCOME_SECTIONS: { title: string; description: string; rows: IncomeBox[][] }[] = [
  {
    title: 'Employment Income',
    description: 'Include income from all jobs, before taxes and deductions.',
    rows: [
      [
        {
          field: 'monthly_gross_wages',
          label: 'Monthly Wages/Salary',
          helpText: 'Regular wages before taxes',
        },
      ],
      [
        {
          field: 'monthly_overtime',
          label: 'Monthly Overtime',
          helpText: 'Average monthly overtime pay',
        },
        {
          field: 'monthly_tips',
          label: 'Monthly Tips',
          helpText: 'Average monthly tips and bonuses',
        },
      ],
    ],
  },
  {
    title: 'Government Benefits',
    description: 'Include Social Security, unemployment, and other government assistance.',
    rows: [
      [
        {
          field: 'monthly_social_security',
          label: 'Social Security',
          helpText: 'SSI, SSDI, or retirement benefits',
        },
        { field: 'monthly_unemployment', label: 'Unemployment Benefits' },
      ],
    ],
  },
  {
    title: 'Other Income',
    description: 'Include rental income, pensions, child support, alimony, and other sources.',
    rows: [
      [
        { field: 'monthly_pension', label: 'Pension/Retirement' },
        { field: 'monthly_rental_income', label: "Rental income after the property's costs" },
      ],
      [
        {
          field: 'monthly_child_support',
          label: 'Child Support Received',
          helpText: 'Child support you receive',
        },
        {
          field: 'monthly_alimony',
          label: 'Alimony Received',
          helpText: 'Alimony/spousal support you receive',
        },
      ],
      [
        {
          field: 'monthly_other_income',
          label: 'Other Monthly Income',
          helpText: 'Any other regular monthly income',
        },
      ],
    ],
  },
];

// Line 1's first level. The third answer, "NOT filing with you", is the browser's own: it stores
// nothing until one of the two answers under it is picked.
type LineOnePick = 'not_married' | 'married_spouse_filing' | 'not_filing';

const SPOUSE_NOT_FILING: MaritalStatus[] = ['married_together', 'married_separately'];

function lineOnePick(answer: MaritalStatus | null | undefined): LineOnePick | null {
  if (!answer) return null;
  return SPOUSE_NOT_FILING.includes(answer) ? 'not_filing' : (answer as LineOnePick);
}

/** A month's total, in dollars and cents */
function formatTotal(total: number) {
  return `$${total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function IncomeInfoStep({
  initialData,
  onDataChange,
  onValidationChange,
  householdRows,
  onHouseholdRowsChange,
  noOneElse,
  onNoOneElseChange,
  initialSpouseIncome,
  onSpouseIncomeChange,
}: IncomeInfoStepProps) {
  // Fields start undefined (empty) rather than 0 so an untouched field reads
  // blank, while a deliberately entered 0 is preserved by parseAmount + `?? ''`.
  const [formData, setFormData] = useState<Partial<IncomeInfo>>(initialData || {});
  const [spouseData, setSpouseData] = useState<SpouseIncome>(initialSpouseIncome || {});
  const [pick, setPick] = useState(() => lineOnePick(initialData?.marital_status));
  // The spouse row this visit added, whose "Lives with you?" follows the marriage answer until
  // the filer answers it. A loaded row is never followed: its answer is the filer's (U:308).
  const [followedKey, setFollowedKey] = useState<string | null>(null);

  const livingTogether = formData.marital_status === 'married_together';

  // Calculate total monthly income
  const totalMonthlyIncome = INCOME_FIELDS.reduce((sum, field) => sum + (formData[field] || 0), 0);
  const spouseTotal = INCOME_FIELDS.reduce((sum, field) => sum + (spouseData[field] || 0), 0);

  // A filer who saved income before it was stored by source has only the old six-month total,
  // read-only. It counts toward nothing, so the step asks them to split it until they enter an
  // amount in any box (forms step 2 §5.5).
  const savedMonths = Array.isArray(formData.monthly_income) ? formData.monthly_income : [];
  const savedTotal = savedMonths.length
    ? savedMonths.reduce((sum, month) => sum + (decimalToNumber(month) ?? 0), 0) /
      savedMonths.length
    : 0;
  const asksToSplit = savedTotal > 0 && INCOME_FIELDS.every((field) => formData[field] == null);

  // An age the server can't store, by the row's position. An unanswered age is never an error.
  const ageErrors = useMemo(() => {
    const found: Record<number, string> = {};
    householdRows.forEach((row, index) => {
      const age = row.age;
      if (age != null && !(Number.isInteger(age) && age >= 0 && age <= MAX_AGE)) {
        found[index] = AGE_OUT_OF_RANGE;
      }
    });
    return found;
  }, [householdRows]);

  const errors = useMemo<Record<string, string>>(() => {
    const newErrors: Record<string, string> = {};

    // No "at least one source" gate: a blank box means none of that kind, and a filer
    // with no income types $0 in a box (O-1). The means test refuses all ten blank.

    // Each amount as the server stores it (amountError). Only the boxes: the total the step
    // last added up comes back in initialData, and no box shows it.
    for (const field of INCOME_FIELDS) {
      const message = amountError(formData[field] ?? undefined, 10);
      if (message) newErrors[field] = message;
    }

    // The spouse's boxes only while they show: a hidden section is neither sent nor checked
    if (livingTogether) {
      for (const field of INCOME_FIELDS) {
        const message = amountError(spouseData[field] ?? undefined, 10);
        if (message) newErrors[`spouse_${field}`] = message;
      }
    }

    for (const [index, message] of Object.entries(ageErrors)) newErrors[`age_${index}`] = message;

    return newErrors;
  }, [formData, spouseData, livingTogether, ageErrors]);

  // Update parent when form data changes
  useEffect(() => {
    const dataWithTotal = {
      ...formData,
      total_monthly_income: totalMonthlyIncome,
    };
    onDataChange(dataWithTotal);
    onSpouseIncomeChange(spouseData);
    onValidationChange(Object.keys(errors).length === 0);
    // onDataChange/onValidationChange are fresh closures each render; including
    // them would loop. Matches the suppression on the sibling step effects.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData, totalMonthlyIncome, spouseData, errors]);

  const handleChange = (field: keyof IncomeInfo, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: parseAmount(value) }));
  };

  const handleSpouseChange = (field: IncomeSource, value: string) => {
    setSpouseData((prev) => ({ ...prev, [field]: parseAmount(value) }));
  };

  // A change of the marriage answer. Picking "Living in the same household" adds the spouse's row,
  // living with the filer, when the list has none and room for one; only this pick adds it, never a
  // load or a render, so it never undoes a Remove.
  const handleMarriageAnswer = (answer: MaritalStatus | null) => {
    setFormData((prev) => ({ ...prev, marital_status: answer }));
    const hasSpouseRow = householdRows.some((row) => row.relationship === 'spouse');
    if (
      answer === 'married_together' &&
      !hasSpouseRow &&
      householdRows.length < MAX_HOUSEHOLD_ROWS
    ) {
      const spouseRow = newHouseholdMember({
        relationship: 'spouse',
        lives_with_you: true,
        spouse_is_dependent: null,
      });
      onHouseholdRowsChange([...householdRows, spouseRow]);
      setFollowedKey(spouseRow._key);
      onNoOneElseChange(false);
      return;
    }
    // The added row's "Lives with you?" rests on the marriage answer until the filer answers it
    const followed = householdRows.find((row) => row._key === followedKey);
    if (followed?.relationship === 'spouse') {
      const livesWithYou = answer === 'married_together' ? true : null;
      onHouseholdRowsChange(
        householdRows.map((row) =>
          row._key === followedKey ? { ...row, lives_with_you: livesWithYou } : row
        )
      );
    }
  };

  const handleLineOnePick = (next: LineOnePick) => {
    setPick(next);
    if (next !== 'not_filing') {
      handleMarriageAnswer(next);
      return;
    }
    // Keeps an answer already given under it; otherwise line 1 is half answered and stores null
    const current = formData.marital_status;
    if (!current || !SPOUSE_NOT_FILING.includes(current)) handleMarriageAnswer(null);
  };

  const amountBox = ({ field, label, helpText }: IncomeBox, spouse: boolean) => {
    const name = spouse ? `spouse_${field}` : field;
    return (
      <FormField
        key={name}
        label={spouse ? `Spouse's ${label}` : label}
        name={name}
        type="number"
        min="0"
        step="0.01"
        value={(spouse ? spouseData[field] : formData[field]) ?? ''}
        onChange={(e) =>
          spouse ? handleSpouseChange(field, e.target.value) : handleChange(field, e.target.value)
        }
        error={errors[name]}
        helpText={helpText}
        placeholder="0.00"
      />
    );
  };

  // Each row of boxes, a row of two sharing a line
  const amountRows = (rows: IncomeBox[][], spouse: boolean) =>
    rows.map((row) =>
      row.length === 1 ? (
        amountBox(row[0], spouse)
      ) : (
        <div key={row[0].field} className="form-row">
          {row.map((box) => amountBox(box, spouse))}
        </div>
      )
    );

  return (
    <div className="income-info-step">
      {/* Explainer */}
      <div className="info-box">
        <svg className="info-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
            clipRule="evenodd"
          />
        </svg>
        <div>
          <h3 className="info-title">Why we ask about income</h3>
          <p className="info-message">
            Income information helps determine which bankruptcy chapter you may qualify for. Enter
            your average monthly income before taxes. Leave a box blank if you don't get that kind
            of income. If you have no income at all, enter $0 in any box.
          </p>
        </div>
      </div>

      {/* A total saved before income was stored by source */}
      {asksToSplit && (
        <div className="info-box">
          <p className="info-message">
            You entered $
            {savedTotal.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}{' '}
            a month in total. Please split it by source.
          </p>
        </div>
      )}

      {/* General error */}
      {errors.general && (
        <div className="form-error" role="alert">
          {errors.general}
        </div>
      )}

      {/* Your marriage: Form 122A-1 line 1, in the form's words */}
      <section className="form-section">
        <h3 className="section-title">Your marriage</h3>
        <fieldset className="form-field fee-waiver-question">
          <legend className="form-label">{LINE_1_QUESTION}</legend>
          <label className="fee-waiver-checkbox">
            <input
              type="radio"
              name="marital_status"
              value="not_married"
              checked={pick === 'not_married'}
              onChange={() => handleLineOnePick('not_married')}
            />{' '}
            {MARRIAGE_ANSWER_WORDS.not_married}
          </label>
          <label className="fee-waiver-checkbox">
            <input
              type="radio"
              name="marital_status"
              value="married_spouse_filing"
              checked={pick === 'married_spouse_filing'}
              onChange={() => handleLineOnePick('married_spouse_filing')}
            />{' '}
            {MARRIAGE_ANSWER_WORDS.married_spouse_filing}
          </label>
          <label className="fee-waiver-checkbox">
            <input
              type="radio"
              name="marital_status"
              value="not_filing"
              checked={pick === 'not_filing'}
              onChange={() => handleLineOnePick('not_filing')}
            />{' '}
            {MARRIED_NOT_FILING}
          </label>

          {pick === 'not_filing' && (
            // The answer above is this question's words, so they name it without showing twice
            <fieldset className="form-field fee-waiver-question" aria-label={MARRIED_NOT_FILING}>
              <label className="fee-waiver-checkbox">
                <input
                  type="radio"
                  name="spouse_household"
                  value="married_together"
                  checked={formData.marital_status === 'married_together'}
                  onChange={() => handleMarriageAnswer('married_together')}
                />{' '}
                {MARRIAGE_ANSWER_WORDS.married_together}
              </label>
              <label className="fee-waiver-checkbox">
                <input
                  type="radio"
                  name="spouse_household"
                  value="married_separately"
                  checked={formData.marital_status === 'married_separately'}
                  onChange={() => handleMarriageAnswer('married_separately')}
                  aria-describedby="living-separately-declaration"
                />{' '}
                {MARRIAGE_ANSWER_WORDS.married_separately}
              </label>
              <p id="living-separately-declaration" className="form-help-text">
                {LIVING_SEPARATELY_DECLARATION}
              </p>
              {!formData.marital_status && <p className="form-help-text">{NOT_ANSWERED_YET}</p>}
            </fieldset>
          )}
        </fieldset>

        {pick === 'married_spouse_filing' && (
          <div className="info-box">
            <p className="info-message">{SPOUSE_FILING_INFO}</p>
          </div>
        )}
      </section>

      <HouseholdList
        rows={householdRows}
        onRowsChange={onHouseholdRowsChange}
        noOneElse={noOneElse}
        onNoOneElseChange={onNoOneElseChange}
        ageErrors={ageErrors}
        followedKey={followedKey}
        onFollowedKeyChange={setFollowedKey}
      />

      {INCOME_SECTIONS.map((section) => (
        <section key={section.title} className="form-section">
          <h3 className="section-title">{section.title}</h3>
          <p className="section-description">{section.description}</p>
          {amountRows(section.rows, false)}
        </section>
      ))}

      {/* The spouse's ten, only for a spouse in the same household (122A-1 Column B) */}
      {livingTogether && (
        <section className="form-section">
          <h3 className="section-title">Your spouse's income</h3>
          <p className="section-description">{SPOUSE_INCOME_HELP}</p>
          {amountRows(
            INCOME_SECTIONS.flatMap((section) => section.rows),
            true
          )}
        </section>
      )}

      {/* Total Summary */}
      <section className="form-section form-section--summary">
        <dl className="income-total">
          <div>
            <dt className="total-label">Your income</dt>
            <dd className="total-amount">{formatTotal(totalMonthlyIncome)}</dd>
          </div>
          {livingTogether && (
            <div>
              <dt className="total-label">Your spouse's income</dt>
              <dd className="total-amount">{formatTotal(spouseTotal)}</dd>
            </div>
          )}
        </dl>
        <p className="total-help-text">
          This is your total monthly income before taxes and deductions.
        </p>
      </section>
    </div>
  );
}

export default IncomeInfoStep;
