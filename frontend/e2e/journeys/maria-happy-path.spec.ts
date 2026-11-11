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
import { DashboardPage } from '../pages/dashboard.page';
import { SOFAPage } from '../pages/sofa.page';

test.describe('Maria Torres — Happy Path', () => {
  test('completes full intake and generates all forms', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const documents = new DocumentsPage(page);
    const filingFee = new FilingFeePage(page);
    const dashboard = new DashboardPage(page);
    const sofa = new SOFAPage(page);

    // Landing → Register
    await landing.goto();
    await expect(landing.title()).toContainText('financial relief');
    await landing.clickGetStarted();

    // Register a new account
    await register.register(MARIA.username, MARIA.debtor.email, MARIA.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(MARIA.debtor);
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

    // Means test sidebar should indicate eligibility
    // (the estimate needs both income and expense data)
    await wizard.waitForMeansTestEstimate();
    const preview = await wizard.getMeansTestPreview();
    expect(preview.toLowerCase()).toContain('may be eligible');

    // Step 5: Assets
    await wizard.walkAssets(MARIA);

    // Step 6: Debts (trauma-informed: "Amounts Owed")
    await wizard.walkDebts(MARIA);

    // Step 7: Contracts & Leases (answered from the persona)
    await wizard.walkContracts(MARIA);

    // Step 8: Codebtors (answered from the persona)
    await wizard.walkCodebtors(MARIA);

    // Step 9: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // Every filer answers Form 101 line 8 after Complete; Maria asks for the waiver (3f spec §10)
    await filingFee.answer(MARIA.filing_fee.payment_choice, MARIA.filing_fee.waiver);

    // The filing-fee page continues to the SOFA step (DIG-149). This journey isn't about
    // financial history, so skip SOFA to reach the forms dashboard. (The SOFA save path
    // itself is covered by sofa-journey.spec.ts.)
    await sofa.waitForLoad();
    await sofa.skipForNow();

    // Dashboard — generate all forms
    await dashboard.generateAllForms(16); // 15 forms + Form 103B (she asks for the waiver)
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(16);

    // UPL disclaimer visible on dashboard
    await expect(dashboard.uplDisclaimer()).toBeVisible();

    // Post-task survey appears
    expect(await dashboard.isSurveyVisible()).toBe(true);
  });
});
