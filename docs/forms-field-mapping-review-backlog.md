# Forms field-mapping — review backlog

Candidate items to fold into the field-mapping reconciliation work. Sourced from
review-bot feedback on **PR #4** ("PDF download infrastructure — fill and stream AO
court forms"), the PR that introduced `pdf_field_map()` and `PDFFormFiller`.
Status column reflects a check of current `main` on 2026-06-16 (PR #4 merged earlier,
so some items were already resolved).

> Note: PR #7 (autosave) carried a `claude[bot]` review too, but it is entirely
> autosave-scoped — no forms/field-mapping content. Not included here. (One item in it
> — a named-vs-default import in `IntakeWizard.test.tsx` — is worth a separate check but
> is unrelated to forms.)

## Work in during mapping — verified OPEN

### 1. Sanitize `field_map` before pypdf · quick win · `pdf_filler.py:62`

`fill()` passes `field_map` straight into
`writer.update_page_form_field_values(page, field_map, auto_regenerate=False)`.
The signature promises `dict[str, str]`, but nothing coerces values — a `None` or a
`Decimal`/`int` leaking from a generator's `pdf_field_map()` can make pypdf write the
literal `"None"` into a court form or raise. While reconciling each generator's map,
add a coercion/filter pass: drop `None`, `str()` everything else.

### 2. Catch `KeyError` / `FileNotFoundError` in `download` · quick win · `views.py:316–326`

`fill()` documents raising `KeyError` (unknown `form_type`) and `FileNotFoundError`
(missing template), but the `download` action only catches `NotImplementedError` (→ 501).
The other two propagate as unhandled 500s. These are exactly the failure modes you hit
while reconciling mappings (a `form_type` with no `FORM_TEMPLATES` entry, a renamed
template). Add explicit handling → 500 with a `detail`, or 422.

### 3. Persist template filename + version on `GeneratedForm` · heavy lift · `models.py` + migration

`GeneratedForm` stores only `form_type`; the template is resolved at download time via
`FORM_TEMPLATES[form_type]`. When the AO updates a form (CLAUDE.md risk #2, "Form Version
Drift"), historical downloads silently shift to the new revision — legal artifacts stop
being reproducible. Mapping reconciliation is the natural moment to bind a template
filename + version to each generated form. Flagged independently by both bots
(`pdf_filler.py:33` and `:63`).

## Already resolved (no action)

- **Media files committed to repo** (PR #4 `claude[bot]` #1) — `/backend/media/` is now
  in `.gitignore` (line 80). Done.

## Adjacent / not mapping-core (separate backlog if wanted)

These were raised on PR #4 but live outside the forms layer — listed so nothing is lost:

- `downloadForm` uses raw `fetch`, bypassing the silent token-refresh in `apiFetch`
  (`api/client.ts`) — flagged by both bots. Frontend.
- `ILND_DISTRICT_ID = 1` hardcoded PK in `DocumentUploadPage.tsx` — look up district by `code`.
- Missing test for the download ownership check (second user → 403/404).
- Two `react-hooks/exhaustive-deps` suppressions (`DebtorInfoStep.tsx`, `DocumentUploadPage.tsx`).
- `DemoLoginView` writes `current_session_id` to `localStorage`, bypassing `IntakeContext`.
