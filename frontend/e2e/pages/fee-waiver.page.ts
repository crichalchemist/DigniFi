/**
 * Fee Waiver Page Object — the waiver application shown after intake
 * completion for fee-waiver-eligible sessions (routes to /forms on submit).
 */

import type { Page } from '@playwright/test';

export class FeeWaiverPage {
  constructor(private page: Page) {}

  async submit(householdSize: number, monthlyIncome: number, monthlyExpenses: number) {
    await this.page.getByLabel(/household size/i).fill(String(householdSize));
    await this.page.getByLabel(/total monthly income/i).fill(String(monthlyIncome));
    await this.page.getByLabel(/total monthly expenses/i).fill(String(monthlyExpenses));
    await this.page.getByLabel(/cannot pay the full filing fee/i).check();
    await this.page.getByLabel(/cannot pay the filing fee in installments/i).check();
    await this.page.getByRole('button', { name: /submit waiver application/i }).click();
    await this.page.waitForURL('**/forms');
  }
}
