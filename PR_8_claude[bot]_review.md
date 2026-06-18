## Code Review — Schema-driven form-fill engine (SP1 + SP2)

This is a well-designed PR. The `FieldSpec`/`FormSchema` dataclasses are clean, the `FillResolver` dispatch model is solid, and the hybrid `SOFAReport` + `FormAnswer` storage is the right architectural call. Test coverage for the engine's form-agnostic contract is strong. The findings below are mostly bugs and gaps to close before the forms are sworn documents in users' hands.

---

### 🔴 Critical — Broken E2E flows after route change

**Files:** `frontend/e2e/journeys/james-borderline.spec.ts`, `priya-ineligible.spec.ts`

The wizard now navigates non-fee-waiver users to `/sofa` instead of `/forms`. The `james` and `priya` journey specs call `completeIntake()` and then immediately invoke `dashboard.generateAllForms(12)` — but they're now on the SOFA page, not the dashboard. Both specs will time out waiting for a generate-all button that doesn't exist on `/sofa`. Each affected spec needs a `await sofa.skipForNow()` + `waitForURL(/\/forms/)` before any dashboard assertions.

---

### 🔴 Bug — Insecure `get_object()` on `SOFAReportViewSet`

**File:** `backend/apps/intake/views.py`, `get_object()` override

```python
def get_object(self):
    session = IntakeSession.objects.get(pk=self.kwargs["pk"])  # ← no user filter
    report, _ = SOFAReport.objects.get_or_create(session=session)
    return report
```

No ownership check. If any future action routes through DRF's standard mechanism, this exposes cross-user data access. The method is currently dead (both `retrieve` and `partial_update` bypass it), so either remove it or add `user=self.request.user` to the lookup:

```python
session = get_object_or_404(IntakeSession, pk=self.kwargs["pk"], user=self.request.user)
```

---

### 🔴 Bug — UPL guard is not applied to repeat-group fields

**File:** `backend/apps/forms/services/fill_resolver.py`, repeat group resolution loop (~line 583–602)

The scalar-field path checks `legal_review` and skips fields marked for legal review, which is correct. The repeat-group resolution path has no equivalent check — a `legal_review=True` field inside a repeat group is silently filled. Add `if f.legal_review: continue` before emitting in the repeat loop.

---

### 🔴 Bug — `_form_answer_predicate` hardcodes `form_type="form_107"` but is called by Form 101

**File:** `backend/apps/forms/services/derivations.py`

Predicates like `has_joint_filer`, `has_prior_bankruptcy`, and `has_attorney` are used as `conditional_on` in `form_101.json`, but always query `FormAnswer(form_type="form_107")`. No code path in the Form 101 context collects those `FormAnswer` rows under `form_107`. As a result, all Form 101 conditional sections gated on these predicates will always evaluate to `False` — those pages won't be filled even for joint filers. This needs either shared predicate lookup keys or a form-type-agnostic query (e.g., by session + field_key across types).

---

### 🟡 Bug — `_scalar_value` raises `KeyError` with no useful message for unknown derivations

**File:** `backend/apps/forms/services/fill_resolver.py`

```python
return DERIVATIONS[field.rule](session)  # KeyError if rule not in registry
```

`validate_schema()` catches this in tests, but `load_schema()` can be called without validation at runtime (e.g., in a future code path that skips the CLI validate step). A schema authoring typo would crash the user's PDF download with a raw `KeyError`. Harden it:

```python
fn = DERIVATIONS.get(field.rule)
if fn is None:
    raise ValueError(f"Unknown derivation rule {field.rule!r} on field {field.pdf_field!r}")
return fn(session)
```

---

### 🟡 Bug — `seed_demo_data` mutates persona data dict via `.pop()`

**File:** `backend/apps/intake/management/commands/seed_demo_data.py`

```python
sofa_data = data.get("sofa", {})     # reference to the nested dict
prior_income_rows = sofa_data.pop("prior_income", [])  # mutates original
```

Not a runtime bug today since each persona function is called once per run, but would silently produce empty SOFA data on a second call with the same data dict. Use `sofa_data = dict(data.get("sofa", {}))` to copy before popping.

---

### 🟡 Bug — Schema authoring error: `source: "constant"` with `value: null`

