/**
 * Sarah Chen — Simplest Case
 *
 * Single, no assets, no dependents, fee waiver eligible.
 * Fastest path through the wizard. Tests minimal-data flow.
 */

import { test, expect } from '@playwright/test';
import { SARAH } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DashboardPage } from '../pages/dashboard.page';

test.describe('Sarah Chen — Simplest Case', () => {
  test('completes intake with no assets (fastest path)', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const dashboard = new DashboardPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(SARAH.username, SARAH.debtor.email, SARAH.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(SARAH.debtor);
    await wizard.nextStep();

    // Step 2: Income ($2,000/mo — well below median, fee waiver eligible)
    await wizard.fillIncomeInfo(SARAH.income);
    await wizard.nextStep();

    // Means test preview — should indicate eligibility + fee waiver
    const preview = await wizard.getMeansTestPreview();
    const previewLower = preview.toLowerCase();
    expect(previewLower).toContain('eligible');

    // Fee waiver indication
    const hasFeeWaiver =
      previewLower.includes('fee waiver') || previewLower.includes('filing fee');
    expect(hasFeeWaiver).toBe(true);

    // Step 3: Expenses (minimal)
    await wizard.fillExpenses(SARAH.expenses);
    await wizard.nextStep();

    // Step 4: Assets — none to add, just proceed
    // The step should allow proceeding with zero assets
    await wizard.nextStep();

    // Step 5: Debts (student loan + medical)
    for (const debt of SARAH.debts) {
      await wizard.addDebt(debt);
    }
    await wizard.nextStep();

    // Step 6: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // Generate all forms
    await dashboard.generateAllForms();
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(13);

    // Survey appears and can be completed
    expect(await dashboard.isSurveyVisible()).toBe(true);
    await dashboard.submitSurvey({
      comprehension: 5,
      dignity: 5,
      confidence: 4,
      confusing: 'Nothing was confusing',
      change: 'Nothing to change',
    });
  });
});
