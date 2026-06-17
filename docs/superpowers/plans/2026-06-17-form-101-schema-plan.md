# SP2: Form 101 Schema Curation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Form 101's hand-authored `pdf_field_map()` with the schema-driven resolver, curating a committed `form_101.json` schema.

**Architecture:** A curated JSON schema declares every fillable field's source, binding, and gate predicate. The resolver reads it and returns `{pdf_field: str}` — same engine as SP1's Form 107, just a new schema.

**Tech Stack:** Python 3.11, Django 5.0, DRF, pypdf 6.13, pytest.

## Global Constraints

- **pypdf 6.13** — pinned; 3.17 raises `KeyError /AP`.
- **Encryption** — financial amounts use `EncryptedDecimalField`; never store amounts in plaintext.
- **UPL** — legal information, never advice. No legal conclusions in derivations/predicates.
- **Schemas are committed + version-pinned.** A schema whose `template_version` hash no longer matches its template must fail tests, not silently fill.
- **Checkbox on-state fallback** — use `or ["/Yes"]` for checkbox AcroForm detection.
- **TDD** — failing test → implementation → passing test → commit.
- **Lint** — `ruff==0.8.5` (CI/container pin); `ruff check . --fix` before commit.
- **Commands** run inside `docker compose exec -T backend`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `data/forms/schemas/form_101.json` | **Create** | Curated schema: 110 fields across 8 pages |
| `backend/apps/forms/services/derivations.py` | Modify | Add `has_attorney` to PREDICATES |
| `backend/apps/forms/services/form_101_generator.py` | Modify | `pdf_field_map()` delegates to resolver; remove hand-authored dict |
| `backend/apps/forms/tests/test_pdf_field_maps.py` | Modify | Update Form 101 field-map test to assert against resolver |
| `backend/apps/forms/tests/test_derivations.py` | Modify | Add test for `has_attorney` predicate |
| `backend/apps/forms/tests/test_coverage.py` | Modify | Add Form 101 coverage proof |
| `Dockerfile.heroku` | Modify | `COPY ./data/forms/schemas /data/forms/schemas` |

---

### Task 1: Add `has_attorney` predicate + test

**Files:**
- Modify: `backend/apps/forms/services/derivations.py`
- Test: `backend/apps/forms/tests/test_derivations.py`

**Interfaces:**
- Consumes: `_form_answer_predicate(session, "attorney_gate")` pattern (same as existing predicates)
- Produces: `PREDICATES["has_attorney"]` — returns `True` when `FormAnswer(session, form_type="form_107", field_key="attorney_gate")` has a truthy value

- [ ] **Step 1: Write the failing test**

Append to `backend/apps/forms/tests/test_derivations.py`:

```python
@pytest.mark.django_db
def test_has_attorney_predicate():
    from apps.forms.services.derivations import PREDICATES
    from apps.intake.models import FormAnswer

    d = District.objects.create(
        code="ilnd", name="Test", court_name="x", state="IL", filing_fee_chapter_7="1.00"
    )
    user = User.objects.create_user(username="pred_attorney", password="x")
    session = IntakeSession.objects.create(district=d, user=user, status="in_progress", current_step=1)

    # No FormAnswer yet → defaults to False
    assert PREDICATES["has_attorney"](session) is False

    # With a "yes" answer → True
    FormAnswer.objects.create(session=session, form_type="form_107", field_key="attorney_gate", value="yes")
    assert PREDICATES["has_attorney"](session) is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec -T backend python -m pytest apps/forms/tests/test_derivations.py::test_has_attorney_predicate -v
```
Expected: `KeyError: 'has_attorney'`

- [ ] **Step 3: Add `has_attorney` to PREDICATES**

In `backend/apps/forms/services/derivations.py`, add to the PREDICATES dict:

```python
    "has_attorney": lambda s: _form_answer_predicate(s, "attorney_gate"),
```

Add it after `has_address_history` or at the end of the PREDICATES dict.

- [ ] **Step 4: Run test to verify it passes**

```bash
docker compose exec -T backend python -m pytest apps/forms/tests/test_derivations.py::test_has_attorney_predicate -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/forms/services/derivations.py backend/apps/forms/tests/test_derivations.py
git commit -m "feat(forms): add has_attorney predicate for Form 101 page 8 gating"
```

---

### Task 2: Curate `form_101.json` (110 fields, 8 pages)

**Files:**
- Create: `data/forms/schemas/form_101.json`
- Tool: `ingest_form_schema` to generate the draft, then hand-curate

