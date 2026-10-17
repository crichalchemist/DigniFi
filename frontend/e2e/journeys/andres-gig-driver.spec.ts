/**
 * Andrés Kettleby — Gig Driver
 *
 * Self-employed rideshare and delivery driver, below median, ten amounts owed.
 * What he keeps from driving goes in the other-income box until the Income step
 * asks for business income (3a1.Q1). Today's flag qualifies him for a fee waiver,
 * so Complete opens the waiver page, but he pays in installments and files no
 * application (3a1.Q2): his packet has no Form 103B.
 */

import { test, expect } from '@playwright/test';
import { ANDRES } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DocumentsPage } from '../pages/documents.page';
import { DashboardPage } from '../pages/dashboard.page';
import { SOFAPage } from '../pages/sofa.page';

test.describe('Andrés Kettleby — Gig Driver', () => {
  test('reaches his forms from the fee waiver page without applying', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const documents = new DocumentsPage(page);
    const sofa = new SOFAPage(page);
    const dashboard = new DashboardPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(ANDRES.username, ANDRES.debtor.email, ANDRES.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(ANDRES.debtor);
    await wizard.nextStep();

    // Uploads come between basic info and Income; this journey types everything in
    await documents.skip();

    // Step 2: Income ($3,370/mo in Other Monthly Income, $0 in every other box)
    await wizard.fillIncomeInfo(ANDRES.income);
    await wizard.nextStep();

    // Step 3: Expenses
    await wizard.fillExpenses(ANDRES.expenses);
    await wizard.nextStep();

    // Step 4: Assets (his half of the Honda Fit, household goods, two accounts)
    for (const asset of ANDRES.assets) {
      await wizard.addAsset(asset);
    }
    await wizard.nextStep();

    // Step 5: Debts (the co-signed Honda Fit loan and nine unsecured debts)
    for (const debt of ANDRES.debts) {
      await wizard.addDebt(debt);
    }
    await wizard.nextStep();

    // Step 6: Contracts & Leases (left empty)
    await wizard.nextStep();

    // Step 7: Codebtors (left empty)
    await wizard.nextStep();

    // Step 8: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // He qualifies under today's flag, so Complete opens the waiver application
    await expect(page).toHaveURL(/\/fee-waiver$/);
    await expect(page.locator('h1')).toHaveText('Filing Fee Waiver Application');

    // He doesn't apply. The page has no way on without applying, so he opens the SOFA
    // step by URL (the silent refresh on load restores his login) and skips it.
    await page.goto('/sofa');
    // A full reload shows the heading only after the token refresh, the session read and the
    // SOFA read, so it gets longer than the default 5 s (two loaded runs missed it)
    await sofa.waitForLoad(30_000);
    await sofa.skipForNow();

    // No waiver application, so no Form 103B; below median, so no Form 122A-2
    await dashboard.generateAllForms(14);
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(14);
  });
});
