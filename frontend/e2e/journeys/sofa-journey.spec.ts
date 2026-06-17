/**
 * SOFA Journey — Form 107 Statement of Financial Affairs
 *
 * Tests that a user can complete intake, fill in SOFA data, generate all
 * forms, and download Form 107 as a PDF.
 *
 * Uses James Washington (borderline, no fee waiver, so handleComplete
 * redirects to /sofa instead of /fee-waiver).
 */

import { test, expect } from '@playwright/test';
import { JAMES } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DashboardPage } from '../pages/dashboard.page';
import { SOFAPage } from '../pages/sofa.page';

test.describe('SOFA — Form 107 Financial History', () => {
  test('fills SOFA data, generates forms, and downloads Form 107', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const sofa = new SOFAPage(page);
    const dashboard = new DashboardPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(JAMES.username, JAMES.debtor.email, JAMES.password);

    // ── Complete Wizard ─────────────────────────────────────

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(JAMES.debtor);
    await wizard.nextStep();

    // Step 2: Income
    await wizard.fillIncomeInfo(JAMES.income);
    await wizard.nextStep();

    // Step 3: Expenses
    await wizard.fillExpenses(JAMES.expenses);
    await wizard.nextStep();

    // Means test check
    await wizard.waitForMeansTestEstimate();

    // Step 4: Assets
    for (const asset of JAMES.assets) {
      await wizard.addAsset(asset);
    }
    await wizard.nextStep();

    // Step 5: Debts
    for (const debt of JAMES.debts) {
      await wizard.addDebt(debt);
    }
    await wizard.nextStep();

    // Step 6: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();
    // James is NOT fee-waiver eligible → handleComplete redirects to /sofa

    // ── SOFA Step ───────────────────────────────────────────

    await sofa.waitForLoad();

    // Toggle Prior Income on and fill a row
    await sofa.togglePriorIncome(true);
    await sofa.addPriorIncomeRow({
      year: 2025,
      source: 'Temp Agency',
      grossAmount: '24000',
    });

    // Toggle Creditor Payments on and fill a row
    await sofa.toggleCreditorPayments(true);
    await sofa.addCreditorPaymentRow({
      creditorName: 'Capital One',
      totalPaid: '1500',
      datesOfPayments: 'Monthly Jan-Mar 2026',
    });

    // Save & Continue → /forms
    await sofa.saveAndContinue();

    // ── Form Generation ─────────────────────────────────────

    await dashboard.generateAllForms(12); // James is not fee-waiver eligible → 12 forms
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(12);

    // ── Download Form 107 ───────────────────────────────────

    // Find the download button for Form 107 and click it
    const form107Card = page.locator('.form-card').filter({ hasText: /form 107/i });
    await expect(form107Card).toBeVisible({ timeout: 10000 });

    const downloadPromise = page.waitForEvent('download');
    await form107Card.getByRole('button', { name: /download/i }).click();
    const download = await downloadPromise;

    // Assert the downloaded file is a PDF
    expect(download.suggestedFilename()).toMatch(/\.pdf$/i);

    // Read the file bytes to verify it's a valid PDF
    const stream = await download.createReadStream();
    const chunks: Buffer[] = [];
    for await (const chunk of stream) {
      chunks.push(chunk as Buffer);
    }
    const head = Buffer.concat(chunks).subarray(0, 5).toString();
    expect(head).toBe('%PDF-');
  });
});
