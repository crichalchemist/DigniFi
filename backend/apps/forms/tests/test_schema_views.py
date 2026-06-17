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
