/**
 * A name and an address in Form 101's words (spec §6.0's party-and-address block): name where the
 * block has one, street, P.O. Box where it has one, city, state and ZIP. No second street line:
 * PetitionAnswers has no key for one, and step 1's street label says to include the unit (F-9).
 * Each box's name is its PetitionAnswers key, passed in (PF2-T8-5).
 */
import { FormField, FormSelect } from '../../../common';
import {
  AB_CITY_LABEL,
  AB_STATE_LABEL,
  AB_ZIP_LABEL,
  CLAIM_STREET_LABEL,
  FORM_101_PO_BOX,
} from '../../../../constants/formText';
import { PETITION_TEXT_LIMITS } from '../../../../constants/petitionLimits';
import type { PetitionAnswers } from '../../../../types/api';
import { zipDigits } from './masks';
import { US_STATES_AND_TERRITORIES } from './usStates';

type TextKey = {
  [K in keyof PetitionAnswers]-?: PetitionAnswers[K] extends string | null | undefined ? K : never;
}[keyof PetitionAnswers];

interface PartyAddressFieldsProps {
  answers: PetitionAnswers;
  onChange: (changes: Partial<PetitionAnswers>) => void;
  /** The name box and its label, where the block has one */
  name?: { key: TextKey; label: string };
  streetKey: TextKey;
  poBoxKey?: TextKey;
  cityKey: TextKey;
  stateKey: TextKey;
  zipKey: TextKey;
}

export function PartyAddressFields({
  answers,
  onChange,
  name,
  streetKey,
  poBoxKey,
  cityKey,
  stateKey,
  zipKey,
}: PartyAddressFieldsProps) {
  const text = (key: TextKey, label: string) => (
    <FormField
      label={label}
      name={key}
      type="text"
      maxLength={PETITION_TEXT_LIMITS[key]}
      value={answers[key] ?? ''}
      onChange={(e) => onChange({ [key]: e.target.value })}
    />
  );

  return (
    <div className="address-fields">
      {name && text(name.key, name.label)}
      {text(streetKey, CLAIM_STREET_LABEL)}
      {poBoxKey && text(poBoxKey, FORM_101_PO_BOX)}
      {text(cityKey, AB_CITY_LABEL)}
      <div className="form-row">
        <FormSelect
          label={AB_STATE_LABEL}
          name={stateKey}
          options={US_STATES_AND_TERRITORIES}
          value={answers[stateKey] ?? ''}
          onChange={(value) => onChange({ [stateKey]: value || null })}
        />
        {/* Digits only, applied before any length limit, so no native maxLength (Q1, PF2-4) */}
        <FormField
          label={AB_ZIP_LABEL}
          name={zipKey}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          value={answers[zipKey] ?? ''}
          onChange={(e) => onChange({ [zipKey]: zipDigits(e.target.value) })}
        />
      </div>
    </div>
  );
}
