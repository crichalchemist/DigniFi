# Wizard Autosave Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the intake wizard's "Your progress is automatically saved" claim true by wiring the existing (dead) `useAutoSave` hook into the wizard, showing a live save-status indicator, and ensuring save failures are never silent.

**Architecture:** A complete debounced-autosave hook already exists at `frontend/src/hooks/useAutoSave.ts` but is imported nowhere. We wire it into `IntakeWizard` so it watches the _current step's_ data slice and calls the existing `saveCurrentStepData()` on a 2s debounce. Autosave is gated by the step's existing validity flag (`canProceed`), so we only ever PATCH a complete, valid step — this means the backend serializer's `update_or_create` always has the required fields and **no backend change is needed**. The hook's status (`idle/saving/saved/error`) is threaded into `WizardLayout`, replacing the false help-text sentence with an honest, `aria-live` indicator. `handleNext`/`handleComplete` call the hook's `saveNow()` and refuse to advance if it fails, fixing today's silent-failure path.

**Tech Stack:** React 19, TypeScript, Vite, vitest + @testing-library/react (`renderHook`, fake timers). No new dependencies.

---

## Background: why this shape

Verified facts (2026-06-13):

- `frontend/src/hooks/useAutoSave.ts` is a finished hook (2s debounce, `saveStatus`, `saveNow`, `lastSavedAt`, unmount cleanup, skips first render) — but `grep -rn "useAutoSave"` finds **only its own definition**. It is dead code. The sibling `useDebouncedMeansTest` is wired into `MeansTestPreview`, proving the debounced-hook pattern works here.
- `IntakeWizard.tsx` persists step data **only** in `handleNext` (`saveCurrentStepData()` at line 96) and `handleComplete` (line 118). Typing does not save; **Go Back** does not save. Close the tab before clicking Continue → that step is lost.
- `handleNext`'s `catch` only `console.error`s (line 104), so a failed save is invisible **and** silently blocks advancing.
- `WizardLayout.tsx` renders `<p className="wizard-help-text">Your progress is automatically saved. You can return anytime to continue.</p>` — the false claim.
- Backend `IntakeSessionSerializer.update()` pops only the nested keys present in the PATCH and uses `update_or_create(session=instance, defaults=<step_data>)`. A single-step PATCH is therefore non-clobbering. The only failure mode is creating a brand-new nested row missing required fields — avoided entirely by gating autosave on `canProceed` (a valid step has all required fields).

Deliberate deferral (YAGNI): persisting _half-finished within-step_ fields (before the step is valid) would require backend partial-nested support. Out of scope. Gating on `canProceed` already eliminates the large data-loss window (whole completed steps) that note 24 is about.

## File Structure

- **Modify** `frontend/src/hooks/useAutoSave.ts` — make `saveNow`/`executeSave` return `Promise<boolean>` so callers can detect failure; export the `SaveStatus` type.
- **Create** `frontend/src/hooks/__tests__/useAutoSave.test.ts` — unit tests for debounce, status transitions, error path, `saveNow`.
- **Modify** `frontend/src/components/wizard/WizardLayout.tsx` — accept `saveStatus`/`lastSavedAt` props; replace the static help-text sentence with a live `aria-live="polite"` indicator.
- **Modify** `frontend/src/pages/IntakeWizard.tsx` — compute the current step's data slice; call `useAutoSave`; pass status to `WizardLayout`; route `handleNext`/`handleComplete` through `saveNow()` and block advancing on failure.
- **Modify** `frontend/src/pages/__tests__/IntakeWizard.test.tsx` — integration tests: debounced autosave fires a PATCH; failed save shows the error and does not advance.
- **Modify** `frontend/src/styles/global.css` — styles for `.wizard-save-status` and its states.

---

## Task 1: Make `useAutoSave.saveNow` report success/failure

**Files:**

- Modify: `frontend/src/hooks/useAutoSave.ts`
- Test: `frontend/src/hooks/__tests__/useAutoSave.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/__tests__/useAutoSave.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAutoSave } from '../useAutoSave';

describe('useAutoSave', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('debounces save until inactivity window elapses', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
      initialProps: { data: { a: 0 } },
    });

    // First render is skipped by the hook; a change should schedule a save.
    rerender({ data: { a: 1 } });
    expect(onSave).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it('does not autosave when disabled', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, enabled: false }), {
      initialProps: { data: { a: 0 } },
    });
    rerender({ data: { a: 1 } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(onSave).not.toHaveBeenCalled();
  });

  it('saveNow returns true on success and false on failure', async () => {
    const onSave = vi
      .fn()
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error('network'));
    const { result } = renderHook(() => useAutoSave({ data: { a: 1 }, onSave }));

    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.saveNow();
    });
    expect(ok).toBe(true);
    expect(result.current.saveStatus).toBe('saved');

    await act(async () => {
      ok = await result.current.saveNow();
    });
    expect(ok).toBe(false);
    expect(result.current.saveStatus).toBe('error');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/hooks/__tests__/useAutoSave.test.ts`
