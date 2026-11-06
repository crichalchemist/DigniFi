/**
 * Priya Sharma — Ineligible (Above Median)
 *
 * $12,000 a month plus her spouse's $1,800 is $13,800 a month, $165,600 a
 * year, with a 4-person household — above the $137,902 HH4 median, so the
 * means test fails.
 * Tests the dignity-preserving ineligibility path.
 */

import { test, expect } from '@playwright/test';
import { PRIYA } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DocumentsPage } from '../pages/documents.page';
import { FilingFeePage } from '../pages/filing-fee.page';

test.describe('Priya Sharma — Ineligible', () => {
  test('sees dignity-preserving ineligibility message', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const documents = new DocumentsPage(page);
    const filingFee = new FilingFeePage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(PRIYA.username, PRIYA.debtor.email, PRIYA.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(PRIYA.debtor);
    await wizard.nextStep();

    // Uploads come between basic info and Income; this journey types everything in
    await documents.skip();

    // Step 2: Income ($12,000/mo plus her spouse's $1,800 — above median for HH of 4)
    await wizard.fillIncomeInfo(PRIYA.income);
    await wizard.nextStep();

    // Step 3: Take-home pay
    await wizard.fillTakeHomePay(PRIYA.deductions, PRIYA.spouse_deductions);
    await wizard.nextStep();

    // Step 4: Expenses
    await wizard.fillExpenses(PRIYA);
    await wizard.nextStep();

    // Means test preview should show above-median messaging
    // (the estimate needs both income and expense data)
    await wizard.waitForMeansTestEstimate();
    const preview = await wizard.getMeansTestPreview();
    const previewLower = preview.toLowerCase();

    // Should NOT contain shaming language
    expect(previewLower).not.toContain('you cannot');
    expect(previewLower).not.toContain('denied');
    expect(previewLower).not.toContain('rejected');

    // Should contain dignity-preserving alternative language —
    // MeansTestPreview's fail verdict is "eligibility may need further review"
    expect(previewLower).toContain('further review');

    await wizard.walkAssets(PRIYA);

    for (const debt of PRIYA.debts) {
      await wizard.addDebt(debt);
    }
    await wizard.nextStep();

    // Step 7: Contracts & Leases (optional — no entries needed)
    await wizard.nextStep();

    // Step 8: Codebtors (optional — no entries needed)
    await wizard.nextStep();

    await wizard.fillReview();
    await wizard.completeIntake();

    // Every filer reaches the filing-fee page; Priya reads the court's limit and stops here
    await filingFee.waitForLoad();
    await expect(filingFee.limitSentence(4, '$4,125.00')).toBeVisible();
    const pageText = await page.textContent('body');
    expect(pageText?.toLowerCase()).not.toContain('error');
  });
});
