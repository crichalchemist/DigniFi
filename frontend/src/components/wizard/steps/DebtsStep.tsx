/**
 * Debts Step - Creditor and amounts owed collection
 *
 * Trauma-informed design:
 * - "Amounts owed" language (not "debt")
 * - Non-judgmental tone
 * - Clear explanations of debt types
 * - Multiple debts support (add/remove)
 * - Privacy-conscious (account numbers encrypted)
 *
 * Each row asks what Schedules D and E/F ask of one claim, in the forms' words (3c3 §7.2).
 * Continue waits on the server's gaps (claims/debtGaps.ts), and the first one shows in a status
 * region, so a disabled Continue never says nothing.
 */

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { FormField, FormSelect, FormTextarea, Button } from '../../common';
import { UPLDisclaimer } from '../../compliance';
import { UPL_EXEMPTION_DISCLAIMER } from '../../../constants/upl';
import { ASSET_LINES } from '../../../constants/assetLines';
import { DEBT_TYPE_WORDS } from '../../../constants/claims';
import {
  ACCOUNT_SAVED,
  ADDRESS_HELP,
  ADD_ANOTHER_PARTY,
  AMOUNT_HELP,
  CHOOSE_ONE,
  CLAIM_STATUS_HELP,
  CLAIM_STATUS_NONE,
  CO_OWNED_NOTE,
  DATE_INCURRED_HELP,
  DEBTS_STEP_WHY,
  HOME_LINE_ADDITIONAL,
  HOME_LINE_FIRST,
  HOME_LINE_QUESTION,
  LIEN_HELP,
  LEGACY_REMOVE,
  LIEN_OTHER_LABEL,
  NOTICE_HELP,
  NOTICE_PARTY_HEADING,
  NOTICE_QUESTION,
  NOT_SAVED_TRY_AGAIN,
  NO_DEBTS_BUTTON,
  OFFSET_HELP,
  PAYMENT_SECURED_HELP,
  REMOVE_PARTY,
  SECURED_PREFILLED_NOTE,
  SECURED_QUESTION,
  SECURING_PROPERTY_LABEL,
  SECURING_PROPERTY_NONE,
  WHO_ONLY_YOU,
  WHO_WITH_SOMEONE,
} from '../../../constants/copy';
import {
  AB_WHO_QUESTION,
  CLAIM_LAST_4_LABEL,
  CLAIM_NOTICE_NAME_LABEL,
  CLAIM_OFFSET_QUESTION,
  CLAIM_STATUS_QUESTION,
  CLAIM_STATUS_WORDS,
  D_COMMUNITY_LABEL,
  D_DATE_LABEL,
  D_DESCRIBE_PROPERTY_LABEL,
  EF_COMMUNITY_LABEL,
  EF_DATE_LABEL,
  LIEN_KIND_WORDS,
  LIEN_QUESTION,
} from '../../../constants/formText';
import { isBlankDebt, keptRows } from '../../../utils/claimRows';
import { YesNoField } from './YesNoQuestion';
import { AddressFields } from './claims/AddressFields';
import { AmountBox } from './claims/AmountBox';
import {
  DATE_INCURRED_MAX_LENGTH,
  MAX_NOTICE_PARTIES,
  assetLabel,
  asksWho,
  fill,
  linkIsLive,
} from './claims/claimNames';
import { firstDebtGap } from './claims/debtGaps';
import type { LegacyGap } from './claims/legacyGaps';
import type {
  AssetInfo,
  AssetWho,
  ClaimStatus,
  DebtInfo,
  DebtRow,
  HomePaymentLine,
  LegacyField,
  LienKind,
  NoticeParty,
  WizardRow,
  YesNo,
} from '../../../types/api';

