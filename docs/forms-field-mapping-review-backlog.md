# Forms field-mapping — review backlog

Candidate items to fold into the field-mapping reconciliation work. Sourced from
review-bot feedback on **PR #4** ("PDF download infrastructure — fill and stream AO
court forms"), the PR that introduced `pdf_field_map()` and `PDFFormFiller`.
Status reflects a check of `main` (07ad5a6) on 2026-10-15.

> Note: PR #7 (autosave) carried a `claude[bot]` review too, but it is entirely
> autosave-scoped — no forms/field-mapping content. Not included here. (One item in it
> — a named-vs-default import in `IntakeWizard.test.tsx` — is worth a separate check but
> is unrelated to forms.)

## Work in during mapping — verified OPEN

### 3. Persist template filename + version on `GeneratedForm` · heavy lift · `models.py` + migration

`GeneratedForm` stores `form_type` and `template_version`; the template itself is resolved
at download time from the registered form's schema (`template_filename`), whose field
index names its widgets. When the AO updates a form (risk #2, "Form Version Drift", in
`docs/internal/dignifi_technical_architecture.md`), a filed form's stored values print on
the new revision, or fail to download if a field was renamed; `template_version` records
the template's hash, but download never checks it — legal artifacts stop
being reproducible. Mapping reconciliation is the natural moment to bind a template
filename + version to each generated form. Flagged independently by both bots
(`pdf_filler.py:33` and `:63`).

## Already resolved (no action)

- **Media files committed to repo** (PR #4 `claude[bot]` #1) — `/backend/media/` is now
  in `.gitignore` (line 79). Done.
- **Sanitize values before pypdf** — `fill_resolver._emit` drops `None` and blanks and
  passes every other value through `str()`; `PDFFormFiller.fill` writes each widget itself. Done.
- **Download failures** — `download` catches every exception: a known one (an unfinished
  intake, income not entered by source, missing data, a form outside the packet, too many
  entries, an unmapped answer, a template with no form) is a 422 in plain words; any other is
  a 500 logged by type only. Done.
- `downloadForm` refreshes the token on a 401 and retries once (`api/client.ts`). Done.

## Adjacent / not mapping-core (separate backlog if wanted)

These were raised on PR #4 but live outside the forms layer — listed so nothing is lost:

- `ILND_DISTRICT_ID = 1` hardcoded PK in `DocumentUploadPage.tsx` — look up district by `code`.
- Missing test for the download ownership check (second user → 403/404).
- Six `react-hooks/exhaustive-deps` suppressions (`DebtorInfoStep.tsx`, `DebtsStep.tsx`, `ExpenseInfoStep.tsx`, `IncomeInfoStep.tsx`, `DocumentUploadPage.tsx`, `IntakeWizard.tsx`).
- The demo login in `LandingPage.tsx` writes `current_session_id` to `localStorage`, bypassing `IntakeContext`.