**Interfaces:**
- Consumes: `ingest_form_schema form_101` → draft JSON with 110 fields, all `source: "TBD"`
- Produces: Curated `form_101.json` — each field has `source`, `binding` (if `asked`), `conditional_on` (if gated), `repeat`/`repeat_capacity`/`row` (if repeat group), `on_states`, `legal_review`

**Approach:** Generate the draft via the `ingest_form_schema` management command, then copy the output and curate each field by editing source/rule/binding/conditional_on. Field structure follows the same template as `form_107.json`.

- [ ] **Step 1: Generate the draft**

```bash
docker compose exec -T backend python manage.py ingest_form_schema form_101
```

This creates `data/forms/schemas/form_101.json` with 110 fields, all `source: "TBD"`, `type`, `page`, `pdf_field` populated from the AO template.

- [ ] **Step 2: Curate every field — section-by-section**

Edit `data/forms/schemas/form_101.json`. Curation rules (same as SP1):

| Source | Set when | Fields |
|--------|----------|--------|
| `constant` | Fixed value known at schema-write time | Checkbox on-state (`"/Yes"`), "7" for chapter |
| `derived` | Computed from session data by DERIVATIONS rule | `full_name`, `district_name` |
| `asked` | Answered by user (FormAnswer or SOFA models) | Most fields |
| `signature` | Must be signed by user in-person | Signature fields |
| `TBD` | Should not remain — only if genuinely undecided | Remove before shipping |

**Page-by-page curation (all in one edit):**

**Page 1 — Debtor names + SSN (27 fields):**

Field naming note: The template uses bare names with `_N` suffixes for repeats on different pages/areas. `Debtor1.` prefix from the old hand-authored map does NOT exist in the template.

- `Bankruptcy District Information` → `source: "derived", rule: "district_name"` — always fills
- `Check Box2` — individual debtor checkbox → `source: "constant", value: "/Yes"`
- `SSNum` → `source: "asked", binding: "answer:form_101.debtor_ssn"` — last 4 digits
- `Debtor1 Tax Payer IDNum` → `source: "asked", binding: "answer:form_101.debtor_tax_id"`
- `Debtor2 SSNum` → `source: "asked", binding: "answer:form_101.debtor2_ssn"`, `conditional_on: "has_joint_filer"`
- `Tax Payer IDNum` → duplicate of above (same Tax ID), `source: "constant", value: "/Yes"` or derive from same answer
- `First name` → `source: "asked", binding: "answer:form_101.first_name"`
- `Middle name` → `source: "asked", binding: "answer:form_101.middle_name"`
- `Last name` → `source: "asked", binding: "answer:form_101.last_name"`
- `Suffix Sr Jr II III` → `source: "asked", binding: "answer:form_101.name_suffix"`
- `Middle name_2` → appears elsewhere on page 1, same answer: `source: "asked", binding: "answer:form_101.middle_name"`
- `Suffix Sr Jr II III_2` → same: `source: "asked", binding: "answer:form_101.name_suffix"`
- `First name_3` → page-1 section header repeat: `source: "derived", rule: "full_name"`
- `Middle name_3` → same: `source: "derived", rule: "full_name"`
- `Last name_3` → same: `source: "derived", rule: "full_name"`
- `First name_5` → another repeat area, same: `source: "derived", rule: "full_name"`
- `Middle name_5` → same as full name
- `Last name_5` → same as full name
- `First name_4` → Debtor 2 first name: `source: "asked", binding: "answer:form_101.debtor2_first_name"`, `conditional_on: "has_joint_filer"`
- `Middle name_4` → Debtor 2 middle name: gated same
- `Last name_4` → Debtor 2 last name: gated same
- `First name_6` → Debtor 2 full name area: `source: "derived", rule: "full_name"` — but needs to be debtor 2's name
- `Middle name_6` → same
- `Last name_6` → same
- `Business name` → `source: "asked", binding: "answer:form_101.business_name"`, `conditional_on: "has_business"`
- `Business name_3` → same repeat
- `Business name_4` → same repeat

**Important note on `full_name` derivation for Debtor 2:** The existing `full_name` derivation concatenates `debtor_info.first_name + last_name` (Debtor 1). For Debtor 2, the schema should use `answer:form_101.debtor2_first_name` etc. directly rather than deriving — the `full_name` derivation only knows about Debtor 1. So `First name_6`, `Middle name_6`, `Last name_6` use asked bindings to Debtor 2's name fields, not the derivation.

**Page 2 — Addresses + venue (26 fields):**

