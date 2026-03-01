/**
 * DeShawn Mitchell — Asset-Heavy Homeowner
 *
 * Below median but owns home ($180k, $160k mortgage).
 * Tests multi-asset entry and exemption awareness.
 */

import { test, expect } from '@playwright/test';
import { DESHAWN } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DashboardPage } from '../pages/dashboard.page';

test.describe('DeShawn Mitchell — Assets', () => {
  test('enters 3 assets and 4 debts successfully', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const dashboard = new DashboardPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(DESHAWN.username, DESHAWN.debtor.email, DESHAWN.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(DESHAWN.debtor);
    await wizard.nextStep();

    // Step 2: Income (married, no dependents, $3,500/mo)
    await wizard.fillIncomeInfo(DESHAWN.income);
    await wizard.nextStep();

    // Should pass means test (below median for HH of 2)
    const preview = await wizard.getMeansTestPreview();
    expect(preview.toLowerCase()).toContain('eligible');

    // Step 3: Expenses
    await wizard.fillExpenses(DESHAWN.expenses);
    await wizard.nextStep();

    // Step 4: Assets — 3 assets (real property, vehicle, retirement)
    for (const asset of DESHAWN.assets) {
      await wizard.addAsset(asset);
    }
    // Verify all 3 assets were entered
    const assetForms = page.locator('input[name="description"]');
    expect(await assetForms.count()).toBeGreaterThanOrEqual(3);
    await wizard.nextStep();

    // Step 5: Debts — 4 debts (mortgage, credit card, utility, medical)
    for (const debt of DESHAWN.debts) {
      await wizard.addDebt(debt);
    }
    await wizard.nextStep();

    // Step 6: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // Generate forms (passes means test)
    await dashboard.generateAllForms();
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(13);
  });
});
