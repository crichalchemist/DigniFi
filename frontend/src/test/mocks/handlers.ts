/**
 * MSW request handlers — default happy-path responses for all API endpoints.
 *
 * Tests can override individual handlers via server.use(...) for error scenarios.
 */

import { http, HttpResponse } from 'msw';

const API = 'http://localhost:8000/api';

// ---------------------------------------------------------------------------
// Fixture data
// ---------------------------------------------------------------------------

const mockUser = {
  id: 1,
  email: 'jane@example.com',
  username: 'janedoe',
  agreed_to_upl_disclaimer: true,
  upl_disclaimer_agreed_at: '2026-01-15T10:00:00Z',
  created_at: '2026-01-15T10:00:00Z',
};

const mockSession = {
  id: 1,
  user: 1,
  district: 1,
  current_step: 1,
  status: 'started' as const,
  created_at: '2026-01-20T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
  completed_at: null,
  debtor_info: null,
  income_info: null,
  expense_info: null,
  assets: [],
  debts: [],
};

const mockGeneratedForm = {
  id: 1,
  session: 1,
  form_type: 'form_101' as const,
  form_type_display: 'Form 101 - Voluntary Petition',
  status: 'generated' as const,
  status_display: 'Generated',
  form_data: {},
  pdf_file_path: '/media/forms/form_101_1.pdf',
  upl_disclaimer: 'This form was prepared using information you provided.',
  generated_by: 1,
  generated_at: '2026-01-20T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
};

const mockMeansTestResult = {
  passes_means_test: true,
  qualifies_for_fee_waiver: false,
  current_monthly_income: 3500,
  median_income_threshold: 71304,
  disposable_monthly_income: 500,
  message:
    'Based on the information you provided, your income is below the median income threshold for your household size in your district.',
  details: {
    household_size: 1,
    total_income: 3500,
    total_expenses: 3000,
    district_name: 'Northern District of Illinois',
  },
};

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

export const handlers = [
  // -- Auth -----------------------------------------------------------------

  http.post(`${API}/token/obtain/`, () =>
    HttpResponse.json({
      access: 'mock-access-token',
      refresh: 'mock-refresh-token',
    }),
  ),

  http.post(`${API}/token/refresh/`, () =>
    HttpResponse.json({ access: 'refreshed-access-token' }),
  ),

  http.post(`${API}/users/register/`, () =>
    HttpResponse.json({ id: 1, email: 'jane@example.com', username: 'janedoe' }),
  ),

  http.get(`${API}/users/me/`, () => HttpResponse.json(mockUser)),

  // -- Intake Sessions ------------------------------------------------------

  http.post(`${API}/intake/sessions/`, () =>
    HttpResponse.json({ session: mockSession, message: 'Session created.' }),
  ),

  http.get(`${API}/intake/sessions/:id/`, () => HttpResponse.json(mockSession)),

  http.post(`${API}/intake/sessions/:id/update_step/`, () =>
    HttpResponse.json({
      session: { ...mockSession, current_step: 2, status: 'in_progress' },
      message: 'Step updated.',
    }),
  ),

  http.post(`${API}/intake/sessions/:id/complete/`, () =>
    HttpResponse.json({ message: 'Session completed.' }),
  ),

  http.post(`${API}/intake/sessions/:id/calculate_means_test/`, () =>
    HttpResponse.json({
      means_test_result: mockMeansTestResult,
      session_id: 1,
    }),
  ),

  http.get(`${API}/intake/sessions/:id/summary/`, () =>
    HttpResponse.json({
      session: mockSession,
      progress: { current_step: 1, status: 'started', completion_percentage: 16 },
      forms: { generated_count: 0, forms: [] },
    }),
  ),

  // -- Debtor / Income / Expense -------------------------------------------

  http.post(`${API}/intake/debtor-info/`, () =>
    HttpResponse.json({ id: 1, session: 1, first_name: 'Jane' }),
  ),

  http.post(`${API}/intake/income-info/`, () =>
    HttpResponse.json({ id: 1, session: 1, monthly_income: [3500, 3500, 3500, 3500, 3500, 3500] }),
  ),

  http.post(`${API}/intake/expense-info/`, () =>
    HttpResponse.json({ id: 1, session: 1, rent_or_mortgage: 1200 }),
  ),

  // -- Assets / Debts ------------------------------------------------------

  http.post(`${API}/intake/assets/`, () =>
    HttpResponse.json({ id: 1, session: 1, asset_type: 'vehicle', description: 'Car' }),
  ),

  http.post(`${API}/intake/debts/`, () =>
    HttpResponse.json({ id: 1, session: 1, debt_type: 'credit_card', creditor_name: 'Visa' }),
  ),

  // -- Forms ---------------------------------------------------------------

  http.post(`${API}/forms/generate_form_101/`, () =>
    HttpResponse.json({
      form: mockGeneratedForm,
      message: 'Form generated.',
    }),
  ),

  http.post(`${API}/forms/generate/`, async ({ request }) => {
    const body = (await request.json()) as { form_type?: string };
    return HttpResponse.json({
      form: {
        ...mockGeneratedForm,
        form_type: body.form_type ?? 'form_101',
        form_type_display: `${body.form_type ?? 'form_101'}`,
      },
      message: 'Form generated.',
    });
  }),

  http.post(`${API}/forms/generate_all/`, () =>
    HttpResponse.json({
      forms: [mockGeneratedForm],
      message: 'All forms generated.',
    }),
  ),

  http.get(`${API}/forms/`, () => HttpResponse.json([mockGeneratedForm])),

  http.get(`${API}/forms/:id/preview/`, () => HttpResponse.json(mockGeneratedForm)),

  http.post(`${API}/forms/:id/mark_downloaded/`, () =>
    HttpResponse.json({ message: 'Marked as downloaded.' }),
  ),

  http.post(`${API}/forms/:id/mark_filed/`, () =>
    HttpResponse.json({ message: 'Marked as filed.' }),
  ),
];
