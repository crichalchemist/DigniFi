/**
 * Fake OpenAI — a stand-in for the Chat Completions API.
 *
 * The scanned-bill journey runs the real upload → OCR → draft-debt path, but no test
 * should need an OpenAI key or the network. The backend reaches this server through
 * OPENAI_BASE_URL=http://127.0.0.1:4010/v1, which the openai SDK reads from the
 * environment on its own (OpenAIProvider passes only the key).
 *
 * Every request to POST /v1/chat/completions gets the same reply: the fields a model
 * would read from fixtures/synthetic-bill.png. Anything else is a 404, so a changed
 * SDK route fails loudly instead of silently returning a bill.
 *
 * The spec that needs it starts it, so completions() counts in that spec's own worker.
 * Nothing else (no CI step, no globalSetup) may listen on the port.
 */

import { createServer } from 'node:http';

/** What the "model" reads from fixtures/synthetic-bill.png. Every value is invented. */
export const CANNED_BILL = {
  creditor_name: 'Lakeside Example Clinic',
  account_number: '4821',
  amount_owed: '1247.83',
  minimum_payment: '65.00',
  due_date: '2026-10-15',
  creditor_type: 'medical',
  confidence_score: 92,
} as const;

export async function startFakeOpenAI(
  port = 4010
): Promise<{ completions(): number; close(): Promise<void> }> {
  let completions = 0;

  const server = createServer((req, res) => {
    // Read the whole request (prompt plus base64 page images) before answering.
    req.resume();
    req.on('end', () => {
      if (req.method !== 'POST' || req.url !== '/v1/chat/completions') {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(
          JSON.stringify({ error: { message: `fake-openai has no ${req.method} ${req.url}` } })
        );
        return;
      }
      completions += 1;
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(
        JSON.stringify({
          id: `chatcmpl-fake-${completions}`,
          object: 'chat.completion',
          created: Math.floor(Date.now() / 1000),
          model: 'gpt-4o',
          choices: [
            {
              index: 0,
              message: { role: 'assistant', content: JSON.stringify(CANNED_BILL), refusal: null },
              finish_reason: 'stop',
              logprobs: null,
            },
          ],
          usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
        })
      );
    });
  });

  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve());
  });

  return {
    completions: () => completions,
    close: () =>
      new Promise<void>((resolve, reject) => {
        // The backend's HTTP client keeps its connection open; drop it so close() returns.
        server.closeAllConnections();
        server.close((err) => (err ? reject(err) : resolve()));
      }),
  };
}
