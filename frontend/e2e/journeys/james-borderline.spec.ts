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
import { SOFAPage } from '../pages/sofa.page';

test.describe('James Washington — Borderline', () => {
  test('completes intake near median threshold', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const sofa = new SOFAPage(page);
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

    // Step 3: Expenses
    await wizard.fillExpenses(JAMES.expenses);
    await wizard.nextStep();

    // Means test should still pass (just under)
    // (the estimate needs both income and expense data)
    await wizard.waitForMeansTestEstimate();
    const preview = await wizard.getMeansTestPreview();
    expect(preview.toLowerCase()).toContain('eligible');

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

    // Step 6: Contracts & Leases (optional — no entries needed)
    await wizard.nextStep();

    // Step 7: Codebtors (optional — no entries needed)
    await wizard.nextStep();

    // Step 8: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // James is not fee-waiver eligible, so handleComplete routes to the SOFA
    // step (not /fee-waiver). This journey isn't about financial history, so
    // skip SOFA to reach the forms dashboard. (The SOFA save path itself is
    // covered by sofa-journey.spec.ts.)
    await sofa.waitForLoad();
    await sofa.skipForNow();

    // Forms generated (passes means test). James doesn't qualify for the
    // fee waiver, so Form 103B (the waiver application) is not generated.
    await dashboard.generateAllForms(12);
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(12);
  });
});
