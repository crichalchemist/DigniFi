/**
 * FormDashboard Page Object — form generation and survey interaction.
 */

import { expect, type Page } from '@playwright/test';

export class DashboardPage {
  constructor(private page: Page) {}

  /**
   * @param expectedCount Forms that should generate. Sessions without a
   * FeeWaiverApplication can't generate Form 103B (the waiver application
   * itself), so non-waiver personas expect 17.
   */
  async generateAllForms(expectedCount = 18) {
    const btn = this.page.getByRole('button', { name: /generate all/i });
    await btn.click();

    // Acknowledge the UPL confirmation modal that gates generation
    await this.page.locator('.upl-modal-checkbox').check();
    await this.page
      .locator('.upl-modal-footer')
      .getByRole('button', { name: /continue/i })
      .click();

    // Bulk generation hits 18 endpoints; wait for the progress text to settle
    await expect(this.page.locator('.form-dashboard-progress-text')).toContainText(
      `${expectedCount} of 18`,
      { timeout: 60000 }
    );
  }

  async getFormStatuses(): Promise<string[]> {
    // Each FormCard shows a status badge
    const cards = this.page.locator('.form-card');
    const count = await cards.count();
    const statuses: string[] = [];
    for (let i = 0; i < count; i++) {
      const status = await cards.nth(i).locator('.form-card-status').textContent();
      statuses.push((status ?? '').trim().toLowerCase());
    }
    return statuses;
  }

  async getGeneratedCount(): Promise<number> {
    const progressText = await this.page.locator('.form-dashboard-progress-text').textContent();
    const match = (progressText ?? '').match(/(\d+) of/);
    return match ? parseInt(match[1], 10) : 0;
  }

  async isSurveyVisible(): Promise<boolean> {
    return this.page.locator('.post-task-survey').isVisible();
  }

  async submitSurvey(responses: Record<string, number | string>) {
    for (const [questionId, value] of Object.entries(responses)) {
      if (typeof value === 'number') {
        // Likert scale — click the nth radio
        await this.page.locator(`input[name="${questionId}"][value="${value}"]`).check();
      } else {
        // Text area
        await this.page.locator(`#survey-${questionId}`).fill(value);
      }
    }
    await this.page.getByRole('button', { name: /submit feedback/i }).click();
  }

  async skipSurvey() {
    await this.page.locator('.survey-skip').click();
  }

  uplDisclaimer() {
    return this.page.locator('.upl-disclaimer--banner');
  }
}
