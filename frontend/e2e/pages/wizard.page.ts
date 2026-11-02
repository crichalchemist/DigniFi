/**
 * Wizard Page Object — wraps the multi-step intake wizard.
 *
 * Methods map to wizard steps and use name attributes / ARIA roles
 * from the actual components (DebtorInfoStep, IncomeInfoStep, etc.).
 */

import { expect, type Page } from '@playwright/test';
import type {
  DeductionField,
  PersonaAssistance,
  PersonaDebtor,
  PersonaIncome,
  PersonaAsset,
  PersonaDebt,
} from '../fixtures/personas';

export class WizardPage {
  constructor(private page: Page) {}

  // ── Navigation ──────────────────────────────────────────────────

  async nextStep() {
    const progress = this.page
      .getByRole('navigation', { name: 'Intake progress' })
      .locator('[aria-live="polite"]');
    const [before] = await progress.allTextContents();
    await this.page.getByRole('button', { name: /continue/i }).click();
    // Wait for the step to change, or for step 1's detour to /documents. A step's
    // save can outlast the fixed delay below, and a click during it lands a step behind.
    await expect(async () => {
      const leftWizard = !new URL(this.page.url()).pathname.startsWith('/intake');
      const [now] = await progress.allTextContents();
      expect(leftWizard || (now !== undefined && now !== before)).toBe(true);
    }).toPass({ timeout: 15_000 });
    // Wait for step transition (network + render)
    await this.page.waitForTimeout(500);
  }

  async completeIntake() {
    await this.page.getByRole('button', { name: /complete intake/i }).click();
    // Fee-waiver-eligible sessions are routed to the waiver application
    // first (see IntakeWizard → /fee-waiver); non-waiver goes to /sofa
    // (the SOFA/Form 107 step), then /forms after saving.
    await this.page.waitForURL(/\/(forms|fee-waiver|sofa)/);
  }

  async getCurrentStep(): Promise<string> {
    const heading = this.page.locator('.step-title');
    return heading.textContent() as Promise<string>;
  }

  /**
   * The eligibility widget is collapsed by default (note 12/15 redesign), so its
   * verdict text isn't in the DOM until opened. Expand it before reading or
   * asserting. Idempotent: only clicks when currently collapsed.
   */
  async expandMeansTestPreview() {
    const toggle = this.page.locator('.means-test-preview-toggle');
    if ((await toggle.getAttribute('aria-expanded')) === 'false') {
      await toggle.click();
    }
  }

  async getMeansTestPreview(): Promise<string> {
    await this.expandMeansTestPreview();
    const sidebar = this.page.locator('.wizard-sidebar');
    return sidebar.textContent() as Promise<string>;
  }

  /**
   * Wait for the debounced means-test estimate to resolve. The widget is
   * collapsed by default, so expand it and wait for the verdict indicator to
   * render — it replaces the loading/placeholder state once income AND expense
   * data have been saved. Call only after completing the expenses step.
   */
  async waitForMeansTestEstimate() {
    await this.expandMeansTestPreview();
    await expect(this.page.locator('.means-test-preview-indicator-text')).toBeVisible({
      timeout: 15000,
    });
  }

  // ── Step 1: Debtor Info ─────────────────────────────────────────

  async fillDebtorInfo(data: PersonaDebtor) {
    const fill = async (name: string, value: string) => {
      if (value) await this.page.locator(`input[name="${name}"]`).fill(value);
    };

    await fill('first_name', data.first_name);
    await fill('middle_name', data.middle_name);
    await fill('last_name', data.last_name);
    await fill('date_of_birth', data.date_of_birth);
    await fill('ssn', data.ssn);
    await fill('street_address', data.street_address);
    await fill('city', data.city);

    // State select
    const stateSelect = this.page.locator('select[name="state"], input[name="state"]');
    if ((await stateSelect.count()) > 0) {
      const tag = await stateSelect.first().evaluate((el) => el.tagName.toLowerCase());
      if (tag === 'select') {
        await stateSelect.first().selectOption(data.state);
      } else {
        await stateSelect.first().fill(data.state);
      }
    }

    await fill('zip_code', data.zip_code);
    await this.page.locator('select[name="county"]').selectOption(data.county);
    // Email is locked (readOnly) to the account address and auto-filled from the
    // authenticated user. The persona registered with data.email, so the field
    // already holds it — assert instead of fill (fill() times out on readOnly).
    await expect(this.page.locator('input[name="email"]')).toHaveValue(data.email);
    await fill('phone', data.phone);
  }

