/**
 * One row of a Schedule A/B line: the boxes the line's shape asks, in the form's words.
 *
 * Every blank goes to the row in the shape the server takes: null for an amount, a share, who and
 * a kind (the request would leave out an undefined, and the server would keep the old figure), ''
 * for text. Nothing starts chosen, and an amount the server would refuse never reaches the row,
 * since this step autosaves mid-Part.
 */

import { useState } from 'react';
import { Button, FormField, FormSelect } from '../../../common';
import {
  AB_ADDRESS_LINE_2_LABEL,
  AB_KIND_LABEL,
  AB_TEXT_LABEL,
  OUT_OF_RANGE_PERCENT,
  VALUE_UNKNOWN_BUTTON,
  VALUE_UNKNOWN_NOTE,
  WHO_ONLY_YOU,
  WHO_WITH_SOMEONE,
} from '../../../../constants/copy';
import {
  AB_ACCOUNT_TYPE_LABEL,
  AB_BENEFICIARY_LABEL,
  AB_CITY_LABEL,
  AB_COMMUNITY,
  AB_COUNTY_LABEL,
  AB_DO_NOT_DEDUCT,
  AB_DO_NOT_DEDUCT_SCHEDULE_D,
  AB_ENTIRE_LABEL,
  AB_KIND_WORDS,
  AB_LINE_WORDS,
  AB_MAKE_LABEL,
  AB_MILEAGE_LABEL,
  AB_MODEL_LABEL,
  AB_NATURE_LABEL,
  AB_PERCENT_LABEL,
  AB_PERSONAL_INFO_QUESTION,
  AB_PLACE_OTHER_INFO_LABEL,
  AB_PORTION_LABEL,
  AB_PROPERTY_KIND_QUESTION,
  AB_PROPERTY_KIND_WORDS,
  AB_STATE_LABEL,
  AB_STREET_LABEL,
  AB_VEHICLE_OTHER_INFO_LABEL,
  AB_WHO_QUESTION,
  AB_YEAR_LABEL,
  AB_ZIP_LABEL,
} from '../../../../constants/formText';
import { amountError, parseAmount } from '../../../../utils/parseAmount';
import { PROPERTY_KINDS } from '../../../../types/api';
import type { AssetLine } from '../../../../constants/assetLines';
import type {
  AssetDetails,
  AssetInfo,
  AssetWho,
  PropertyKind,
  WizardRow,
} from '../../../../types/api';

type Row = WizardRow<AssetInfo>;

// The serializer's bounds on a row's text: `details` boxes and the description
const DETAIL_MAX_LENGTH = 200;
const DESCRIPTION_MAX_LENGTH = 255;

// DecimalField(max_digits=12, decimal_places=2) on current_value and entire_value
const VALUE_MAX_DIGITS = 12;

// FormField's mark, for the questions asked in a fieldset, which has no required prop
const REQUIRED_MARK = (
  <span className="required-indicator" aria-label="required">
    *
  </span>
);

interface ValueBoxProps {
  name: string;
  label: string;
  help: string;
  value: number | null | undefined;
  unknown: boolean;
  unknownName: string;
  onValue: (value: number | null) => void;
  onUnknown: (pressed: boolean) => void;
}

/** A value and its "I don't know the value", each of which clears the other */
function ValueBox({
  name,
  label,
  help,
  value,
  unknown,
  unknownName,
  onValue,
  onUnknown,
}: ValueBoxProps) {
  const [refused, setRefused] = useState<string>();
  return (
    <div className="ab-value">
      <FormField
        label={label}
        name={name}
        type="number"
        inputMode="decimal"
        min="0"
        step="0.01"
        required={!unknown}
        value={value ?? ''}
        onChange={(e) => {
          const parsed = parseAmount(e.target.value);
          const error = amountError(parsed, VALUE_MAX_DIGITS);
          setRefused(error);
          if (error === undefined) onValue(parsed ?? null);
        }}
        error={refused}
        helpText={help}
        placeholder="0.00"
      />
      <Button
        variant="outline"
        name={unknownName}
        aria-pressed={unknown}
        onClick={() => {
          setRefused(undefined);
          onUnknown(!unknown);
        }}
      >
        {VALUE_UNKNOWN_BUTTON}
      </Button>
      {unknown && <p className="form-help-text">{VALUE_UNKNOWN_NOTE}</p>}
    </div>
  );
}

interface AssetRowFieldsProps {
  line: AssetLine;
  row: Row;
  /** The row's place among this line's rows, which names its boxes */
  rowIndex: number;
  onRowChange: (row: Row) => void;
  onRemove: () => void;
}