interface DebtsStepProps {
  /** The wizard's rows. The step keeps no copy, so an id a save writes into a row stays there. */
  rows: DebtRow[];
  onRowsChange: (rows: DebtRow[]) => void;
  /** "I have no amounts owed" is pressed (3c3 R18) */
  noDebts: boolean;
  onNoDebtsChange: (pressed: boolean) => void;
  /** The Assets step's rows, for the property a debt is secured by */
  assets: WizardRow<AssetInfo>[];
  onValidationChange: (isValid: boolean) => void;
  /** Stored payments the links don't cover (3c4 R10): shown with Remove, never a gap (B46) */
  legacyGaps?: LegacyGap[];
  onRemoveLegacy?: (field: LegacyField) => Promise<void>;
}

// Debt categories matching backend DEBT_TYPE_CHOICES with derived classification
// eslint-disable-next-line react-refresh/only-export-components
export const DEBT_CATEGORY_META: Record<
  DebtInfo['debt_type'],
  { label: string; is_secured: boolean; priority_classification: string }
> = {
  credit_card: {
    label: DEBT_TYPE_WORDS.credit_card,
    is_secured: false,
    priority_classification: 'unsecured',
  },
  medical: {
    label: DEBT_TYPE_WORDS.medical,
    is_secured: false,
    priority_classification: 'unsecured',
  },
  personal_loan: {
    label: DEBT_TYPE_WORDS.personal_loan,
    is_secured: false,
    priority_classification: 'unsecured',
  },
  student_loan: {
    label: DEBT_TYPE_WORDS.student_loan,
    is_secured: false,
    priority_classification: 'priority',
  },
  auto_loan: {
    label: DEBT_TYPE_WORDS.auto_loan,
    is_secured: true,
    priority_classification: 'secured',
  },
  mortgage: {
    label: DEBT_TYPE_WORDS.mortgage,
    is_secured: true,
    priority_classification: 'secured',
  },
  utility: {
    label: DEBT_TYPE_WORDS.utility,
    is_secured: false,
    priority_classification: 'unsecured',
  },
  other: { label: DEBT_TYPE_WORDS.other, is_secured: false, priority_classification: 'unsecured' },
};

const DEBT_CATEGORY_OPTIONS = Object.entries(DEBT_CATEGORY_META).map(([value, { label }]) => ({
  value,
  label,
}));

// The ticks in the form's order: a list sent in any other order would print in it
const LIEN_KINDS = Object.keys(LIEN_KIND_WORDS) as LienKind[];
const CLAIM_STATUSES = Object.keys(CLAIM_STATUS_WORDS) as ClaimStatus[];

// The last new row's key: unique while the page is open, and the prefix keeps it apart from a
// loaded row's key, which is its id
let nextKey = 0;

/** A new row with every key the server takes, and nothing answered (the filer's to answer) */
function createEmptyDebt(): DebtRow {
  return {
    _key: `new-${++nextKey}`,
    debt_type: undefined,
    creditor_name: '',
    account_number: '',
    amount_owed: undefined,
    monthly_payment: undefined,
    is_secured: false,
    collateral_description: '',
    street_address: '',
    street_2: '',
    city: '',
    state: '',
    zip_code: '',
    outside_us: false,
    secured_by: null,
    home_payment_line: null,
    collateral_who: null,
    lien: null,
    claim_status: null,
    offset_answer: null,
    notice_parties: null,
    community_debt: '',
    date_incurred: '',
    _securedPressed: false,
  };
}

function emptyParty(): NoticeParty {
  return {
    name: '',
    street_address: '',
    street_2: '',
    city: '',
    state: '',
    zip_code: '',
    outside_us: false,
    last_4: '',
  };
}

/** What a secured answer takes away from the side it hides (the filer's words stay) */
function securedChanges(isSecured: boolean): Partial<DebtRow> {
  return isSecured
    ? { is_secured: true, offset_answer: null }
    : { is_secured: false, secured_by: null, home_payment_line: null, collateral_who: null };
}

interface ChoiceGroupProps<V extends string> {
  legend: string;
  name: string;
  options: { value: V; label: string }[];
  selected: V | null | undefined;
  onSelect: (value: V) => void;
  required?: boolean;
}

