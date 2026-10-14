import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { api } from '../api/client';
import { Button } from '../components/common';
import { amountError } from '../utils/parseAmount';

export function FeeWaiverPage() {
  const navigate = useNavigate();
  const { session, meansTestResult } = useIntake();
  const sessionId = session?.id;

  const [householdSize, setHouseholdSize] = useState('');
  const [takeHomePay, setTakeHomePay] = useState('');
  // null until the filer picks Yes or No: neither is selected to start with
  const [receivesNoncash, setReceivesNoncash] = useState<boolean | null>(null);
  const [noncashKind, setNoncashKind] = useState('');
  const [cannotPayFull, setCannotPayFull] = useState(false);
  const [cannotPayInstallments, setCannotPayInstallments] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [savedRead, setSavedRead] = useState<'pending' | 'done' | 'failed'>('pending');
  const [readAttempt, setReadAttempt] = useState(0);

  // Pre-fill the household size the filer already gave during intake — they only need
  // to confirm it. Take-home pay is never pre-filled: the intake asks income before taxes.
  useEffect(() => {
    const hh = session?.debtor_info?.household_size;
    if (hh != null) setHouseholdSize((cur) => cur || String(hh));
  }, [session]);

  // Open with the answers this session already sent. They win over the pre-fill, so sending
  // the application again keeps every box the filer ticked (DIG-157). The form waits for the
  // read: an empty form sent over the saved answers would undo them.
  useEffect(() => {
    if (sessionId == null) return;
    let cancelled = false;
    api.feeWaiver
      .getBySession(sessionId)
      .then((saved) => {
        if (cancelled) return;
        if (saved) {
          setHouseholdSize(String(saved.household_size));
          setTakeHomePay(saved.monthly_take_home_pay ?? '');
          setReceivesNoncash(saved.receives_noncash_assistance);
          setNoncashKind(saved.benefit_types.join(', '));
          setCannotPayFull(saved.cannot_pay_full);
          setCannotPayInstallments(saved.cannot_pay_installments);
        }
        setSavedRead('done');
      })
      .catch(() => {
        if (!cancelled) setSavedRead('failed');
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, readAttempt]);

  const handleRetry = () => {
    setSavedRead('pending');
    setReadAttempt((attempt) => attempt + 1);
  };

  // Only show the application to filers the means test flags as fee-waiver
  // eligible. If we have a result and it says no, offer a gentle off-ramp
  // rather than a form they can't benefit from (note 21).
  const ineligible = meansTestResult != null && !meansTestResult.qualifies_for_fee_waiver;

  // The server refuses an amount it can't store, and its refusal could only say to try again,
  // so the box says what is wrong, as on the Income and Expenses steps
  const takeHomePayError = takeHomePay === '' ? undefined : amountError(Number(takeHomePay), 10);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session) return;
    if (
      !householdSize ||
      !takeHomePay ||
      receivesNoncash === null ||
      (receivesNoncash && !noncashKind.trim())
    ) {
      setError('Please fill in all required fields.');
      return;
    }
    // Said beside the box. An earlier alert for the whole form no longer holds. The message
    // showed while the filer typed, so focus goes to the box to show why nothing was sent.
    if (takeHomePayError) {
      setError(null);
      document.getElementById('take-home-pay')?.focus();
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await api.feeWaiver.create({
        session: session.id,
        household_size: parseInt(householdSize, 10),
        // The number amountError checked: the server counts the zeros past the cents of
        // "1250.500" as decimal places and refuses it
        monthly_take_home_pay: String(Number(takeHomePay)),
        receives_noncash_assistance: receivesNoncash,
        benefit_types: receivesNoncash ? [noncashKind.trim()] : [],
        cannot_pay_full: cannotPayFull,
        cannot_pay_installments: cannotPayInstallments,
      });
      // Form 107 is in every packet, so its questions come before the forms (DIG-149)
      navigate('/sofa');
    } catch {
      setError('Unable to submit your fee waiver application. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="fee-waiver-page">
      <h1>Filing Fee Waiver Application</h1>

      {ineligible && (
        <div className="fee-waiver-ineligible info-box" role="status">
          <p>
            Based on the information you entered, you don't appear to qualify for a filing fee
            waiver. That's okay — you can continue to your financial history and then your forms. A
            court makes the final decision.
          </p>
          <Button type="button" onClick={() => navigate('/sofa')}>
            Continue
          </Button>
        </div>
      )}

      {!ineligible && (
        <>
          <p>
            Based on your intake information, you may qualify to have the $338 filing fee waived.
            Please confirm the details below.
          </p>

          {savedRead === 'failed' && (
            <div className="fee-waiver-error">
              <p role="alert">
                We couldn't get your latest information just now. Please try again in a moment.
              </p>
              <Button type="button" onClick={handleRetry}>
                Try again
              </Button>
            </div>
          )}

          {error && (
            <div className="fee-waiver-error" role="alert">
              <p>{error}</p>
            </div>
          )}

          {savedRead === 'done' && (
            <form onSubmit={handleSubmit} noValidate>
              <div className="form-field">
                <label className="form-label" htmlFor="household-size">
                  Household Size
                </label>
                <input
                  className="form-input"
                  id="household-size"
                  type="number"
                  min={1}
                  value={householdSize}
                  onChange={(e) => setHouseholdSize(e.target.value)}
                  required
                />
              </div>

              <div className={`form-field ${takeHomePayError ? 'has-error' : ''}`}>
                <label className="form-label" htmlFor="take-home-pay">
                  Your average monthly take-home pay (after taxes and payroll deductions)
                </label>
                <input
                  className="form-input"
                  id="take-home-pay"
                  type="number"
                  min={0}
                  step="0.01"
                  value={takeHomePay}
                  onChange={(e) => setTakeHomePay(e.target.value)}
                  aria-describedby={takeHomePayError ? 'take-home-pay-error' : undefined}
                  aria-invalid={takeHomePayError ? 'true' : 'false'}
                  required
                />
                {takeHomePayError && (
                  <p
                    id="take-home-pay-error"
                    className="form-error"
                    role="alert"
                    aria-live="assertive"
                  >
                    {takeHomePayError}
                  </p>
                )}
              </div>

              <fieldset className="form-field fee-waiver-question">
                <legend className="form-label">
                  Do you receive non-cash help from the government, such as SNAP (food stamps) or a
                  housing subsidy?
                </legend>
                <label className="fee-waiver-checkbox">
                  <input
                    type="radio"
                    name="receives-noncash-assistance"
                    checked={receivesNoncash === true}
                    onChange={() => setReceivesNoncash(true)}
                  />{' '}
                  Yes
                </label>
                <label className="fee-waiver-checkbox">
                  <input
                    type="radio"
                    name="receives-noncash-assistance"
                    checked={receivesNoncash === false}
                    onChange={() => setReceivesNoncash(false)}
                  />{' '}
                  No
                </label>
              </fieldset>

              {receivesNoncash && (
                <div className="form-field">
                  <label className="form-label" htmlFor="noncash-kind">
                    What kind?
                  </label>
                  <input
                    className="form-input"
                    id="noncash-kind"
                    type="text"
                    maxLength={255}
                    value={noncashKind}
                    onChange={(e) => setNoncashKind(e.target.value)}
                    required
                  />
                </div>
              )}

              <div className="form-field">
                <label className="fee-waiver-checkbox">
                  <input
                    type="checkbox"
                    checked={cannotPayFull}
                    onChange={(e) => setCannotPayFull(e.target.checked)}
                  />{' '}
                  I cannot pay the full filing fee ($338) today
                </label>
              </div>

              <div className="form-field">
                <label className="fee-waiver-checkbox">
                  <input
                    type="checkbox"
                    checked={cannotPayInstallments}
                    onChange={(e) => setCannotPayInstallments(e.target.checked)}
                  />{' '}
                  I cannot pay the filing fee in installments
                </label>
              </div>

              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Submitting...' : 'Submit Waiver Application'}
              </Button>
            </form>
          )}
        </>
      )}
    </main>
  );
}
