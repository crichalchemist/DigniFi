/**
 * Household List - the people in the filer's home and the people they support (3e1 spec §4.2)
 *
 * Trauma-informed design:
 * - Relationship is a list, never free text, so no name is ever typed or stored
 * - An unanswered question is marked, never an error: Complete names it
 * - Only a value the server can't store (an age outside 0-120) stops saving
 */

import { FormField, FormSelect, Button } from '../../common';
import { MAX_AGE, MAX_HOUSEHOLD_ROWS, RELATIONSHIP_WORDS } from '../../../constants/household';
import { DEPENDENT_GLOSSARY } from '../../../constants/formText';
import {
  DEPENDENT_GLOSSARY_LEAD,
  HOUSEHOLD_NO_NAMES,
  LIVES_WITH_YOU_HELP,
  NO_ONE_ELSE,
  NOT_ANSWERED_YET,
  SPOUSE_DEPENDENT_QUESTION,
} from '../../../constants/copy';
import { isTouched, newHouseholdMember } from '../../../utils/householdRows';
import type { HouseholdMember, Relationship, WizardRow } from '../../../types/api';

type MemberRow = WizardRow<HouseholdMember>;

interface HouseholdListProps {
  /** The wizard's rows. The list keeps no copy, so an id a save writes into a row stays there. */
  rows: MemberRow[];
  onRowsChange: (rows: MemberRow[]) => void;
  /** The filer said no one else lives with them or depends on them */
  noOneElse: boolean;
  onNoOneElseChange: (pressed: boolean) => void;
  /** What is wrong with each row's age, by the row's position */
  ageErrors: Record<number, string>;
  /** The spouse row the step added this visit, whose "Lives with you?" follows the marriage answer */
  followedKey: string | null;
  onFollowedKeyChange: (key: string | null) => void;
}

const RELATIONSHIP_OPTIONS = Object.entries(RELATIONSHIP_WORDS).map(([value, label]) => ({
  value,
  label,
}));

interface YesNoQuestionProps {
  legend: string;
  name: string;
  answer: boolean | null | undefined;
  unanswered: boolean;
  onAnswer: (answer: boolean) => void;
}

/** A yes/no question, nothing checked until the filer answers */
function YesNoQuestion({ legend, name, answer, unanswered, onAnswer }: YesNoQuestionProps) {
  return (
    <fieldset className="form-field fee-waiver-question">
      <legend className="form-label">{legend}</legend>
      <label className="fee-waiver-checkbox">
        <input
          type="radio"
          name={name}
          value="yes"
          checked={answer === true}
          onChange={() => onAnswer(true)}
        />{' '}
        Yes
      </label>
      <label className="fee-waiver-checkbox">
        <input
          type="radio"
          name={name}
          value="no"
          checked={answer === false}
          onChange={() => onAnswer(false)}
        />{' '}
        No
      </label>
      {unanswered && <p className="form-help-text">{NOT_ANSWERED_YET}</p>}
    </fieldset>
  );
}

