/**
 * Step 1's Form 101 questions (forms step 4b spec §6.1), after the county block, in the form's
 * words and its order: 1a the suffix, 1b other names, 1c the ITIN, 1d another Social Security
 * number, 1e the EIN, 1f the mailing address, 1g why this district, 1h earlier cases, 1i pending
 * cases, 1j a sole proprietorship. Every yes/no starts unanswered, No before Yes; its details show
 * only under its Yes, and what was typed stays stored under a No, hidden with a line that offers
 * Show and Delete (spec §5.3). Each control's name is its PetitionAnswers key, a row cell's
 * `<list>_<i>_<cell>` (PF2-T8-5). Continue waits only for the gates (petitionGaps.ts).
 */
import { useState } from 'react';
import type { FocusEvent, ReactNode } from 'react';
import { Button, FormField } from '../../../common';
import { PublicRecordNotice } from '../../PublicRecordNotice';
import { YesNoThenDetails } from '../../YesNoThenDetails';
import {
  DELETE_HIDDEN,
  HIDDEN_ANSWERS,
  NOT_SAVED_TRY_AGAIN,
  HIDDEN_ROWS_MANY,
  HIDDEN_ROWS_ONE,
  ITIN_SAVED,
  LINE_12_FEEDS_107,
  OTHER_SSN_SAVED,
  PETITION_ADD_BUSINESS_NAME,
  PETITION_ADD_OTHER_NAME,
  PETITION_ADD_PENDING_CASE,
  PETITION_ADD_PRIOR_CASE,
  PETITION_ASKED_AS_ITIN,
  PETITION_ASKED_AS_MAILING,
  PETITION_ASKED_AS_OTHER_SSN,
  PETITION_BUSINESS_NAME_ROW,
  PETITION_DETAIL_ITIN_NINE,
  PETITION_OTHER_NAME_ROW,
  PETITION_PENDING_CASE_ROW,
  PETITION_PRIOR_CASE_ROW,
  PETITION_REMOVE_BUSINESS_NAME,
  PETITION_REMOVE_OTHER_NAME,
  PETITION_REMOVE_PENDING_CASE,
  PETITION_REMOVE_PRIOR_CASE,
  REPLACE_SAVED,
  SHOW_HIDDEN,
  VENUE_DIVISION_EASTERN,
  VENUE_DIVISION_WESTERN,
  WHY_ITIN,
  WHY_MAILING,
  WHY_OTHER_NAMES,
  WHY_OTHER_SSN,
} from '../../../../constants/copy';
import {
  FORM_101_BUSINESS_KINDS,
  FORM_101_DATE_FORMAT,
  FORM_101_LINE_10,
  FORM_101_LINE_10_CELLS,
  FORM_101_LINE_12,
  FORM_101_LINE_12_KIND,
  FORM_101_LINE_12_LOCATION,
  FORM_101_LINE_12_NAME,
  FORM_101_LINE_2,
  FORM_101_LINE_2_CELLS,
  FORM_101_LINE_2_INSTRUCTIONS,
  FORM_101_LINE_3_ITIN,
  FORM_101_LINE_4,
  FORM_101_LINE_5,
  FORM_101_LINE_6,
  FORM_101_LINE_9,
  FORM_101_LINE_9_CELLS,
  FORM_101_SUFFIX,
  FORM_101_VENUE_CHOICES,
  FORM_121_LINE_2_OTHER_SSN,
} from '../../../../constants/formText';
import {
  PETITION_ROW_CELL_MAX_LENGTH,
  PETITION_TEXT_LIMITS,
} from '../../../../constants/petitionLimits';
import type { BusinessKind, PetitionAnswers, VenueChoice } from '../../../../types/api';
import { einNumber, mmDdYyyy, nineDigitNumber } from './masks';
import { PartyAddressFields } from './PartyAddressFields';
import {
  firstPetitionGap,
  HAZARD_KEYS,
  isBlankPetitionRow,
  isItin,
  isNineDigits,
  LANDLORD_KEYS,
  RENT_KEYS,
} from './petitionGaps';

type Secret = 'itin' | 'other_ssn';
type Division = 'Eastern' | 'Western' | null;

