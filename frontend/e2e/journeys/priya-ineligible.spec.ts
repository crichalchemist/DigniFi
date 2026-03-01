/**
 * Priya Sharma — Ineligible (Above Median)
 *
 * $120k annual income with 4-person household. Fails means test.
 * Tests the dignity-preserving ineligibility path.
 */

import { test, expect } from '@playwright/test';
import { PRIYA } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';

test.describe('Priya Sharma — Ineligible', () => {
  test('sees dignity-preserving ineligibility message', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(PRIYA.username, PRIYA.debtor.email, PRIYA.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(PRIYA.debtor);
    await wizard.nextStep();

    // Step 2: Income ($10,000/mo — well above median for HH of 4)
    await wizard.fillIncomeInfo(PRIYA.income);
    await wizard.nextStep();

    // Means test preview should show above-median messaging
    const preview = await wizard.getMeansTestPreview();
    const previewLower = preview.toLowerCase();

    // Should NOT contain shaming language
    expect(previewLower).not.toContain('you cannot');
    expect(previewLower).not.toContain('denied');
    expect(previewLower).not.toContain('rejected');

    // Should contain dignity-preserving alternative language
    // "above the median" or "additional calculations" or "Chapter 13"
    const hasGracefulMessage =
      previewLower.includes('above') ||
      previewLower.includes('additional calculations') ||
      previewLower.includes('chapter 13');
    expect(hasGracefulMessage).toBe(true);

    // Complete remaining steps
    await wizard.fillExpenses(PRIYA.expenses);
    await wizard.nextStep();

    for (const asset of PRIYA.assets) {
      await wizard.addAsset(asset);
    }
    await wizard.nextStep();

    for (const debt of PRIYA.debts) {
      await wizard.addDebt(debt);
    }
    await wizard.nextStep();

    await wizard.fillReview();
    await wizard.completeIntake();

    // Dashboard should NOT allow form generation for ineligible filer
    // (or should show appropriate messaging)
    const pageText = await page.textContent('body');
    expect(pageText?.toLowerCase()).not.toContain('error');
  });
});
