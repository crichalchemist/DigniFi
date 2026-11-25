/**
 * Maria Torres — Happy Path
 *
 * Below-median single parent who asks for a fee waiver.
 * Tests the complete intake → form generation flow.
 */

import { test, expect } from '@playwright/test';
import { MARIA } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DocumentsPage } from '../pages/documents.page';
import { FilingFeePage } from '../pages/filing-fee.page';
import { ExemptionsPage } from '../pages/exemptions.page';
import { DashboardPage } from '../pages/dashboard.page';

test.describe('Maria Torres — Happy Path', () => {
  test('completes full intake and generates all forms', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const documents = new DocumentsPage(page);
    const filingFee = new FilingFeePage(page);
    const exemptions = new ExemptionsPage(page);
    const dashboard = new DashboardPage(page);

    // Landing → Register
    await landing.goto();
    await expect(landing.title()).toContainText('financial relief');
    await landing.clickGetStarted();

    // Register a new account
    await register.register(MARIA.username, MARIA.debtor.email, MARIA.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(MARIA.debtor);
    await wizard.fillPetitionQuestions(MARIA.petition);
    await wizard.nextStep();

    // Uploads come between basic info and Income; this journey types everything in
    await documents.skip();

    // Step 2: Income
    await wizard.fillIncomeInfo(MARIA.income);
    await wizard.nextStep();

    // Step 3: Take-home pay
    await wizard.fillTakeHomePay(MARIA.deductions, MARIA.spouse_deductions);
    await wizard.nextStep();

    // Step 4: Expenses
    await wizard.fillExpenses(MARIA);
    await wizard.nextStep();

    // Means test sidebar should say her income is at or below the median
    // (the result reads income alone, so it shows once income is saved)
    await wizard.waitForMeansTestResult();
    const preview = await wizard.getMeansTestPreview();
    expect(preview.toLowerCase()).toContain('at or below the median');

    // Step 5: Assets
    await wizard.walkAssets(MARIA);

    // Step 6: Debts (trauma-informed: "Amounts Owed")
    await wizard.walkDebts(MARIA);

    // Step 7: Contracts & Leases (answered from the persona)
    await wizard.walkContracts(MARIA);

    // Step 8: Codebtors (answered from the persona)
    await wizard.walkCodebtors(MARIA);

    // Step 9: Your Plans (Form 108 doesn't apply)
    await wizard.walkPlans(MARIA);

    // Step 10: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // Every filer answers Form 101 line 8 after Complete; Maria asks for the waiver (3f spec §10)
    await filingFee.answer(MARIA.filing_fee.payment_choice, MARIA.filing_fee.waiver);
    await exemptions.answer(MARIA.exemptions);

    // The filing-fee page continues to the exemptions page (DIG-149), and the forms dashboard
    // follows it.
    await page.waitForURL('**/forms');

    // Dashboard — generate all forms
    await dashboard.generateAllForms(16); // 15 forms + Form 103B (she asks for the waiver)
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(16);

    // Download Form 107
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

    // UPL disclaimer visible on dashboard
    await expect(dashboard.uplDisclaimer()).toBeVisible();

    // Post-task survey appears
    expect(await dashboard.isSurveyVisible()).toBe(true);
  });
});
