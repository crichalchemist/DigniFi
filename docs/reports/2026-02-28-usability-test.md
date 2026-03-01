# Usability Test Report — 2026-02-28

## Test Method

AI persona simulation using Playwright browser automation against the live
DigniFi application (Docker Compose, ILND district). Tested registration
flow, wizard step discovery, and form validation behavior.

## Summary Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Completion rate | 5/5 | 0/5 | BLOCKED |
| Registration flow | Works | Works after throttle fix | PASS |
| Step 1 validation | All fields fillable | All fields fillable | PASS |
| Step advancement | Continue advances | 404 on debtor API save | BLOCKED |

**Overall status: PAUSE** — two blocking issues prevent full flow testing.

## Blocking Issues Found

### 1. Throttle rate missing for `auth` scope (FIXED)

**Severity:** Critical (500 error on registration)
**Root cause:** `ScopedRateThrottle` scope `'auth'` was only configured in
`production.py`, not `base.py`. Docker dev env uses base settings.
**Fix:** Added `"auth": "30/minute"` to `base.py` `DEFAULT_THROTTLE_RATES`.
**Commit:** `15c6f15`

### 2. Debtor API returns 404 for new sessions of existing users

**Severity:** Critical (blocks step advancement)
**Root cause:** When `demo_maria` logs in, the wizard creates a new
`IntakeSession`, but `saveCurrentStepData()` calls `api.debtor.createOrUpdate(session.id, data)`
which hits a 404. The session ID may not be properly passed to the API,
or the backend endpoint requires the session to already exist in a specific state.
**Status:** Not yet fixed — requires investigation of `IntakeWizard.tsx`
session creation flow and backend debtor API endpoint behavior.

## Friction Points Discovered

### High Severity

1. **SSN requested on first step without trust signal**
   - Persona: Maria Torres (low trust, scam-wary)
   - The SSN field appears on Step 1 with no visible encryption badge
   - Maria's reaction: "Is this site legit? Why do they need my SSN?"
   - Recommendation: Add lock icon + "encrypted and never shared" text near SSN

### Medium Severity

2. **"Means test" jargon in sidebar**
   - Not yet confirmed via live test (blocked at Step 1)
   - Based on code review: `MeansTestPreview` component uses "means test"
   - Recommendation: Use "income check" or add inline plain-language definition

3. **Filing type select unclear for persona**
   - Options are "Individual (filing alone)" and "Joint (filing with spouse)"
   - Maria would understand this, but the field label could be clearer
   - Recommendation: Add help text explaining the choice

### Observations (Not Friction)

4. **Trauma-informed language confirmed:**
   - Step 5 title uses "Amounts Owed" (not "Debts") ✓
   - Landing page messaging is warm and dignity-preserving ✓
   - Error messages use "We encountered an issue" (not blame language) ✓

5. **UPL disclaimer visible:**
   - Landing page footer has clear disclaimer ✓
   - Registration requires UPL acknowledgment checkbox ✓

## Per-Persona Status

| Persona | Registration | Step 1 | Step 2+ | Forms | Survey |
|---------|-------------|--------|---------|-------|--------|
| Maria Torres | ✓ | ✓ (fills OK) | BLOCKED (404) | — | — |
| James Washington | ✓ | Not tested | — | — | — |
| Priya Sharma | ✓ | Not tested | — | — | — |
| DeShawn Mitchell | ✓ | Not tested | — | — | — |
| Sarah Chen | ✓ | Not tested | — | — | — |

## Stop Rule Evaluation

| Condition | Result |
|-----------|--------|
| 2+ personas cannot complete | **YES — PAUSE** |
| Mean dignity score < 3.0 | N/A (survey not reachable) |
| Action | **Fix blocking API issue, then rerun** |

## Recommendations (Priority Order)

1. **Fix debtor API 404** — Investigate why `createOrUpdate` fails on new
   sessions for existing users. Likely needs session creation to complete
   before debtor data can be saved.
2. **Add SSN trust signal** — Lock icon + "encrypted" text next to SSN field
3. **Replace "means test" with plain language** — Use "income check" or add tooltip
4. **Rerun persona tests** after fixes

## Infrastructure Verified

- [x] `seed_demo_data` command creates 5 personas successfully
- [x] Playwright discovers all 5 journey specs
- [x] Registration flow works (after throttle fix)
- [x] Step 1 form validation works correctly
- [x] Analytics `trackEvent` function created
- [x] PostTaskSurvey component created
- [x] CI pipeline has e2e-test job

## Next Steps

1. Debug and fix the debtor API 404 issue
2. Rerun all 5 persona tests end-to-end
3. Aggregate full survey responses
4. Write final usability report with PRD metrics
