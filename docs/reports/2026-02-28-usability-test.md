# Usability Test Report — AI Persona Simulation

**Test Period:** 2026-02-28 through 2026-03-02
**Method:** AI persona simulation using Playwright browser automation against the live DigniFi application (Docker Compose, ILND district)
**Status:** COMPLETE — all blocking issues resolved, full flow validated

## Summary Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Completion rate | 5/5 | 5/5 | PASS |
| Form generation | 13/13 per persona | 13/13 | PASS |
| Survey submission | 5/5 | 5/5 | PASS |
| Console errors | 0 | 0 | PASS |
| Total forms generated | 65 | 65 | PASS |

## Bugs Found & Fixed (13 Total)

### Critical (Blocked full flow)

| # | Bug | Root Cause | Fix | Commit |
|---|-----|-----------|-----|--------|
| 1 | Auth throttle 500 on registration | `ScopedRateThrottle` rate only in `production.py` | Added `auth: 30/minute` to `base.py` | `15c6f15` |
| 2 | FeeWaiverApplication missing in seed | Seed command didn't create fee waiver records | Create for eligible personas | `eb0c402` |
| 3 | Step data 404 — non-existent endpoints | Frontend called `/debtor-info/`, `/income-info/` (don't exist) | Route through `updateSession()` PATCH | `7bd0bf7` |
| 8 | `forms.map is not a function` | DRF pagination wraps results in `{count, results}` | `Array.isArray` guard in `listBySession` | `874d601` |
| 9 | `navigate()` during render crashes React 19 | Login/Register called `navigate()` in render body | Move to `useEffect` | `874d601` |
| 11 | `GenerateAllFormsResponse` type mismatch | API returns `{generated}` but type expected `{forms}` | Update type + handler | `b0956bb` |

### High (Broke specific persona flows)

| # | Bug | Root Cause | Fix | Commit |
|---|-----|-----------|-----|--------|
| 4 | Empty assets/debts sent as null → 400 | Default empty form objects failed backend validation | Filter blank entries before PATCH | `c5c2f5b` |
| 5 | Assets validation blocked empty skip | `hasValidAsset` required but UI said "leave blank" | Allow `allBlank` as valid | `c5c2f5b` |
| 6 | `real_estate` ≠ `real_property` | Frontend/backend asset type enum mismatch | Fix frontend to `real_property` | `c5c2f5b` |
| 7 | Debt type `secured/unsecured` ≠ backend | Frontend radio uses generic; backend expects specific types | Map to `other` + `is_secured` flag | `9ef43fb` |

### Low (Cosmetic / non-blocking)

| # | Bug | Root Cause | Fix | Commit |
|---|-----|-----------|-----|--------|
| 10 | Unhandled `loadSession` rejection | IntakeProvider mount `useEffect` lacked `.catch()` | Add `.catch()` | `874d601` |
| 12 | Analytics 401s in console | `trackEvent()` used raw `fetch()` without JWT | Use `getAccessToken()` for Bearer header | `b0956bb` |
| 13 | FormDashboard loading state stuck | Local `isLoading` never reset when session was null | Use IntakeProvider's `isLoading` | `b0956bb` |

## Per-Persona Final Results

| Persona | Auth | Wizard (6 steps) | Forms Dashboard | Generate All (13) | UPL Modal | Survey |
|---------|------|-------------------|-----------------|--------------------|-----------|---------|
| Maria Torres | PASS | PASS | PASS | PASS | PASS | PASS |
| James Washington | PASS | PASS | PASS | PASS | PASS | PASS |
| Priya Sharma | PASS | PASS | PASS | PASS | PASS | PASS |
| DeShawn Mitchell | PASS | PASS | PASS | PASS | PASS | PASS |
| Sarah Chen | PASS | PASS | PASS | PASS | PASS | PASS |

## UX Friction Points Observed

### High Severity

1. **SSN requested on first step without trust signal**
   - Persona: Maria Torres (low trust, scam-wary)
   - SSN field appears on Step 1 with no visible encryption badge
   - Recommendation: Add lock icon + "encrypted and never shared" text near SSN

### Medium Severity

2. **"Means test" jargon in sidebar**
   - `MeansTestPreview` component uses "means test" terminology
   - Recommendation: Use "income check" or add inline plain-language definition

3. **Debt type mapping is lossy**
   - Frontend only offers `secured/unsecured` radio; backend has specific types
   - All debts map to `other` — works but loses classification fidelity
   - Recommendation: Add specific debt type options (medical, credit card, student loan)

### Observations (Positive)

4. **Trauma-informed language confirmed:**
   - Step 5 title uses "Amounts Owed" (not "Debts")
   - Error messages use "We encountered an issue" (not blame language)
   - Progress indicators emphasize accomplishment

5. **UPL compliance validated:**
   - UPL confirmation modal gates all form generation
   - Checkbox acknowledgment required before Continue
   - Landing page and registration include disclaimers

## Infrastructure Verified

- [x] `seed_demo_data` command creates 5 personas with completed sessions
- [x] Playwright discovers all journey specs
- [x] Registration flow works (after throttle fix)
- [x] All 6 wizard steps complete for all personas
- [x] Forms dashboard loads correctly with session from localStorage
- [x] Generate All creates 13 forms per persona (65 total)
- [x] UPL modal checkbox + Continue flow works
- [x] PostTaskSurvey renders after generation
- [x] Survey Likert scales + text inputs submit correctly
- [x] "Thank you" confirmation appears after submission
- [x] Analytics `trackEvent` sends authenticated requests
- [x] CI pipeline has e2e-test job
- [x] Zero console errors in final run

## Test Scripts

- `test_persona_full_flow.py` — Runs all 5 personas through auth → forms → generate → survey
- `test_maria_quick.py` — Quick smoke test with Maria only
- Both use API-based auth setup (bypasses UI login race condition)

## Recommendations (Priority Order)

1. **Add SSN trust signal** — Lock icon + "encrypted" text next to SSN field
2. **Replace "means test" with plain language** — Use "income check" or tooltip
3. **Expand debt type options** — Add specific types to match backend model
4. **Paper prototype testing** — Validate with real users at legal clinic partner
5. **Monitor form generation performance** — 13 forms take ~10-15s; consider async generation with progress indicator
