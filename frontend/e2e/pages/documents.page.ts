/**
 * Documents Page Object — the upload step between wizard step 1 and step 2.
 *
 * Locators follow the upload page's E2E contract (spec 2026-10-09 §4.10): the
 * drop-zone aria-label pattern, the "Upload queue" list, a done row containing
 * "Done", and the "Skip for now" / "Continue" button labels.
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

  /** Send one file through the "Bills and statements" area (document type creditor_bill). */
  async uploadBill(filePath: string) {
    const zone = this.page.getByRole('button', {
      name: 'Bills and statements: drop files here or click to upload',
    });
    // The zone is aria-disabled until the session exists and while a file is sending.
    await expect(zone).toBeEnabled();
    await zone.locator('input[type="file"]').setInputFiles(filePath);
  }

  /** Wait until a file in the upload queue has been read ("✓ Done"). */
  async expectDone() {
    const queue = this.page.getByRole('list', { name: 'Upload queue' });
    await expect(queue.getByRole('listitem').filter({ hasText: /\bDone\b/ })).toBeVisible({
      timeout: 30_000,
    });
  }
}
