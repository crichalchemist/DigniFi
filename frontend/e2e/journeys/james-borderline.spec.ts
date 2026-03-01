/**
 * James Washington — Borderline Case
 *
 * Just below single-filer median ($71,304). Tests near-threshold messaging.
 */

import { test, expect } from '@playwright/test';
import { JAMES } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DashboardPage } from '../pages/dashboard.page';

test.describe('James Washington — Borderline', () => {
  test('completes intake near median threshold', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const dashboard = new DashboardPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(JAMES.username, JAMES.debtor.email, JAMES.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(JAMES.debtor);
    await wizard.nextStep();

    // Step 2: Income (borderline — $5,833/mo × 12 = $69,996 < $71,304 median)
    await wizard.fillIncomeInfo(JAMES.income);
    await wizard.nextStep();

    // Means test should still pass (just under)
    const preview = await wizard.getMeansTestPreview();
    expect(preview.toLowerCase()).toContain('eligible');

    // Step 3: Expenses
    await wizard.fillExpenses(JAMES.expenses);
    await wizard.nextStep();

    // Step 4: Assets (vehicle + bank account)
    for (const asset of JAMES.assets) {
      await wizard.addAsset(asset);
    }
    await wizard.nextStep();

    // Step 5: Debts (includes secured auto loan)
    for (const debt of JAMES.debts) {
      await wizard.addDebt(debt);
    }
    await wizard.nextStep();

    // Step 6: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // Forms generated (passes means test)
    await dashboard.generateAllForms();
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(13);
  });
});
