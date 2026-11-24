/**
 * Eviction statement journey — Form 101A
 *
 * A synthetic renter (James's data) answers Yes to Form 101 line 11's rent and eviction
 * questions, copies the landlord from the lease he listed on the same step, and gets Form 101A in
 * his packet beside James's fifteen forms (Form 101 among them).
 */

import { test, expect } from '@playwright/test';
import { JAMES } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DocumentsPage } from '../pages/documents.page';
import { FilingFeePage } from '../pages/filing-fee.page';
import { ExemptionsPage } from '../pages/exemptions.page';
import { DashboardPage } from '../pages/dashboard.page';
import { SOFAPage } from '../pages/sofa.page';

// Spec-local ID, so this registration never collides with another spec's in the same worker
const RUN_ID = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

const RENTER = {
  ...JAMES,
  petition: {
    ...JAMES.petition,
    eviction_judgment: 'yes' as const,
    landlord_pick: 'Gold Coast Example Residential LLC',
    landlord_name: 'Demo Property Holdings LLC',
  },
};

test.describe('Eviction statement — Form 101A', () => {
  test('a renter with an eviction judgment copies the landlord from a lease and gets Form 101A', async ({
    page,
  }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const documents = new DocumentsPage(page);
    const filingFee = new FilingFeePage(page);
    const exemptions = new ExemptionsPage(page);
    const sofa = new SOFAPage(page);
    const dashboard = new DashboardPage(page);

    const email = `eviction.e2e+${RUN_ID}@test.dignifi.org`;
    await landing.goto();
    await landing.clickGetStarted();
    await register.register(`e2e_eviction_${RUN_ID}`, email, JAMES.password);

    await wizard.fillDebtorInfo({ ...JAMES.debtor, email });
    await wizard.fillPetitionQuestions(RENTER.petition);
    await wizard.nextStep();

    await documents.skip();

    await wizard.fillIncomeInfo(RENTER.income);
    await wizard.nextStep();

    await wizard.fillTakeHomePay(RENTER.deductions, RENTER.spouse_deductions);
    await wizard.nextStep();

    await wizard.fillExpenses(RENTER);
    await wizard.nextStep();

    await wizard.waitForMeansTestResult();

    await wizard.walkAssets(RENTER);
    await wizard.walkDebts(RENTER);

    // Step 7: the lease is copied into the landlord's boxes, then typed over
    await wizard.fillContracts(RENTER);
    await expect(page.locator('input[name="landlord_name"]')).toHaveValue(
      'Demo Property Holdings LLC'
    );
    await expect(page.locator('input[name="landlord_city"]')).toHaveValue('Chicago');
    await expect(page.locator('input[name="landlord_street"]')).toHaveValue(
      '850 N State St, c/o Management Office'
    );

    // The notice leaves the two certification boxes blank and, for Cook County (the Eastern
    // Division), gives the clerk's number under them; it never says DigniFi skips Form 101A.
    await expect(
      page.getByText('DigniFi leaves these two boxes blank.', { exact: false })
    ).toBeVisible();
    await expect(
      page.getByText("The clerk's office can tell you how the deposit is made: (312) 408-5000.")
    ).toBeVisible();
    await expect(page.getByText("doesn't prepare Form 101A")).toHaveCount(0);

    await wizard.nextStep();

    await wizard.walkCodebtors(RENTER);

    await wizard.fillReview();
    await wizard.completeIntake();

    await filingFee.answer(RENTER.filing_fee.payment_choice);
    await exemptions.answer(RENTER.exemptions);
    await sofa.waitForLoad();
    await sofa.skipForNow();

    // James's 16 forms (Form 108 among them, for his car loan) and Form 101A
    await dashboard.generateAllForms(17);
    await expect(page.getByText('Form 101A - Eviction Judgment Statement')).toBeVisible();
  });
});
