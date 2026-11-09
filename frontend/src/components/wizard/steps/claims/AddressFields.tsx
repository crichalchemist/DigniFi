/**
 * An address in the form's words (3c3 §7.2): street, second line, city, state and ZIP, and a tick
 * for an address outside the United States, which has no state or ZIP to ask. Each box's name is
 * `${prefix}${field}` and `_${index}` after it when the row is one of a list.
 */
import { FormField } from '../../../common';
import {
  AB_ADDRESS_LINE_2_LABEL,
  OUTSIDE_US_HELP,
  OUTSIDE_US_LABEL,
} from '../../../../constants/copy';
import {
  AB_CITY_LABEL,
  AB_STATE_LABEL,
  AB_ZIP_LABEL,
  CLAIM_STREET_LABEL,
} from '../../../../constants/formText';
import type { AddressValue } from './claimNames';

interface AddressFieldsProps {
  prefix: string;
  index?: number;
  value: Partial<AddressValue>;
  onChange: (changes: Partial<AddressValue>) => void;
  required?: boolean;
}

// The column widths (Task 1): street and second line 255, city 100, state 2, ZIP 10
const STREET_MAX_LENGTH = 255;
const CITY_MAX_LENGTH = 100;
const STATE_MAX_LENGTH = 2;
const ZIP_MAX_LENGTH = 10;

export function AddressFields({ prefix, index, value, onChange, required }: AddressFieldsProps) {
  const name = (field: string) => `${prefix}${field}${index === undefined ? '' : `_${index}`}`;
  const outside = value.outside_us === true;
  const tickId = `field-${name('outside_us')}`;
  const tickHelpId = `${tickId}-help`;

  return (
    <div className="address-fields">
      <FormField
        label={CLAIM_STREET_LABEL}
        name={name('street_address')}
        type="text"
        maxLength={STREET_MAX_LENGTH}
        required={required}
        value={value.street_address ?? ''}
        onChange={(e) => onChange({ street_address: e.target.value })}
      />
      <FormField
        label={AB_ADDRESS_LINE_2_LABEL}
        name={name('street_2')}
        type="text"
        maxLength={STREET_MAX_LENGTH}
        value={value.street_2 ?? ''}
        onChange={(e) => onChange({ street_2: e.target.value })}
      />
      <FormField
        label={AB_CITY_LABEL}
        name={name('city')}
        type="text"
        maxLength={CITY_MAX_LENGTH}
        required={required}
        value={value.city ?? ''}
        onChange={(e) => onChange({ city: e.target.value })}
      />
      {!outside && (
        <div className="form-row">
          <FormField
            label={AB_STATE_LABEL}
            name={name('state')}
            type="text"
            maxLength={STATE_MAX_LENGTH}
            required={required}
            value={value.state ?? ''}
            onChange={(e) => onChange({ state: e.target.value })}
          />
          <FormField
            label={AB_ZIP_LABEL}
            name={name('zip_code')}
            type="text"
            maxLength={ZIP_MAX_LENGTH}
            required={required}
            value={value.zip_code ?? ''}
            onChange={(e) => onChange({ zip_code: e.target.value })}
          />
        </div>
      )}
      <div className="form-field">
        <label className="fee-waiver-checkbox" htmlFor={tickId}>
          <input
            id={tickId}
            type="checkbox"
            name={name('outside_us')}
            aria-describedby={tickHelpId}
            checked={outside}
            onChange={(e) =>
              onChange(
                e.target.checked
                  ? { outside_us: true, state: '', zip_code: '' }
                  : { outside_us: false }
              )
            }
          />{' '}
          {OUTSIDE_US_LABEL}
        </label>
        <p id={tickHelpId} className="form-help-text">
          {OUTSIDE_US_HELP}
        </p>
      </div>
    </div>
  );
}