/** One question with a radio for each way to answer it, nothing checked until the filer picks */
function ChoiceGroup<V extends string>({
  legend,
  name,
  options,
  selected,
  onSelect,
  required,
}: ChoiceGroupProps<V>) {
  return (
    <fieldset className="form-field fee-waiver-question">
      <legend className="form-label">
        {legend}
        {required && (
          <>
            {' '}
            <span className="required-indicator" aria-label="required">
              *
            </span>
          </>
        )}
      </legend>
      {options.map((option) => (
        <label key={option.value} className="fee-waiver-checkbox">
          <input
            type="radio"
            name={name}
            value={option.value}
            aria-required={required || undefined}
            checked={selected === option.value}
            onChange={() => onSelect(option.value)}
          />{' '}
          {option.label}
        </label>
      ))}
    </fieldset>
  );
}

interface CheckGroupProps {
  legend: string;
  help?: string;
  children: ReactNode;
}

/** A question answered by ticks. The mark is on the legend: the ticks are each optional alone. */
function CheckGroup({ legend, help, children }: CheckGroupProps) {
  return (
    <fieldset className="form-field fee-waiver-question">
      <legend className="form-label">
        {legend}{' '}
        <span className="required-indicator" aria-label="required">
          *
        </span>
      </legend>
      {help && <p className="form-help-text">{help}</p>}
      {children}
    </fieldset>
  );
}