export function AssetRowFields({
  line,
  row,
  rowIndex,
  onRowChange,
  onRemove,
}: AssetRowFieldsProps) {
  const [percentRefused, setPercentRefused] = useState<string>();
  const { shape, key } = line;
  const words = AB_LINE_WORDS[key];
  const details = row.details ?? {};
  const prefix = `line_${key}_${rowIndex}`;

  const setDetails = (changes: AssetDetails) =>
    onRowChange({ ...row, details: { ...details, ...changes } });

  const detailBox = (label: string, field: keyof AssetDetails, required = false) => (
    <FormField
      label={label}
      name={`${prefix}_${field}`}
      type="text"
      required={required}
      maxLength={DETAIL_MAX_LENGTH}
      value={(details[field] as string | null | undefined) ?? ''}
      onChange={(e) => setDetails({ [field]: e.target.value })}
    />
  );

  const textBox = (
    <FormField
      label={words.textLabel ?? AB_TEXT_LABEL}
      name={`${prefix}_description`}
      type="text"
      required
      maxLength={DESCRIPTION_MAX_LENGTH}
      value={row.description ?? ''}
      onChange={(e) => onRowChange({ ...row, description: e.target.value })}
    />
  );

  const hasEntire = shape === 'place' || shape === 'vehicle' || shape === 'vehicle_no_mileage';
  const deductHelp = hasEntire ? AB_DO_NOT_DEDUCT_SCHEDULE_D : AB_DO_NOT_DEDUCT;

  // A typed figure takes back "I don't know"; pressing it clears the figure. Only a flag that is
  // set changes, so a row that never used it sends no flag.
  const valueBoxes = (
    <>
      {hasEntire && (
        <ValueBox
          name={`${prefix}_entire_value`}
          label={AB_ENTIRE_LABEL}
          help={deductHelp}
          value={row.entire_value}
          unknown={details.entire_unknown === true}
          unknownName={`${prefix}_entire_unknown`}
          onValue={(value) =>
            onRowChange({
              ...row,
              entire_value: value,
              details: details.entire_unknown ? { ...details, entire_unknown: false } : details,
            })
          }
          onUnknown={(pressed) =>
            onRowChange({
              ...row,
              entire_value: null,
              details: { ...details, entire_unknown: pressed },
            })
          }
        />
      )}
      <ValueBox
        name={`${prefix}_current_value`}
        label={words.valueLabel ?? AB_PORTION_LABEL}
        help={deductHelp}
        value={row.current_value}
        unknown={details.value_unknown === true}
        unknownName={`${prefix}_value_unknown`}
        onValue={(value) =>
          onRowChange({
            ...row,
            current_value: value,
            details: details.value_unknown ? { ...details, value_unknown: false } : details,
          })
        }
        onUnknown={(pressed) =>
          onRowChange({
            ...row,
            current_value: null,
            details: { ...details, value_unknown: pressed },
          })
        }
      />
    </>
  );

  const whoQuestion = (
    <fieldset className="form-field fee-waiver-question">
      <legend className="form-label">
        {AB_WHO_QUESTION}
        {REQUIRED_MARK}
      </legend>
      {(
        [
          ['only_you', WHO_ONLY_YOU],
          ['with_someone', WHO_WITH_SOMEONE],
        ] as [AssetWho, string][]
      ).map(([value, label]) => (
        <label key={value} className="ab-choice">
          <input
            type="radio"
            name={`${prefix}_who`}
            value={value}
            checked={details.who === value}
            onChange={() => setDetails({ who: value })}
          />
          {label}
        </label>
      ))}
    </fieldset>
  );

  const communityBox = (
    <label className="ab-choice">
      <input
        type="checkbox"
        name={`${prefix}_community`}
        checked={details.community === true}
        onChange={(e) => setDetails({ community: e.target.checked })}
      />
      {AB_COMMUNITY}
    </label>
  );

  const toggleKind = (kind: PropertyKind, ticked: boolean) => {
    const kinds = details.property_kinds ?? [];
    const changes: AssetDetails = {
      property_kinds: ticked ? [...kinds, kind] : kinds.filter((other) => other !== kind),
    };
    // The form prints what is stored, so text the filer can no longer see can't stay in the row
    if (kind === 'other' && !ticked) changes.other_kind = '';
    setDetails(changes);
  };

  return (
    <section className="form-section ab-row">
      <div className="ab-row-header">
        <h4 className="section-title">Item {rowIndex + 1}</h4>
        <Button
          variant="text"
          onClick={onRemove}
          aria-label={`Remove item ${rowIndex + 1} on line ${key}`}
        >
          Remove
        </Button>
      </div>

      {shape === 'place' && (
        <>
          {detailBox(AB_STREET_LABEL, 'street', true)}
          {detailBox(AB_ADDRESS_LINE_2_LABEL, 'street_2')}
          {detailBox(AB_CITY_LABEL, 'city')}
          {detailBox(AB_STATE_LABEL, 'state')}
          {detailBox(AB_ZIP_LABEL, 'zip')}
          {detailBox(AB_COUNTY_LABEL, 'county')}
          <fieldset className="form-field fee-waiver-question">
            <legend className="form-label">
              {AB_PROPERTY_KIND_QUESTION}
              {REQUIRED_MARK}
            </legend>
            {PROPERTY_KINDS.map((kind) => (
              <label key={kind} className="ab-choice">
                <input
                  type="checkbox"
                  name={`${prefix}_property_kinds`}
                  value={kind}
                  checked={(details.property_kinds ?? []).includes(kind)}
                  onChange={(e) => toggleKind(kind, e.target.checked)}
                />
                {AB_PROPERTY_KIND_WORDS[kind]}
              </label>
            ))}
          </fieldset>
          {(details.property_kinds ?? []).includes('other') &&
            detailBox(AB_PROPERTY_KIND_WORDS.other, 'other_kind', true)}
          {whoQuestion}
          {communityBox}
          {detailBox(AB_NATURE_LABEL, 'nature')}
          {detailBox(AB_PLACE_OTHER_INFO_LABEL, 'other_info')}
        </>
      )}

      {(shape === 'vehicle' || shape === 'vehicle_no_mileage') && (
        <>
          {detailBox(AB_MAKE_LABEL, 'make', true)}
          {detailBox(AB_MODEL_LABEL, 'model')}
          {detailBox(AB_YEAR_LABEL, 'year')}
          {shape === 'vehicle' && detailBox(AB_MILEAGE_LABEL, 'mileage')}
          {detailBox(AB_VEHICLE_OTHER_INFO_LABEL, 'other_info')}
          {whoQuestion}
          {communityBox}
        </>
      )}

      {line.kinds.length > 0 && (
        <FormSelect
          label={key === '21' ? AB_ACCOUNT_TYPE_LABEL : AB_KIND_LABEL}
          name={`${prefix}_kind`}
          required
          options={line.kinds.map(([kind]) => ({ value: kind, label: AB_KIND_WORDS[key][kind] }))}
          value={details.kind ?? ''}
          onChange={(value) => setDetails({ kind: value === '' ? null : value })}
        />
      )}

      {shape === 'item_question' && (
        <fieldset className="form-field fee-waiver-question">
          <legend className="form-label">
            {AB_PERSONAL_INFO_QUESTION}
            {REQUIRED_MARK}
          </legend>
          <label className="ab-choice">
            <input
              type="radio"
              name={`${prefix}_has_personal_info`}
              value="no"
              checked={details.has_personal_info === false}
              onChange={() =>
                // The form prints what is stored, and a No has no Describe box
                onRowChange({
                  ...row,
                  description: '',
                  details: { ...details, has_personal_info: false },
                })
              }
            />
            No
          </label>
          <label className="ab-choice">
            <input
              type="radio"
              name={`${prefix}_has_personal_info`}
              value="yes"
              checked={details.has_personal_info === true}
              onChange={() => setDetails({ has_personal_info: true })}
            />
            Yes
          </label>
        </fieldset>
      )}

      {shape !== 'cash' && !hasEntire && shape !== 'item_question' && textBox}
      {shape === 'item_question' && details.has_personal_info === true && textBox}

      {shape === 'named_share' && (
        <FormField
          label={AB_PERCENT_LABEL}
          name={`${prefix}_percent`}
          type="number"
          inputMode="decimal"
          required
          min="0"
          max="100"
          step="0.01"
          value={details.percent ?? ''}
          onChange={(e) => {
            const parsed = parseAmount(e.target.value);
            // DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)
            const refused =
              parsed !== undefined && (parsed > 100 || amountError(parsed, 5) !== undefined);
            setPercentRefused(refused ? OUT_OF_RANGE_PERCENT : undefined);
            if (!refused) setDetails({ percent: parsed ?? null });
          }}
          error={percentRefused}
        />
      )}

      {shape === 'insurance' && detailBox(AB_BENEFICIARY_LABEL, 'beneficiary')}

      {valueBoxes}
    </section>
  );
}

export default AssetRowFields;
