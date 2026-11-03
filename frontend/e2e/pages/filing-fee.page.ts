/**
 * Filing Fee Page Object — Form 101 line 8, "How you will pay the fee", which every filer
 * answers after Complete, with 103B lines 4, 5, 7 and 9 under the waiver. Continues to /sofa.
 */

import { expect, type Page } from '@playwright/test';
import type { PaymentChoice, PersonaWaiverAnswers } from '../fixtures/personas';

export class FilingFeePage {
  constructor(private page: Page) {}

  /** The page shows its choices only once the saved answers are read */
  async waitForLoad() {
    await this.page.waitForURL('**/filing-fee');
    await expect(this.page.locator('h1')).toHaveText('How you will pay the filing fee');
    await expect(this.page.locator('input[name="payment_choice"]').first()).toBeVisible();
  }

  /** The court's limit for the filer's family, as the page words it; limit as "$1,995.00" */
  limitSentence(familySize: number, limit: string) {
    return this.page.getByText(
      `150% of the official poverty line for a family of ${familySize}: ${limit} a month.`
    );
  }

  /** Choose, answer 103B's questions under the waiver, and continue to the SOFA step */
  async answer(choice: PaymentChoice, waiver?: PersonaWaiverAnswers) {
    await this.waitForLoad();
    await this.page.locator(`input[name="payment_choice"][value="${choice}"]`).check();
    if (choice === 'installments') {
      // §6.3: the page says where to get Form 103A, which DigniFi doesn't prepare yet
      await expect(
        this.page.getByRole('link', { name: 'Get Form 103A from the U.S. Courts website' })
      ).toBeVisible();
    }
    if (waiver) {
      const questions = ['income_change_answer', 'others_covered_answer', 'expense_change_answer'];
      for (const name of questions as (keyof PersonaWaiverAnswers)[]) {
        await this.page.locator(`input[name="${name}"][value="${waiver[name]}"]`).check();
      }
      await this.page
        .locator('textarea[name="installments_explanation"]')
        .fill(waiver.installments_explanation);
    }
    await this.page.getByRole('button', { name: 'Continue', exact: true }).click();
    await this.page.waitForURL('**/sofa');
  }
}
