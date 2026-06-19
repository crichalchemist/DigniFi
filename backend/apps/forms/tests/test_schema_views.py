from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.forms.schema import FieldSpec, FormSchema, UIFieldSpec


class TestUISpecView(APITestCase):
    def setUp(self):
        self.test_schema = FormSchema(
            form_type="form_test",
            template_filename="test.pdf",
            template_version="v1",
            fields=[
                FieldSpec(
                    pdf_field="Q1",
                    type="text",
                    source="asked",
                    binding="answer:test.q1",
                    on_states=(),
                    page=1,
                    label="l",
                    required=False,
                    conditional_on=None,
                    value=None,
                    rule=None,
                    ingest_key=None,
                    repeat=None,
                    repeat_capacity=None,
                    row=None,
                    legal_review=False,
                    ui=UIFieldSpec(step="Step 1", prompt="Prompt 1", widget="text"),
                )
            ],
        )
        self.patcher = patch("apps.forms.views.load_schema")
        self.mock_load_schema = self.patcher.start()

        # Only return the test_schema if form_type matches
        def side_effect(form_type):
            if form_type == "form_test":
                return self.test_schema
            raise FileNotFoundError(f"Schema file not found: {form_type}.json")

        self.mock_load_schema.side_effect = side_effect

    def tearDown(self):
        self.patcher.stop()

    def test_get_ui_spec_returns_structured_data(self):
        url = reverse("form-schema-ui-spec", kwargs={"form_type": "form_test"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("steps", data)
        self.assertEqual(len(data["steps"]), 1)
        self.assertEqual(data["steps"][0]["title"], "Step 1")
        self.assertEqual(data["steps"][0]["fields"][0]["binding"], "answer:test.q1")
        self.assertEqual(data["steps"][0]["fields"][0]["prompt"], "Prompt 1")

    def test_get_ui_spec_groups_repeat_fields(self):
        self.test_schema.fields.extend(
            [
                FieldSpec(
                    pdf_field="R1_Source",
                    type="text",
                    source="asked",
                    binding="expense.source",
                    on_states=(),
                    page=1,
                    label="l",
                    required=False,
                    conditional_on={"field": "has_expenses", "value": True},
                    value=None,
                    rule=None,
                    ingest_key=None,
                    repeat="expenses",
                    repeat_capacity=3,
                    row=1,
                    legal_review=False,
                    ui=UIFieldSpec(step="Expenses", prompt="Source", widget="text"),
                ),
                FieldSpec(
                    pdf_field="R1_Amount",
                    type="text",
                    source="asked",
                    binding="expense.amount",
                    on_states=(),
                    page=1,
                    label="l",
                    required=False,
                    conditional_on={"field": "has_expenses", "value": True},
                    value=None,
                    rule=None,
                    ingest_key=None,
                    repeat="expenses",
                    repeat_capacity=3,
                    row=1,
                    legal_review=False,
                    ui=UIFieldSpec(step="Expenses", prompt="Amount", widget="currency"),
                ),
                FieldSpec(
                    pdf_field="R2_Source",
                    type="text",
                    source="asked",
                    binding="expense.source",
                    on_states=(),
                    page=1,
                    label="l",
                    required=False,
                    conditional_on={"field": "has_expenses", "value": True},
                    value=None,
                    rule=None,
                    ingest_key=None,
                    repeat="expenses",
                    repeat_capacity=3,
                    row=2,
                    legal_review=False,
                    ui=UIFieldSpec(step="Expenses", prompt="Source", widget="text"),
                ),
                FieldSpec(
                    pdf_field="R2_Amount",
                    type="text",
                    source="asked",
                    binding="expense.amount",
                    on_states=(),
                    page=1,
                    label="l",
                    required=False,
                    conditional_on={"field": "has_expenses", "value": True},
                    value=None,
                    rule=None,
                    ingest_key=None,
                    repeat="expenses",
                    repeat_capacity=3,
                    row=2,
                    legal_review=False,
                    ui=UIFieldSpec(step="Expenses", prompt="Amount", widget="currency"),
                ),
                FieldSpec(
                    pdf_field="R3",
                    type="text",
                    source="asked",
                    binding="expense.other.amount",
                    on_states=(),
                    page=1,
                    label="l",
                    required=False,
                    conditional_on=None,
                    value=None,
                    rule=None,
                    ingest_key=None,
                    repeat=None,
                    repeat_capacity=None,
                    row=None,
                    legal_review=False,
                    ui=UIFieldSpec(step="Expenses", prompt="Other", widget="currency"),
                ),
            ]
        )

        url = reverse("form-schema-ui-spec", kwargs={"form_type": "form_test"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        expenses_step = next(s for s in data["steps"] if s["title"] == "Expenses")
        # Should have 2 fields at the top level: the repeat_group, and the non-repeated field
        self.assertEqual(len(expenses_step["fields"]), 2)

        group = expenses_step["fields"][0]
        self.assertEqual(group["widget"], "repeat_group")
        self.assertEqual(group["repeat"], "expenses")
        self.assertEqual(group["repeat_capacity"], 3)
        self.assertEqual(group["conditional_on"], {"field": "has_expenses", "value": True})
        self.assertEqual(len(group["fields"]), 2)
        self.assertEqual(group["fields"][0]["binding"], "expense.source")
        self.assertEqual(group["fields"][1]["binding"], "expense.amount")

        non_repeat = expenses_step["fields"][1]
        self.assertEqual(non_repeat["binding"], "expense.other.amount")
        self.assertEqual(non_repeat["widget"], "currency")
