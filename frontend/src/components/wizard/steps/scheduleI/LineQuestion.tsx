/**
 * One of Schedule I's or Schedule J's yes/no lines (4c spec §6.2): the question, No then Yes with
 * nothing checked, and its boxes under the Yes. What was typed stays stored under a No, hidden
 * behind one line that offers Show and Delete (4c-R6); Show keeps the boxes open for the visit, so
 * clearing the last one never unmounts them. Each control's name is its ScheduleIAnswers key
 * (PF-4c-J).
 */
import { useState } from 'react';
import { FormField, FormTextarea } from '../../../common';
import { YesNoThenDetails } from '../../YesNoThenDetails';
import { HIDDEN_ANSWERS } from '../../../../constants/copy';
import { SCHEDULE_I_TEXT_LIMITS } from '../../../../constants/scheduleILimits';
import type { ScheduleIAnswers, ScheduleITextKey } from '../../../../types/api';
import { HiddenLine } from '../petition/PetitionQuestions';

/** One box under the Yes */
export interface LineBox {
  key: ScheduleITextKey | 'line_11_amount';
  label: string;
  /** A dollar figure, held as typed (4c-R7) */
  amount?: boolean;
  /** A text of several lines */
  long?: boolean;
  /** Why the box is held: it then stays shown, so nothing holds the step out of sight */
  error?: string;
}

interface LineQuestionProps {
  question: string;
  /** Help under the question; several strings are several paragraphs */
  note?: string | readonly string[];
  name: 'line_11_answer' | 'line_13_answer' | 'schedule_j_line_24_answer';
  answers: ScheduleIAnswers;
  onChange: (next: ScheduleIAnswers) => void;
  boxes: LineBox[];
}

export function LineQuestion({
  question,
  note,
  name,
  answers,
  onChange,
  boxes,
}: LineQuestionProps) {
  const [shown, setShown] = useState(false);
  const set = (changes: ScheduleIAnswers) => onChange({ ...answers, ...changes });
  const value = answers[name];
  const answer = value === 'yes' || value === 'no' ? value : null;
  const kept = boxes.some((box) => (answers[box.key] ?? '').trim() !== '');
  const open = answer === 'yes' || shown || boxes.some((box) => box.error);

  const field = (box: LineBox) => {
    const common = {
      label: box.label,
      name: box.key,
      value: answers[box.key] ?? '',
      error: box.error,
    };
    if (box.amount) {
      // Text, not a number box: the step judges exactly what was typed (PF-4c-C)
      return (
        <FormField
          key={box.key}
          {...common}
          type="text"
          inputMode="decimal"
          autoComplete="off"
          placeholder="0.00"
          onChange={(e) => set({ [box.key]: e.target.value })}
        />
      );
    }
    const maxLength = SCHEDULE_I_TEXT_LIMITS[box.key as ScheduleITextKey];
    return box.long ? (
      <FormTextarea
        key={box.key}
        {...common}
        maxLength={maxLength}
        rows={3}
        onChange={(e) => set({ [box.key]: e.target.value })}
      />
    ) : (
      <FormField
        key={box.key}
        {...common}
        type="text"
        maxLength={maxLength}
        onChange={(e) => set({ [box.key]: e.target.value })}
      />
    );
  };

  return (
    <YesNoThenDetails
      question={question}
      name={name}
      value={answer}
      onChange={(next) => set({ [name]: next })}
      note={note}
    >
      {open
        ? boxes.map(field)
        : answer === 'no' &&
          kept && (
            <HiddenLine
              sentence={HIDDEN_ANSWERS}
              onShow={() => setShown(true)}
              onDelete={() => set(Object.fromEntries(boxes.map((box) => [box.key, null])))}
            />
          )}
    </YesNoThenDetails>
  );
}
