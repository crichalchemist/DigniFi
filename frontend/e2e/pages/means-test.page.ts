/**
 * Means Test Page Object — Form 122A-2's questions, asked on the page after the exemptions page
 * to a filer the form applies to. Continues to /sofa.
 */

import { expect, type Locator, type Page } from '@playwright/test';
import type { MeansAskedLine, PersonaMeansTest } from '../fixtures/personas';

export class MeansTestPage {
  constructor(private page: Page) {}

  /** The page shows its questions only once the saved answers are read */
  async waitForLoad() {
    await this.page.waitForURL('**/means-test');
    await expect(this.page.locator('h1')).toHaveText(
      'Form 122A-2: Chapter 7 Means Test Calculation'
    );
    // The name has two radios, and a Playwright locator is strict
    await expect(this.page.locator('input[name="means_line_43"]').first()).toBeVisible();
  }

  private radio(name: string, value: string, scope: Page | Locator = this.page) {
    return scope.locator(`input[name="${name}"][value="${value}"]`);
  }

  /** Answer every question the persona answers; Continue is pressed apart, by continue() */
  async answer(data: PersonaMeansTest) {
    // Line 3 and the spouse's vehicles and loans: only a filer married and living together
    if (data.line_3) {
      await this.radio('means_line_3', data.line_3).check();
      for (const [i, row] of (data.line_3_rows ?? []).entries()) {
        await this.page.getByRole('button', { name: 'Add a row' }).click();
        await this.page.locator(`input[name="means_line_3_${i}_purpose"]`).fill(row.purpose);
        await this.page.locator(`input[name="means_line_3_${i}_amount"]`).fill(row.amount);
      }
    }
    if (data.spouse_vehicles)
      await this.radio('means_spouse_vehicles', data.spouse_vehicles).check();
    if (data.spouse_loans) await this.radio('means_spouse_loans', data.spouse_loans).check();

    // Line 11: each vehicle's claim, inside its own group (the legend also holds the required mark)
    for (const vehicle of data.vehicles) {
      const group = this.page.getByRole('group', {
        name: `Do you claim an ownership or operating expense for ${vehicle.name}?`,
      });
      await group.locator(`input[value="${vehicle.claimed}"]`).check();
    }
    const claimed = data.vehicles.some((vehicle) => vehicle.claimed === 'yes');

    const optIn = async (line: MeansAskedLine) => {
      const choice = data.opt_ins[line];
      if (!choice) return;
      await this.radio(`means_line_${line}`, choice.answer).check();
      if (choice.answer === 'yes' && choice.amount !== undefined) {
        await this.page.locator(`input[name="means_line_${line}_amount"]`).fill(choice.amount);
      }
    };

    // Line 15 is on the page only while a vehicle is claimed
    if (claimed) await optIn('15');

    for (const [line, amount] of Object.entries(data.amounts)) {
      await this.page.locator(`input[name="means_line_${line}"]`).fill(amount);
    }
    await optIn('22');

    // Line 25: its three amounts, then whether the filer spends the total
    await this.radio('means_line_25', data.line_25.answer).check();
    await this.page.locator('input[name="means_line_25_health"]').fill(data.line_25.health);
    await this.page.locator('input[name="means_line_25_disability"]').fill(data.line_25.disability);
    await this.page.locator('input[name="means_line_25_hsa"]').fill(data.line_25.hsa);
    await this.radio('means_line_25_spends', data.line_25.spends).check();

    for (const line of ['26', '27', '28', '29', '30', '31'] as const) await optIn(line);

    // Each secured debt's questions sit inside the region its creditor names
    for (const debt of data.debts) {
      const region = this.page.getByRole('region', { name: debt.creditor, exact: true });
      await region
        .locator('select[name$="_payments_left"]')
        .selectOption({ label: debt.payments_left });
      await region.locator(`input[name$="_changes"][value="${debt.changes}"]`).check();
    }

    await this.radio('means_line_34', data.line_34).check();
    await this.radio('means_line_36', data.line_36.answer).check();
    if (data.line_36.payment !== undefined) {
      await this.page.locator('input[name="means_line_36_payment"]').fill(data.line_36.payment);
    }
    await this.radio('means_line_43', data.line_43).check();
  }

  async continue() {
    await this.page.getByRole('button', { name: 'Continue', exact: true }).click();
  }

  /** The result block's words */
  async result() {
    return this.page.getByRole('status', { name: 'Income test' }).innerText();
  }

  line43Link() {
    return this.page.getByRole('link', { name: 'Go to line 43, special circumstances' });
  }

  /** The unnamed status beside Continue; the page has two status regions */
  status() {
    return this.page.locator('main > div[role="status"]');
  }

  /**
   * §8.2's phone layout, which jsdom can't see: at 375 x 800 the page has no horizontal scroll
   * and every hit target in main is at least 44 px tall. The viewport is put back after.
   */
  async checkPhoneWidth() {
    const original = this.page.viewportSize();
    await this.page.setViewportSize({ width: 375, height: 800 });
    try {
      const noSideScroll = await this.page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth
      );
      expect(noSideScroll).toBe(true);

      // A radio's hit target is its label, never the dot
      const targets = this.page.locator(
        'main label.ab-choice, main select, main input:not([type="radio"]), main textarea, main button'
      );
      const count = await targets.count();
      for (let i = 0; i < count; i++) {
        const target = targets.nth(i);
        if (!(await target.isVisible())) continue;
        const box = await target.boundingBox();
        expect(box?.height ?? 0, `target ${i} is at least 44 px tall`).toBeGreaterThanOrEqual(44);
      }
    } finally {
      if (original) await this.page.setViewportSize(original);
    }
  }
}
