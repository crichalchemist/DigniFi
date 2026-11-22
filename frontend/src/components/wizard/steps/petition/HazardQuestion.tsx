/**
 * Form 101 line 14 (forms step 4b spec §6.5), asked on the Assets step after Part 7's lines, in the
 * form's words: whether the filer owns property that poses a hazard or needs attention right away,
 * and under its Yes what the hazard is, why attention is needed and where the property is. Nothing
 * starts answered; what was typed stays stored under a No, hidden with a line that offers Show and
 * Delete (PF2-U1). The step's one status region names the gate (hazardGap, PF2-T9-6).
 */
import { useState } from 'react';
import type { FocusEvent } from 'react';
import { FormField } from '../../../common';
import { YesNoThenDetails } from '../../YesNoThenDetails';
import { HIDDEN_ANSWERS } from '../../../../constants/copy';
import {
  FORM_101_LINE_14,
  FORM_101_LINE_14_EXAMPLE,
  FORM_101_LINE_14_PROMPTS,
} from '../../../../constants/formText';
import { PETITION_TEXT_LIMITS } from '../../../../constants/petitionLimits';
import type { PetitionAnswers } from '../../../../types/api';
import { PartyAddressFields } from './PartyAddressFields';
import { HiddenLine } from './PetitionQuestions';

const HAZARD_TEXT_KEYS = [
  'hazard_what',
  'hazard_why',
  'hazard_street',
  'hazard_city',
  'hazard_state',
  'hazard_zip',
] as const;

interface HazardQuestionProps {
  answers: PetitionAnswers;
  onChange: (next: PetitionAnswers) => void;
  /** The step has seen the filer pass the block (PF2-T8-10): an unanswered gate says so */
  touched: boolean;
  /** Focus has left the block */
  onLeave: () => void;
}

export function HazardQuestion({ answers, onChange, touched, onLeave }: HazardQuestionProps) {
  const [shown, setShown] = useState(false);
  const set = (changes: Partial<PetitionAnswers>) => onChange({ ...answers, ...changes });
  const value = answers.hazard_answer;
  const answer = value === 'yes' || value === 'no' ? value : null;
  const kept = HAZARD_TEXT_KEYS.some((key) => (answers[key] ?? '').trim() !== '');

  const leave = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) onLeave();
  };

  const text = (key: 'hazard_what' | 'hazard_why', label: string) => (
    <FormField
      label={label}
      name={key}
      type="text"
      maxLength={PETITION_TEXT_LIMITS[key]}
      value={answers[key] ?? ''}
      onChange={(e) => set({ [key]: e.target.value })}
    />
  );

  return (
    <div className="petition-questions" onBlur={leave}>
      <YesNoThenDetails
        question={FORM_101_LINE_14}
        name="hazard_answer"
        value={answer}
        onChange={(next) => set({ hazard_answer: next })}
        note={FORM_101_LINE_14_EXAMPLE}
        unanswered={touched && answer === null}
      >
        {answer === 'yes' || shown ? (
          <>
            {text('hazard_what', FORM_101_LINE_14_PROMPTS.what)}
            {text('hazard_why', FORM_101_LINE_14_PROMPTS.why)}
            <p className="form-label">{FORM_101_LINE_14_PROMPTS.where}</p>
            <PartyAddressFields
              answers={answers}
              onChange={set}
              streetKey="hazard_street"
              cityKey="hazard_city"
              stateKey="hazard_state"
              zipKey="hazard_zip"
            />
          </>
        ) : (
          answer === 'no' &&
          kept && (
            <HiddenLine
              sentence={HIDDEN_ANSWERS}
              onShow={() => setShown(true)}
              onDelete={() => set(Object.fromEntries(HAZARD_TEXT_KEYS.map((key) => [key, null])))}
            />
          )
        )}
      </YesNoThenDetails>
    </div>
  );
}