Expected: FAIL — the `saveNow returns true/false` assertions fail because `saveNow` currently resolves to `void`.

- [ ] **Step 3: Make `executeSave` and `saveNow` return a boolean and export `SaveStatus`**

In `frontend/src/hooks/useAutoSave.ts`:

Change the type export line:

```ts
export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';
```

Change `UseAutoSaveReturn.saveNow`:

```ts
interface UseAutoSaveReturn {
  saveStatus: SaveStatus;
  /** Manually trigger an immediate save. Resolves true on success, false on failure. */
  saveNow: () => Promise<boolean>;
  /** Last successful save timestamp */
  lastSavedAt: Date | null;
}
```

Change `executeSave` to return `Promise<boolean>`:

```ts
const executeSave = useCallback(async (): Promise<boolean> => {
  setSaveStatus('saving');
  try {
    await onSaveRef.current(dataRef.current);
    setSaveStatus('saved');
    setLastSavedAt(new Date());
    // Reset to idle after 3 seconds
    setTimeout(() => setSaveStatus((s) => (s === 'saved' ? 'idle' : s)), 3000);
    return true;
  } catch {
    setSaveStatus('error');
    return false;
  }
}, []);
```

Change `saveNow`:

```ts
const saveNow = useCallback(async (): Promise<boolean> => {
  if (timerRef.current) clearTimeout(timerRef.current);
  return executeSave();
}, [executeSave]);
```

