/**
 * Priya Sharma — Above the Median
 *
 * $12,000 a month plus her spouse's $1,800 is $13,800 a month, $165,600 a
 * year, with a 4-person household — above the $137,902 HH4 median, so
 * Form 122A-2 applies. She answers its page and reads the form's arithmetic with no verdict;
 * she reaches the dashboard, where Generate All makes 17 forms.
 * Tests that the above-median result is shown with dignity and no verdict.
 */

import { test, expect } from '@playwright/test';
import { PRIYA } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DocumentsPage } from '../pages/documents.page';
import { FilingFeePage } from '../pages/filing-fee.page';
import { ExemptionsPage } from '../pages/exemptions.page';
import { MeansTestPage } from '../pages/means-test.page';
import { SOFAPage } from '../pages/sofa.page';
import { DashboardPage } from '../pages/dashboard.page';

test.describe('Priya Sharma — Above the Median', () => {
  test('sees that Form 122A-2 applies, in words with no verdict', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const documents = new DocumentsPage(page);
    const filingFee = new FilingFeePage(page);
    const exemptions = new ExemptionsPage(page);
    const meansTest = new MeansTestPage(page);
    const sofa = new SOFAPage(page);
    const dashboard = new DashboardPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(PRIYA.username, PRIYA.debtor.email, PRIYA.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(PRIYA.debtor);
    await wizard.fillPetitionQuestions(PRIYA.petition);
    await wizard.nextStep();

    // Uploads come between basic info and Income; this journey types everything in
    await documents.skip();

    // Step 2: Income ($12,000/mo plus her spouse's $1,800 — above median for HH of 4)
    await wizard.fillIncomeInfo(PRIYA.income);
    await wizard.nextStep();

    // Step 3: Take-home pay
    await wizard.fillTakeHomePay(PRIYA.deductions, PRIYA.spouse_deductions);
    await wizard.nextStep();

    // Step 4: Expenses
    await wizard.fillExpenses(PRIYA);
    await wizard.nextStep();

    // Means test preview should show above-median messaging
    // (the result reads income alone, so it shows once income is saved)
    await wizard.waitForMeansTestResult();
    const preview = await wizard.getMeansTestPreview();
    const previewLower = preview.toLowerCase();

    // Should NOT contain shaming language
    expect(previewLower).not.toContain('you cannot');
    expect(previewLower).not.toContain('denied');
    expect(previewLower).not.toContain('rejected');

    // Should contain dignity-preserving alternative language —
    // Above the median, the sidebar can't work Form 122A-2 out until she answers its page
    expect(previewLower).toContain("can't be worked out until you answer");

    await wizard.walkAssets(PRIYA);

    await wizard.walkDebts(PRIYA);

    // Step 7: Contracts & Leases (answered from the persona)
    await wizard.walkContracts(PRIYA);

    // Step 8: Codebtors (answered from the persona)
    await wizard.walkCodebtors(PRIYA);

    // Step 9: Your Plans (Form 108, the persona's choices)
    await wizard.walkPlans(PRIYA);

    await wizard.fillReview();
    await wizard.completeIntake();

    // Every filer reaches the filing-fee page; Priya reads the court's limit first
    await filingFee.waitForLoad();
    await expect(filingFee.limitSentence(4, '$4,125.00')).toBeVisible();
    const pageText = await page.textContent('body');
    expect(pageText?.toLowerCase()).not.toContain('error');
    await filingFee.answer(PRIYA.filing_fee.payment_choice);

    // Above the median, the exemptions page continues to Form 122A-2's page
    await exemptions.answer(PRIYA.exemptions, '**/means-test');
    await meansTest.waitForLoad();
    await meansTest.answer(PRIYA.means_test!);
    // With her answers in, the rows, line 25's boxes and line 36's payment are on the page
    await meansTest.checkPhoneWidth();
    await meansTest.continue();

    // Her answers give a presumption, said in the form's words and never as a verdict. The
    // first Continue stays here so she reads the changed result at the top.
    await expect(page).toHaveURL(/means-test/);
    // The save's reply brings the new result, so wait for it before reading the block
    await expect(page.getByRole('status', { name: 'Income test' })).toContainText(
      "The form's arithmetic gives: There is a presumption of abuse."
    );
    const result = await meansTest.result();
    expect(result.trim().endsWith('A court makes the final decision.')).toBe(true);
    await expect(meansTest.line43Link()).toBeVisible();
    await expect(meansTest.status()).toHaveText(
      'Your result has changed. It is at the top of the page. Press Continue again when you are ready.'
    );

    await meansTest.continue();
    await sofa.waitForLoad();
    await sofa.skipForNow();

    // Above the median, her packet holds Form 122A-2, and her car loan Form 108: 15 forms plus
    // those two
    await dashboard.generateAllForms(17);
    expect(await dashboard.getGeneratedCount()).toBe(17);
    await expect(
      page.getByRole('article', { name: /122A-2/ }).getByRole('button', { name: 'Download' })
    ).toBeVisible();
  });
});
