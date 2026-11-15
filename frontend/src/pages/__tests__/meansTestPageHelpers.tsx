/**
 * What both Form 122A-2 page test files share: the stand-in server, the render and the queries.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { MeansTestPage } from '../MeansTestPage';
import { FORM_122A2_TITLE } from '../../constants/formText';
import { MEANS_TEST_PREVIEW_TITLE } from '../../constants/copy';
import type { MeansPage } from '../../types/api';

export const URL = 'http://localhost:8000/api/intake/sessions/:id/means-test/';
export const SOFA = 'Statement of Financial Affairs';

export type Body = Record<string, unknown>;

/** Serve `saved`; each PUT is recorded and answered with `reply` (the saved page by default) */
export function serve(
  saved: MeansPage,
  options: { status?: number; reply?: MeansPage; body?: Body } = {}
) {
  const sent: Body[] = [];
  server.use(
    http.get(URL, () => HttpResponse.json(saved)),
    http.put(URL, async ({ request }) => {
      sent.push((await request.json()) as Body);
      if (options.status !== undefined && options.status !== 200) {
        return HttpResponse.json(options.body ?? { detail: 'Bad request' }, {
          status: options.status,
        });
      }
      return HttpResponse.json(options.reply ?? saved);
    })
  );
  return sent;
}

export function renderPage(entry = '/means-test') {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <IntakeProvider>
        <Routes>
          <Route path="/means-test" element={<MeansTestPage />} />
          <Route path="/sofa" element={<div>{SOFA}</div>} />
          <Route path="/exemptions" element={<div>Exemptions</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

export const ready = () => screen.findByRole('heading', { level: 1, name: FORM_122A2_TITLE });
export const field = (name: string) =>
  document.querySelector(`input[name="${name}"]`) as HTMLInputElement;
export const radio = (name: string, value: string) =>
  document.querySelector(`input[name="${name}"][value="${value}"]`) as HTMLInputElement;
export const gapRegion = () => document.querySelector('main > div[role="status"]') as HTMLElement;
export const result = () => screen.getByRole('status', { name: MEANS_TEST_PREVIEW_TITLE });
export const pressContinue = () =>
  userEvent.click(screen.getByRole('button', { name: 'Continue' }));
