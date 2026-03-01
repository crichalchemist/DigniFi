/**
 * Wizard Page Object — wraps the multi-step intake wizard.
 *
 * Methods map to wizard steps and use name attributes / ARIA roles
 * from the actual components (DebtorInfoStep, IncomeInfoStep, etc.).
 */

import type { Page } from '@playwright/test';
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
    await this.page.waitForURL('**/forms');
  }

  async getCurrentStep(): Promise<string> {
    const heading = this.page.locator('.step-title');
    return heading.textContent() as Promise<string>;
  }

  async getMeansTestPreview(): Promise<string> {
    const sidebar = this.page.locator('.wizard-sidebar');
    return sidebar.textContent() as Promise<string>;
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
    if (await stateSelect.count() > 0) {
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
  }

  // ── Step 2: Income Info ─────────────────────────────────────────

  async fillIncomeInfo(income: PersonaIncome) {
    // Select marital status
    const maritalSelect = this.page.locator(
      'select[name="marital_status"], input[name="marital_status"]',
    );
    if (await maritalSelect.count() > 0) {
      const tag = await maritalSelect.first().evaluate((el) => el.tagName.toLowerCase());
      if (tag === 'select') {
        await maritalSelect.first().selectOption(income.marital_status);
      } else {
        await maritalSelect.first().fill(income.marital_status);
      }
    }

    // Dependents
    const depsInput = this.page.locator('input[name="number_of_dependents"]');
    if (await depsInput.count() > 0) {
      await depsInput.fill(String(income.number_of_dependents));
    }

    // Monthly income
    const incomeInput = this.page.locator(
      'input[name="total_monthly_income"], input[name="monthly_income"]',
    );
    if (await incomeInput.count() > 0) {
      await incomeInput.first().fill(String(income.total_monthly_income));
    }
  }

  // ── Step 3: Expenses ────────────────────────────────────────────

  async fillExpenses(expenses: Record<string, number>) {
    for (const [name, value] of Object.entries(expenses)) {
      const input = this.page.locator(`input[name="${name}"]`);
      if ((await input.count()) > 0) {
        await input.fill(String(value));
      }
    }
  }

  // ── Step 4: Assets ──────────────────────────────────────────────

  async addAsset(asset: PersonaAsset) {
    // Click "Add Asset" button if present
    const addBtn = this.page.getByRole('button', { name: /add.*asset/i });
    if (await addBtn.isVisible()) {
      await addBtn.click();
      await this.page.waitForTimeout(300);
    }

    // Fill asset type
    const typeSelect = this.page.locator('select[name="asset_type"]');
    if (await typeSelect.count() > 0) {
      await typeSelect.last().selectOption(asset.asset_type);
    }

    // Fill fields in the last asset form (for multiple assets)
    const descInput = this.page.locator('input[name="description"]');
    if (await descInput.count() > 0) await descInput.last().fill(asset.description);

    const valueInput = this.page.locator('input[name="current_value"]');
    if (await valueInput.count() > 0) await valueInput.last().fill(String(asset.current_value));

    const owedInput = this.page.locator('input[name="amount_owed"]');
    if (await owedInput.count() > 0) await owedInput.last().fill(String(asset.amount_owed));

    if (asset.financial_institution) {
      const fiInput = this.page.locator('input[name="financial_institution"]');
      if (await fiInput.count() > 0) await fiInput.last().fill(asset.financial_institution);
    }
  }

  // ── Step 5: Debts ───────────────────────────────────────────────

  async addDebt(debt: PersonaDebt) {
    // Click "Add" button if present
    const addBtn = this.page.getByRole('button', { name: /add.*(debt|amount)/i });
    if (await addBtn.isVisible()) {
      await addBtn.click();
      await this.page.waitForTimeout(300);
    }

    const creditorInput = this.page.locator('input[name="creditor_name"]');
    if (await creditorInput.count() > 0) await creditorInput.last().fill(debt.creditor_name);

    const typeSelect = this.page.locator('select[name="debt_type"]');
    if (await typeSelect.count() > 0) await typeSelect.last().selectOption(debt.debt_type);

    const amountInput = this.page.locator('input[name="amount_owed"]');
    if (await amountInput.count() > 0) await amountInput.last().fill(String(debt.amount_owed));

    const paymentInput = this.page.locator('input[name="monthly_payment"]');
    if (await paymentInput.count() > 0) await paymentInput.last().fill(String(debt.monthly_payment));

    if (debt.is_in_collections) {
      const collectionsCheck = this.page.locator('input[name="is_in_collections"]');
      if (await collectionsCheck.count() > 0) await collectionsCheck.last().check();
    }
  }

  // ── Step 6: Review ──────────────────────────────────────────────

  async fillReview() {
    // Review step may just need a confirmation/acknowledgment
    const confirmCheck = this.page.locator(
      'input[type="checkbox"][name*="confirm"], input[type="checkbox"][name*="review"]',
    );
    if (await confirmCheck.count() > 0) {
      await confirmCheck.first().check();
    }
  }
}
