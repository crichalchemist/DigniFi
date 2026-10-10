/**
 * Scanned bill — from upload to Amounts Owed (spec 2026-10-09 §4.12; DIG-1, DIG-6)
 *
 * A filer uploads a photo of a bill after step 1 and sees it read. At Amounts Owed
 * the creditor, the kind of debt and the amount are already filled in, and they are
 * still there after the filer saves and reloads. The real backend reads the upload;
 * only OpenAI is replaced, by the fake server this spec starts (fixtures/fake-openai.ts).
 *
 * Wiring: the backend and this runner both need OPENAI_BASE_URL=http://127.0.0.1:4010/v1,
 * and the backend also needs OCR_PROVIDER=openai and a dummy OPENAI_API_KEY. The CI E2E
 * job sets all three at job level. Without them this journey skips locally (and prints
 * why) and fails in CI.
 *
 * fixtures/synthetic-bill.png is a fictional patient statement drawn with PyMuPDF
 * (Lakeside Example Clinic, account ending 4821, amount due $1,247.83, due 10/15/2026).
 * The fake never looks at it; CANNED_BILL is what a model would read from it.
 *
 * Not asserted:
 * - The "From scan" badge after the reload. Saving debts clears is_draft
 *   (intake/views.py), so the badge is gone once step 5 has saved (DIG-14).
 * - The account number. It is write-only; backend tests prove saving keeps it.
 */

import { fileURLToPath } from 'node:url';
import { test, expect, type Page } from '@playwright/test';
import { SARAH, type PersonaData } from '../fixtures/personas';
import { CANNED_BILL, startFakeOpenAI } from '../fixtures/fake-openai';
import { RegisterPage } from '../pages/register.page';
import { DocumentsPage } from '../pages/documents.page';
import { WizardPage } from '../pages/wizard.page';

// startFakeOpenAI() listens on 4010 by default; .github/workflows/ci.yml uses the same URL.
const FAKE_OPENAI_BASE_URL = 'http://127.0.0.1:4010/v1';
const WIRING =
  `start the backend with OPENAI_BASE_URL=${FAKE_OPENAI_BASE_URL} OCR_PROVIDER=openai ` +
  'OPENAI_API_KEY=e2e-dummy-key, and export the same OPENAI_BASE_URL before npm run e2e';

const BILL = fileURLToPath(new URL('../fixtures/synthetic-bill.png', import.meta.url));

// Sarah's simple finances under a login of its own. personas.ts fixes RUN_ID once per
// module load, so SARAH's username would collide with sarah-simplest in a shared worker.
const RUN_ID = Date.now().toString(36);
const FILER: PersonaData = {
  ...SARAH,
  username: `e2e_scan_${RUN_ID}`,
  debtor: { ...SARAH.debtor, email: `scan.e2e+${RUN_ID}@test.dignifi.org` },
};

/** The scanned bill is the only row at Amounts Owed, with what the model read. */
async function expectScannedBill(page: Page) {
  await expect(page.locator('input[name^="creditor_name_"]')).toHaveCount(1);
  await expect(page.locator('input[name="creditor_name_0"]')).toHaveValue(
    CANNED_BILL.creditor_name
  );
  await expect(page.locator('select[name="debt_type_0"]')).toHaveValue(CANNED_BILL.creditor_type);
  await expect(page.locator('input[name="amount_owed_0"]')).toHaveValue(CANNED_BILL.amount_owed);
}

test.describe('Scanned bill — upload to Amounts Owed', () => {
  test('a bill read at upload is waiting at Amounts Owed and survives save and reload', async ({
    page,
  }) => {
    if (process.env.OPENAI_BASE_URL !== FAKE_OPENAI_BASE_URL) {
      if (process.env.CI) throw new Error(`CI must run this journey: ${WIRING}`);
      console.warn(`[scanned-bill-journey] skipped. To run it, ${WIRING}`);
      test.skip(true, `To run it, ${WIRING}`);
    }

    const fake = await startFakeOpenAI();
    try {
      const register = new RegisterPage(page);
      const documents = new DocumentsPage(page);
      const wizard = new WizardPage(page);
      const stepTitle = page.locator('.step-title');

      await register.goto();
      await register.register(FILER.username, FILER.debtor.email, FILER.password);

      // Step 1, then the upload detour
      await wizard.fillDebtorInfo(FILER.debtor);
      await wizard.nextStep();
      await expect(
        page.getByRole('heading', { level: 1, name: 'Upload your documents' })
      ).toBeVisible();

      await documents.uploadBill(BILL);
      await documents.expectDone();
      expect(
        fake.completions(),
        `the backend never called the fake: ${WIRING}`
      ).toBeGreaterThanOrEqual(1);

      // Back to the wizard, which re-reads the session and resumes at Income
      await page.getByRole('button', { name: 'Continue', exact: true }).click();
      await expect(stepTitle).toHaveText('Income');
      await wizard.fillIncomeInfo(FILER.income);
      await wizard.nextStep();
      await expect(stepTitle).toHaveText('Expenses');
      await wizard.fillExpenses(FILER.expenses);
      await wizard.nextStep();
      await expect(stepTitle).toHaveText('Assets');
      await wizard.nextStep(); // no assets
      await expect(stepTitle).toHaveText('Amounts Owed');

      // First visit: the bill is there, marked as coming from the scan
      await expectScannedBill(page);
      await expect(page.getByText('From scan', { exact: true })).toBeVisible();

      // Continue saves step 5 and stores step 6 as the place to resume
      await wizard.nextStep();
      await expect(stepTitle).toHaveText('Contracts & Leases');

      // A reload re-runs the token refresh and the wizard's session re-read before any step renders
      await page.reload();
      await expect(stepTitle).toHaveText('Contracts & Leases', { timeout: 15_000 });
      await page.getByRole('button', { name: 'Go Back' }).click();
      await expect(stepTitle).toHaveText('Amounts Owed');
      await expectScannedBill(page);
    } finally {
      await fake.close();
    }
  });
});