export function DebtsStep({
  rows,
  onRowsChange,
  noDebts,
  onNoDebtsChange,
  assets,
  onValidationChange,
  legacyGaps = [],
  onRemoveLegacy,
}: DebtsStepProps) {
  // The field whose Remove failed; the figure stays and the step says it was not saved
  const [removeFailed, setRemoveFailed] = useState<LegacyField | null>(null);
  const removeLegacy = async (field: LegacyField) => {
    setRemoveFailed(null);
    try {
      await onRemoveLegacy?.(field);
    } catch {
      setRemoveFailed(field);
    }
  };
  // With no rows, the step shows one blank row. It joins the wizard's rows at the filer's first
  // edit, and a blank row is never saved.
  const [blankRow, setBlankRow] = useState(createEmptyDebt);
  const debts = useMemo(() => (rows.length > 0 ? rows : [blankRow]), [rows, blankRow]);
  // A box holding only part of a number keeps the row's figure without showing it
  const [partialBoxes, setPartialBoxes] = useState(0);
  const countPartialBox = useCallback(
    (change: 1 | -1) => setPartialBoxes((count) => count + change),
    []
  );

  const kept = keptRows(rows, isBlankDebt);
  const gap = firstDebtGap(rows, noDebts, assets);
  const isValid = gap === null && partialBoxes === 0;

  // Tell the parent whether the step can be saved
  useEffect(() => {
    onValidationChange(isValid);
  }, [isValid, onValidationChange]);

  // Any change to the rows takes back "I have no amounts owed": the answer is for an empty list
  const changeRows = (next: DebtRow[]) => {
    if (noDebts) onNoDebtsChange(false);
    onRowsChange(next);
  };

  const update = (index: number, changes: Partial<DebtRow>) =>
    changeRows(debts.map((debt, i) => (i === index ? { ...debt, ...changes } : debt)));

  const handleAddDebt = () => changeRows([...debts, createEmptyDebt()]);

  // Removing the last row brings the blank row back under a new key, so no box keeps the old typing
  const handleRemoveDebt = (index: number) => {
    const next = rows.filter((_, i) => i !== index);
    if (next.length === 0) setBlankRow(createEmptyDebt());
    changeRows(next);
  };

  // The one read of the pressed mark: the kind sets the secured answer only until the filer has
  // pressed it. The classification follows the kind either way.
  const changeType = (index: number, value: string) => {
    const meta = DEBT_CATEGORY_META[value as DebtInfo['debt_type']];
    const changes: Partial<DebtRow> = {
      debt_type: (value || undefined) as DebtInfo['debt_type'] | undefined,
      priority_classification: meta?.priority_classification as DebtInfo['priority_classification'],
    };
    if (meta && debts[index]._securedPressed !== true) {
      Object.assign(changes, securedChanges(meta.is_secured));
    }
    update(index, changes);
  };

  // The one write of the mark
  const answerSecured = (index: number, answer: YesNo) =>
    update(index, { ...securedChanges(answer === 'yes'), _securedPressed: true });

  // Another property's home line and who answers don't carry over
  const pickProperty = (index: number, value: string) =>
    update(index, {
      secured_by: value === '' ? null : Number(value),
      home_payment_line: null,
      collateral_who: null,
    });

  const toggleLien = (index: number, kind: LienKind, checked: boolean) => {
    const lien = debts[index].lien;
    const ticked = new Set(lien?.kinds ?? []);
    if (checked) ticked.add(kind);
    else ticked.delete(kind);
    if (ticked.size === 0) {
      update(index, { lien: null });
      return;
    }
    update(index, {
      lien: {
        kinds: LIEN_KINDS.filter((each) => ticked.has(each)),
        other: ticked.has('other') ? (lien?.other ?? '') : '',
      },
    });
  };

  const toggleStatus = (index: number, status: ClaimStatus, checked: boolean) => {
    const ticked = new Set(debts[index].claim_status ?? []);
    if (checked) ticked.add(status);
    else ticked.delete(status);
    update(index, {
      claim_status: ticked.size === 0 ? null : CLAIM_STATUSES.filter((each) => ticked.has(each)),
    });
  };

  const setNotice = (index: number, answer: YesNo) => {
    const parties = debts[index].notice_parties ?? [];
    update(index, {
      notice_parties: answer === 'no' ? [] : parties.length > 0 ? parties : [emptyParty()],
    });
  };

  const updateParty = (index: number, party: number, changes: Partial<NoticeParty>) =>
    update(index, {
      notice_parties: (debts[index].notice_parties ?? []).map((each, i) =>
        i === party ? { ...each, ...changes } : each
      ),
    });

  const addParty = (index: number) =>
    update(index, { notice_parties: [...(debts[index].notice_parties ?? []), emptyParty()] });

  const removeParty = (index: number, party: number) =>
    update(index, {
      notice_parties: (debts[index].notice_parties ?? []).filter((_, i) => i !== party),
    });

  const propertyChoices = assets
    .filter((asset) => asset.id !== undefined && asset.ab_line)
    .map((asset) => ({ value: String(asset.id), label: assetLabel(asset) }));

  return (
    <div className="debts-step">
      {/* Explainer */}
      <div className="info-box">
        <svg className="info-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
            clipRule="evenodd"
          />
        </svg>
        <div>
          <h3 className="info-title">About amounts you owe</h3>
          <p className="info-message">
            List all creditors (companies or people you owe money to). Include credit cards, medical
            bills, loans, and any other amounts owed.
          </p>
          <p className="info-message">{DEBTS_STEP_WHY}</p>
        </div>
      </div>

      {/* Debts List */}
      {debts.map((debt, index) => {
        const secured = debt.is_secured === true;
        const linked = linkIsLive(debt.secured_by, assets)
          ? assets.find((asset) => asset.id === debt.secured_by)
          : undefined;
        const linkedShape = ASSET_LINES.find((line) => line.key === linked?.ab_line)?.shape;
        const asksHome = secured && linked?.details?.lives_here === 'yes';
        const asksOwner = secured && linked !== undefined && !asksWho(linkedShape);
        const coOwned =
          secured &&
          (linked?.details?.who === 'with_someone' || debt.collateral_who === 'with_someone');
        const securedAnswer: YesNo | null = secured
          ? 'yes'
          : debt._securedPressed === true || debt.debt_type
            ? 'no'
            : null;
        const parties = debt.notice_parties;
        const noticeAnswer: YesNo | null =
          parties === null || parties === undefined ? null : parties.length > 0 ? 'yes' : 'no';
        const status = debt.claim_status;
        const lienKinds = debt.lien?.kinds ?? [];

        return (
          <section key={debt._key} className="form-section debt-card">
            <div className="debt-card-header">
              <h3 className="section-title">
                Amount Owed {index + 1}
                {debt.creditor_name && ` - ${debt.creditor_name}`}
                {debt.is_draft && (
                  <span aria-label="Pre-filled from document scan" className="draft-badge">
                    From scan
                  </span>
                )}
              </h3>
              {rows.length > 0 && (
                <button
                  type="button"
                  onClick={() => handleRemoveDebt(index)}
                  className="remove-debt-button"
                  aria-label={`Remove amount owed ${index + 1}`}
                >
                  <svg
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="remove-icon"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Remove
                </button>
              )}
            </div>

            {/* Debt Type Dropdown — 8 categories matching backend enum */}
            <FormSelect
              label="What kind of amount owed is this?"
              name={`debt_type_${index}`}
              options={DEBT_CATEGORY_OPTIONS}
              placeholder={CHOOSE_ONE}
              value={debt.debt_type ?? ''}
              onChange={(value) => changeType(index, value)}
              required
              helpText="Choose the category that best describes this amount owed"
            />

            <div className="form-row">
              {/* Draft until counsel rules on C-17 (DIG-280) */}
              <FormField
                label="Creditor Name"
                name={`creditor_name_${index}`}
                type="text"
                value={debt.creditor_name ?? ''}
                onChange={(e) => update(index, { creditor_name: e.target.value })}
                required
                helpText="Company or person you owe money to"
                placeholder="e.g., Capital One, Dr. Smith"
              />

              <div>
                <FormField
                  label="Account Number (Last 4 Digits)"
                  name={`account_number_${index}`}
                  type="text"
                  value={debt.account_number ?? ''}
                  onChange={(e) => update(index, { account_number: e.target.value })}
                  helpText="Optional - helps identify the account. Your account number is encrypted."
                  placeholder="XXXX-1234"
                />
                {debt.account_last_4 && (
                  <p className="form-help-text">
                    {fill(ACCOUNT_SAVED, { last4: debt.account_last_4 })}
                  </p>
                )}
              </div>
            </div>

            <p className="form-help-text">{ADDRESS_HELP}</p>
            <AddressFields
              prefix=""
              index={index}
              value={debt}
              onChange={(changes) => update(index, changes)}
              required
            />

            <div className="form-row">
              <AmountBox
                label="Amount Owed"
                name={`amount_owed_${index}`}
                value={debt.amount_owed}
                zeroIsBlank
                required
                maxDigits={12}
                help={AMOUNT_HELP}
                onValue={(value) => update(index, { amount_owed: value })}
                onPartialBox={countPartialBox}
              />

              <AmountBox
                label="Monthly Payment"
                name={`monthly_payment_${index}`}
                value={debt.monthly_payment}
                required={secured}
                maxDigits={10}
                help={secured ? PAYMENT_SECURED_HELP : 'Your regular monthly payment (if any)'}
                onValue={(value) => update(index, { monthly_payment: value })}
                onPartialBox={countPartialBox}
              />
            </div>

            <YesNoField
              legend={SECURED_QUESTION}
              name={`is_secured_${index}`}
              answer={securedAnswer}
              onAnswer={(answer) => answerSecured(index, answer)}
            />
            {securedAnswer !== null && debt._securedPressed !== true && (
              <p className="form-help-text">{SECURED_PREFILLED_NOTE}</p>
            )}

            {secured && (
              <div className="secured-answers">
                <FormSelect
                  label={SECURING_PROPERTY_LABEL}
                  name={`secured_by_${index}`}
                  options={propertyChoices}
                  placeholder={CHOOSE_ONE}
                  value={linked ? String(debt.secured_by) : ''}
                  onChange={(value) => pickProperty(index, value)}
                  required
                  helpText={propertyChoices.length === 0 ? SECURING_PROPERTY_NONE : undefined}
                />
                {coOwned && <p className="form-help-text">{CO_OWNED_NOTE}</p>}

                {asksHome && (
                  <ChoiceGroup<HomePaymentLine>
                    legend={HOME_LINE_QUESTION}
                    name={`home_payment_line_${index}`}
                    options={[
                      { value: 'first', label: HOME_LINE_FIRST },
                      { value: 'additional', label: HOME_LINE_ADDITIONAL },
                    ]}
                    selected={debt.home_payment_line}
                    onSelect={(value) => update(index, { home_payment_line: value })}
                    required
                  />
                )}

                {asksOwner && (
                  <ChoiceGroup<AssetWho>
                    legend={AB_WHO_QUESTION}
                    name={`collateral_who_${index}`}
                    options={[
                      { value: 'only_you', label: WHO_ONLY_YOU },
                      { value: 'with_someone', label: WHO_WITH_SOMEONE },
                    ]}
                    selected={debt.collateral_who}
                    onSelect={(value) => update(index, { collateral_who: value })}
                    required
                  />
                )}

                <CheckGroup legend={LIEN_QUESTION} help={LIEN_HELP}>
                  {LIEN_KINDS.map((kind) => (
                    <label key={kind} className="fee-waiver-checkbox">
                      <input
                        type="checkbox"
                        name={`lien_${index}`}
                        value={kind}
                        checked={lienKinds.includes(kind)}
                        onChange={(e) => toggleLien(index, kind, e.target.checked)}
                      />{' '}
                      {LIEN_KIND_WORDS[kind]}
                    </label>
                  ))}
                  {lienKinds.includes('other') && (
                    <FormField
                      label={LIEN_OTHER_LABEL}
                      name={`lien_other_${index}`}
                      type="text"
                      maxLength={255}
                      required
                      value={debt.lien?.other ?? ''}
                      onChange={(e) =>
                        update(index, { lien: { kinds: lienKinds, other: e.target.value } })
                      }
                    />
                  )}
                </CheckGroup>

                <FormTextarea
                  label={D_DESCRIBE_PROPERTY_LABEL}
                  name={`collateral_description_${index}`}
                  value={debt.collateral_description ?? ''}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                    update(index, { collateral_description: e.target.value })
                  }
                  required
                  rows={3}
                  placeholder="e.g., 2015 Honda Civic, Family home at 123 Main Street"
                />
              </div>
            )}

            <CheckGroup legend={CLAIM_STATUS_QUESTION} help={CLAIM_STATUS_HELP}>
              {CLAIM_STATUSES.map((each) => (
                <label key={each} className="fee-waiver-checkbox">
                  <input
                    type="checkbox"
                    name={`claim_status_${index}`}
                    value={each}
                    checked={status?.includes(each) ?? false}
                    onChange={(e) => toggleStatus(index, each, e.target.checked)}
                  />{' '}
                  {CLAIM_STATUS_WORDS[each]}
                </label>
              ))}
              <label className="fee-waiver-checkbox">
                <input
                  type="checkbox"
                  name={`claim_status_${index}`}
                  value="none"
                  checked={Array.isArray(status) && status.length === 0}
                  onChange={(e) => update(index, { claim_status: e.target.checked ? [] : null })}
                />{' '}
                {CLAIM_STATUS_NONE}
              </label>
            </CheckGroup>

            {!secured && (
              <>
                <YesNoField
                  legend={CLAIM_OFFSET_QUESTION}
                  name={`offset_answer_${index}`}
                  answer={debt.offset_answer}
                  onAnswer={(answer) => update(index, { offset_answer: answer })}
                  required
                />
                <p className="form-help-text">{OFFSET_HELP}</p>
              </>
            )}

            <FormField
              label={secured ? D_DATE_LABEL : EF_DATE_LABEL}
              name={`date_incurred_${index}`}
              type="text"
              maxLength={DATE_INCURRED_MAX_LENGTH}
              value={debt.date_incurred ?? ''}
              onChange={(e) => update(index, { date_incurred: e.target.value })}
              helpText={DATE_INCURRED_HELP}
            />

            <label className="fee-waiver-checkbox">
              <input
                type="checkbox"
                name={`community_debt_${index}`}
                value="yes"
                checked={debt.community_debt === 'yes'}
                onChange={(e) => update(index, { community_debt: e.target.checked ? 'yes' : '' })}
              />{' '}
              {secured ? D_COMMUNITY_LABEL : EF_COMMUNITY_LABEL}
            </label>

            <YesNoField
              legend={NOTICE_QUESTION}
              name={`notice_${index}`}
              answer={noticeAnswer}
              onAnswer={(answer) => setNotice(index, answer)}
              required
            />
            {parties !== null && parties !== undefined && parties.length > 0 && (
              <p className="form-help-text">{NOTICE_HELP}</p>
            )}
            {(parties ?? []).map((party, partyIndex) => (
              // A party has no key of its own: the list is held by position
              <div key={partyIndex} className="notice-party">
                <h4 className="section-title">
                  {fill(NOTICE_PARTY_HEADING, { n: String(partyIndex + 1) })}
                </h4>
                <FormField
                  label={CLAIM_NOTICE_NAME_LABEL}
                  name={`notice_${index}_${partyIndex}_name`}
                  type="text"
                  maxLength={255}
                  required
                  value={party.name}
                  onChange={(e) => updateParty(index, partyIndex, { name: e.target.value })}
                />
                <AddressFields
                  prefix={`notice_${index}_${partyIndex}_`}
                  value={party}
                  onChange={(changes) => updateParty(index, partyIndex, changes)}
                  required
                />
                <FormField
                  label={CLAIM_LAST_4_LABEL}
                  name={`notice_${index}_${partyIndex}_last_4`}
                  type="text"
                  maxLength={4}
                  value={party.last_4}
                  onChange={(e) => updateParty(index, partyIndex, { last_4: e.target.value })}
                />
                <Button
                  variant="text"
                  aria-label={fill(REMOVE_PARTY, {
                    n: String(partyIndex + 1),
                    debt: String(index + 1),
                  })}
                  onClick={() => removeParty(index, partyIndex)}
                >
                  Remove
                </Button>
              </div>
            ))}
            {parties !== null && parties !== undefined && parties.length > 0 && (
              <Button
                variant="outline"
                disabled={parties.length >= MAX_NOTICE_PARTIES}
                onClick={() => addParty(index)}
              >
                {ADD_ANOTHER_PARTY}
              </Button>
            )}
          </section>
        );
      })}

      {/* Add Debt Button */}
      <div className="add-debt-section">
        <Button
          variant="outline"
          onClick={handleAddDebt}
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="icon" aria-hidden="true">
              <path
                fillRule="evenodd"
                d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                clipRule="evenodd"
              />
            </svg>
          }
        >
          Add Another Amount Owed
        </Button>
        {kept.length === 0 && (
          <Button
            variant="outline"
            name="no_debts"
            aria-pressed={noDebts}
            onClick={() => onNoDebtsChange(!noDebts)}
          >
            {NO_DEBTS_BUTTON}
          </Button>
        )}
      </div>

      {/* A status, not an alert: a sentence can quote a row's name while it's typed. It stays
          mounted because a screen reader may not read a status region that arrives with its text. */}
      <div role="status">
        {gap !== null && (
          <div className="info-box">
            <p className="info-message">{gap}</p>
          </div>
        )}
      </div>

      {legacyGaps.map(({ field, sentence }) => (
        <div className="info-box" key={field}>
          <div>
            <p className="info-message" id={`legacy-${field}`}>
              {sentence}
            </p>
            <Button
              type="button"
              variant="outline"
              aria-describedby={`legacy-${field}`}
              onClick={() => removeLegacy(field)}
            >
              {LEGACY_REMOVE}
            </Button>
            {removeFailed === field && (
              <p className="form-error" role="alert">
                {NOT_SAVED_TRY_AGAIN}
              </p>
            )}
          </div>
        </div>
      ))}

      <UPLDisclaimer text={UPL_EXEMPTION_DISCLAIMER} variant="inline" />

      {/* Total Summary */}
      <section className="form-section form-section--summary">
        <div className="debts-total">
          <h3 className="total-label">Total Amounts Owed</h3>
          <p className="total-amount">
            $
            {debts
              .reduce((sum, debt) => sum + (debt.amount_owed || 0), 0)
              .toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
          </p>
          <p className="total-help-text">
            This is the total of all amounts you currently owe to creditors.
          </p>
        </div>
      </section>
    </div>
  );
}

export default DebtsStep;