interface PetitionQuestionsProps {
  answers: PetitionAnswers;
  onChange: (next: PetitionAnswers) => void;
  /** The ITIN and other Social Security number typed since the last save, as digits */
  pendingSecrets: { itin?: string; other_ssn?: string };
  onSecretChange: (key: Secret, value: string) => void;
  /** Removes a saved number on the server; rejects when the server refuses (F10) */
  onSecretDelete?: (key: Secret) => Promise<void>;
  /** The county's division, which names the clerk and line 6's information; null before one */
  division: Division;
  /**
   * Every field above the block is valid, so an open gate here alone holds Continue: the status
   * region names it before the block is touched (F8)
   */
  fieldsAboveComplete?: boolean;
}

type RowList = 'other_names' | 'other_business_names' | 'prior_cases' | 'pending_cases';
type Row = { _key: string } & Record<string, string | null | undefined>;

interface ListSpec {
  key: RowList;
  cells: { name: string; label: string; date?: boolean }[];
  row: string;
  add: string;
  remove: string;
  /** The most rows the form's boxes and the server take (PF2-T8-7) */
  most: number;
}

/** The block each yes/no gates: a new answer to the gate hides what Show opened in these again */
const GATE_BLOCKS: Partial<Record<keyof PetitionAnswers, string[]>> = {
  other_names_answer: ['other_names'],
  itin_answer: ['itin'],
  other_ssn_answer: ['other_ssn'],
  mailing_answer: ['mailing'],
  prior_bankruptcy_answer: ['prior_cases'],
  pending_case_answer: ['pending_cases'],
  sole_proprietor_answer: ['business'],
};

const OTHER_NAMES: ListSpec = {
  key: 'other_names',
  cells: [
    { name: 'first', label: FORM_101_LINE_2_CELLS.first },
    { name: 'middle', label: FORM_101_LINE_2_CELLS.middle },
    { name: 'last', label: FORM_101_LINE_2_CELLS.last },
  ],
  row: PETITION_OTHER_NAME_ROW,
  add: PETITION_ADD_OTHER_NAME,
  remove: PETITION_REMOVE_OTHER_NAME,
  most: 2,
};
const OTHER_BUSINESS_NAMES: ListSpec = {
  key: 'other_business_names',
  cells: [{ name: 'name', label: FORM_101_LINE_2_CELLS.name }],
  row: PETITION_BUSINESS_NAME_ROW,
  add: PETITION_ADD_BUSINESS_NAME,
  remove: PETITION_REMOVE_BUSINESS_NAME,
  most: 2,
};
const PRIOR_CASES: ListSpec = {
  key: 'prior_cases',
  cells: [
    { name: 'district', label: FORM_101_LINE_9_CELLS.district },
    { name: 'filed_on', label: FORM_101_LINE_9_CELLS.filed_on, date: true },
    { name: 'case_number', label: FORM_101_LINE_9_CELLS.case_number },
  ],
  row: PETITION_PRIOR_CASE_ROW,
  add: PETITION_ADD_PRIOR_CASE,
  remove: PETITION_REMOVE_PRIOR_CASE,
  most: 20,
};
const PENDING_CASES: ListSpec = {
  key: 'pending_cases',
  cells: [
    { name: 'debtor', label: FORM_101_LINE_10_CELLS.debtor },
    { name: 'relationship', label: FORM_101_LINE_10_CELLS.relationship },
    { name: 'district', label: FORM_101_LINE_10_CELLS.district },
    { name: 'filed_on', label: FORM_101_LINE_10_CELLS.filed_on, date: true },
    { name: 'case_number', label: FORM_101_LINE_10_CELLS.case_number },
  ],
  row: PETITION_PENDING_CASE_ROW,
  add: PETITION_ADD_PENDING_CASE,
  remove: PETITION_REMOVE_PENDING_CASE,
  most: 20,
};

const MAILING_KEYS = [
  'mailing_street',
  'mailing_po_box',
  'mailing_city',
  'mailing_state',
  'mailing_zip',
] as const;
const BUSINESS_KEYS = [
  'business_name',
  'business_street',
  'business_city',
  'business_state',
  'business_zip',
  'business_kind',
] as const;