(The debounced effect at the `setTimeout(executeSave, debounceMs)` call is unchanged — it ignores the returned promise.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/hooks/__tests__/useAutoSave.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useAutoSave.ts frontend/src/hooks/__tests__/useAutoSave.test.ts
git commit -m "test(intake): cover useAutoSave; saveNow reports success/failure

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Render a live save-status indicator in WizardLayout

**Files:**

- Modify: `frontend/src/components/wizard/WizardLayout.tsx`
- Modify: `frontend/src/styles/global.css`

- [ ] **Step 1: Add the props to `WizardLayoutProps`**

In `frontend/src/components/wizard/WizardLayout.tsx`, import the type and extend the interface:

```ts
import type { SaveStatus } from '../../hooks/useAutoSave';
```

Add to `interface WizardLayoutProps`:

```ts
  /** Live autosave status from useAutoSave (optional; falls back to static copy) */
  saveStatus?: SaveStatus;
  /** Timestamp of the last successful autosave */
  lastSavedAt?: Date | null;
```

Add to the destructured params (with defaults):

```ts
  saveStatus,
  lastSavedAt = null,
```

- [ ] **Step 2: Replace the false help-text sentence with an honest indicator**

Find:

```tsx
{
  /* Help text */
}
<p className="wizard-help-text">
  Your progress is automatically saved. You can return anytime to continue.
</p>;
```

Replace with:

```tsx
{
  /* Save status — honest, live autosave feedback (replaces the prior
              "automatically saved" claim, which was never wired to a real save). */
}
<p className="wizard-save-status" role="status" aria-live="polite">
  {saveStatus === 'saving' && (
    <span className="wizard-save-status--saving">Saving your progress…</span>
  )}
  {saveStatus === 'saved' && (
    <span className="wizard-save-status--saved">Saved. You can return anytime to continue.</span>
  )}
  {saveStatus === 'error' && (
    <span className="wizard-save-status--error">
      We couldn’t save just now — we’ll try again when you continue.
    </span>
  )}
  {(saveStatus === undefined || saveStatus === 'idle') && (
    <span className="wizard-save-status--idle">
      {lastSavedAt
        ? 'Saved. You can return anytime to continue.'
        : 'Your progress saves automatically as you complete each step.'}
    </span>
  )}
</p>;
```

- [ ] **Step 3: Add styles**

Append to `frontend/src/styles/global.css` (near the existing `.wizard-help-text` rule; reuse the caption token floor and existing colors):

```css
.wizard-save-status {
  font-size: var(--text-caption);
  color: var(--color-muted);
  margin: var(--space-2) 0 0;
  min-height: 1.25rem; /* reserve space so the footer doesn't jump between states */
}

.wizard-save-status--saving {
  color: var(--color-muted);
}

.wizard-save-status--saved {
  color: var(--color-pine);
}

.wizard-save-status--error {
  color: var(--color-rust);
}
```

- [ ] **Step 4: Verify typecheck + existing tests still pass**

Run: `cd frontend && npx tsc --noEmit && npx vitest run src/components/wizard`
Expected: tsc clean; existing WizardLayout tests pass (the new props are optional, so current callers compile).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/wizard/WizardLayout.tsx frontend/src/styles/global.css
git commit -m "feat(intake): live autosave status in WizardLayout, drop false claim

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Wire useAutoSave into IntakeWizard (gated by step validity)

**Files:**

- Modify: `frontend/src/pages/IntakeWizard.tsx`

- [ ] **Step 1: Import the hook**

Add to the imports in `frontend/src/pages/IntakeWizard.tsx`:

```ts
import { useAutoSave } from '../hooks/useAutoSave';
```

- [ ] **Step 2: Compute the current step's data slice and call the hook**

Place this **after** `saveCurrentStepData` is defined and **after** the `currentStepNumber`/`canProceed`/data states exist (so the closures are current), e.g. just above the `Navigation Handlers` section:

```ts
// The data object for the step currently on screen. useAutoSave watches this;
// when it changes (the user typing), it debounces a call to saveCurrentStepData.
const currentStepKey = WIZARD_STEPS[currentStepNumber - 1]?.key;
const currentStepData =
  currentStepKey === 'debtor_info'
    ? debtorData
    : currentStepKey === 'income_info'
      ? incomeData
      : currentStepKey === 'expense_info'
        ? expenseData
        : currentStepKey === 'assets'
          ? assetsData
          : currentStepKey === 'debts'
            ? debtsData
            : null;

const { saveStatus, saveNow, lastSavedAt } = useAutoSave({
  data: currentStepData,
  onSave: saveCurrentStepData,
  // Only autosave a complete, valid step. This guarantees the PATCH carries
  // every required field, so the backend's update_or_create never fails on a
  // partial create — no backend changes needed. The 'review' step has no data
  // to save. Disabled until a session exists.
  enabled: !!session && canProceed && currentStepKey !== 'review',
});
```

Note: `saveCurrentStepData` ignores its argument and reads the latest step state from its closure; `useAutoSave` refreshes its `onSave` ref every render, so it always calls the current definition.

- [ ] **Step 3: Route Continue/Complete through saveNow and block advancing on failure**

Replace `handleNext` body:

```ts
const handleNext = async () => {
  if (!session) return;

  // Save the current step immediately (flushes any pending debounce). If the
  // save fails, do NOT advance — the WizardLayout indicator shows the error.
  const saved = await saveNow();
  if (!saved) return;

  const nextStep = currentStepNumber + 1;
  await updateCurrentStep(nextStep);
  setCurrentStepNumber(nextStep);
  setCanProceed(false); // Reset validation for next step
};
```

Replace the save call at the top of `handleComplete`:

```ts
  const handleComplete = async () => {
    const saved = await saveNow();
    if (!saved) return;
    try {
      await completeSession();
      // ...existing completion logic (means test + navigate) unchanged...
```

(Keep the existing `try/catch` and navigation that follow `completeSession()`.)

- [ ] **Step 4: Pass status to WizardLayout**

In the returned JSX, add the two props to `<WizardLayout ... />`:

```tsx
saveStatus = { saveStatus };
lastSavedAt = { lastSavedAt };
```

- [ ] **Step 5: Typecheck + run the wizard tests**

Run: `cd frontend && npx tsc --noEmit && npx vitest run src/pages/__tests__/IntakeWizard.test.tsx`
Expected: tsc clean. Existing IntakeWizard tests pass (handleNext still advances on a successful save — the API mock resolves, so `saveNow()` returns true).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/IntakeWizard.tsx
git commit -m "feat(intake): wire debounced autosave; block advance on save failure

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Integration tests — autosave fires, failures surface and block

**Files:**

- Modify: `frontend/src/pages/__tests__/IntakeWizard.test.tsx`

> The existing test file already mocks `useAuth` and renders the wizard. These tests add fake timers and assert on the autosave behavior. Match the file's existing render/setup helpers — read them before writing and reuse the session/API mock pattern already present.

- [ ] **Step 1: Write the failing test — typing debounces a PATCH**

Add to `frontend/src/pages/__tests__/IntakeWizard.test.tsx`:

```tsx
it('autosaves the current step after the debounce once the step is valid', async () => {
  vi.useFakeTimers();
  const updateSession = vi.spyOn(api.intake, 'updateSession').mockResolvedValue({} as never);

  renderWizard(); // existing helper that mounts IntakeWizard with a ready session

  // Make step 1 valid (fill the required debtor fields the step validates on).
  // Use the file's existing helper for filling step 1 if present; otherwise
  // fire change events on the required inputs so onValidationChange(true) fires.
  await fillDebtorStepValid();

  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000);
  });

  expect(updateSession).toHaveBeenCalledWith(
    expect.any(Number),
    expect.objectContaining({ debtor_info: expect.any(Object) })
  );
  vi.useRealTimers();
});
```

- [ ] **Step 2: Write the failing test — failed save shows error and does not advance**

```tsx
it('shows a save error and stays on the step when Continue fails to save', async () => {
  const user = userEvent.setup();
  vi.spyOn(api.intake, 'updateSession').mockRejectedValue(new Error('network'));

  renderWizard();
  await fillDebtorStepValid();

  await user.click(screen.getByRole('button', { name: /continue/i }));

  expect(await screen.findByText(/couldn’t save just now/i)).toBeInTheDocument();
  // Still on step 1 — the income step heading has not appeared.
  expect(screen.queryByRole('heading', { name: /income/i })).not.toBeInTheDocument();
});
```

- [ ] **Step 3: Run tests to verify they fail (before wiring is correct) / pass (after Tasks 1–3)**

Run: `cd frontend && npx vitest run src/pages/__tests__/IntakeWizard.test.tsx`
Expected after Tasks 1–3: PASS. If `fillDebtorStepValid`/`renderWizard` helpers don't exist in the file, create them from the existing setup code in that test file (do not invent new fixtures — reuse the session mock already there).

- [ ] **Step 4: Run the full frontend suite**

Run: `cd frontend && npx vitest run`
Expected: all green. (Note: the pre-existing flake "navigates to /fee-waiver when qualifies_for_fee_waiver is true" can fail under parallel CPU; re-run it in isolation to confirm: `npx vitest run -t "navigates to /fee-waiver"`.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/__tests__/IntakeWizard.test.tsx
git commit -m "test(intake): autosave fires on debounce; failed save blocks advance

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Manual verification + lint/format gate

- [ ] **Step 1: Lint and format**

Run: `cd frontend && npm run lint && npm run format`
Expected: no errors. (Pre-commit also runs eslint with `--max-warnings 0`; the new effect deps should be complete — `useAutoSave`'s deps are already correct, and the new IntakeWizard code adds no effects.)

- [ ] **Step 2: Manual smoke (docker compose up)**

Run: `docker compose up` then in the browser:

1. Start intake, fill step 1 validly, wait ~2s without clicking Continue → footer shows "Saving…" then "Saved."
2. Reload the page → step 1 data is still there (loaded from backend).
3. Stop the backend, edit a field, click Continue → footer shows the "couldn't save" message and the wizard stays on the step.

Expected: all three behaviors as described. (Restart the frontend container if Vite HMR shows stale types — known gotcha.)

- [ ] **Step 3: Update CLAUDE.md gotchas/status if behavior is non-obvious**

If anything surprised you (e.g., a step that reports `canProceed` differently than expected), add a one-line note to the project `CLAUDE.md` "Gotchas". Otherwise skip.

---

## Self-Review Checklist (run before handing off)

1. **Spec coverage:** false "automatically saved" copy replaced (Task 2) ✓; real autosave wired (Task 3) ✓; silent-failure fixed (Task 3 + indicator) ✓; tests (Tasks 1, 4) ✓.
2. **Placeholder scan:** the only soft spots are the test helpers `renderWizard`/`fillDebtorStepValid` — Task 4 Step 3 instructs reusing the existing file's setup rather than inventing fixtures. Confirm those helpers exist or lift them from the current test body.
3. **Type consistency:** `SaveStatus` exported from `useAutoSave` and imported by `WizardLayout`; `saveNow: () => Promise<boolean>` used consistently in `handleNext`/`handleComplete`.
4. **No backend change required** — confirmed via `IntakeSessionSerializer.update()` (`update_or_create`, pops only present keys) + `enabled: canProceed` gating.