- `Employer Identification Number1` → `source: "asked", binding: "answer:form_101.employer_ein"`
- `Employer Identification Number2` → same answer
- `Debtor2 Employer Identification Number2` → `source: "asked", binding: "answer:form_101.debtor2_employer_ein"`, `conditional_on: "has_joint_filer"`
- `Street` → `source: "asked", binding: "answer:form_101.street_address"`
- `Street1` → same (appears elsewhere)
- `City` → `source: "asked", binding: "answer:form_101.city"`
- `State` → `source: "asked", binding: "answer:form_101.state"`
- `ZIP Code` → `source: "asked", binding: "answer:form_101.zip_code"`
- `Street2` → mailing address: `source: "asked", binding: "answer:form_101.mailing_street"`
- `ZIP` → mailing zip: `source: "asked", binding: "answer:form_101.mailing_zip"`
- `County` → `source: "asked", binding: "answer:form_101.county"`
- `County_2` → same (appears elsewhere)
- `Street_2` → mailing address repeat: same binding as `Street2`
- `PO Box` → `source: "asked", binding: "answer:form_101.po_box"`
- `City_2` → mailing city: `source: "asked", binding: "answer:form_101.mailing_city"`
- `State_2` → mailing state: `source: "asked", binding: "answer:form_101.mailing_state"`
- `ZIP Code_4` → mailing zip: same binding as `ZIP`
- `See 28 USC 1408 1` through `See 28 USC 1408 4` (4 fields) → venue district info: `source: "asked", binding: "answer:form_101.venue_{1..4}_district"` or single binding each
- `See 28 USC 1408 1_2` through `See 28 USC 1408 4_2` (4 fields) → venue basis explanation: `source: "asked", binding: "answer:form_101.venue_{1..4}_basis"`
- `ZIP Code_2` → another zip repeat: same binding as `zip_code`

**Page 3 — Prior bankruptcy history (19 fields):**

All gated behind `conditional_on: "has_prior_bankruptcy"`. Four prior-case sets:

- `District` → `source: "asked", binding: "answer:form_101.prior_bankruptcy_1_district"`
- `When` → `source: "asked", binding: "answer:form_101.prior_bankruptcy_1_when"`
- `Case number` → `source: "asked", binding: "answer:form_101.prior_bankruptcy_1_case_number"`
- `District_2` → set 2: `binding: "answer:form_101.prior_bankruptcy_2_district"`
- `When_2` → set 2
- `Case number_2` → set 2
- `District_3` → set 3
- `When_3` → set 3
- `Case number_3` → set 3
- `District_4` → set 4
- `When_4` → set 4
- `Case number if known_3` → set 4
- `Debtor` → name as debtor in prior case: `source: "derived", rule: "full_name"`, `conditional_on: "has_prior_bankruptcy"`
- `Relationship to you` → for joint filer only: `source: "asked", binding: "answer:form_101.prior_bankruptcy_1_relationship"`, `conditional_on: "has_prior_bankruptcy"`
- `Debtor_2` → set 2 name
- `Relationship to you_2` → set 2
- `District_5` → pending case district
- `When_5` → pending case
- `Case number if known_4` → pending case

**Page 4 — Business (6 fields):**

All gated behind `conditional_on: "has_business"`:
- `Name of business if any` → `source: "asked", binding: "answer:form_101.business_name"` (same as page 1)
- `Business Street address` → `source: "asked", binding: "answer:form_101.business_street"`
- `Business Street address2` → same
- `Business City` → `source: "asked", binding: "answer:form_101.business_city"`
- `Business State` → `source: "asked", binding: "answer:form_101.business_state"`
- `ZIP Code_5` → `source: "asked", binding: "answer:form_101.business_zip"`

**Page 5 — Hazard/emergency (8 fields):**

No gate — always applicable:
- `What is the hazard1` → `source: "asked", binding: "answer:form_101.hazard_description"`
- `What is the hazard2` → same
- `If immediate attention is needed why is it needed1` → `source: "asked", binding: "answer:form_101.hazard_reason"`
- `If immediate attention is needed why is it needed2` → same
- `Street_6` → hazard location street: `source: "asked", binding: "answer:form_101.hazard_street"`
- `Street_7` → same
- `State_6` → hazard location state: `source: "asked", binding: "answer:form_101.hazard_state"`
- `ZIP Code_6` → hazard location zip: `source: "asked", binding: "answer:form_101.hazard_zip"`

**Page 7 — Non-consumer debt + signature (3 fields):**

- `16c State the type of debts you owe that are not consumer debts or business debts` → `source: "asked", binding: "answer:form_101.non_consumer_debt_type"`
- `signature` → `source: "signature"`
- `Executed on` → `source: "asked", binding: "answer:form_101.executed_on"`

