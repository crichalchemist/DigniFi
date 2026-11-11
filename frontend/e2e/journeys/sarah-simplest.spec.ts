/**
 * Sarah Chen — Simplest Case
 *
 * Single, no assets, no dependents, asks for a fee waiver.
 * Fastest path through the wizard. Tests minimal-data flow.
 */

import { test, expect } from '@playwright/test';
import { SARAH } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DocumentsPage } from '../pages/documents.page';
import { FilingFeePage } from '../pages/filing-fee.page';
import { DashboardPage } from '../pages/dashboard.page';
import { SOFAPage } from '../pages/sofa.page';

test.describe('Sarah Chen — Simplest Case', () => {
  test('completes intake with no assets (fastest path)', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const documents = new DocumentsPage(page);
    const filingFee = new FilingFeePage(page);
    const dashboard = new DashboardPage(page);
    const sofa = new SOFAPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(SARAH.username, SARAH.debtor.email, SARAH.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(SARAH.debtor);
    await wizard.nextStep();

    // Uploads come between basic info and Income; this journey types everything in
    await documents.skip();

    // Step 2: Income ($2,000/mo — well below median)
    await wizard.fillIncomeInfo(SARAH.income);
    await wizard.nextStep();

    // Step 3: Take-home pay
    await wizard.fillTakeHomePay(SARAH.deductions, SARAH.spouse_deductions);
    await wizard.nextStep();

    // Step 4: Expenses (minimal)
    await wizard.fillExpenses(SARAH);
    await wizard.nextStep();

    // Means test preview — should indicate eligibility
    // (the estimate needs both income and expense data)
    await wizard.waitForMeansTestEstimate();
    const preview = await wizard.getMeansTestPreview();
    const previewLower = preview.toLowerCase();
    expect(previewLower).toContain('eligible');

    // Step 5: Assets — none to add: No on every line, Part by Part
    await wizard.walkAssets(SARAH);

    // Step 6: Debts (student loan + medical)
    await wizard.walkDebts(SARAH);

    // Step 7: Contracts & Leases (answered from the persona)
    await wizard.walkContracts(SARAH);

    // Step 8: Codebtors (answered from the persona)
    await wizard.walkCodebtors(SARAH);

    // Step 9: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // The page shows the court's limit and her own figure as information, never a verdict (§6.2)
    await filingFee.waitForLoad();
    await expect(filingFee.limitSentence(1, '$1,995.00')).toBeVisible();
    await expect(
      page.getByText(
        "Your family's income, as Form 103B counts it from your answers: $1,750.00 a month."
      )
    ).toBeVisible();
    await expect(page.locator('main')).not.toContainText(/qualif|eligib/i);
    await filingFee.answer(SARAH.filing_fee.payment_choice, SARAH.filing_fee.waiver);

    // The filing-fee page continues to the SOFA step (DIG-149). This journey isn't about
    // financial history, so skip SOFA to reach the forms dashboard. (The SOFA save path
    // itself is covered by sofa-journey.spec.ts.)
    await sofa.waitForLoad();
    await sofa.skipForNow();

    // Generate all forms
    await dashboard.generateAllForms(16); // 15 forms + Form 103B (she asks for the waiver)
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(15);

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
