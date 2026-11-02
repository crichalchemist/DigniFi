/**
 * Income Entry List - one person's businesses and rental properties (3e2 spec §4.2)
 *
 * Trauma-informed design:
 * - Every question may stay blank: an unanswered one is marked, never an error
 * - Only an amount the server can't store stops saving
 * - The net is shown, never typed, and a loss is explained in information, never advice
 *
 * The list is the filer's or the spouse's. It is modelled on HouseholdList, which it follows in
 * how rows are keyed and saved.
 */

import { FormField, FormSelect, Button } from '../../common';
import {
  ADD_ENTRY,
  DOUBLE_COUNT_INCOME_NOTE,
  ENTRIES_HEADING,
  ENTRY_DESCRIPTION_HELP,
  ENTRY_NET_LABEL,
  FLOOR_AVERAGE_BUSINESS,
  FLOOR_AVERAGE_RENTAL,
  NOT_ANSWERED_YET,
  NO_ENTRIES,
  SPOUSE_ADD_ENTRY,
  SPOUSE_FLOOR_AVERAGE_BUSINESS,
  SPOUSE_FLOOR_AVERAGE_RENTAL,
  SPOUSE_NO_ENTRIES,
} from '../../../constants/copy';
import {
  AVERAGING_SENTENCE,
  ENTRY_KIND_WORDS,
  GROSS_RECEIPTS_LABEL,
  ONE_COLUMN_ONLY,
  OPERATING_EXPENSES_LABEL,
} from '../../../constants/formText';
import { MAX_ENTRIES, isEntryTouched, kindNet, newIncomeEntry } from '../../../utils/incomeEntries';
import type { EntryRow } from '../../../utils/incomeEntries';
import type { EntryKind } from '../../../types/api';

interface IncomeEntryListProps {
  /** The wizard's rows. The list keeps no copy, so an id a save writes into a row stays there. */
  rows: EntryRow[];
  onRowsChange: (rows: EntryRow[]) => void;
  /** The person said they have no business or rental income */
  noEntries: boolean;
  onNoEntriesChange: (pressed: boolean) => void;
  /** The spouse's list: every name and label takes the spouse's prefix */
  spouse: boolean;
  /** What is wrong with each amount, by its box's name */
  errors: Record<string, string>;
}

const KIND_OPTIONS = Object.entries(ENTRY_KIND_WORDS).map(([value, label]) => ({ value, label }));

// A new row's key, from a count that outlives the step: the step remounts on each visit while
// unsaved rows stay in the wizard, so a count per mount could repeat a key
let lastKey = 0;

