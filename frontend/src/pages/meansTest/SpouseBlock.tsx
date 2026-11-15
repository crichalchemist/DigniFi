import { Button, FormField, FormSelect } from '../../components/common';
import { REQUIRED_MARK } from '../../components/wizard/steps/assets/AssetRowFields';
import {
  MEANS_SPOUSE_ADD_LOAN,
  MEANS_SPOUSE_ADD_VEHICLE,
  MEANS_SPOUSE_INTRO,
  MEANS_SPOUSE_LOAN_CREDITOR,
  MEANS_SPOUSE_LOAN_HOME,
  MEANS_SPOUSE_LOAN_LEGEND,
  MEANS_SPOUSE_LOAN_ON_AMOUNTS_OWED,
  MEANS_SPOUSE_LOAN_OTHER,
  MEANS_SPOUSE_LOAN_PAYMENT,
  MEANS_SPOUSE_LOAN_PROPERTY,
  MEANS_SPOUSE_LOAN_SECURED_BY,
  MEANS_SPOUSE_LOAN_WHICH,
  MEANS_SPOUSE_LOAN_WHICH_NOTE,
  MEANS_SPOUSE_LOANS_HINT,
  MEANS_SPOUSE_LOANS_QUESTION,
  MEANS_SPOUSE_REMOVE_LOAN,
  MEANS_SPOUSE_REMOVE_VEHICLE,
  MEANS_SPOUSE_TITLE,
  MEANS_SPOUSE_VEHICLE_DESCRIBE,
  MEANS_SPOUSE_VEHICLE_LEASED,
  MEANS_SPOUSE_VEHICLE_LEGEND,
  MEANS_SPOUSE_VEHICLES_QUESTION,
} from '../../constants/copy';
import type { MeansPage, YesNo } from '../../types/api';
import { AmountBox } from './AmountBox';
import {
  line11Vehicles,
  spouseLoanViews,
  type KeyedSpouseLoan,
  type KeyedSpouseVehicle,
  type PageAnswers,
  type PageState,
} from './pageState';
import { YesNoQuestion } from './YesNoQuestion';

/** The server refuses a list of more than 10 rows (MAX_ROWS in apps/intake/means_test.py) */
const MAX_ROWS = 10;
/** The serializer's limit on each spouse text box, before the fit check */
const MAX_TEXT = 200;

interface SpouseBlockProps {
  page: MeansPage;
  answers: PageAnswers;
  edit: (change: (current: PageState) => PageState) => void;
  /** The page's one counter: a new row's first ref and its key */
  nextKey: () => string;
  /** Sentences about a box the server refused, by `spouse_vehicle:<_key>:description` and so on */
  boxErrors: Record<string, string>;
  clearBoxError: (key: string) => void;
}

const number = (sentence: string, n: number) => sentence.replace('{n}', String(n));

