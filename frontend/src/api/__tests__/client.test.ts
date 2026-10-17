import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { api, APIClientError } from '../client';

/** The error a call rejects with, so its fields can be read. */
async function refusalOf(call: Promise<unknown>): Promise<APIClientError> {
  try {
    await call;
  } catch (err) {
    if (err instanceof APIClientError) return err;
    throw err;
  }
  throw new Error('the call was not refused');
}

// A refusal says what fixes it (step 3a1 spec §4): the wizard and the dashboard can only point
// the filer there if the client keeps it.
describe('what a refusal says fixes it', () => {
  it('keeps each reason Complete gives with its step, and drops an entry that lacks either', async () => {
    const noExpenses = {
      step: 'expense_info',
      message: 'Go through the Expenses step, even if you have no expenses to enter.',
    };
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
        HttpResponse.json(
          {
            message: 'Please complete all required sections before finalizing',
            errors: [
              noExpenses,
              'Expense information is required',
              { message: 'A sentence with no step' },
              { step: 'income_info' },
            ],
          },
          { status: 400 }
        )
      )
    );

    const err = await refusalOf(api.intake.completeSession(1));

    expect(err.message).toBe('Please complete all required sections before finalizing');
    expect(err.errors).toEqual([noExpenses]);
  });

  it('keeps the step or page a forms refusal names', async () => {
    server.use(
      http.post('http://localhost:8000/api/forms/generate_all/', () =>
        HttpResponse.json(
          { error: 'Finish your intake before preparing your forms.', page: '/intake' },
          { status: 422 }
        )
      ),
      http.post('http://localhost:8000/api/forms/generate/', () =>
        HttpResponse.json(
          {
            form_type: 'form_101',
            error: 'Enter your income by source on the Income step.',
            step: 'income_info',
          },
          { status: 422 }
        )
      )
    );

    const unfinished = await refusalOf(api.forms.generateAll(1));
    const notSplit = await refusalOf(api.forms.generate(1, 'form_101'));

    expect(unfinished.page).toBe('/intake');
    expect(unfinished.step).toBeUndefined();
    expect(notSplit.step).toBe('income_info');
    expect(notSplit.page).toBeUndefined();
  });

  it('keeps no step or page that is not a string, such as a field error', async () => {
    server.use(
      http.post('http://localhost:8000/api/forms/generate_all/', () =>
        HttpResponse.json(
          { step: ['This field is required.'], page: { number: 2 } },
          { status: 400 }
        )
      )
    );

    const err = await refusalOf(api.forms.generateAll(1));

    expect(err.step).toBeUndefined();
    expect(err.page).toBeUndefined();
    expect(err.errors).toBeUndefined();
  });
});
