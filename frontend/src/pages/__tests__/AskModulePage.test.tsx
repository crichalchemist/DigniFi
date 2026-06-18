import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi } from 'vitest';
import { AskModulePage } from '../AskModulePage';

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'test@example.com' } }),
}));

vi.mock('../../context/IntakeContext', () => ({
  useIntake: () => ({
    session: { id: 1, current_step: 6 },
    createSession: vi.fn(),
    updateCurrentStep: vi.fn(),
  }),
}));

vi.mock('../../api/client', () => ({
  askModulesAPI: {
    getUISpec: vi.fn().mockResolvedValue({
      form_type: 'form_106dec',
      steps: [{ title: 'Debtor Info', fields: [] }],
    }),
    bulkUpsertAnswers: vi.fn().mockResolvedValue({ status: 'success', created: 0, updated: 0 }),
  },
}));

function renderPage(formType = 'form_106dec') {
  return render(
    <MemoryRouter initialEntries={[`/ask/${formType}`]}>
      <Routes>
        <Route path="/ask/:formType" element={<AskModulePage />} />
        <Route path="/forms" element={<div>FormDashboard</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AskModulePage', () => {
  it('renders form title', async () => {
    renderPage();
    expect(await screen.findByText('Declaration About Schedules')).toBeInTheDocument();
  });

  it('shows back link', async () => {
    renderPage();
    expect(await screen.findByText(/back to forms/i)).toBeInTheDocument();
  });

  it('renders wizard for unknown form type', async () => {
    renderPage('unknown_form');
    expect(await screen.findByText('unknown_form')).toBeInTheDocument();
  });
});
