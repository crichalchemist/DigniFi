/**
 * Schedule I line 1 for one column (4c spec §6.2): the employment status, then the occupation,
 * and under Employed the employer's name and address and how long, in the form's words, the
 * address in the labels the other address blocks use. Nothing starts answered. What the answer
 * hides stays stored, behind one line that offers Show and Delete (4c-R6), and Show keeps the
 * boxes open for the visit. The spouse's block carries the `spouse_` keys and its own column words,
 * and never the pay stub's hint, which is read from one stub of unknown owner (D7). Each control's
 * name is its ScheduleIAnswers key (PF-4c-J).
 */
import { useState } from 'react';
import { FormField, FormSelect } from '../../../common';
import {
  AB_ADDRESS_LINE_2_LABEL,
  HIDDEN_ANSWERS,
  PAYSTUB_EMPLOYER_HINT,
  SCHEDULE_I_ONE_EMPLOYER,
} from '../../../../constants/copy';
import {
  AB_CITY_LABEL,
  AB_STATE_LABEL,
  AB_ZIP_LABEL,
  CLAIM_STREET_LABEL,
  FORM_106I_COLUMN_SPOUSE,
  FORM_106I_COLUMN_YOU,
  FORM_106I_EMPLOYED,
  FORM_106I_EMPLOYER_ADDRESS,
  FORM_106I_EMPLOYER_NAME,
  FORM_106I_EMPLOYMENT_STATUS,
  FORM_106I_HOW_LONG,
  FORM_106I_LINE_1_NOTES,
  FORM_106I_NOT_EMPLOYED,
  FORM_106I_OCCUPATION,
} from '../../../../constants/formText';
import { SCHEDULE_I_TEXT_LIMITS } from '../../../../constants/scheduleILimits';
import type { EmploymentStatus, ScheduleIAnswers, ScheduleITextKey } from '../../../../types/api';
import { zipDigits } from '../petition/masks';
import { HiddenLine } from '../petition/PetitionQuestions';
import { US_STATES_AND_TERRITORIES } from '../petition/usStates';

// What Employed asks beyond the occupation, and Delete under Not employed clears (4c-R6)
const EMPLOYER_KEYS = [
  'employer_name',
  'employer_street',
  'employer_street_2',
  'employer_city',
  'employer_state',
  'employer_zip',
  'time_employed',
] as const;
type EmployerKey = (typeof EMPLOYER_KEYS)[number];

const STATUS_WORDS: [EmploymentStatus, string][] = [
  ['employed', FORM_106I_EMPLOYED],
  ['not_employed', FORM_106I_NOT_EMPLOYED],
];

interface EmploymentBlockProps {
  answers: ScheduleIAnswers;
  onChange: (next: ScheduleIAnswers) => void;
  /** The spouse's column: the `spouse_` keys, and no hint */
  spouse: boolean;
  /** The employer's name a pay stub gave, or "" (4c-R10) */
  payStubName?: string;
}

export function EmploymentBlock({ answers, onChange, spouse, payStubName }: EmploymentBlockProps) {
  const [shown, setShown] = useState(false);
  const prefix = spouse ? 'spouse_' : '';
  const keyOf = (key: 'occupation' | EmployerKey) => `${prefix}${key}` as ScheduleITextKey;
  const set = (changes: ScheduleIAnswers) => onChange({ ...answers, ...changes });
  const blank = (key: ScheduleITextKey) => (answers[key] ?? '').trim() === '';

  const statusKey = spouse ? 'spouse_employment_status' : 'employment_status';
  const status = answers[statusKey] ?? null;
  const employerKeys = EMPLOYER_KEYS.map((key) => keyOf(key));
  const occupationKey = keyOf('occupation');
  // What Delete clears: under no answer the occupation too, since nothing asks it yet
  const hiddenKeys: ScheduleITextKey[] =
    status === null ? [occupationKey, ...employerKeys] : status === 'employed' ? [] : employerKeys;
  const occupationShown = status !== null || shown;
  const employerShown = status === 'employed' || shown;
  const hidden = !shown && hiddenKeys.some((key) => !blank(key));

  const text = (key: ScheduleITextKey, label: string, helpText?: string) => (
    <FormField
      label={label}
      name={key}
      type="text"
      maxLength={SCHEDULE_I_TEXT_LIMITS[key]}
      value={answers[key] ?? ''}
      helpText={helpText}
      onChange={(e) => set({ [key]: e.target.value })}
    />
  );

  const stateKey = keyOf('employer_state');
  const zipKey = keyOf('employer_zip');
  // Only your own block, only under Employed, and only when a stub gave a name (4c-R10, D7). A
  // function replacer, so a "$" the scan read prints as read, never as a replacement pattern
  const stubName = (payStubName ?? '').trim();
  const hint =
    !spouse && status === 'employed' && stubName !== ''
      ? PAYSTUB_EMPLOYER_HINT.replace('{name}', () => stubName)
      : undefined;

  return (
    <fieldset className="form-section">
      <legend className="section-title">
        {spouse ? FORM_106I_COLUMN_SPOUSE : FORM_106I_COLUMN_YOU}
      </legend>
      <fieldset className="form-field fee-waiver-question">
        <legend className="form-label">{FORM_106I_EMPLOYMENT_STATUS}</legend>
        <p className="form-help-text">{FORM_106I_LINE_1_NOTES[1]}</p>
        <div className="ab-yes-no">
          {STATUS_WORDS.map(([choice, words]) => (
            <label key={choice} className="ab-choice ab-answer">
              <input
                type="radio"
                name={statusKey}
                value={choice}
                checked={status === choice}
                onChange={() => set({ [statusKey]: choice })}
              />
              {words}
            </label>
          ))}
        </div>
      </fieldset>
      {occupationShown && text(occupationKey, FORM_106I_OCCUPATION)}
      {employerShown && (
        <>
          {text(keyOf('employer_name'), FORM_106I_EMPLOYER_NAME, hint)}
          <fieldset className="form-field">
            <legend className="form-label">{FORM_106I_EMPLOYER_ADDRESS}</legend>
            <div className="address-fields">
              {text(keyOf('employer_street'), CLAIM_STREET_LABEL)}
              {text(keyOf('employer_street_2'), AB_ADDRESS_LINE_2_LABEL)}
              {text(keyOf('employer_city'), AB_CITY_LABEL)}
              <div className="form-row">
                <FormSelect
                  label={AB_STATE_LABEL}
                  name={stateKey}
                  options={US_STATES_AND_TERRITORIES}
                  value={answers[stateKey] ?? ''}
                  onChange={(value) => set({ [stateKey]: value || null })}
                />
                {/* Digits only, applied before any length limit, so no native maxLength (PF2-4) */}
                <FormField
                  label={AB_ZIP_LABEL}
                  name={zipKey}
                  type="text"
                  inputMode="numeric"
                  autoComplete="off"
                  value={answers[zipKey] ?? ''}
                  onChange={(e) => set({ [zipKey]: zipDigits(e.target.value) })}
                />
              </div>
            </div>
          </fieldset>
          {text(keyOf('time_employed'), FORM_106I_HOW_LONG)}
          <p className="form-help-text">{FORM_106I_LINE_1_NOTES[0]}</p>
          <p className="form-help-text">{SCHEDULE_I_ONE_EMPLOYER}</p>
        </>
      )}
      {hidden && (
        <HiddenLine
          sentence={HIDDEN_ANSWERS}
          onShow={() => setShown(true)}
          onDelete={() => set(Object.fromEntries(hiddenKeys.map((key) => [key, null])))}
        />
      )}
    </fieldset>
  );
}
