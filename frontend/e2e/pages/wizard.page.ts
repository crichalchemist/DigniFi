/**
 * Wizard Page Object — wraps the multi-step intake wizard.
 *
 * Methods map to wizard steps and use name attributes / ARIA roles
 * from the actual components (DebtorInfoStep, IncomeInfoStep, etc.).
 */

import { expect, type Page } from '@playwright/test';
import type { PersonaDebtor, PersonaIncome, PersonaAsset, PersonaDebt } from '../fixtures/personas';

export class WizardPage {
  constructor(private page: Page) {}

  // ── Navigation ──────────────────────────────────────────────────

  async nextStep() {
    await this.page.getByRole('button', { name: /continue/i }).click();
    // Wait for step transition (network + render)
    await this.page.waitForTimeout(500);
  }

  async completeIntake() {
    await this.page.getByRole('button', { name: /complete intake/i }).click();
    // Fee-waiver-eligible sessions are routed to the waiver application
    // first (see IntakeWizard → /fee-waiver); everyone else goes to /forms.
    await this.page.waitForURL(/\/(forms|fee-waiver)/);
  }

  async getCurrentStep(): Promise<string> {
    const heading = this.page.locator('.step-title');
    return heading.textContent() as Promise<string>;
  }

  async getMeansTestPreview(): Promise<string> {
    const sidebar = this.page.locator('.wizard-sidebar');
    return sidebar.textContent() as Promise<string>;
  }

  /**
   * Wait for the debounced means-test estimate to resolve. The sidebar shows
   * a placeholder until income AND expense data have been saved, so call
   * this only after completing the expenses step.
   */
  async waitForMeansTestEstimate() {
    const sidebar = this.page.locator('.wizard-sidebar');
    await expect(sidebar).not.toContainText('once you provide income and expense', {
      timeout: 15000,
    });
  }

  // ── Step 1: Debtor Info ─────────────────────────────────────────

  async fillDebtorInfo(data: PersonaDebtor) {
    const fill = async (name: string, value: string) => {
      if (value) await this.page.locator(`input[name="${name}"]`).fill(value);
    };

    await fill('first_name', data.first_name);
    await fill('middle_name', data.middle_name);
    await fill('last_name', data.last_name);
    await fill('date_of_birth', data.date_of_birth);
    await fill('ssn', data.ssn);
    await fill('street_address', data.street_address);
    await fill('city', data.city);

    // State select
    const stateSelect = this.page.locator('select[name="state"], input[name="state"]');
    if ((await stateSelect.count()) > 0) {
      const tag = await stateSelect.first().evaluate((el) => el.tagName.toLowerCase());
      if (tag === 'select') {
        await stateSelect.first().selectOption(data.state);
      } else {
        await stateSelect.first().fill(data.state);
      }
    }

    await fill('zip_code', data.zip_code);
    await fill('email', data.email);
    await fill('phone_number', data.phone);

    // Household & filing info (required since the joint-filing feature)
    await fill('household_size', String(data.household_size));
    await this.page.locator('select[name="filing_type"]').selectOption(data.filing_type);
  }

  // ── Step 2: Income Info ─────────────────────────────────────────

  async fillIncomeInfo(income: PersonaIncome) {
    // The income step itemizes sources and requires a total > 0; enter the
    // persona's total as gross wages. Marital status / dependents are no
    // longer collected on this step.
    await this.page
      .locator('input[name="monthly_gross_wages"]')
      .fill(String(income.total_monthly_income));
  }

  // ── Step 3: Expenses ────────────────────────────────────────────

  /** Persona expense keys → current ExpenseInfoStep field names. */
  private static readonly EXPENSE_FIELD_MAP: Record<string, string> = {
    rent_or_mortgage: 'rent_or_mortgage',
    utilities: 'utilities',
    home_maintenance: 'home_maintenance',
    vehicle_payment: 'car_payment',
    vehicle_insurance: 'car_insurance',
    vehicle_maintenance: 'gas_transportation',
    food_and_groceries: 'food_groceries',
    clothing: 'other_necessary_expenses',
    medical_expenses: 'medical_expenses',
    childcare: 'childcare',
    child_support_paid: 'other_necessary_expenses',
    insurance_not_deducted: 'insurance_not_deducted',
    other_expenses: 'other_necessary_expenses',
  };

  async fillExpenses(expenses: Record<string, number>) {
    // Sum persona values into their mapped fields (several map to "other")
    const totals: Record<string, number> = {};
    for (const [key, value] of Object.entries(expenses)) {
      const field = WizardPage.EXPENSE_FIELD_MAP[key];
      if (!field) continue;
      totals[field] = (totals[field] || 0) + value;
    }
    for (const [field, value] of Object.entries(totals)) {
      await this.page.locator(`input[name="${field}"]`).fill(String(value));
    }
  }

  // ── Step 4: Assets ──────────────────────────────────────────────

  // Both steps render one empty row by default and suffix field names with
  // the row index (asset_type_0, creditor_name_1, ...). Track how many rows
  // we've filled so we only click "Add Another" from the second entry on.
  private assetCount = 0;
  private debtCount = 0;

  async addAsset(asset: PersonaAsset) {
    const index = this.assetCount;
    if (index > 0) {
      await this.page.getByRole('button', { name: /add another asset/i }).click();
    }

    await this.page.locator(`select[name="asset_type_${index}"]`).selectOption(asset.asset_type);
    await this.page.locator(`input[name="description_${index}"]`).fill(asset.description);
    await this.page
      .locator(`input[name="current_value_${index}"]`)
      .fill(String(asset.current_value));
    await this.page.locator(`input[name="amount_owed_${index}"]`).fill(String(asset.amount_owed));

    this.assetCount++;
  }

  // ── Step 5: Debts ───────────────────────────────────────────────

  async addDebt(debt: PersonaDebt) {
    const index = this.debtCount;
    if (index > 0) {
      await this.page.getByRole('button', { name: /add another amount owed/i }).click();
    }

    await this.page.locator(`select[name="debt_type_${index}"]`).selectOption(debt.debt_type);
    await this.page.locator(`input[name="creditor_name_${index}"]`).fill(debt.creditor_name);
    await this.page.locator(`input[name="amount_owed_${index}"]`).fill(String(debt.amount_owed));
    await this.page
      .locator(`input[name="monthly_payment_${index}"]`)
      .fill(String(debt.monthly_payment));

    // Secured debt types reveal a required collateral textarea; the step
    // blocks Continue until it's filled.
    if (debt.collateral_description) {
      await this.page
        .locator(`textarea[name="collateral_description_${index}"]`)
        .fill(debt.collateral_description);
    }

    this.debtCount++;
  }

  // ── Step 6: Review ──────────────────────────────────────────────

  async fillReview() {
    // Review step may just need a confirmation/acknowledgment
    const confirmCheck = this.page.locator(
      'input[type="checkbox"][name*="confirm"], input[type="checkbox"][name*="review"]'
    );
    if ((await confirmCheck.count()) > 0) {
      await confirmCheck.first().check();
    }
  }
}
