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
import { DocumentsPage } from '../pages/documents.page';
import { FilingFeePage } from '../pages/filing-fee.page';
import { DashboardPage } from '../pages/dashboard.page';
import { SOFAPage } from '../pages/sofa.page';

test.describe('DeShawn Mitchell — Assets', () => {
  test('enters 3 assets and 4 debts successfully', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const documents = new DocumentsPage(page);
    const filingFee = new FilingFeePage(page);
    const dashboard = new DashboardPage(page);
    const sofa = new SOFAPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(DESHAWN.username, DESHAWN.debtor.email, DESHAWN.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(DESHAWN.debtor);
    await wizard.nextStep();

    // Uploads come between basic info and Income; this journey types everything in
    await documents.skip();

    // Step 2: Income (living with his spouse, no dependents, $3,500/mo plus the spouse's $1,000)
    await wizard.fillIncomeInfo(DESHAWN.income);
    await wizard.nextStep();

    // Step 3: Take-home pay
    await wizard.fillTakeHomePay(DESHAWN.deductions, DESHAWN.spouse_deductions);
    await wizard.nextStep();

    // Step 4: Expenses
    await wizard.fillExpenses(DESHAWN);
    await wizard.nextStep();

    // Should pass means test (below median for HH of 2)
    // (the estimate needs both income and expense data)
    await wizard.waitForMeansTestEstimate();
    const preview = await wizard.getMeansTestPreview();
    expect(preview.toLowerCase()).toContain('eligible');

    // Step 5: Assets — his home (line 1), the truck (line 3) and his 401(k) (line 21),
    // with the household goods and accounts, Part by Part. The walk fails if a row
    // has no line to sit on.
    await wizard.walkAssets(DESHAWN);

    // Step 6: Debts — 4 debts (mortgage, credit card, utility, medical)
    await wizard.walkDebts(DESHAWN);

    // Step 7: Contracts & Leases (answered from the persona)
    await wizard.walkContracts(DESHAWN);

    // Step 8: Codebtors (answered from the persona)
    await wizard.walkCodebtors(DESHAWN);

    // Step 9: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // DeShawn pays in installments (3f spec §10), so Form 103B leaves his packet
    await filingFee.answer(DESHAWN.filing_fee.payment_choice);

    // The filing-fee page continues to the SOFA step (DIG-149). This journey isn't about
    // financial history, so skip SOFA to reach the forms dashboard. (The SOFA save path
    // itself is covered by sofa-journey.spec.ts.)
    await sofa.waitForLoad();
    await sofa.skipForNow();

    // Generate forms (passes means test)
    await dashboard.generateAllForms(15); // he pays in installments, so no Form 103B
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(14);
  });
});