export function HouseholdList({
  rows,
  onRowsChange,
  noOneElse,
  onNoOneElseChange,
  ageErrors,
  followedKey,
  onFollowedKeyChange,
}: HouseholdListProps) {
  // Every answer is the filer's, so it also takes back an earlier "no one else"
  const answer = (index: number, row: MemberRow) => {
    onRowsChange(rows.map((other, i) => (i === index ? row : other)));
    onNoOneElseChange(false);
  };

  const answerRelationship = (index: number, value: string) => {
    const row = rows[index];
    const relationship = value === '' ? null : (value as Relationship);
    const next: MemberRow = { ...row, relationship };
    // The server refuses an answer to the spouse's question on any other row, so only the spouse's row carries it
    if (relationship === 'spouse' && row.relationship !== 'spouse') next.spouse_is_dependent = null;
    if (relationship !== 'spouse') delete next.spouse_is_dependent;
    answer(index, next);
  };

  const answerLivesWithYou = (index: number, livesWithYou: boolean) => {
    // The filer's own answer: the row stops following the marriage answer
    if (rows[index]._key === followedKey) onFollowedKeyChange(null);
    answer(index, { ...rows[index], lives_with_you: livesWithYou });
  };

  const removeRow = (index: number) => {
    if (rows[index]._key === followedKey) onFollowedKeyChange(null);
    onRowsChange(rows.filter((_, i) => i !== index));
  };

  const otherRowIsSpouse = (index: number) =>
    rows.some((row, i) => i !== index && row.relationship === 'spouse');

  return (
    <section className="form-section">
      <h3 className="section-title">People in your home, and people you support</h3>
      <p className="section-description">{HOUSEHOLD_NO_NAMES}</p>
      <p className="section-description">{LIVES_WITH_YOU_HELP}</p>

      {rows.map((row, index) => {
        const touched = isTouched(row);
        return (
          // Keyed by the row's own key, so each answer stays with its row when one is removed
          <section key={row._key} className="form-section household-card">
            <div className="household-card-header">
              <h4 className="section-title">Person {index + 1}</h4>
              <button
                type="button"
                onClick={() => removeRow(index)}
                className="remove-household-button"
                aria-label={`Remove person ${index + 1}`}
              >
                Remove
              </button>
            </div>

            <div className="form-row">
              <FormSelect
                label="Relationship"
                name={`relationship_${index}`}
                options={
                  otherRowIsSpouse(index)
                    ? RELATIONSHIP_OPTIONS.filter((option) => option.value !== 'spouse')
                    : RELATIONSHIP_OPTIONS
                }
                value={row.relationship ?? ''}
                onChange={(value) => answerRelationship(index, value)}
                helpText={touched && row.relationship == null ? NOT_ANSWERED_YET : undefined}
              />

              <FormField
                label="Age"
                name={`age_${index}`}
                type="number"
                min="0"
                max={MAX_AGE}
                step="1"
                value={row.age ?? ''}
                onChange={(e) =>
                  answer(index, {
                    ...row,
                    age: e.target.value === '' ? null : Number(e.target.value),
                  })
                }
                error={ageErrors[index]}
                helpText={touched && row.age == null ? NOT_ANSWERED_YET : undefined}
              />
            </div>

            <YesNoQuestion
              legend="Lives with you?"
              name={`lives_with_you_${index}`}
              answer={row.lives_with_you}
              unanswered={touched && row.lives_with_you == null}
              onAnswer={(livesWithYou) => answerLivesWithYou(index, livesWithYou)}
            />

            <YesNoQuestion
              legend="Claimed on your tax return, or supported by you?"
              name={`claimed_or_supported_${index}`}
              answer={row.claimed_or_supported}
              unanswered={touched && row.claimed_or_supported == null}
              onAnswer={(claimed) => answer(index, { ...row, claimed_or_supported: claimed })}
            />

            {row.relationship === 'spouse' && (
              <>
                <YesNoQuestion
                  legend={SPOUSE_DEPENDENT_QUESTION}
                  name={`spouse_is_dependent_${index}`}
                  answer={row.spouse_is_dependent}
                  unanswered={row.spouse_is_dependent == null}
                  onAnswer={(dependent) =>
                    answer(index, { ...row, spouse_is_dependent: dependent })
                  }
                />
                <p className="form-help-text">
                  {DEPENDENT_GLOSSARY_LEAD} “{DEPENDENT_GLOSSARY}”
                </p>
              </>
            )}
          </section>
        );
      })}

      <div className="add-asset-section">
        <Button
          variant="outline"
          onClick={() => onRowsChange([...rows, newHouseholdMember()])}
          disabled={rows.length >= MAX_HOUSEHOLD_ROWS}
        >
          + Add a person
        </Button>
      </div>

      {!rows.some(isTouched) && (
        <Button
          variant="outline"
          aria-pressed={noOneElse}
          onClick={() => onNoOneElseChange(!noOneElse)}
        >
          {NO_ONE_ELSE}
        </Button>
      )}
    </section>
  );
}

export default HouseholdList;
