/**
 * Wizard Page Object — wraps the multi-step intake wizard.
 *
 * Methods map to wizard steps and use name attributes / ARIA roles
 * from the actual components (DebtorInfoStep, IncomeInfoStep, etc.).
 */

import { expect, type Locator, type Page } from '@playwright/test';
import type {
  DeductionField,
  PersonaAssistance,
  PersonaDebtor,
  PersonaIncome,
  PersonaAddress,
  PersonaAsset,
  PersonaDebt,
  PersonaData,
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
    // Every filer answers Form 101 line 8 on the filing-fee page next (see IntakeWizard →
    // /filing-fee), which continues to /sofa.
    await this.page.waitForURL(/\/filing-fee/);
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

  async fillExpenses(
    persona: Pick<PersonaData, 'expenses' | 'expenses_include_others' | 'expense_texts'>
  ) {
    // Line 3 comes first on the page and is never answered for the filer
    await this.page
      .locator(`input[name="expenses_include_others"][value="${persona.expenses_include_others}"]`)
      .check();
    // Persona keys are the backend's ExpenseInfo names, and ExpenseInfoStep names each
    // box the same way, so every amount goes straight into its own box.
    for (const [field, value] of Object.entries(persona.expenses)) {
      await this.page.locator(`input[name="${field}"]`).fill(String(value));
    }
    for (const [field, text] of Object.entries(persona.expense_texts ?? {})) {
      await this.page.locator(`input[name="${field}"]`).fill(text);
    }
  }

  // ── Step 5: Assets ──────────────────────────────────────────────

  // The step is Schedule A/B a Part at a time. Each line has a No/Yes radio pair named
  // line_<key>_answer, and each row on it names its boxes line_<key>_<rowIndex>_<field>.
  // A second row on a line comes from the line's "Add another" and takes the next index, so this
  // counts the rows filled on each line.
  private assetRows = new Map<string, number>();
  // Amounts Owed suffixes its boxes with the row index too: this counts the debts filled, so its
  // "Add another" is clicked only from the second on.
  private debtCount = 0;

  private lineBlock(key: string) {
    return this.page
      .locator('.ab-line')
      .filter({ has: this.page.locator(`input[name="line_${key}_answer"]`) });
  }

  /** Answers the line Yes, then fills the next row on it by shape: the boxes the line shows. */
  async addAsset(asset: PersonaAsset) {
    const key = asset.ab_line;
    const index = this.assetRows.get(key) ?? 0;
    const line = this.lineBlock(key);
    if (index === 0) {
      // Yes opens the line's first row
      await this.page.locator(`input[name="line_${key}_answer"][value="yes"]`).check();
    } else {
      await line.getByRole('button', { name: 'Add another', exact: true }).click();
    }
    const prefix = `line_${key}_${index}`;

    if (asset.description !== undefined) {
      await this.page.locator(`input[name="${prefix}_description"]`).fill(asset.description);
    }
    for (const [field, value] of Object.entries(asset.details ?? {})) {
      if (field === 'kind') {
        await this.page.locator(`select[name="${prefix}_kind"]`).selectOption(value as string);
      } else if (field === 'who' || field === 'lives_here') {
        await this.page.locator(`input[name="${prefix}_${field}"][value="${value}"]`).check();
      } else if (field === 'property_kinds') {
        for (const kind of value as string[]) {
          await this.page
            .locator(`input[name="${prefix}_property_kinds"][value="${kind}"]`)
            .check();
        }
      } else {
        await this.page.locator(`input[name="${prefix}_${field}"]`).fill(value as string);
      }
    }
    // A $0 is typed as 0: an empty box is "not answered"
    if (asset.entire_value !== undefined) {
      await this.page
        .locator(`input[name="${prefix}_entire_value"]`)
        .fill(String(asset.entire_value));
    }
    await this.page
      .locator(`input[name="${prefix}_current_value"]`)
      .fill(String(asset.current_value));

    this.assetRows.set(key, index + 1);
  }

  /** Answers No on every line of the Part showing that has no answer yet. */
  async answerLinesNo() {
    // A No on a gate hides the lines under it, and a Yes shows them, so ask the page again
    // after each press instead of listing the radios once.
    for (;;) {
      const names = await this.page
        .locator('input[type="radio"][name^="line_"][name$="_answer"][value="no"]')
        .evaluateAll((radios) =>
          radios
            .map((radio) => (radio as HTMLInputElement).name)
            .filter(
              (name) => document.querySelectorAll(`input[name="${name}"]:checked`).length === 0
            )
        );
      if (names.length === 0) return;
      await this.page.locator(`input[name="${names[0]}"][value="no"]`).check();
    }
  }

  private async assetPart(): Promise<number> {
    const text = await this.page.getByText(/^Part \d of 7$/).textContent();
    return Number(/Part (\d)/.exec(text ?? '')?.[1]);
  }

  /**
   * The whole Assets step: for each Part, the persona's rows on the lines it shows, a No on
   * every other line, then Continue. Continue moves a Part until Part 7, then leaves the step.
   */
  async walkAssets(persona: Pick<PersonaData, 'assets' | 'asset_gates'>) {
    this.assetRows = new Map();
    const unfilled = new Set(persona.assets);
    for (;;) {
      const part = await this.assetPart();
      for (const gate of persona.asset_gates ?? []) {
        const radio = this.page.locator(`input[name="line_${gate}_answer"][value="yes"]`);
        if ((await radio.count()) > 0) await radio.check();
      }
      for (const asset of persona.assets) {
        if (!unfilled.has(asset)) continue;
        const shown = this.page.locator(`input[name="line_${asset.ab_line}_answer"]`);
        if ((await shown.count()) === 0) continue;
        await this.addAsset(asset);
        unfilled.delete(asset);
      }
      await this.answerLinesNo();
      if (part === 7) {
        expect(unfilled.size, 'every persona asset sits on a line the walk showed').toBe(0);
        await this.nextStep();
        return;
      }
      await this.page.getByRole('button', { name: /continue/i }).click();
      await expect(this.page.getByText(`Part ${part + 1} of 7`, { exact: true })).toBeVisible({
        timeout: 15_000,
      });
    }
  }

  // ── Step 6: Debts ───────────────────────────────────────────────

  /** Types each address box of one address; an address outside the US stops before state and ZIP. */
  private async fillAddress(
    prefix: '' | 'codebtor_' | 'community_spouse_',
    suffix: string,
    address: PersonaAddress
  ) {
    const box = (field: string) => this.page.locator(`input[name="${prefix}${field}${suffix}"]`);
    await box('street_address').fill(address.street_address);
    if (address.street_2) await box('street_2').fill(address.street_2);
    await box('city').fill(address.city);
    if (address.outside_us) {
      await box('outside_us').check();
      return;
    }
    await box('state').fill(address.state);
    await box('zip_code').fill(address.zip_code);
  }

  /** Picks the option whose words contain `text`; fails the journey when none does. */
  private async pick(select: Locator, text: string) {
    const value = await select.locator('option', { hasText: text }).first().getAttribute('value');
    expect(value, `an option containing "${text}"`).not.toBeNull();
    await select.selectOption(value as string);
  }

  async addDebt(debt: PersonaDebt) {
    const index = this.debtCount;
    if (index > 0) {
      await this.page.getByRole('button', { name: /add another amount owed/i }).click();
    }

    await this.page.locator(`select[name="debt_type_${index}"]`).selectOption(debt.debt_type);
    await this.page.locator(`input[name="creditor_name_${index}"]`).fill(debt.creditor_name);
    await this.page.locator(`input[name="amount_owed_${index}"]`).fill(String(debt.amount_owed));
    await this.fillDebtAnswers(index, debt);

    this.debtCount++;
  }

  /**
   * Everything a row asks after its kind, name and amount, which a scanned draft already holds.
   * The order is the step's own.
   */
  async fillDebtAnswers(index: number, debt: PersonaDebt) {
    const page = this.page;
    await this.fillAddress('', `_${index}`, debt.address);
    if (debt.account_last_4) {
      await page.locator(`input[name="account_number_${index}"]`).fill(debt.account_last_4);
    }
    if (debt.date_incurred) {
      await page.locator(`input[name="date_incurred_${index}"]`).fill(debt.date_incurred);
    }

    // The kind starts this answer for the filer; a press on the chosen radio changes nothing
    const secured = debt.secured;
    await page
      .locator(`input[name="is_secured_${index}"][value="${secured ? 'yes' : 'no'}"]`)
      .check();
    if (secured) {
      await this.pick(page.locator(`select[name="secured_by_${index}"]`), secured.pick);
      for (const lien of secured.lien) {
        await page.locator(`input[name="lien_${index}"][value="${lien}"]`).check();
      }
      if (debt.collateral_description) {
        await page
          .locator(`textarea[name="collateral_description_${index}"]`)
          .fill(debt.collateral_description);
      }
      if (secured.home_payment_line) {
        await page
          .locator(`input[name="home_payment_line_${index}"][value="${secured.home_payment_line}"]`)
          .check();
      }
      if (secured.collateral_who) {
        await page
          .locator(`input[name="collateral_who_${index}"][value="${secured.collateral_who}"]`)
          .check();
      }
    }
    await page.locator(`input[name="monthly_payment_${index}"]`).fill(String(debt.monthly_payment));

    if (debt.claim_status.length === 0) {
      await page.locator(`input[name="claim_status_${index}"][value="none"]`).check();
    }
    for (const status of debt.claim_status) {
      await page.locator(`input[name="claim_status_${index}"][value="${status}"]`).check();
    }
    if (!secured) {
      await page
        .locator(`input[name="offset_answer_${index}"][value="${debt.offset_answer ?? 'no'}"]`)
        .check();
      await page
        .locator(`input[name="priority_answer_${index}"][value="${debt.priority_answer ?? 'no'}"]`)
        .check();
    }

    const parties = debt.notice_parties;
    await page
      .locator(`input[name="notice_${index}"][value="${parties.length > 0 ? 'yes' : 'no'}"]`)
      .check();
    for (const [j, party] of parties.entries()) {
      const box = (field: string) => page.locator(`input[name="notice_${index}_${j}_${field}"]`);
      await box('name').fill(party.name);
      await box('street_address').fill(party.street_address);
      if (party.street_2) await box('street_2').fill(party.street_2);
      await box('city').fill(party.city);
      if (party.outside_us) {
        await box('outside_us').check();
      } else {
        await box('state').fill(party.state);
        await box('zip_code').fill(party.zip_code);
      }
      await box('last_4').fill(party.last_4);
    }
  }

  async answerNoDebts() {
    await this.page.getByRole('button', { name: 'I have no amounts owed', exact: true }).click();
  }

  /** The whole Amounts Owed step: "I have no amounts owed", or each row, then Continue. */
  async walkDebts(persona: Pick<PersonaData, 'debts'>) {
    if (persona.debts.length === 0) {
      await this.answerNoDebts();
    }
    for (const debt of persona.debts) {
      await this.addDebt(debt);
    }
    await this.nextStep();
  }

  // ── Step 7: Contracts & Leases ──────────────────────────────────

  async walkContracts(persona: Pick<PersonaData, 'contracts' | 'claim_answers'>) {
    const page = this.page;
    await page
      .locator(`input[name="contracts_answer"][value="${persona.claim_answers.contracts_answer}"]`)
      .check();
    for (const [i, contract] of persona.contracts.entries()) {
      // No blank row shows, so the button makes the first row too
      await page.getByRole('button', { name: /add contract/i }).click();
      await page.locator(`select[name="contract_type_${i}"]`).selectOption(contract.contract_type);
      await page.locator(`input[name="counterparty_name_${i}"]`).fill(contract.counterparty_name);
      await page.locator(`input[name="description_${i}"]`).fill(contract.description);
      await this.fillAddress('', `_${i}`, contract.address);
      if (contract.lease_kind) {
        await page.locator(`select[name="lease_kind_${i}"]`).selectOption(contract.lease_kind);
      }
      if (contract.vehicle) {
        await this.pick(page.locator(`select[name="vehicle_asset_${i}"]`), contract.vehicle.pick);
      }
      if (contract.monthly_payment !== undefined) {
        await page
          .locator(`input[name="monthly_payment_${i}"]`)
          .fill(String(contract.monthly_payment));
      }
      await page.locator(`input[name="owes_now_${i}"][value="${contract.owes_now}"]`).check();
    }
    await this.nextStep();
  }

  // ── Step 8: Codebtors ───────────────────────────────────────────

  async walkCodebtors(persona: Pick<PersonaData, 'codebtors' | 'claim_answers'>) {
    const page = this.page;
    const answers = persona.claim_answers;
    if (answers.community_lived !== 'no') {
      throw new Error('No persona has data for a community-property answer of yes');
    }
    await page
      .locator(`input[name="codebtors_answer"][value="${answers.codebtors_answer}"]`)
      .check();
    await page.locator(`input[name="community_lived"][value="${answers.community_lived}"]`).check();
    for (const [i, codebtor] of persona.codebtors.entries()) {
      await page.getByRole('button', { name: /add codebtor/i }).click();
      await page.locator(`input[name="codebtor_name_${i}"]`).fill(codebtor.name);
      if (codebtor.relationship) {
        await page
          .locator(`select[name="codebtor_relationship_${i}"]`)
          .selectOption(codebtor.relationship);
      }
      await this.fillAddress('codebtor_', `_${i}`, codebtor.address);
      for (const name of codebtor.links) {
        await page
          .getByLabel(name, { exact: true })
          .and(page.locator(`input[name="codebtor_links_${i}"]`))
          .check();
      }
    }
    await this.nextStep();
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