  // ── Step 2: Income Info ─────────────────────────────────────────

  async fillIncomeInfo(income: PersonaIncome) {
    // Line 1 first: picking "Living in the same household" adds the spouse's row, so it sits
    // at index 0 and the persona's members line up with the rows.
    if (
      income.marital_status === 'married_together' ||
      income.marital_status === 'married_separately'
    ) {
      await this.page.locator('input[name="marital_status"][value="not_filing"]').check();
      await this.page
        .locator(`input[name="spouse_household"][value="${income.marital_status}"]`)
        .check();
    } else {
      await this.page
        .locator(`input[name="marital_status"][value="${income.marital_status}"]`)
        .check();
    }

    if (income.members.length === 0) {
      await this.page
        .getByRole('button', { name: 'No one else lives with me or depends on me.' })
        .click();
    }
    const yesNo = (answer: boolean) => (answer ? 'yes' : 'no');
    for (const [index, member] of income.members.entries()) {
      const relationship = this.page.locator(`select[name="relationship_${index}"]`);
      if ((await relationship.count()) === 0) {
        await this.page.getByRole('button', { name: '+ Add a person' }).click();
      }
      await relationship.selectOption(member.relationship);
      await this.page.locator(`input[name="age_${index}"]`).fill(String(member.age));
      await this.page
        .locator(`input[name="lives_with_you_${index}"][value="${yesNo(member.lives_with_you)}"]`)
        .check();
      await this.page
        .locator(
          `input[name="claimed_or_supported_${index}"][value="${yesNo(member.claimed_or_supported)}"]`
        )
        .check();
      if (member.spouse_is_dependent !== undefined) {
        await this.page
          .locator(
            `input[name="spouse_is_dependent_${index}"][value="${yesNo(member.spouse_is_dependent)}"]`
          )
          .check();
      }
    }

    // A box for each source, named as the backend stores it, so each amount goes into its own
    // box and a source the persona leaves out stays blank. The spouse's boxes add `spouse_`.
    for (const [source, amount] of Object.entries(income.sources)) {
      await this.page.locator(`input[name="${source}"]`).fill(String(amount));
    }
    // The businesses and rental properties: "none" when the list is empty, else one card each
    await this.fillEntries(income.business, {
      none: 'I have no business or rental income.',
      add: '+ Add a business or property',
      prefix: '',
    });
    for (const [source, amount] of Object.entries(income.spouse_sources ?? {})) {
      await this.page.locator(`input[name="spouse_${source}"]`).fill(String(amount));
    }
    // The persona answers "now different" and assistance after the list. A persona answering
    // "yes" would need current figures, and none does, so the page object only picks the radio.
    await this.fillNowAndAssistance('', income.now_different, income.assistance);
    if (income.spouse_business) {
      await this.fillEntries(income.spouse_business, {
        none: 'My spouse has no business or rental income.',
        add: "+ Add your spouse's business or property",
        prefix: 'spouse_',
      });
    }
    if (income.spouse_now_different && income.spouse_assistance) {
      await this.fillNowAndAssistance(
        'spouse_',
        income.spouse_now_different,
        income.spouse_assistance
      );
    }
  }

  private async fillNowAndAssistance(
    prefix: string,
    nowDifferent: 'yes' | 'no',
    assistance: PersonaAssistance
  ) {
    await this.page
      .locator(`input[name="${prefix}income_now_different"][value="${nowDifferent}"]`)
      .check();
    await this.page
      .locator(`input[name="${prefix}assistance_answer"][value="${assistance.answer}"]`)
      .check();
    const boxes: [string, string | number | undefined][] = [
      ['cash_assistance_kind', assistance.cash_kind],
      ['cash_assistance_amount', assistance.cash_amount],
      ['noncash_assistance_kind', assistance.noncash_kind],
      ['noncash_assistance_value', assistance.noncash_value],
    ];
    for (const [name, value] of boxes) {
      if (value !== undefined) {
        await this.page.locator(`input[name="${prefix}${name}"]`).fill(String(value));
      }
    }
  }