**Page 8 — Attorney info (11 fields):**

All gated behind `conditional_on: "has_attorney"`:
- `Sig` → `source: "signature"`
- `Date signed` → `source: "asked", binding: "answer:form_101.attorney_date_signed"`
- `Printed name` → `source: "asked", binding: "answer:form_101.attorney_printed_name"`
- `Firm name` → `source: "asked", binding: "answer:form_101.attorney_firm_name"`
- `Street address_2` → `source: "asked", binding: "answer:form_101.attorney_street"`
- `Street address_3` → same
- `Zip` → `source: "asked", binding: "answer:form_101.attorney_zip"`
- `phone` → `source: "asked", binding: "answer:form_101.attorney_phone"`
- `Email address` → `source: "asked", binding: "answer:form_101.attorney_email"`
- `Bar number` → `source: "asked", binding: "answer:form_101.attorney_bar_number"`
- `Bar State` → `source: "asked", binding: "answer:form_101.attorney_bar_state"`

**Page 9 — Petition preparer (10 fields):**

No gate — always applicable:
- `Name of person payed to help file` → `source: "asked", binding: "answer:form_101.preparer_name"`
- `Signature` → `source: "signature"`
- `Contact phone_2` → `source: "asked", binding: "answer:form_101.preparer_phone"`
- `Contact phone` → same
- `Cell phone` → same
- `Email address_2` → `source: "asked", binding: "answer:form_101.preparer_email"`
- `Print1` → checkbox: `source: "constant", value: "/Yes"` (agreement checkbox)
- `SaveAs` → button: `source: "constant", value: ""` (non-fillable action button)
- `attach` → button: `source: "constant", value: ""`
- `Reset` → button: `source: "constant", value: ""`

**All fields get:**
- `required: false` (all Form 101 fields are optional / conditionally filled — no PDF field is strictly required for the form to be accepted)
- `legal_review: false` (no field involves a legal conclusion)
- `on_states` populated from draft (pypdf detection)

After editing, validate with:

```bash
docker compose exec -T backend python -c "
from apps.forms.schema import validate_schema, load_schema
from apps.forms.services.derivations import DERIVATIONS, PREDICATES
schema = load_schema('form_101')
errors = validate_schema(schema, set(DERIVATIONS), set(PREDICATES))
if errors:
    for e in errors: print(e)
else:
    print('Schema validates clean — 0 errors')
"
```
Expected: "Schema validates clean — 0 errors"

- [ ] **Step 3: Run validation to confirm clean**

```bash
docker compose exec -T backend python -c "
from apps.forms.schema import validate_schema, load_schema
from apps.forms.services.derivations import DERIVATIONS, PREDICATES
schema = load_schema('form_101')
errors = validate_schema(schema, set(DERIVATIONS), set(PREDICATES))
if errors:
    for e in errors: print(e)
else:
    print('0 errors')
"
```
Expected: "0 errors"

- [ ] **Step 4: Commit**

```bash
git add data/forms/schemas/form_101.json
git commit -m "feat(forms): curated Form 101 schema (110 fields, 8 pages)"
```

---

### Task 3: Wire-up — switch `Form101Generator` to resolver, update field-map test

**Files:**
- Modify: `backend/apps/forms/services/form_101_generator.py`
- Modify: `backend/apps/forms/tests/test_pdf_field_maps.py`

**Interfaces:**
- Consumes: `load_schema("form_101")`, `resolve(schema, session)` from SP1
- Produces: `Form101Generator.pdf_field_map()` returns resolver output
- Removes: The hand-authored dict of ~24 field entries in `pdf_field_map()`

- [ ] **Step 1: Update the failing test first**

Edit `backend/apps/forms/tests/test_pdf_field_maps.py`. The existing `test_form_101_pdf_field_map` checks old dotted field names. Replace with resolver-based assertions:

```python
def test_form_101_pdf_field_map(full_session):
    gen = get_generator("form_101", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    # The resolver returns actual template field names (no "Debtor1." prefix)
    assert field_map.get("First name") == "Maria"
    assert field_map.get("Last name") == "Torres"
    # SSN last-4
    assert field_map.get("SSNum") == "0001"
    assert field_map.get("City") == "Chicago"
    # Chapter 7 checkbox constant
    assert field_map.get("Check Box2") == "/Yes"
    # Attorney-gated fields are absent (pro se = no attorney)
    assert field_map.get("Firm name") is None  # gated behind has_attorney
    # Business-gated fields absent if no business
    assert field_map.get("Business name") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec -T backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_101_pdf_field_map -v
```
Expected: FAIL — the generator still returns the old dict with `Debtor1.First name`

