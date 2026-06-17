/**
 * SOFA Page - Statement of Financial Affairs (Form 107)
 *
 * Config-driven sections that expand based on gate answers:
 * - Prior Income (has_prior_income toggle → row table)
 * - Creditor Payments (has_creditor_payments toggle → row table)
 * - Business (has_business toggle → fields)
 *
 * Trauma-informed design:
 * - "Amounts you paid" instead of "payments to creditors"
 * - Dignity-preserving explanations
 * - No shame around financial history
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { sofaReportAPI } from '../api/client';
import { Button, FormField } from '../components/common';
import { UPLDisclaimer } from '../components/compliance';
import type { SOFAReport, SOFAPriorIncome, SOFACreditorPayment } from '../types/api';

function emptyPriorIncome(): SOFAPriorIncome {
  return { id: 0, year: new Date().getFullYear() - 1, source: '', gross_amount: '' };
}

function emptyCreditorPayment(): SOFACreditorPayment {
  return { id: 0, creditor_name: '', total_paid: '', dates_of_payments: '' };
}

export function SOFAStep() {
  const navigate = useNavigate();
  const { session } = useIntake();

  const [report, setReport] = useState<SOFAReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Load report on mount
  useEffect(() => {
    if (!session) return;
    setLoading(true);
    sofaReportAPI
      .get(session.id)
      .then((data) => {
        setReport(data);
        // Ensure at least one empty row in each section when gated on
        if (data.has_prior_income && data.prior_income.length === 0) {
          data.prior_income.push(emptyPriorIncome());
        }
        if (data.has_creditor_payments && data.creditor_payments.length === 0) {
          data.creditor_payments.push(emptyCreditorPayment());
        }
      })
      .catch(() => setError('Could not load your financial history data.'))
      .finally(() => setLoading(false));
  }, [session]);

  // ── Gate toggles ──────────────────────────────────────────────

  const togglePriorIncome = () => {
    setReport((prev) => {
      if (!prev) return prev;
      const on = !prev.has_prior_income;
      return {
        ...prev,
        has_prior_income: on,
        prior_income:
          on && prev.prior_income.length === 0 ? [emptyPriorIncome()] : prev.prior_income,
      };
    });
  };

  const toggleCreditorPayments = () => {
    setReport((prev) => {
      if (!prev) return prev;
      const on = !prev.has_creditor_payments;
      return {
        ...prev,
        has_creditor_payments: on,
        creditor_payments:
          on && prev.creditor_payments.length === 0
            ? [emptyCreditorPayment()]
            : prev.creditor_payments,
      };
    });
  };

  // ── Row management ────────────────────────────────────────────

  const addPriorIncomeRow = () => {
    setReport((prev) => {
      if (!prev) return prev;
      return { ...prev, prior_income: [...prev.prior_income, emptyPriorIncome()] };
    });
  };

  const removePriorIncomeRow = (idx: number) => {
    setReport((prev) => {
      if (!prev) return prev;
      const rows = prev.prior_income.filter((_, i) => i !== idx);
      return { ...prev, prior_income: rows.length === 0 ? [emptyPriorIncome()] : rows };
    });
  };

  const updatePriorIncomeRow = (idx: number, field: keyof SOFAPriorIncome, value: unknown) => {
    setReport((prev) => {
      if (!prev) return prev;
      const rows = [...prev.prior_income];
      rows[idx] = { ...rows[idx], [field]: value };
      return { ...prev, prior_income: rows };
    });
  };

  const addCreditorPaymentRow = () => {
    setReport((prev) => {
      if (!prev) return prev;
      return { ...prev, creditor_payments: [...prev.creditor_payments, emptyCreditorPayment()] };
    });
  };

  const removeCreditorPaymentRow = (idx: number) => {
    setReport((prev) => {
      if (!prev) return prev;
      const rows = prev.creditor_payments.filter((_, i) => i !== idx);
      return { ...prev, creditor_payments: rows.length === 0 ? [emptyCreditorPayment()] : rows };
    });
  };

  const updateCreditorPaymentRow = (
    idx: number,
    field: keyof SOFACreditorPayment,
    value: unknown
  ) => {
    setReport((prev) => {
      if (!prev) return prev;
      const rows = [...prev.creditor_payments];
      rows[idx] = { ...rows[idx], [field]: value };
      return { ...prev, creditor_payments: rows };
    });
  };

  // ── Save ──────────────────────────────────────────────────────

  const handleSave = async () => {
    if (!session || !report) return;
    setSaving(true);
    setError(null);
    setSaved(false);

    try {
      // Clean empty rows before saving
      const clean = {
        ...report,
        prior_income: report.prior_income.filter((r) => r.source?.trim() || r.gross_amount),
        creditor_payments: report.creditor_payments.filter(
          (r) => r.creditor_name?.trim() || r.total_paid
        ),
      };
      await sofaReportAPI.patch(session.id, clean);
      setSaved(true);
      setTimeout(() => navigate('/forms'), 800);
    } catch {
      setError('Could not save your financial history. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // ── Loading state ─────────────────────────────────────────────

  if (loading) {
    return (
      <main className="sofa-page">
        <div className="loading-spinner" />
        <p>Loading your financial history...</p>
      </main>
    );
  }

  if (!session || !report) {
    return (
      <main className="sofa-page">
        <p>Please complete the intake wizard first.</p>
        <Button type="button" onClick={() => navigate('/intake')}>
          Go to Intake
        </Button>
      </main>
    );
  }

  // ── Render ────────────────────────────────────────────────────

  return (
    <main className="sofa-page">
      <div className="sofa-header">
        <h1>Statement of Financial Affairs</h1>
        <p className="sofa-description">
          This information goes into <strong>Form 107: Statement of Financial Affairs</strong> — a
          required court form that asks about your financial history over the past few years.
        </p>
        <UPLDisclaimer />
      </div>

      {error && (
        <div className="info-box info-box--error" role="alert">
          {error}
        </div>
      )}

      {saved && (
        <div className="info-box info-box--success" role="status">
          Saved! Redirecting to your forms...
        </div>
      )}

      {/* ── Section 1: Prior Income ────────────────────────── */}

      <section className="form-section sofa-section">
        <div className="sofa-section-header">
          <h2>Prior Income</h2>
          <label className="sofa-gate-toggle">
            <input
              type="checkbox"
              checked={report.has_prior_income}
              onChange={togglePriorIncome}
              aria-describedby="prior-income-desc"
            />
            <span>I had income in the past 3 years</span>
          </label>
        </div>
        <p id="prior-income-desc" className="sofa-section-desc">
          Tell us about your jobs and other income sources over the past 3 years. This helps the
          court understand your financial history.
        </p>

        {report.has_prior_income && (
          <div className="sofa-rows">
            {report.prior_income.map((row, idx) => (
              <div key={idx} className="sofa-row">
                <div className="sofa-row-header">
                  <span className="sofa-row-number">Income source {idx + 1}</span>
                  {report.prior_income.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removePriorIncomeRow(idx)}
                      className="remove-row-button"
                      aria-label={`Remove income source ${idx + 1}`}
                    >
                      Remove
                    </button>
                  )}
                </div>
                <div className="form-row">
                  <FormField
                    label="Year"
                    name={`prior-income-year-${idx}`}
                    type="number"
                    min="2018"
                    max="2026"
                    value={row.year || ''}
                    onChange={(e) =>
                      updatePriorIncomeRow(idx, 'year', parseInt(e.target.value, 10) || 0)
                    }
                    placeholder="2025"
                  />
                  <FormField
                    label="Source"
                    name={`prior-income-source-${idx}`}
                    type="text"
                    value={row.source}
                    onChange={(e) => updatePriorIncomeRow(idx, 'source', e.target.value)}
                    placeholder="Employer name or income type"
                    helpText="e.g., 'Walmart', 'Self-employment', 'Unemployment benefits'"
                  />
                  <FormField
                    label="Gross Amount"
                    name={`prior-income-amount-${idx}`}
                    type="number"
                    min="0"
                    step="0.01"
                    value={row.gross_amount}
                    onChange={(e) => updatePriorIncomeRow(idx, 'gross_amount', e.target.value)}
                    placeholder="0.00"
                  />
                </div>
              </div>
            ))}
            <Button type="button" variant="outline" onClick={addPriorIncomeRow}>
              + Add another income source
            </Button>
          </div>
        )}
      </section>

      {/* ── Section 2: Creditor Payments ───────────────────── */}

      <section className="form-section sofa-section">
        <div className="sofa-section-header">
          <h2>Amounts Paid to Creditors</h2>
          <label className="sofa-gate-toggle">
            <input
              type="checkbox"
              checked={report.has_creditor_payments}
              onChange={toggleCreditorPayments}
              aria-describedby="creditor-payments-desc"
            />
            <span>I made payments to creditors in the past year</span>
          </label>
        </div>
        <p id="creditor-payments-desc" className="sofa-section-desc">
          List any payments of $600 or more you made to a single creditor in the past year. This
          includes any payments a family member made on your behalf.
        </p>

        {report.has_creditor_payments && (
          <div className="sofa-rows">
            {report.creditor_payments.map((row, idx) => (
              <div key={idx} className="sofa-row">
                <div className="sofa-row-header">
                  <span className="sofa-row-number">Creditor {idx + 1}</span>
                  {report.creditor_payments.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeCreditorPaymentRow(idx)}
                      className="remove-row-button"
                      aria-label={`Remove creditor ${idx + 1}`}
                    >
                      Remove
                    </button>
                  )}
                </div>
                <div className="form-row">
                  <FormField
                    label="Creditor Name"
                    name={`creditor-name-${idx}`}
                    type="text"
                    value={row.creditor_name}
                    onChange={(e) => updateCreditorPaymentRow(idx, 'creditor_name', e.target.value)}
                    placeholder="Name of the creditor"
                  />
                  <FormField
                    label="Total Amount Paid"
                    name={`creditor-paid-${idx}`}
                    type="number"
                    min="0"
                    step="0.01"
                    value={row.total_paid}
                    onChange={(e) => updateCreditorPaymentRow(idx, 'total_paid', e.target.value)}
                    placeholder="0.00"
                  />
                  <FormField
                    label="Dates of Payments"
                    name={`creditor-dates-${idx}`}
                    type="text"
                    value={row.dates_of_payments}
                    onChange={(e) =>
                      updateCreditorPaymentRow(idx, 'dates_of_payments', e.target.value)
                    }
                    placeholder="e.g., Monthly Jan-Mar 2026"
                    helpText="When did you make these payments?"
                  />
                </div>
              </div>
            ))}
            <Button type="button" variant="outline" onClick={addCreditorPaymentRow}>
              + Add another creditor
            </Button>
          </div>
        )}
      </section>

      {/* ── Action Bar ─────────────────────────────────────── */}

      <div className="sofa-actions">
        <Button type="button" variant="secondary" onClick={() => navigate('/forms')}>
          Skip for now
        </Button>
        <Button type="button" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save & Continue'}
        </Button>
      </div>
    </main>
  );
}

export default SOFAStep;