**File:** `data/forms/schemas/form_101.json` (`"Debtor2.Middle name_2"`)

`source: "constant"` with `value: null` silently skips the field (no crash, but no fill either). The source should be `"asked"` or `"skip"` depending on intent.

---

### 🟡 Bug — `SOFAReport.has_prior_income` defaults to `True`

A freshly `get_or_create`'d `SOFAReport` (the view's side effect on every GET) has `has_prior_income=True`. New users will see the prior income section pre-checked before they've entered any data — misleading at best, potentially resulting in an incorrectly populated court form.

---

### 🟡 Performance — `load_schema()` reads disk on every call, no caching

**File:** `backend/apps/forms/schema.py`

`form_107.json` is ~300KB / 8,719 lines. It's parsed from disk on every `pdf_field_map()` call. Since schemas are immutable at runtime (baked into the image), a simple `@lru_cache(maxsize=32)` on `load_schema` eliminates the I/O entirely. Tests can call `load_schema.cache_clear()` in teardown.

---

### 🟡 Performance — N+1 queries in repeat group resolution

**File:** `backend/apps/forms/services/fill_resolver.py`

`getattr(report, coll_name).all()` runs a fresh DB query for every distinct collection binding. For Form 107 with prior income + creditor payments this is at minimum 2 extra queries per download, and it grows with schema complexity. Prefetch both collections on the `SOFAReport` queryset at the view level before passing to the resolver.

---

### 🟡 Performance — Predicate DB hit on every `conditional_on` check

**File:** `backend/apps/forms/services/derivations.py`

Each `_form_answer_predicate` call issues a `FormAnswer.objects.filter(...).first()`. With ~8,000 fields in `form_107.json` sharing 14 predicates, this adds up to 14+ round-trips per `resolve()`. Fetch all `FormAnswer` rows for the session at the start of `resolve()` into a dict and do in-memory lookups.

---

### 🟡 Test Coverage Gaps

1. **No test for UPL guard bypass in repeat groups** (the `legal_review=True` gap noted above).
2. **No `test_form_101_schema_is_valid`** — `form_101.json` is not validated in the test suite (only `form_107` is).
3. **`SOFAReportViewSet` PATCH with wrong user** — `test_404_for_wrong_user` covers GET only; a cross-user PATCH should also return 404.
4. **`_scalar_value` with `source="asked"` and `binding=None`** — crashes with `AttributeError`; no test covers this authoring-error path.
5. **`ingest_form_schema` drift detection** — when drift is detected the command overwrites the curated JSON with a raw TBD draft, destroying all hand-curated annotations. There is no test or guard that preserves existing curated fields. This is a data-loss risk on AO template updates.

---

### 🟢 Nits

- **`FieldSpec` is `frozen=True` but `on_states: list[str]`** — mutable container in a frozen dataclass. Use `tuple[str, ...]` for genuine immutability.
- **`SOFAStep.tsx` uses `key={idx}` for list items** — unstable key causes wrong rows to re-render when items are removed from the middle. Use a stable `id` (or a temporary uuid for unsaved rows).
- **`SOFAStep.tsx` mutates the API response before calling `setReport`** (`data.prior_income.push(...)`). Use `setReport({...data, prior_income: [...data.prior_income, emptyPriorIncome()]})` instead.
- **`SOFAStep.tsx` year field `max="2026"` is hardcoded** — will silently reject valid data in 2027. Use `String(new Date().getFullYear())`.
- **Derived fields in `form_107.json` carry a non-null `binding`** — `_scalar_value` ignores `binding` for `derived` sources, so this is dead metadata that's confusing to future schema authors. Null it out.
- **`ingest_form_schema` uses `obj.get("/_States_")`** — internal pypdf attribute, not the public API. Use `annotation.get("/AP", {}).get("/N", {}).keys()` for forward-compatibility.

---

### Summary

The architecture is solid and the engine is worth landing. The two must-fix items before merge are the E2E regression (broken journey specs) and the UPL guard gap in repeat groups — both are correctness issues on sworn documents. The cross-user `get_object()` and the predicate `form_type` hardcoding are high-priority follow-ups. The performance items (schema caching, N+1 queries) should be addressed before the first load test.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
