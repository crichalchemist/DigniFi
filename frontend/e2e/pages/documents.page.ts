/**
 * Documents Page Object — the upload step. IntakeWizard sends the filer here
 * after step 1 (Your Information) and before step 2 (Income).
 */

import { expect, type Page } from '@playwright/test';

export class DocumentsPage {
  constructor(private page: Page) {}

  /** Leave the upload step without uploading anything; the wizard resumes at Income. */
  async skip() {
    await this.page.waitForURL('**/documents');
    await expect(
      this.page.getByRole('heading', { level: 1, name: 'Upload your documents' })
    ).toBeVisible();
    await this.page.getByRole('button', { name: 'Skip for now', exact: true }).click();
    await this.page.waitForURL('**/intake');
  }
}
