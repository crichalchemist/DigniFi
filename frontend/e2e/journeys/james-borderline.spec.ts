/**
 * James Washington — Borderline Case
 *
 * Just below single-filer median ($73,180). Tests near-threshold messaging.
 */

import { test, expect } from '@playwright/test';
import { JAMES } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DocumentsPage } from '../pages/documents.page';
import { FilingFeePage } from '../pages/filing-fee.page';
import { DashboardPage } from '../pages/dashboard.page';
import { SOFAPage } from '../pages/sofa.page';

test.describe('James Washington — Borderline', () => {
  test('completes intake near median threshold', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const documents = new DocumentsPage(page);
    const filingFee = new FilingFeePage(page);
    const sofa = new SOFAPage(page);
    const dashboard = new DashboardPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(JAMES.username, JAMES.debtor.email, JAMES.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(JAMES.debtor);
    await wizard.nextStep();

    // Uploads come between basic info and Income; this journey types everything in
    await documents.skip();

    // Step 2: Income (borderline — $5,833/mo × 12 = $69,996 < $73,180 median)
    await wizard.fillIncomeInfo(JAMES.income);
    await wizard.nextStep();

    // Step 3: Take-home pay
    await wizard.fillTakeHomePay(JAMES.deductions, JAMES.spouse_deductions);
    await wizard.nextStep();

    // Step 4: Expenses
    await wizard.fillExpenses(JAMES);
    await wizard.nextStep();

    // Means test should still pass (just under)
    // (the estimate needs both income and expense data)
    await wizard.waitForMeansTestEstimate();
    const preview = await wizard.getMeansTestPreview();
    expect(preview.toLowerCase()).toContain('eligible');

    // Step 5: Assets (vehicle, household goods, bank account), Part by Part
    await wizard.walkAssets(JAMES);

    // Step 6: Debts (includes secured auto loan)
    await wizard.walkDebts(JAMES);

    // Step 7: Contracts & Leases (answered from the persona)
    await wizard.walkContracts(JAMES);

    // Step 8: Codebtors (answered from the persona)
    await wizard.walkCodebtors(JAMES);

    // Step 9: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // James pays the fee in full, then the page continues to the SOFA step. This journey
    // isn't about financial history, so skip SOFA to reach the forms dashboard. (The SOFA
    // save path itself is covered by sofa-journey.spec.ts.)
    await filingFee.answer(JAMES.filing_fee.payment_choice);
    await sofa.waitForLoad();
    await sofa.skipForNow();

    // Forms generated (passes means test). James pays in full, so Form 103B is not in his
    // packet.
    await dashboard.generateAllForms(15);
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(15);
  });
});
