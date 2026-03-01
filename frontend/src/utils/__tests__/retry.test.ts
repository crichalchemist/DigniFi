import { withRetry } from '../retry';
import { APIClientError } from '../../api/client';

describe('withRetry', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns result on first success', async () => {
    const fn = vi.fn().mockResolvedValue('ok');
    const result = await withRetry(fn);
    expect(result).toBe('ok');
    expect(fn).toHaveBeenCalledOnce();
  });

  it('retries on 5xx errors and eventually succeeds', async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new APIClientError('Server error', 500))
      .mockResolvedValue('recovered');

    const promise = withRetry(fn, { baseDelay: 10 });

    // Advance past first retry delay
    await vi.advanceTimersByTimeAsync(20);

    const result = await promise;
    expect(result).toBe('recovered');
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it('does not retry on 4xx errors', async () => {
    const fn = vi.fn().mockRejectedValue(new APIClientError('Bad request', 400));

    await expect(withRetry(fn)).rejects.toThrow('Bad request');
    expect(fn).toHaveBeenCalledOnce();
  });

  it('does not retry on 401 errors', async () => {
    const fn = vi.fn().mockRejectedValue(new APIClientError('Unauthorized', 401));

    await expect(withRetry(fn)).rejects.toThrow('Unauthorized');
    expect(fn).toHaveBeenCalledOnce();
  });

  it('retries on network errors (TypeError with fetch)', async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValue('ok');

    const promise = withRetry(fn, { baseDelay: 10 });
    await vi.advanceTimersByTimeAsync(20);

    const result = await promise;
    expect(result).toBe('ok');
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it('throws after exhausting max retries', async () => {
    vi.useRealTimers(); // Real timers to avoid unhandled rejection with fake timer flush
    const fn = vi.fn().mockRejectedValue(new APIClientError('Down', 503));

    await expect(
      withRetry(fn, { maxRetries: 2, baseDelay: 10 }),
    ).rejects.toThrow('Down');
    expect(fn).toHaveBeenCalledTimes(3); // 1 initial + 2 retries
  });

  it('uses exponential backoff delays', async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new APIClientError('err', 500))
      .mockRejectedValueOnce(new APIClientError('err', 500))
      .mockResolvedValue('ok');

    const promise = withRetry(fn, { maxRetries: 3, baseDelay: 100 });

    // After 100ms (first delay), second attempt fires
    await vi.advanceTimersByTimeAsync(100);
    expect(fn).toHaveBeenCalledTimes(2);

    // After 200ms more (second delay = 100 * 2^1), third attempt fires
    await vi.advanceTimersByTimeAsync(200);
    expect(fn).toHaveBeenCalledTimes(3);

    const result = await promise;
    expect(result).toBe('ok');
  });

  it('accepts custom shouldRetry predicate', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('custom'));

    await expect(
      withRetry(fn, {
        maxRetries: 1,
        shouldRetry: () => false,
      }),
    ).rejects.toThrow('custom');

    expect(fn).toHaveBeenCalledOnce();
  });
});
