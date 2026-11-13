/**
 * Exemptions Page Object — Schedule C's line 1, the filer's claims and line 3, asked on the
 * page after the filing-fee page. Continues to /sofa.
 */

import { expect, type Page } from '@playwright/test';
import type { PersonaExemptions } from '../fixtures/personas';

export class ExemptionsPage {
  constructor(private page: Page) {}

  /** The page shows its questions only once the saved answers are read */
  async waitForLoad() {
    await this.page.waitForURL('**/exemptions');
    await expect(this.page.locator('h1')).toHaveText('The property you claim as exempt');
    await expect(this.page.locator('input[name="exemptions_line_1"]').first()).toBeVisible();
  }

  /** Answer line 1, press "not claiming" or add each claim, answer line 3 and continue */
  async answer(exemptions: PersonaExemptions) {
    await this.waitForLoad();
    await this.page
      .locator(`input[name="exemptions_line_1"][value="${exemptions.line_1}"]`)
      .check();

    if (exemptions.claims.length === 0) {
      await this.page
        .getByRole('button', { name: "I'm not claiming any property as exempt" })
        .click();
    }
    for (const [i, claim] of exemptions.claims.entries()) {
      await this.page.getByRole('button', { name: 'Add a claim' }).click();
      await this.page.locator(`select[name="claim_${i}_asset"]`).selectOption({
        label: claim.property,
      });
      await this.page.locator(`select[name="claim_${i}_law"]`).selectOption({ label: claim.law });
      const kind = claim.amount === 'fair_market_value' ? 'fair_market_value' : 'dollars';
      await this.page.locator(`input[name="claim_${i}_amount_kind"][value="${kind}"]`).check();
      // The amount box shows only once the dollar kind is checked
      if (claim.amount !== 'fair_market_value') {
        await this.page.locator(`input[name="claim_${i}_amount"]`).fill(String(claim.amount));
      }
      // The shorter-description box shows only once a property whose name doesn't fit is chosen
      if (claim.short) {
        await this.page.locator(`input[name="claim_${i}_short_description"]`).fill(claim.short);
      }
    }

    await this.page
      .locator(`input[name="exemptions_line_3"][value="${exemptions.line_3}"]`)
      .check();
    await this.page.getByRole('button', { name: 'Continue', exact: true }).click();
    await this.page.waitForURL('**/sofa');
  }
}
