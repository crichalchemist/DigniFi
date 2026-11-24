/**
 * Form 101 line 16 and Form 122A-1Supp's two military questions (forms step 4 spec §6.6, 4d),
 * asked on Amounts Owed in the forms' words: what kind of debts the filer has, as one choice, and
 * under consumer debts the Supp's line 2 (disabled veteran) and line 3 (Reservist or National
 * Guard) with their follow-ups, each where the Supp reaches it (R-D2). Beside the question, the
 * step's amounts owed by the kind chosen for each, with no sum, count or comparison (4d-R16).
 * Information, never advice: nothing here says which kind the debts are. An answer a changed
 * answer hides stays stored behind one line that offers Show and Delete (4d-R15). The gates are
 * line 16, line 2 and line 3 (debtNatureGap); the step's one status region names them.
 */
import { useState } from 'react';
import type { FocusEvent, ReactNode } from 'react';
import { FormField } from '../../../common';
import { WhatDoesThisMean } from '../../WhatDoesThisMean';
import { YesNoThenDetails } from '../../YesNoThenDetails';
import { REQUIRED_MARK } from '../assets/AssetRowFields';
import { claimRowName } from '../claims/claimNames';
import { formatFigure } from '../claims/linkedPayments';
import { DEBT_TYPE_WORDS } from '../../../../constants/claims';
import {
  DEBT_NATURE_KIND_NOT_CHOSEN,
  DEBT_NATURE_LIST_EMPTY,
  DEBT_NATURE_LIST_HEADING,
  DEBT_NATURE_LIST_NOTE,
  DUTY_CATEGORY_NONE,
  HIDDEN_ANSWERS,
  MILITARY_540_DAYS,
  MILITARY_FRAMING,
  NAMELESS_DEBT,
  NOT_ANSWERED_YET,
  WHAT_DOES_DISABLED_VETERAN_MEAN,
  WHAT_DOES_HOMELAND_DEFENSE_MEAN,
} from '../../../../constants/copy';
import {
  FORM_101_LINE_16,
  FORM_101_LINE_16A,
  FORM_101_LINE_16B,
  FORM_101_LINE_16C,
  FORM_122A1SUPP_CATEGORIES,
  FORM_122A1SUPP_CATEGORIES_LEAD,
  FORM_122A1SUPP_LINE_2,
  FORM_122A1SUPP_LINE_2_FOLLOW_UP,
  FORM_122A1SUPP_LINE_3,
  FORM_122A1SUPP_LINE_3_FOLLOW_UP,
  STATUTE_DISABLED_VETERAN,
  STATUTE_DISABLED_VETERAN_CITATION,
  STATUTE_HOMELAND_DEFENSE,
  STATUTE_HOMELAND_DEFENSE_CITATION,
} from '../../../../constants/formText';
import { PETITION_TEXT_LIMITS } from '../../../../constants/petitionLimits';
import type { DebtRow, PetitionAnswers, YesNo } from '../../../../types/api';
import { debtsByKind } from './debtNatureList';
import { mmDdYyyy } from './masks';
import { HiddenLine } from './PetitionQuestions';
import { anyAnswerIn, DEBT_NATURE_CHOICES, supplementLineThreeReached } from './petitionGaps';

interface DebtNatureQuestionProps {
  answers: PetitionAnswers;
  onChange: (next: PetitionAnswers) => void;
  /** The step's amounts owed, listed by kind beside the question (4d-R16) */
  rows: DebtRow[];
  /** The step has seen the filer pass the block (PF2-T8-10): an unanswered gate says so */
  touched: boolean;
  /** Focus has left the block */
  onLeave: () => void;
}

type DebtNature = (typeof DEBT_NATURE_CHOICES)[number];
type Category = '1' | '2' | '3' | '4';

const NATURE_WORDS: Record<DebtNature, string> = {
  consumer: FORM_101_LINE_16A,
  business: FORM_101_LINE_16B,
  neither: FORM_101_LINE_16C,
};
const CATEGORIES = Object.keys(FORM_122A1SUPP_CATEGORIES) as Category[];

// The keys each hidden block keeps, which its Delete clears
const MILITARY_KEYS = [
  'disabled_veteran',
  'debts_on_duty',
  'reservist',
  'called_to_duty',
  'duty_category',
  'duty_released_on',
  'duty_ended_on',
] as const;
const LINE_3_KEYS = MILITARY_KEYS.slice(2);
const CALLED_KEYS = MILITARY_KEYS.slice(3);
const CATEGORY_KEYS = MILITARY_KEYS.slice(4);

// The date each category asks, as the Supp prints it under categories 2 and 4
const DATE_OF: Partial<Record<Category, 'duty_released_on' | 'duty_ended_on'>> = {
  2: 'duty_released_on',
  4: 'duty_ended_on',
};

/** The blocks each answer gates: a new answer hides what Show opened in these again */
const GATE_BLOCKS: Partial<Record<keyof PetitionAnswers, string[]>> = {
  debt_nature: ['debt_nature_text', 'military'],
  disabled_veteran: ['debts_on_duty', 'line_3'],
  debts_on_duty: ['line_3'],
  reservist: ['called_to_duty'],
  called_to_duty: ['categories'],
  duty_category: ['duty_released_on', 'duty_ended_on'],
};