- [ ] **Step 3: Switch `pdf_field_map()` to resolver**

Replace the entire `pdf_field_map()` method in `backend/apps/forms/services/form_101_generator.py`:

```python
def pdf_field_map(self) -> dict:
    """Delegate to the schema-driven resolver."""
    from apps.forms.schema import load_schema
    from apps.forms.services.fill_resolver import resolve

    schema = load_schema("form_101")
    return resolve(schema, self.intake_session)
```

Also remove the `import` at line 10 (`from apps.intake.models import IntakeSession`) if it's no longer needed — check whether `_build_form_data` and other methods still use it. Keep it if used elsewhere.

The hand-authored field dict (currently lines ~57-83 in `pdf_field_map()`) is removed entirely.

- [ ] **Step 4: Run test to verify it passes**

```bash
docker compose exec -T backend python -m pytest apps/forms/tests/test_pdf_field_maps.py::test_form_101_pdf_field_map -v
```
Expected: PASS

- [ ] **Step 5: Run full forms test suite**

```bash
docker compose exec -T backend python -m pytest apps/forms/tests/ -v
```
Expected: All tests pass (any failures are from the schema being wrong — fix the schema, not the test)

- [ ] **Step 6: Commit**

```bash
git add backend/apps/forms/services/form_101_generator.py backend/apps/forms/tests/test_pdf_field_maps.py
git commit -m "feat(forms): Form 101 delegates to schema-driven resolver"
```

---

### Task 4: Coverage proof (Form 101)

**Files:**
- Modify: `backend/apps/forms/tests/test_coverage.py`

**Interfaces:**
- Consumes: `load_schema("form_101")`, `resolve(schema, session)`, `_section_applies`
- Produces: Proof that every applicable Form 101 field resolves for at least one persona

- [ ] **Step 1: Add Form 101 coverage tests**

Append to `backend/apps/forms/tests/test_coverage.py`:

```python
@pytest.mark.django_db
def test_form_101_all_applicable_fields_resolve(ilnd_fixture):
    """Every applicable Form 101 field resolves to a value for a seeded persona."""
    call_command("seed_demo_data", "--reset", persona="maria")
    session = IntakeSession.objects.filter(user__username="demo_maria").first()

    schema = load_schema("form_101")
    out = resolve(schema, session)

    applicable_required = [
        f
        for f in schema.fields
        if f.required
        and _section_applies(f, session)
        and f.source not in ("signature", "ingested")
        and not f.legal_review
    ]
    unresolved = [f.pdf_field for f in applicable_required if f.pdf_field not in out]
    assert unresolved == [], f"unresolved Form 101 fields: {unresolved}"


@pytest.mark.django_db
def test_form_101_resolved_fields_from_multiple_sources(ilnd_fixture):
    """Form 101 resolved fields come from derivations + FormAnswer + constants."""
    call_command("seed_demo_data", "--reset", persona="maria")
    session = IntakeSession.objects.filter(user__username="demo_maria").first()

    schema = load_schema("form_101")
    out = resolve(schema, session)

    values = list(out.values())
    # At least one constant (Check Box2)
    assert any(v == "/Yes" for v in values)
    # At least one derived value (full name or district)
    assert any(v and "Maria" in str(v) for v in values)
```

- [ ] **Step 2: Run the coverage tests**

```bash
docker compose exec -T backend python -m pytest apps/forms/tests/test_coverage.py -v
```
Expected: PASS. If any field is unresolved, fix the schema in `form_101.json`.

- [ ] **Step 3: Commit**

```bash
git add backend/apps/forms/tests/test_coverage.py
git commit -m "test(forms): Form 101 coverage proof — every applicable field resolves"
```

---

### Task 5: Schema deployment (Dockerfile.heroku)

**Files:**
- Modify: `Dockerfile.heroku`

- [ ] **Step 1: Add COPY for schemas**

In `Dockerfile.heroku`, after the existing `COPY ./data/forms/pdfs /data/forms/pdfs` line, add:

```dockerfile
COPY ./data/forms/schemas /data/forms/schemas
```

- [ ] **Step 2: Verify build**

```bash
docker build -f Dockerfile.heroku -t dignifi-heroku --target runner .
```
Expected: Build succeeds. The schema directory is present in the runner stage.

- [ ] **Step 3: Commit**

```bash
git add Dockerfile.heroku
git commit -m "fix(deploy): bake form schemas into Heroku image (carried from SP1 findings)"
```
