/**
 * SOFA Page Object — Form 107 Statement of Financial Affairs.
 *
 * Methods map to the standalone SOFA step page at /sofa.
 */

import { expect, type Page } from '@playwright/test';

export interface SOFAPriorIncomeRow {
  year: number;
  source: string;
  grossAmount: string;
}

export interface SOFACreditorPaymentRow {
  creditorName: string;
  totalPaid: string;
  datesOfPayments: string;
}

export class SOFAPage {
  constructor(private page: Page) {}

  /**
   * Wait for the SOFA page to be fully loaded.
   */
  async waitForLoad() {
    await expect(this.page.locator('h1')).toContainText('Statement of Financial Affairs');
  }

  /**
   * Toggle the Prior Income gate checkbox.
   * @param on true to check (show section), false to uncheck
   */
  async togglePriorIncome(on: boolean) {
    const checkbox = this.page.locator('.sofa-section').first().locator('input[type="checkbox"]');
    const isChecked = await checkbox.isChecked();
    if (isChecked !== on) {
      await checkbox.check({ force: true });
      if (on) await this.page.waitForTimeout(200);
    }
  }

  /**
   * Add a prior income row with the given data.
   */
  async addPriorIncomeRow(data: SOFAPriorIncomeRow) {
    // If this is the first row it's already present when gate is toggled on
    const rows = this.page.locator('.sofa-section').first().locator('.sofa-row');
    const count = await rows.count();

    // Check if we need the "Add another" button or it's the first/last existing row
    // We'll fill the last row and add a new one if needed
    const lastRow = rows.nth(count - 1);

    // Fill the row
    await lastRow.locator('input[type="number"]').first().fill(String(data.year));
    await lastRow.locator('input[type="text"]').first().fill(data.source);
    await lastRow.locator('input[type="number"]').last().fill(data.grossAmount);
  }

  /**
   * Click "Add another income source" button.
   */
  async clickAddPriorIncome() {
    const section = this.page.locator('.sofa-section').first();
    await section.getByRole('button', { name: /add another income source/i }).click();
  }

  /**
   * Toggle the Creditor Payments gate checkbox.
   * @param on true to check (show section), false to uncheck
   */
  async toggleCreditorPayments(on: boolean) {
    const checkbox = this.page
      .locator('.sofa-section')
      .nth(1)
      .locator('input[type="checkbox"]');
    const isChecked = await checkbox.isChecked();
    if (isChecked !== on) {
      await checkbox.check({ force: true });
      if (on) await this.page.waitForTimeout(200);
    }
  }

  /**
   * Add a creditor payment row with the given data.
   */
  async addCreditorPaymentRow(data: SOFACreditorPaymentRow) {
    const rows = this.page.locator('.sofa-section').nth(1).locator('.sofa-row');
    const count = await rows.count();
    const lastRow = rows.nth(count - 1);

    await lastRow.locator('input[type="text"]').first().fill(data.creditorName);
    await lastRow.locator('input[type="number"]').first().fill(data.totalPaid);
    await lastRow.locator('input[type="text"]').last().fill(data.datesOfPayments);
  }

  /**
   * Click "Add another creditor" button.
   */
  async clickAddCreditor() {
    const section = this.page.locator('.sofa-section').nth(1);
    await section.getByRole('button', { name: /add another creditor/i }).click();
  }

  /**
   * Click "Save & Continue" button.
   */
  async saveAndContinue() {
    await this.page.getByRole('button', { name: /save & continue/i }).click();
    // After saving, redirects to /forms
    await this.page.waitForURL(/\/forms/);
  }

  /**
   * Click "Skip for now" button.
   */
  async skipForNow() {
    await this.page.getByRole('button', { name: /skip for now/i }).click();
  }
}
