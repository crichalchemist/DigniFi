/**
 * Fee Waiver Page Object — the waiver application shown after intake
 * completion for fee-waiver-eligible sessions (continues to /sofa on submit).
 */

import type { Page } from '@playwright/test';

export class FeeWaiverPage {
  constructor(private page: Page) {}

  /** noncashAssistance is the "What kind?" answer, or null to answer No */
  async submit(householdSize: number, takeHomePay: number, noncashAssistance: string | null) {
    await this.page.getByLabel(/household size/i).fill(String(householdSize));
    await this.page.getByLabel(/take-home pay/i).fill(String(takeHomePay));
    const question = this.page.getByRole('group', { name: /non-cash help/i });
    if (noncashAssistance === null) {
      await question.getByRole('radio', { name: 'No' }).check();
    } else {
      await question.getByRole('radio', { name: 'Yes' }).check();
      await this.page.getByLabel('What kind?').fill(noncashAssistance);
    }
    await this.page.getByLabel(/cannot pay the full filing fee/i).check();
    await this.page.getByLabel(/cannot pay the filing fee in installments/i).check();
    await this.page.getByRole('button', { name: /submit waiver application/i }).click();
    await this.page.waitForURL('**/sofa');
  }
}
