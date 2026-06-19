/**
 * Maria Torres — Happy Path
 *
 * Below-median single parent, fee waiver eligible.
 * Tests the complete intake → form generation flow.
 */

import { test, expect } from '@playwright/test';
import { MARIA } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { FeeWaiverPage } from '../pages/fee-waiver.page';
import { DashboardPage } from '../pages/dashboard.page';

test.describe('Maria Torres — Happy Path', () => {
  test('completes full intake and generates all forms', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const feeWaiver = new FeeWaiverPage(page);
    const dashboard = new DashboardPage(page);

    // Landing → Register
    await landing.goto();
    await expect(landing.title()).toContainText('financial relief');
    await landing.clickGetStarted();

    // Register a new account
    await register.register(MARIA.username, MARIA.debtor.email, MARIA.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(MARIA.debtor);
    await wizard.nextStep();

    // Step 2: Income
    await wizard.fillIncomeInfo(MARIA.income);
    await wizard.nextStep();

    // Step 3: Expenses
    await wizard.fillExpenses(MARIA.expenses);
    await wizard.nextStep();

    // Means test sidebar should indicate eligibility
    // (the estimate needs both income and expense data)
    await wizard.waitForMeansTestEstimate();
    const preview = await wizard.getMeansTestPreview();
    expect(preview.toLowerCase()).toContain('may be eligible');

    // Step 4: Assets
    for (const asset of MARIA.assets) {
      await wizard.addAsset(asset);
    }
    await wizard.nextStep();

    // Step 5: Debts (trauma-informed: "Amounts Owed")
    for (const debt of MARIA.debts) {
      await wizard.addDebt(debt);
    }
    await wizard.nextStep();

    // Step 6: Contracts & Leases (optional — no entries needed)
    await wizard.nextStep();

    // Step 7: Codebtors (optional — no entries needed)
    await wizard.nextStep();

    // Step 8: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // Maria is fee-waiver eligible → routed to the waiver application first
    const totalExpenses = Object.values(MARIA.expenses).reduce((a, b) => a + b, 0);
    await feeWaiver.submit(
      MARIA.debtor.household_size,
      MARIA.income.total_monthly_income,
      totalExpenses
    );

    // Dashboard — generate all forms
    await dashboard.generateAllForms();
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(13);

    // UPL disclaimer visible on dashboard
    await expect(dashboard.uplDisclaimer()).toBeVisible();

    // Post-task survey appears
    expect(await dashboard.isSurveyVisible()).toBe(true);
  });
});