/** The blocks shown inside each block, so a hidden block hides what Show opened inside it too */
const NESTED_BLOCKS: Record<string, string[]> = {
  military: ['debts_on_duty', 'line_3'],
  line_3: ['called_to_duty'],
  called_to_duty: ['categories'],
  categories: ['duty_released_on', 'duty_ended_on'],
};

/** The blocks an answer gates, and every block nested inside them */
const blocksUnder = (blocks: string[]): string[] =>
  blocks.flatMap((block) => [block, ...blocksUnder(NESTED_BLOCKS[block] ?? [])]);

const yesNo = (value: unknown): YesNo | null => (value === 'yes' || value === 'no' ? value : null);
const nullAll = (keys: readonly (keyof PetitionAnswers)[]) =>
  Object.fromEntries(keys.map((key) => [key, null])) as Partial<PetitionAnswers>;

export function DebtNatureQuestion({
  answers,
  onChange,
  rows,
  touched,
  onLeave,
}: DebtNatureQuestionProps) {
  // Hidden answers the filer asked to see again, by block
  const [shown, setShown] = useState<Record<string, boolean>>({});
  const set = (changes: Partial<PetitionAnswers>) => onChange({ ...answers, ...changes });
  const show = (block: string) => setShown((current) => ({ ...current, [block]: true }));
  const answer = (key: keyof PetitionAnswers, value: PetitionAnswers[keyof PetitionAnswers]) => {
    setShown((current) => ({
      ...current,
      ...Object.fromEntries(blocksUnder(GATE_BLOCKS[key] ?? []).map((block) => [block, false])),
    }));
    set({ [key]: value });
  };
  const leave = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) onLeave();
  };

  const nature = answers.debt_nature ?? null;
  const consumer = nature === 'consumer';
  // Inside the military block the Supp's own routing decides what shows, also while Show has it
  // open under another line 16 answer
  const asConsumer: PetitionAnswers = { ...answers, debt_nature: 'consumer' };
  const veteran = yesNo(answers.disabled_veteran);
  const onDuty = yesNo(answers.debts_on_duty);
  const reservist = yesNo(answers.reservist);
  const called = yesNo(answers.called_to_duty);
  const category = answers.duty_category ?? null;
  const lineThreeReached = supplementLineThreeReached(asConsumer);

  const hidden = (keys: readonly (keyof PetitionAnswers)[], block: string): ReactNode =>
    anyAnswerIn(answers, keys) && (
      <HiddenLine
        sentence={HIDDEN_ANSWERS}
        onShow={() => show(block)}
        onDelete={() => set(nullAll(keys))}
      />
    );

  // Both follow-ups name "homeland defense activity", so each carries the definition (T8-R2)
  const homeland = (
    <WhatDoesThisMean
      label={WHAT_DOES_HOMELAND_DEFENSE_MEAN}
      citation={STATUTE_HOMELAND_DEFENSE_CITATION}
    >
      {STATUTE_HOMELAND_DEFENSE}
    </WhatDoesThisMean>
  );

  const dateBox = (date: 'duty_released_on' | 'duty_ended_on', words: string) => (
    <FormField
      label={words}
      // The category's radio reads the same words; the box adds the question above it after
      // them, so the two are told apart and the name starts with the visible label (T8-R1)
      aria-label={`${words} ${FORM_122A1SUPP_LINE_3_FOLLOW_UP}`}
      name={date}
      type="text"
      inputMode="numeric"
      value={answers[date] ?? ''}
      onChange={(e) => set({ [date]: mmDdYyyy(e.target.value) })}
    />
  );

  const categories = (
    <>
      <fieldset className="form-field">
        <legend className="form-label">{FORM_122A1SUPP_CATEGORIES_LEAD}</legend>
        {CATEGORIES.map((choice) => {
          const date = DATE_OF[choice];
          return (
            <div key={choice}>
              <label className="ab-choice">
                <input
                  type="radio"
                  name="duty_category"
                  value={choice}
                  checked={category === choice}
                  onChange={() => answer('duty_category', choice)}
                />
                {FORM_122A1SUPP_CATEGORIES[choice]}
              </label>
              {date &&
                (category === choice || shown[date]
                  ? dateBox(date, FORM_122A1SUPP_CATEGORIES[choice])
                  : category !== null && hidden([date], date))}
            </div>
          );
        })}
        <label className="ab-choice">
          <input
            type="radio"
            name="duty_category"
            value="none"
            checked={category === 'none'}
            onChange={() => answer('duty_category', 'none')}
          />
          {DUTY_CATEGORY_NONE}
        </label>
      </fieldset>
      <p className="form-help-text">{MILITARY_540_DAYS}</p>
    </>
  );

  const lineThree = (
    <YesNoThenDetails
      question={FORM_122A1SUPP_LINE_3}
      name="reservist"
      value={reservist}
      onChange={(next) => answer('reservist', next)}
      // Required only where the Supp reaches line 3, as Continue holds it: Show under line 2 Yes
      // and Yes opens it with no mark
      unanswered={consumer && lineThreeReached && touched && reservist === null}
      required={consumer && lineThreeReached}
    >
      {reservist === 'yes' || shown.called_to_duty ? (
        <YesNoThenDetails
          question={FORM_122A1SUPP_LINE_3_FOLLOW_UP}
          name="called_to_duty"
          value={called}
          onChange={(next) => answer('called_to_duty', next)}
          required={false}
        >
          {homeland}
          {called === 'yes' || shown.categories
            ? categories
            : called === 'no' && hidden(CATEGORY_KEYS, 'categories')}
        </YesNoThenDetails>
      ) : (
        reservist === 'no' && hidden(CALLED_KEYS, 'called_to_duty')
      )}
    </YesNoThenDetails>
  );

  const military = (
    <div className="petition-questions">
      <p className="form-help-text">{MILITARY_FRAMING}</p>
      <YesNoThenDetails
        question={FORM_122A1SUPP_LINE_2}
        name="disabled_veteran"
        value={veteran}
        onChange={(next) => answer('disabled_veteran', next)}
        unanswered={consumer && touched && veteran === null}
        required={consumer}
      >
        <WhatDoesThisMean
          label={WHAT_DOES_DISABLED_VETERAN_MEAN}
          citation={STATUTE_DISABLED_VETERAN_CITATION}
        >
          {STATUTE_DISABLED_VETERAN}
        </WhatDoesThisMean>
        {veteran === 'yes' || shown.debts_on_duty ? (
          <YesNoThenDetails
            question={FORM_122A1SUPP_LINE_2_FOLLOW_UP}
            name="debts_on_duty"
            value={onDuty}
            onChange={(next) => answer('debts_on_duty', next)}
            required={false}
          >
            {homeland}
          </YesNoThenDetails>
        ) : (
          veteran === 'no' && hidden(['debts_on_duty'], 'debts_on_duty')
        )}
      </YesNoThenDetails>
      {lineThreeReached || shown.line_3 ? lineThree : hidden(LINE_3_KEYS, 'line_3')}
    </div>
  );

  const groups = debtsByKind(rows);

  return (
    <div className="petition-questions" onBlur={leave}>
      <fieldset className="form-field fee-waiver-question">
        <legend className="form-label">
          {FORM_101_LINE_16}
          {REQUIRED_MARK}
        </legend>
        {DEBT_NATURE_CHOICES.map((choice) => (
          <label key={choice} className="ab-choice">
            <input
              type="radio"
              name="debt_nature"
              value={choice}
              aria-required
              checked={nature === choice}
              onChange={() => answer('debt_nature', choice)}
            />
            {NATURE_WORDS[choice]}
          </label>
        ))}
        {touched && nature === null && <p className="form-help-text">{NOT_ANSWERED_YET}</p>}
        {nature === 'neither' || shown.debt_nature_text ? (
          <FormField
            label={FORM_101_LINE_16C}
            // The radio above reads the choice's words alone; the box adds the line's question
            // after them, so the two are told apart and the name starts with the visible label
            // (T8-R1)
            aria-label={`${FORM_101_LINE_16C} ${FORM_101_LINE_16}`}
            name="debt_nature_text"
            type="text"
            maxLength={PETITION_TEXT_LIMITS.debt_nature_text}
            value={answers.debt_nature_text ?? ''}
            onChange={(e) => set({ debt_nature_text: e.target.value })}
          />
        ) : (
          nature !== null && hidden(['debt_nature_text'], 'debt_nature_text')
        )}
      </fieldset>

      {/* DRAFT: counsel C-39 */}
      <section className="form-field debt-nature-list" aria-labelledby="debt-nature-list-heading">
        <h3 id="debt-nature-list-heading" className="section-title">
          {DEBT_NATURE_LIST_HEADING}
        </h3>
        <p className="form-help-text">{DEBT_NATURE_LIST_NOTE}</p>
        {groups.length === 0 ? (
          <p className="form-help-text">{DEBT_NATURE_LIST_EMPTY}</p>
        ) : (
          groups.map((group) => (
            <div key={group.kind ?? 'none'}>
              <h4 className="section-title">
                {group.kind === null ? DEBT_NATURE_KIND_NOT_CHOSEN : DEBT_TYPE_WORDS[group.kind]}
              </h4>
              <ul>
                {group.rows.map((row) => (
                  <li key={row._key}>
                    {claimRowName(row.creditor_name, NAMELESS_DEBT)}
                    {/* A stored 0 is an amount not given yet (B29, T8-R3), so it shows no figure */}
                    {typeof row.amount_owed === 'number' &&
                      row.amount_owed !== 0 &&
                      `: ${formatFigure(row.amount_owed)}`}
                  </li>
                ))}
              </ul>
            </div>
          ))
        )}
      </section>

      {consumer || shown.military ? military : nature !== null && hidden(MILITARY_KEYS, 'military')}
    </div>
  );
}
