/**
 * Andrés Kettleby — Gig Driver
 *
 * Self-employed rideshare and delivery driver, below median, eleven amounts owed.
 * His driving is a business he adds on the Income step ($4,200 from the apps less
 * $830 of driving costs), so it prints on 122A-1 line 5 and Schedule I line 8a. He pays the
 * fee in installments, so his packet has no Form 103B.
 */

import { test, expect } from '@playwright/test';
import { ANDRES } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DocumentsPage } from '../pages/documents.page';
import { FilingFeePage } from '../pages/filing-fee.page';
import { ExemptionsPage } from '../pages/exemptions.page';
import { DashboardPage } from '../pages/dashboard.page';
import { SOFAPage } from '../pages/sofa.page';

// FORM_122A2_TITLE in src/constants/formText.ts, as the means test page object reads it
const MEANS_TEST_TITLE = 'Form 122A-2: Chapter 7 Means Test Calculation';

/** The flag the page's own watcher sets once the Form 122A-2 heading is drawn */
type WatchedWindow = Window & { meansTitleSeen: boolean };

test.describe('Andrés Kettleby — Gig Driver', () => {
  test('reaches his forms after choosing to pay in installments', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const documents = new DocumentsPage(page);
    const filingFee = new FilingFeePage(page);
    const exemptions = new ExemptionsPage(page);
    const sofa = new SOFAPage(page);
    const dashboard = new DashboardPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(ANDRES.username, ANDRES.debtor.email, ANDRES.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(ANDRES.debtor);
    await wizard.fillPetitionQuestions(ANDRES.petition);
    await wizard.nextStep();

    // Uploads come between basic info and Income; this journey types everything in
    await documents.skip();

    // Step 2: Income (his driving added as a business entry, $0 in every box)
    await wizard.fillIncomeInfo(ANDRES.income);
    await wizard.nextStep();

    // Step 3: Take-home pay
    await wizard.fillTakeHomePay(ANDRES.deductions, ANDRES.spouse_deductions);
    await wizard.nextStep();

    // Step 4: Expenses
    await wizard.fillExpenses(ANDRES);
    await wizard.nextStep();

    // Step 5: Assets (the leased Corolla, his half of the Honda Fit, household goods, two
    // accounts; line 37 is Yes, so Part 5 shows and he fills lines 38 and 40)
    await wizard.walkAssets(ANDRES);

    // Step 6: Debts (the co-signed Honda Fit loan and ten unsecured debts)
    await wizard.walkDebts(ANDRES);

    // Step 7: Contracts & Leases (answered from the persona)
    await wizard.walkContracts(ANDRES);

    // Step 8: Codebtors (answered from the persona)
    await wizard.walkCodebtors(ANDRES);

    // Step 9: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // He pays in installments; the page says where to get Form 103A, then continues to the exemptions page
    await filingFee.answer(ANDRES.filing_fee.payment_choice);
    // Below the median, he never sees the Form 122A-2 page. The page replaces itself with /sofa
    // in the same document, which Playwright still reports as a navigation, so this watches what
    // he would see: whether the page's heading is ever drawn between Continue and /sofa.
    await exemptions.waitForLoad();
    await page.evaluate((title) => {
      const watched = window as unknown as WatchedWindow;
      watched.meansTitleSeen = false;
      const look = () => {
        for (const heading of document.querySelectorAll('h1')) {
          if (heading.textContent === title) watched.meansTitleSeen = true;
        }
      };
      look();
      new MutationObserver(look).observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true,
      });
    }, MEANS_TEST_TITLE);
    await exemptions.answer(ANDRES.exemptions);
    await sofa.waitForLoad();
    const seen = await page.evaluate(() => (window as unknown as WatchedWindow).meansTitleSeen);
    expect(seen).toBe(false);
    await sofa.skipForNow();

    // He pays in installments, so no Form 103B; below median, so no Form 122A-2; his car loan
    // and his car lease bring Form 108
    await dashboard.generateAllForms(16);
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(16);
  });
});
