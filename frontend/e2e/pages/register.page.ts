import type { Page } from '@playwright/test';

export class RegisterPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/register');
  }

  async register(username: string, email: string, password: string) {
    await this.page.locator('input[name="email"]').fill(email);
    await this.page.locator('input[name="username"]').fill(username);
    await this.page.locator('input[name="password"]').fill(password);
    await this.page.locator('input[name="confirmPassword"]').fill(password);

    // Check both required checkboxes (UPL + Terms)
    const checkboxes = this.page.locator('.auth-checkbox');
    await checkboxes.nth(0).check();
    await checkboxes.nth(1).check();

    await this.page.getByRole('button', { name: /create account/i }).click();
    await this.page.waitForURL('**/intake');
  }
}