/** An amount in dollars and cents, with a leading minus below $0 */
function formatNet(net: number) {
  const dollars = Math.abs(net).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${net < 0 ? '-' : ''}$${dollars}`;
}

const FLOOR_SENTENCES: Record<EntryKind, { filer: string; spouse: string }> = {
  business: { filer: FLOOR_AVERAGE_BUSINESS, spouse: SPOUSE_FLOOR_AVERAGE_BUSINESS },
  rental: { filer: FLOOR_AVERAGE_RENTAL, spouse: SPOUSE_FLOOR_AVERAGE_RENTAL },
};

export function IncomeEntryList({
  rows,
  onRowsChange,
  noEntries,
  onNoEntriesChange,
  spouse,
  errors,
}: IncomeEntryListProps) {
  const prefix = spouse ? 'spouse_' : '';

  // Every answer is the person's own, so it also takes back an earlier "I have none"
  const answer = (index: number, row: EntryRow) => {
    onRowsChange(rows.map((other, i) => (i === index ? row : other)));
    onNoEntriesChange(false);
  };

  const answerAmount = (index: number, key: 'gross' | 'expenses', value: string) => {
    const parsed = value.trim() === '' ? NaN : Number.parseFloat(value);
    answer(index, { ...rows[index], [key]: Number.isFinite(parsed) ? parsed : null });
  };

  const removeRow = (index: number) => {
    onRowsChange(rows.filter((_, i) => i !== index));
  };

  // A box's own help, with "Not answered yet" joined on while it is blank on a touched entry, so
  // a screen reader announces it on the box
  const helpFor = (help: string | undefined, touched: boolean, value: unknown) =>
    [help, touched && value == null ? NOT_ANSWERED_YET : undefined].filter(Boolean).join(' ') ||
    undefined;

  const kindsBelowZero = (['business', 'rental'] as const).filter(
    (kind) => kindNet(rows, kind, false) < 0
  );

  return (
    <section className="form-section">
      <h3 className="section-title">{ENTRIES_HEADING}</h3>
      {spouse && <blockquote className="section-description">{ONE_COLUMN_ONLY}</blockquote>}

      {rows.map((row, index) => {
        const touched = isEntryTouched(row);
        const net = (row.gross ?? 0) - (row.expenses ?? 0);
        return (
          // Keyed by the row's own key, so each answer stays with its row when one is removed
          <section key={row._key} className="form-section household-card">
            <div className="household-card-header">
              <h4 className="section-title">
                {spouse ? "Spouse's business or property" : 'Business or property'} {index + 1}
              </h4>
              <button
                type="button"
                onClick={() => removeRow(index)}
                className="remove-household-button"
                aria-label={
                  spouse
                    ? `Remove your spouse's business or property ${index + 1}`
                    : `Remove business or property ${index + 1}`
                }
              >
                Remove
              </button>
            </div>

            <FormSelect
              label={spouse ? "Spouse's kind of income" : 'Kind of income'}
              name={`${prefix}entry_kind_${index}`}
              options={KIND_OPTIONS}
              value={row.kind ?? ''}
              onChange={(value) =>
                answer(index, { ...row, kind: value === '' ? null : (value as EntryKind) })
              }
              helpText={touched && row.kind == null ? NOT_ANSWERED_YET : undefined}
            />

            <FormField
              label={spouse ? "Spouse's: what it is" : 'What it is'}
              name={`${prefix}entry_description_${index}`}
              type="text"
              maxLength={200}
              value={row.description ?? ''}
              onChange={(e) =>
                answer(index, {
                  ...row,
                  description: e.target.value === '' ? null : e.target.value,
                })
              }
              helpText={helpFor(ENTRY_DESCRIPTION_HELP, touched, row.description)}
            />

            <div className="form-row">
              <FormField
                label={spouse ? `Spouse's ${GROSS_RECEIPTS_LABEL}` : GROSS_RECEIPTS_LABEL}
                name={`${prefix}entry_gross_${index}`}
                type="number"
                min="0"
                step="0.01"
                value={row.gross ?? ''}
                onChange={(e) => answerAmount(index, 'gross', e.target.value)}
                error={errors[`${prefix}entry_gross_${index}`]}
                // The help speaks to the filer, so it stays out from under the spouse's box
                helpText={helpFor(spouse ? undefined : AVERAGING_SENTENCE, touched, row.gross)}
                placeholder="0.00"
              />
              <FormField
                label={spouse ? `Spouse's ${OPERATING_EXPENSES_LABEL}` : OPERATING_EXPENSES_LABEL}
                name={`${prefix}entry_expenses_${index}`}
                type="number"
                min="0"
                step="0.01"
                value={row.expenses ?? ''}
                onChange={(e) => answerAmount(index, 'expenses', e.target.value)}
                error={errors[`${prefix}entry_expenses_${index}`]}
                helpText={helpFor(
                  spouse ? undefined : DOUBLE_COUNT_INCOME_NOTE,
                  touched,
                  row.expenses
                )}
                placeholder="0.00"
              />
            </div>

            <p className="form-help-text">
              <span>{ENTRY_NET_LABEL}</span> <strong>{formatNet(net)}</strong>
            </p>
          </section>
        );
      })}

      {kindsBelowZero.map((kind) => (
        <div key={kind} className="info-box">
          <p className="info-message">{FLOOR_SENTENCES[kind][spouse ? 'spouse' : 'filer']}</p>
        </div>
      ))}

      <div className="add-asset-section">
        <Button
          variant="outline"
          onClick={() => onRowsChange([...rows, newIncomeEntry(`new-${++lastKey}`)])}
          disabled={rows.length >= MAX_ENTRIES}
        >
          {spouse ? SPOUSE_ADD_ENTRY : ADD_ENTRY}
        </Button>
      </div>

      {!rows.some(isEntryTouched) && (
        <Button
          variant="outline"
          aria-pressed={noEntries}
          onClick={() => onNoEntriesChange(!noEntries)}
        >
          {spouse ? SPOUSE_NO_ENTRIES : NO_ENTRIES}
        </Button>
      )}
    </section>
  );
}

export default IncomeEntryList;
