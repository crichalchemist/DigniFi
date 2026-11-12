import { useState } from 'react';
import { Button, FormField, FormSelect } from '../../components/common';
import { REQUIRED_MARK } from '../../components/wizard/steps/assets/AssetRowFields';
import { EXEMPTIONS_FAIR_MARKET_WORDS } from '../../constants/formText';
import {
  AMOUNT_NOT_A_NUMBER,
  EXEMPTIONS_AMOUNT_LABEL,
  EXEMPTIONS_ANOTHER_LAW,
  EXEMPTIONS_CHOOSE_ONE,
  EXEMPTIONS_CLAIM_NUMBER,
  EXEMPTIONS_DOLLAR_AMOUNT,
  EXEMPTIONS_LAW_LABEL,
  EXEMPTIONS_PROPERTY_LABEL,
  EXEMPTIONS_REMOVE_CLAIM,
  EXEMPTIONS_SHORT_LABEL,
  EXEMPTION_DESCRIPTION_TOO_LONG,
  EXEMPTION_ITEM_GONE,
} from '../../constants/copy';
import type { ExemptionAmountKind, ExemptionItem, ExemptionLaw } from '../../types/api';
import { claimAmountError, type ClaimRow } from './exemptionGaps';

const OTHER_LAW = '__other__';

interface Props {
  index: number;
  row: ClaimRow;
  items: ExemptionItem[];
  laws: ExemptionLaw[];
  onChange: (row: ClaimRow) => void;
  onRemove: () => void;
  /** The server's refusal of this row's short description or typed law, as a sentence */
  descriptionError?: string;
  otherLawError?: string;
}

const AMOUNT_KINDS: { value: ExemptionAmountKind; label: string }[] = [
  { value: 'dollars', label: EXEMPTIONS_DOLLAR_AMOUNT },
  { value: 'fair_market_value', label: EXEMPTIONS_FAIR_MARKET_WORDS },
];

/** One claim: a property, a law, an amount. Nothing is chosen for the filer. */
export function ClaimRowFields({
  index,
  row,
  items,
  laws,
  onChange,
  onRemove,
  descriptionError,
  otherLawError,
}: Props) {
  const item = items.find((candidate) => candidate.id === row.asset);
  // A box holding part of a number ('-') reads as empty, so the row can't show why Continue waits
  const [partialAmount, setPartialAmount] = useState(false);
  const lawValue = row.otherLawChosen ? OTHER_LAW : (row.law ?? '');

  const changeLaw = (value: string) => {
    if (value === OTHER_LAW) onChange({ ...row, law: null, otherLawChosen: true });
    else onChange({ ...row, law: value === '' ? null : value, otherLawChosen: false });
  };

  // Each row's group and Remove carry its number, so a screen reader tells nine claims apart
  const numbered = (template: string) => template.replace('{n}', String(index + 1));

  return (
    <fieldset className="exemption-claim fee-waiver-question">
      <legend className="form-label">{numbered(EXEMPTIONS_CLAIM_NUMBER)}</legend>
      <FormSelect
        label={EXEMPTIONS_PROPERTY_LABEL}
        name={`claim_${index}_asset`}
        placeholder={EXEMPTIONS_CHOOSE_ONE}
        value={row.asset === null ? '' : String(row.asset)}
        options={items.map((candidate) => ({
          value: String(candidate.id),
          label: `${candidate.name} (line ${candidate.line_label})`,
        }))}
        onChange={(value) => onChange({ ...row, asset: value === '' ? null : Number(value) })}
      />
      {row.id !== null && !item && <p className="form-help-text">{EXEMPTION_ITEM_GONE}</p>}

      <FormSelect
        label={EXEMPTIONS_LAW_LABEL}
        name={`claim_${index}_law`}
        placeholder={EXEMPTIONS_CHOOSE_ONE}
        value={lawValue}
        options={[
          ...laws.map((law) => ({ value: law.key, label: law.citation })),
          { value: OTHER_LAW, label: EXEMPTIONS_ANOTHER_LAW },
        ]}
        onChange={changeLaw}
      />
      {row.otherLawChosen && (
        <FormField
          label={EXEMPTIONS_ANOTHER_LAW}
          name={`claim_${index}_other_law`}
          maxLength={300}
          value={row.other_law}
          error={otherLawError}
          onChange={(event) => onChange({ ...row, other_law: event.target.value })}
        />
      )}

      <fieldset className="form-field fee-waiver-question">
        <legend className="form-label">
          {EXEMPTIONS_AMOUNT_LABEL}
          {REQUIRED_MARK}
        </legend>
        {AMOUNT_KINDS.map((kind) => (
          <div key={kind.value}>
            <label className="ab-choice ab-answer">
              <input
                type="radio"
                name={`claim_${index}_amount_kind`}
                value={kind.value}
                aria-required
                checked={row.amount_kind === kind.value}
                onChange={() => {
                  // The part-typed message belongs to the box, which a switch of kind unmounts
                  setPartialAmount(false);
                  onChange({ ...row, amount_kind: kind.value });
                }}
              />
              {kind.label}
            </label>
            {kind.value === 'dollars' && row.amount_kind === 'dollars' && (
              <FormField
                label={EXEMPTIONS_AMOUNT_LABEL}
                name={`claim_${index}_amount`}
                type="number"
                min="0"
                step="0.01"
                value={row.amount}
                // onInput too: onChange skips a '' to '' change, such as the first '-'
                onInput={(event) => setPartialAmount(event.currentTarget.validity.badInput)}
                onChange={(event) => onChange({ ...row, amount: event.target.value })}
                error={partialAmount ? AMOUNT_NOT_A_NUMBER : claimAmountError(row)}
              />
            )}
          </div>
        ))}
      </fieldset>

      {item && !item.description_fits && (
        <>
          <p className="form-help-text">{EXEMPTION_DESCRIPTION_TOO_LONG}</p>
          <FormField
            label={EXEMPTIONS_SHORT_LABEL}
            name={`claim_${index}_short_description`}
            maxLength={60}
            value={row.short_description}
            error={descriptionError}
            onChange={(event) => onChange({ ...row, short_description: event.target.value })}
          />
        </>
      )}

      <Button type="button" variant="outline" onClick={onRemove}>
        {numbered(EXEMPTIONS_REMOVE_CLAIM)}
      </Button>
    </fieldset>
  );
}