/** Line 3's neighbour: the spouse's vehicles and loans (spec 8.12), under married_together only */
export function SpouseBlock({
  page,
  answers,
  edit,
  nextKey,
  boxErrors,
  clearBoxError,
}: SpouseBlockProps) {
  const setAnswers = (change: Partial<PageAnswers>) =>
    edit((current) => ({ ...current, answers: { ...current.answers, ...change } }));
  const changeVehicle = (key: string, change: Partial<KeyedSpouseVehicle>) =>
    edit((current) => ({
      ...current,
      answers: {
        ...current.answers,
        spouse_vehicles: current.answers.spouse_vehicles.map((row) =>
          row._key === key ? { ...row, ...change } : row
        ),
      },
    }));
  const changeLoan = (key: string, change: Partial<KeyedSpouseLoan>) =>
    edit((current) => ({
      ...current,
      answers: {
        ...current.answers,
        spouse_loans: current.answers.spouse_loans.map((row) =>
          row._key === key ? { ...row, ...change } : row
        ),
      },
    }));

  // Built inside the updater, from the latest state, so two queued adds never drop a row
  const addVehicle = () => {
    const key = nextKey();
    edit((current) => ({
      ...current,
      answers: {
        ...current.answers,
        spouse_vehicles: [
          ...current.answers.spouse_vehicles,
          { _key: key, ref: key, description: '', leased: null, claimed: null },
        ],
      },
    }));
  };
  const addLoan = () => {
    const key = nextKey();
    edit((current) => ({
      ...current,
      answers: {
        ...current.answers,
        spouse_loans: [
          ...current.answers.spouse_loans,
          {
            _key: key,
            ref: key,
            on_amounts_owed: null,
            debt: null,
            creditor: '',
            secured_by: null,
            property: '',
            payment: null,
            payments_left: null,
            payment_changes: null,
            total_60_months: null,
            taxes_or_insurance: null,
            necessary_for_support: null,
            cure: null,
          },
        ],
      },
    }));
  };

  // What the loans read as once their references are live; the views run in the rows' order
  const views = spouseLoanViews(page, { answers, debts: [] });
  const listed = line11Vehicles(page, answers);
  const filerRefs = new Set(page.vehicles.map((vehicle) => vehicle.ref));
  // A debt named by a Yes row (earlier or later) is offered to no other row
  const taken = (own: KeyedSpouseLoan) =>
    new Set(
      views
        .filter(({ loan }) => loan._key !== own._key && loan.on_amounts_owed === 'yes')
        .map(({ loan }) => loan.debt)
    );

  return (
    <div className="means-line">
      <h2>{MEANS_SPOUSE_TITLE}</h2>
      <p className="form-help-text">{MEANS_SPOUSE_INTRO}</p>

      <YesNoQuestion
        question={MEANS_SPOUSE_VEHICLES_QUESTION}
        name="means_spouse_vehicles"
        value={answers.spouse_vehicles_answer}
        onChange={(next) => setAnswers({ spouse_vehicles_answer: next })}
      />
      {answers.spouse_vehicles_answer === 'yes' && (
        <>
          {answers.spouse_vehicles.map((row, index) => {
            const errorKey = `spouse_vehicle:${row._key}:description`;
            return (
              <fieldset key={row._key} className="form-field fee-waiver-question">
                <legend className="form-label">
                  {number(MEANS_SPOUSE_VEHICLE_LEGEND, index + 1)}
                </legend>
                <FormField
                  label={MEANS_SPOUSE_VEHICLE_DESCRIBE}
                  name={`means_spouse_vehicle_${index}_name`}
                  value={row.description}
                  maxLength={MAX_TEXT}
                  error={boxErrors[errorKey]}
                  onChange={(event) => {
                    clearBoxError(errorKey);
                    changeVehicle(row._key, { description: event.target.value });
                  }}
                />
                <YesNoQuestion
                  question={MEANS_SPOUSE_VEHICLE_LEASED}
                  name={`means_spouse_vehicle_${index}_leased`}
                  value={row.leased}
                  onChange={(next) => changeVehicle(row._key, { leased: next })}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() =>
                    edit((current) => ({
                      ...current,
                      answers: {
                        ...current.answers,
                        spouse_vehicles: current.answers.spouse_vehicles.filter(
                          (own) => own._key !== row._key
                        ),
                      },
                    }))
                  }
                >
                  {number(MEANS_SPOUSE_REMOVE_VEHICLE, index + 1)}
                </Button>
              </fieldset>
            );
          })}
          {answers.spouse_vehicles.length < MAX_ROWS && (
            <Button type="button" variant="outline" onClick={addVehicle}>
              {MEANS_SPOUSE_ADD_VEHICLE}
            </Button>
          )}
        </>
      )}

      <YesNoQuestion
        question={MEANS_SPOUSE_LOANS_QUESTION}
        name="means_spouse_loans"
        note={MEANS_SPOUSE_LOANS_HINT}
        value={answers.spouse_loans_answer}
        onChange={(next) => setAnswers({ spouse_loans_answer: next })}
      />
      {answers.spouse_loans_answer === 'yes' && (
        <>
          {answers.spouse_loans.map((row, index) => {
            const view = views[index];
            const loan = view?.loan ?? row;
            const name = `means_spouse_loan_${index}`;
            const creditorKey = `spouse_loan:${row._key}:creditor`;
            const propertyKey = `spouse_loan:${row._key}:property`;
            const onList = loan.on_amounts_owed === 'yes';
            const named = taken(row);
            const securedChoices = [
              { value: 'home', label: MEANS_SPOUSE_LOAN_HOME },
              // An Amounts Owed loan names only the spouse's vehicles (a filer's own is on that step)
              ...listed
                .filter((vehicle) => !(onList && filerRefs.has(vehicle.ref)))
                .map((vehicle) => ({ value: vehicle.ref, label: vehicle.name })),
              { value: 'other', label: MEANS_SPOUSE_LOAN_OTHER },
            ];
            const property = loan.secured_by === 'home' || loan.secured_by === 'other';
            return (
              <fieldset key={row._key} className="form-field fee-waiver-question">
                <legend className="form-label">
                  {number(MEANS_SPOUSE_LOAN_LEGEND, index + 1)}
                </legend>
                <YesNoQuestion
                  question={MEANS_SPOUSE_LOAN_ON_AMOUNTS_OWED}
                  name={`${name}_on_amounts_owed`}
                  value={row.on_amounts_owed}
                  onChange={(next: YesNo) => changeLoan(row._key, { on_amounts_owed: next })}
                />
                {onList && (
                  <FormSelect
                    label={MEANS_SPOUSE_LOAN_WHICH}
                    name={`${name}_debt`}
                    placeholder=""
                    required
                    helpText={MEANS_SPOUSE_LOAN_WHICH_NOTE}
                    value={loan.debt === null ? '' : String(loan.debt)}
                    options={page.amounts_owed_loans
                      .filter((debt) => !named.has(debt.id))
                      .map((debt) => ({ value: String(debt.id), label: debt.creditor }))}
                    onChange={(value) =>
                      changeLoan(row._key, { debt: value === '' ? null : Number(value) })
                    }
                  />
                )}
                {row.on_amounts_owed === 'no' && (
                  <FormField
                    label={MEANS_SPOUSE_LOAN_CREDITOR}
                    name={`${name}_creditor`}
                    value={row.creditor}
                    maxLength={MAX_TEXT}
                    error={boxErrors[creditorKey]}
                    onChange={(event) => {
                      clearBoxError(creditorKey);
                      changeLoan(row._key, { creditor: event.target.value });
                    }}
                  />
                )}
                <fieldset className="form-field fee-waiver-question">
                  <legend className="form-label">
                    {MEANS_SPOUSE_LOAN_SECURED_BY}
                    {REQUIRED_MARK}
                  </legend>
                  <div className="ab-yes-no">
                    {securedChoices.map((choice) => (
                      <label key={choice.value} className="ab-choice ab-answer">
                        <input
                          type="radio"
                          name={`${name}_secured_by`}
                          value={choice.value}
                          aria-required
                          checked={loan.secured_by === choice.value}
                          onChange={() => changeLoan(row._key, { secured_by: choice.value })}
                        />
                        {choice.label}
                      </label>
                    ))}
                  </div>
                </fieldset>
                {property && (
                  <FormField
                    label={MEANS_SPOUSE_LOAN_PROPERTY}
                    name={`${name}_property`}
                    value={row.property}
                    maxLength={MAX_TEXT}
                    error={boxErrors[propertyKey]}
                    onChange={(event) => {
                      clearBoxError(propertyKey);
                      changeLoan(row._key, { property: event.target.value });
                    }}
                  />
                )}
                <AmountBox
                  name={`${name}_payment`}
                  label={MEANS_SPOUSE_LOAN_PAYMENT}
                  value={row.payment}
                  onChange={(value) => changeLoan(row._key, { payment: value })}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() =>
                    edit((current) => ({
                      ...current,
                      answers: {
                        ...current.answers,
                        spouse_loans: current.answers.spouse_loans.filter(
                          (own) => own._key !== row._key
                        ),
                      },
                    }))
                  }
                >
                  {number(MEANS_SPOUSE_REMOVE_LOAN, index + 1)}
                </Button>
              </fieldset>
            );
          })}
          {answers.spouse_loans.length < MAX_ROWS && (
            <Button type="button" variant="outline" onClick={addLoan}>
              {MEANS_SPOUSE_ADD_LOAN}
            </Button>
          )}
        </>
      )}
    </div>
  );
}
