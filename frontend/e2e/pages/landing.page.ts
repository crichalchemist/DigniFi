import type { Page } from '@playwright/test';

export class LandingPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  async clickGetStarted() {
    await this.page.getByRole('link', { name: /get started/i }).click();
    await this.page.waitForURL('**/register');
  }

  async clickSignIn() {
    await this.page.getByRole('link', { name: /sign in/i }).click();
    await this.page.waitForURL('**/login');
  }

  title() {
    return this.page.getByRole('heading', { level: 1 });
  }

  disclaimer() {
    return this.page.locator('.landing-disclaimer');
  }
}