  private async fillEntries(
    entries: PersonaIncome['business'],
    { none, add, prefix }: { none: string; add: string; prefix: string }
  ) {
    if (entries.length === 0) {
      await this.page.getByRole('button', { name: none }).click();
      return;
    }
    for (const [index, entry] of entries.entries()) {
      await this.page.getByRole('button', { name: add }).click();
      await this.page
        .locator(`select[name="${prefix}entry_kind_${index}"]`)
        .selectOption(entry.kind);
      await this.page
        .locator(`input[name="${prefix}entry_description_${index}"]`)
        .fill(entry.description);
      await this.page
        .locator(`input[name="${prefix}entry_gross_${index}"]`)
        .fill(String(entry.gross));
      await this.page
        .locator(`input[name="${prefix}entry_expenses_${index}"]`)
        .fill(String(entry.expenses));
    }
  }

  // ── Step 3: Take-home pay ───────────────────────────────────────

  async fillTakeHomePay(
    deductions: Partial<Record<DeductionField, number>>,
    spouseDeductions?: Partial<Record<DeductionField, number>>
  ) {
    for (const [field, value] of Object.entries(deductions)) {
      await this.page.locator(`input[name="${field}"]`).fill(String(value));
    }
    for (const [field, value] of Object.entries(spouseDeductions ?? {})) {
      await this.page.locator(`input[name="spouse_${field}"]`).fill(String(value));
    }
  }

  // ── Step 4: Expenses ────────────────────────────────────────────

  async fillExpenses(expenses: Record<string, number>) {
    // Persona keys are the backend's ExpenseInfo names, and ExpenseInfoStep names each
    // box the same way, so every amount goes straight into its own box.
    for (const [field, value] of Object.entries(expenses)) {
      await this.page.locator(`input[name="${field}"]`).fill(String(value));
    }
  }

  // ── Step 5: Assets ──────────────────────────────────────────────

  // Both steps render one empty row by default and suffix field names with
  // the row index (asset_type_0, creditor_name_1, ...). Track how many rows
  // we've filled so we only click "Add Another" from the second entry on.
  private assetCount = 0;
  private debtCount = 0;

  async addAsset(asset: PersonaAsset) {
    const index = this.assetCount;
    if (index > 0) {
      await this.page.getByRole('button', { name: /add another asset/i }).click();
    }

    await this.page.locator(`select[name="asset_type_${index}"]`).selectOption(asset.asset_type);
    await this.page.locator(`input[name="description_${index}"]`).fill(asset.description);
    await this.page
      .locator(`input[name="current_value_${index}"]`)
      .fill(String(asset.current_value));
    await this.page.locator(`input[name="amount_owed_${index}"]`).fill(String(asset.amount_owed));

    this.assetCount++;
  }

  // ── Step 6: Debts ───────────────────────────────────────────────

  async addDebt(debt: PersonaDebt) {
    const index = this.debtCount;
    if (index > 0) {
      await this.page.getByRole('button', { name: /add another amount owed/i }).click();
    }

    await this.page.locator(`select[name="debt_type_${index}"]`).selectOption(debt.debt_type);
    await this.page.locator(`input[name="creditor_name_${index}"]`).fill(debt.creditor_name);
    await this.page.locator(`input[name="amount_owed_${index}"]`).fill(String(debt.amount_owed));
    await this.page
      .locator(`input[name="monthly_payment_${index}"]`)
      .fill(String(debt.monthly_payment));

    // Secured debt types reveal a required collateral textarea; the step
    // blocks Continue until it's filled.
    if (debt.collateral_description) {
      await this.page
        .locator(`textarea[name="collateral_description_${index}"]`)
        .fill(debt.collateral_description);
    }

    this.debtCount++;
  }

  // ── Step 9: Review ──────────────────────────────────────────────

  async fillReview() {
    // Review step may just need a confirmation/acknowledgment
    const confirmCheck = this.page.locator(
      'input[type="checkbox"][name*="confirm"], input[type="checkbox"][name*="review"]'
    );
    if ((await confirmCheck.count()) > 0) {
      await confirmCheck.first().check();
    }
  }
}