const LATER_STEP_KEYS: ReadonlySet<string> = new Set([
  ...HAZARD_KEYS,
  ...RENT_KEYS,
  ...LANDLORD_KEYS,
]);

// The last new row's key: unique while the page is open, apart from a loaded row's `loaded-<i>`
let nextKey = 0;

const blank = (value: unknown) => typeof value !== 'string' || value.trim() === '';

function rowsOf(answers: PetitionAnswers, key: RowList): Row[] {
  return (answers[key] ?? []) as Row[];
}

/** The line under a No that holds what was typed: Show brings it back, Delete removes it */
export function HiddenLine({
  sentence,
  onShow,
  onDelete,
}: {
  sentence: string;
  onShow: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="form-field">
      <p className="form-help-text">{sentence}</p>
      <Button variant="outline" size="sm" type="button" onClick={onShow}>
        {SHOW_HIDDEN}
      </Button>{' '}
      <Button variant="outline" size="sm" type="button" onClick={onDelete}>
        {DELETE_HIDDEN}
      </Button>
    </div>
  );
}

function hiddenRowsSentence(count: number): string {
  return count === 1 ? HIDDEN_ROWS_ONE : HIDDEN_ROWS_MANY.replace('{count}', String(count));
}

export function PetitionQuestions({
  answers,
  onChange,
  pendingSecrets,
  onSecretChange,
  onSecretDelete,
  division,
  fieldsAboveComplete = false,
}: PetitionQuestionsProps) {
  // Touched once any answer is set or focus has left the block (PF2-T8-10): until then nothing
  // says "Not answered yet", and the status region stays empty unless the fields above are all
  // valid, when the gate alone holds Continue (F8)
  const [blurred, setBlurred] = useState(false);
  // Hidden answers the filer asked to see again under a No, by block
  const [shown, setShown] = useState<Record<string, boolean>>({});
  // A secret box the filer emptied, by Replace or by clearing it: it stays open while empty. Once
  // digits are typed the box stays open because of them, so when a save takes them the saved line
  // shows again
  const [replacing, setReplacing] = useState<Record<Secret, boolean>>({
    itin: false,
    other_ssn: false,
  });
  // The secret box that has focus, and the digits typed into it since it took focus: a save that
  // takes them clears the wizard's copy, but the box keeps them, and stays, until focus leaves (F9)
  const [focusedSecret, setFocusedSecret] = useState<Secret | null>(null);
  const [typedHere, setTypedHere] = useState('');
  // A saved number's Delete the server refused, by key: the line stays and says so (F10)
  const [deleteFailed, setDeleteFailed] = useState<Record<Secret, boolean>>({
    itin: false,
    other_ssn: false,
  });

  // The record also holds the later steps' answers (the hazard, the rent), which are no answer in
  // this block
  const touched =
    blurred ||
    Object.entries(answers).some(
      ([key, value]) =>
        !key.endsWith('_saved') &&
        key !== 'answered_on' &&
        !LATER_STEP_KEYS.has(key) &&
        value !== null &&
        value !== undefined &&
        value !== '' &&
        !(Array.isArray(value) && value.length === 0)
    );
  const gap = firstPetitionGap(answers);

  const set = (changes: Partial<PetitionAnswers>) => onChange({ ...answers, ...changes });
  const show = (block: string) => setShown((current) => ({ ...current, [block]: true }));
  const leaveBlock = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setBlurred(true);
  };

  const yesNo = (
    key: keyof PetitionAnswers,
    question: string,
    note: string | readonly string[] | undefined,
    children?: ReactNode
  ) => {
    const value = answers[key];
    const answer = value === 'yes' || value === 'no' ? value : null;
    return (
      <YesNoThenDetails
        question={question}
        name={key}
        value={answer}
        onChange={(next) => {
          // Show opens a hidden saved number once: a new answer hides it again
          setShown((current) => ({
            ...current,
            ...Object.fromEntries((GATE_BLOCKS[key] ?? []).map((block) => [block, false])),
          }));
          set({ [key]: next });
        }}
        note={note}
        unanswered={touched && answer === null}
      >
        {children}
      </YesNoThenDetails>
    );
  };

  const rowList = (spec: ListSpec) => {
    const rows = rowsOf(answers, spec.key);
    const setRows = (next: Row[]) => set({ [spec.key]: next.length === 0 ? null : next });
    return (
      <div key={spec.key} className="petition-rows">
        {rows.map((row, index) => {
          const n = String(index + 1);
          const legend = spec.row.replace('{n}', n);
          return (
            <fieldset key={row._key} className="border rounded p-4 mb-4">
              <legend className="form-label">{legend}</legend>
              {spec.cells.map((cell) => (
                <FormField
                  key={cell.name}
                  label={cell.label}
                  name={`${spec.key}_${index}_${cell.name}`}
                  type="text"
                  {...(cell.date
                    ? { inputMode: 'numeric' as const, helpText: FORM_101_DATE_FORMAT }
                    : { maxLength: PETITION_ROW_CELL_MAX_LENGTH })}
                  value={row[cell.name] ?? ''}
                  onChange={(e) =>
                    setRows(
                      rows.map((r, i) =>
                        i === index
                          ? {
                              ...r,
                              [cell.name]: cell.date ? mmDdYyyy(e.target.value) : e.target.value,
                            }
                          : r
                      )
                    )
                  }
                />
              ))}
              <Button
                variant="outline"
                size="sm"
                type="button"
                onClick={() => setRows(rows.filter((_, i) => i !== index))}
              >
                {spec.remove.replace('{n}', n)}
              </Button>
            </fieldset>
          );
        })}
        {rows.length < spec.most && (
          <Button
            variant="outline"
            size="sm"
            type="button"
            onClick={() => setRows([...rows, { _key: `new-${++nextKey}` }])}
          >
            {spec.add}
          </Button>
        )}
      </div>
    );
  };

  /** The rows of `lists` under their Yes, or under a No the line that keeps them */
  const rowsUnder = (gate: keyof PetitionAnswers, block: string, lists: ListSpec[]) => {
    if (answers[gate] === 'yes' || shown[block]) return lists.map((spec) => rowList(spec));
    if (answers[gate] !== 'no') return null;
    const kept = lists.reduce(
      (count, spec) =>
        count + rowsOf(answers, spec.key).filter((row) => !isBlankPetitionRow(row)).length,
      0
    );
    if (kept === 0) return null;
    return (
      <HiddenLine
        sentence={hiddenRowsSentence(kept)}
        onShow={() => show(block)}
        onDelete={() => set(Object.fromEntries(lists.map((spec) => [spec.key, null])))}
      />
    );
  };

  /** A block's boxes under its Yes, or under a No the line that keeps what was typed */
  const boxesUnder = (
    gate: keyof PetitionAnswers,
    block: string,
    keys: readonly (keyof PetitionAnswers)[],
    boxes: ReactNode
  ) => {
    if (answers[gate] === 'yes' || shown[block]) return boxes;
    if (answers[gate] !== 'no' || keys.every((key) => blank(answers[key]))) return null;
    return (
      <HiddenLine
        sentence={HIDDEN_ANSWERS}
        onShow={() => show(block)}
        onDelete={() => set(Object.fromEntries(keys.map((key) => [key, null])))}
      />
    );
  };

  /** The ITIN's or other number's box, or the line saying one is saved (F-3, PF2-5) */
  const secretBox = (key: Secret, label: string, savedLine: string, saved: boolean) => {
    const pending = pendingSecrets[key] ?? '';
    const focused = focusedSecret === key;
    if (saved && pending === '' && !replacing[key] && !focused) {
      return (
        <div className="form-field">
          <p className="form-help-text">{savedLine}</p>
          <Button
            variant="outline"
            size="sm"
            type="button"
            onClick={() => setReplacing((current) => ({ ...current, [key]: true }))}
          >
            {REPLACE_SAVED}
          </Button>
        </div>
      );
    }
    // Nine digits that aren't an ITIN would print blank, so they stay here, unsent, with the
    // server's own sentence beside them (PF2-U2, owner ruling Q7)
    const shownDigits = focused && pending === '' ? typedHere : pending;
    const notAnItin = key === 'itin' && isNineDigits(shownDigits) && !isItin(shownDigits);
    return (
      <FormField
        label={label}
        name={key}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        placeholder="XXX-XX-XXXX"
        helpText={notAnItin ? PETITION_DETAIL_ITIN_NINE : undefined}
        value={nineDigitNumber(shownDigits)}
        onFocus={() => {
          setFocusedSecret(key);
          setTypedHere(pending);
        }}
        onBlur={() => {
          setFocusedSecret(null);
          setTypedHere('');
          // Left with nothing typed: the saved number is still what is stored, so its line returns
          if (pending === '') setReplacing((current) => ({ ...current, [key]: false }));
        }}
        onChange={(e) => {
          const digits = nineDigitNumber(e.target.value).replace(/\D/g, '');
          setReplacing((current) => ({ ...current, [key]: digits === '' }));
          setTypedHere(digits);
          onSecretChange(key, digits);
        }}
      />
    );
  };

  /** A secret's box under its Yes; under a No, or unanswered, a saved one named as hidden (F10) */
  const secretUnder = (
    gate: 'itin_answer' | 'other_ssn_answer',
    key: Secret,
    label: string,
    savedLine: string
  ) => {
    const saved = answers[`${key}_saved`] === true;
    if (answers[gate] === 'yes') return secretBox(key, label, savedLine, saved);
    if (!saved) return null;
    const remove = async () => {
      setDeleteFailed((current) => ({ ...current, [key]: false }));
      try {
        await onSecretDelete?.(key);
      } catch {
        setDeleteFailed((current) => ({ ...current, [key]: true }));
      }
    };
    const failure = deleteFailed[key] && (
      <p className="form-error" role="alert">
        {NOT_SAVED_TRY_AGAIN}
      </p>
    );
    // Shown under a No: the saved line keeps a Delete beside it, so the filer can still remove it
    if (shown[key]) {
      return (
        <>
          {secretBox(key, label, savedLine, saved)}
          <Button variant="outline" size="sm" type="button" onClick={remove}>
            {DELETE_HIDDEN}
          </Button>
          {failure}
        </>
      );
    }
    return (
      <>
        <HiddenLine sentence={HIDDEN_ANSWERS} onShow={() => show(key)} onDelete={remove} />
        {failure}
      </>
    );
  };

  const venue = answers.venue_choice ?? null;
  const divisionLine =
    division === 'Eastern'
      ? VENUE_DIVISION_EASTERN
      : division === 'Western'
        ? VENUE_DIVISION_WESTERN
        : null;

  return (
    <section className="form-section petition-questions" onBlur={leaveBlock}>
      <FormField
        label={FORM_101_SUFFIX}
        name="name_suffix"
        type="text"
        maxLength={PETITION_TEXT_LIMITS.name_suffix}
        value={answers.name_suffix ?? ''}
        onChange={(e) => set({ name_suffix: e.target.value })}
      />

      <PublicRecordNotice division={division} />

      {/* 1b, Form 101 line 2 */}
      {yesNo(
        'other_names_answer',
        FORM_101_LINE_2,
        // The form's instructions come with the question, before the answer: a maiden or trade
        // name counts, and a filer told so only after a Yes could answer No without knowing it
        [FORM_101_LINE_2_INSTRUCTIONS, WHY_OTHER_NAMES],
        rowsUnder('other_names_answer', 'other_names', [OTHER_NAMES, OTHER_BUSINESS_NAMES])
      )}

      {/* 1c, Form 101 line 3 and Form 121 line 3 */}
      {yesNo(
        'itin_answer',
        PETITION_ASKED_AS_ITIN,
        WHY_ITIN,
        secretUnder('itin_answer', 'itin', FORM_101_LINE_3_ITIN, ITIN_SAVED)
      )}

      {/* 1d, Form 121 line 2 */}
      {yesNo(
        'other_ssn_answer',
        PETITION_ASKED_AS_OTHER_SSN,
        WHY_OTHER_SSN,
        secretUnder('other_ssn_answer', 'other_ssn', FORM_121_LINE_2_OTHER_SSN, OTHER_SSN_SAVED)
      )}

      {/* 1e, Form 101 line 4 */}
      <FormField
        label={FORM_101_LINE_4}
        name="ein"
        type="text"
        inputMode="numeric"
        autoComplete="off"
        placeholder="XX-XXXXXXX"
        value={einNumber(answers.ein ?? '')}
        onChange={(e) => set({ ein: einNumber(e.target.value) })}
      />

      <PublicRecordNotice division={division} />

      {/* 1f, Form 101 line 5 */}
      {yesNo(
        'mailing_answer',
        PETITION_ASKED_AS_MAILING,
        WHY_MAILING,
        boxesUnder(
          'mailing_answer',
          'mailing',
          MAILING_KEYS,
          <>
            <p className="form-help-text">{FORM_101_LINE_5}</p>
            <PartyAddressFields
              answers={answers}
              onChange={set}
              streetKey="mailing_street"
              poBoxKey="mailing_po_box"
              cityKey="mailing_city"
              stateKey="mailing_state"
              zipKey="mailing_zip"
            />
          </>
        )
      )}

      {/* 1g, Form 101 line 6: a choice, never a gate (spec §5.7) */}
      <fieldset className="form-field fee-waiver-question">
        <legend className="form-label">{FORM_101_LINE_6}</legend>
        {divisionLine && <p className="form-help-text">{divisionLine}</p>}
        {(Object.keys(FORM_101_VENUE_CHOICES) as VenueChoice[]).map((choice) => (
          <label key={choice} className="ab-choice">
            <input
              type="radio"
              name="venue_choice"
              value={choice}
              checked={venue === choice}
              onChange={() => set({ venue_choice: choice })}
            />
            {FORM_101_VENUE_CHOICES[choice]}
          </label>
        ))}
        {venue === 'other' && (
          <FormField
            label={FORM_101_VENUE_CHOICES.other}
            // The radio above reads the choice's words alone; the box adds the line's question,
            // so the two are told apart
            aria-label={`${FORM_101_LINE_6} ${FORM_101_VENUE_CHOICES.other}`}
            name="venue_reason"
            type="text"
            maxLength={PETITION_TEXT_LIMITS.venue_reason}
            value={answers.venue_reason ?? ''}
            onChange={(e) => set({ venue_reason: e.target.value })}
          />
        )}
      </fieldset>

      {/* 1h, Form 101 line 9 */}
      {yesNo(
        'prior_bankruptcy_answer',
        FORM_101_LINE_9,
        undefined,
        rowsUnder('prior_bankruptcy_answer', 'prior_cases', [PRIOR_CASES])
      )}

      {/* 1i, Form 101 line 10 */}
      {yesNo(
        'pending_case_answer',
        FORM_101_LINE_10,
        undefined,
        rowsUnder('pending_case_answer', 'pending_cases', [PENDING_CASES])
      )}

      {/* 1j, Form 101 line 12 */}
      {yesNo(
        'sole_proprietor_answer',
        FORM_101_LINE_12,
        undefined,
        boxesUnder(
          'sole_proprietor_answer',
          'business',
          BUSINESS_KEYS,
          <>
            <p className="form-help-text">{LINE_12_FEEDS_107}</p>
            <p className="form-label">{FORM_101_LINE_12_LOCATION}</p>
            <PartyAddressFields
              answers={answers}
              onChange={set}
              name={{ key: 'business_name', label: FORM_101_LINE_12_NAME }}
              streetKey="business_street"
              cityKey="business_city"
              stateKey="business_state"
              zipKey="business_zip"
            />
            <fieldset className="form-field">
              <legend className="form-label">{FORM_101_LINE_12_KIND}</legend>
              {(Object.keys(FORM_101_BUSINESS_KINDS) as BusinessKind[]).map((kind) => (
                <label key={kind} className="ab-choice">
                  <input
                    type="radio"
                    name="business_kind"
                    value={kind}
                    checked={answers.business_kind === kind}
                    onChange={() => set({ business_kind: kind })}
                  />
                  {FORM_101_BUSINESS_KINDS[kind]}
                </label>
              ))}
            </fieldset>
          </>
        )
      )}

      {/* A status, not an alert, mounted from the start so a screen reader reads what arrives */}
      <div role="status">
        {(touched || fieldsAboveComplete) && gap !== null && (
          <div className="info-box">
            <p className="info-message">{gap}</p>
          </div>
        )}
      </div>
    </section>
  );
}
