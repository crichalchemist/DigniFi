/**
 * The site footer links to the source on every route (DigniFi is AGPL-3.0-or-later).
 */

import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import App from './App';

const SOURCE_URL = 'https://github.com/crichalchemist/DigniFi';

function renderAt(path: string) {
  window.history.pushState({}, '', path);
  return render(<App />);
}

describe('Source code link', () => {
  it('a visitor on a public page can reach the source', () => {
    renderAt('/terms');
    expect(screen.getByRole('link', { name: 'Source code' })).toHaveAttribute('href', SOURCE_URL);
  });

  it('a signed-in filer can reach the source', async () => {
    localStorage.setItem('refresh_token', 'refresh-token');
    renderAt('/fee-waiver');
    await screen.findByRole('button', { name: 'Sign out' });
    expect(screen.getByRole('link', { name: 'Source code' })).toHaveAttribute('href', SOURCE_URL);
  });

  it('the landing page has exactly one contentinfo landmark', async () => {
    const { container } = renderAt('/');
    expect(screen.getAllByRole('contentinfo')).toHaveLength(1);
    expect(screen.getByRole('link', { name: 'Source code' })).toBeInTheDocument();
    // Only the contentinfo rules: the landing page already has two banners (pre-existing).
    const results = await axe(container, {
      runOnly: ['landmark-no-duplicate-contentinfo', 'landmark-contentinfo-is-top-level'],
    });
    expect(results).toHaveNoViolations();
  });
});
