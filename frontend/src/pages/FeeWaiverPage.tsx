import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { api } from '../api/client';
import { Button } from '../components/common';

export function FeeWaiverPage() {
  const navigate = useNavigate();
  const { session, meansTestResult } = useIntake();

  const [householdSize, setHouseholdSize] = useState('');
  const [monthlyIncome, setMonthlyIncome] = useState('');
  const [monthlyExpenses, setMonthlyExpenses] = useState('');
  const [receivesPublicBenefits, setReceivesPublicBenefits] = useState(false);
  const [cannotPayFull, setCannotPayFull] = useState(false);
  const [cannotPayInstallments, setCannotPayInstallments] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Pre-fill the figures the filer already gave during intake — they only need
  // to confirm them. Functional updates avoid clobbering any edits they make.
  useEffect(() => {
    if (!session) return;
    const hh = session.debtor_info?.household_size;
    const income = session.income_info?.total_monthly_income;
    const expenses = session.expense_info?.total_monthly_expenses;
    if (hh != null) setHouseholdSize((cur) => cur || String(hh));
    if (income != null) setMonthlyIncome((cur) => cur || String(income));
    if (expenses != null) setMonthlyExpenses((cur) => cur || String(expenses));
  }, [session]);

  // Only show the application to filers the means test flags as fee-waiver
  // eligible. If we have a result and it says no, offer a gentle off-ramp
  // rather than a form they can't benefit from (note 21).
  const ineligible = meansTestResult != null && !meansTestResult.qualifies_for_fee_waiver;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session) return;
    if (!householdSize || !monthlyIncome || !monthlyExpenses) {
      setError('Please fill in all required fields.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await api.feeWaiver.create({
        session: session.id,
        household_size: parseInt(householdSize, 10),
        monthly_income: monthlyIncome,
        monthly_expenses: monthlyExpenses,
        receives_public_benefits: receivesPublicBenefits,
        benefit_types: [],
        cannot_pay_full: cannotPayFull,
        cannot_pay_installments: cannotPayInstallments,
      });
      navigate('/forms');
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
            waiver. That's okay — you can continue to your forms. A court makes the final decision.
          </p>
          <Button type="button" onClick={() => navigate('/forms')}>
            Continue to my forms
          </Button>
        </div>
      )}

      {!ineligible && (
        <>
          <p>
            Based on your intake information, you may qualify to have the $338 filing fee waived.
            Please confirm the details below.
          </p>

          {error && (
            <div className="fee-waiver-error" role="alert">
              <p>{error}</p>
            </div>
          )}

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

            <div className="form-field">
              <label className="form-label" htmlFor="monthly-income">
                Total Monthly Income
              </label>
              <input
                className="form-input"
                id="monthly-income"
                type="number"
                min={0}
                step="0.01"
                value={monthlyIncome}
                onChange={(e) => setMonthlyIncome(e.target.value)}
                required
              />
            </div>

            <div className="form-field">
              <label className="form-label" htmlFor="monthly-expenses">
                Total Monthly Expenses
              </label>
              <input
                className="form-input"
                id="monthly-expenses"
                type="number"
                min={0}
                step="0.01"
                value={monthlyExpenses}
                onChange={(e) => setMonthlyExpenses(e.target.value)}
                required
              />
            </div>

            <div className="form-field">
              <label className="fee-waiver-checkbox">
                <input
                  type="checkbox"
                  checked={receivesPublicBenefits}
                  onChange={(e) => setReceivesPublicBenefits(e.target.checked)}
                />{' '}
                I receive SSI, SNAP, TANF, or other means-tested public benefits
              </label>
            </div>

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
        </>
      )}
    </main>
  );
}
