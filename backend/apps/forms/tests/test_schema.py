from apps.forms.schema import FieldSpec, FormSchema, load_schema


class TestFieldSpec:
    """Test FieldSpec dataclass"""

    def test_fieldspec_creation(self):
        """Test creating a FieldSpec instance with all required fields"""
        field = FieldSpec(
            pdf_field="Debtor 1",
            type="text",
            source="asked",
            on_states=["intake"],
            page=1,
            label="Debtor 1 Name",
            required=True,
            conditional_on=None,
            value=None,
            rule=None,
            ingest_key=None,
            binding=None,
            repeat=None,
            repeat_capacity=None,
            row=None,
            legal_review=False,
        )
        assert field.pdf_field == "Debtor 1"
        assert field.type == "text"
        assert field.source == "asked"
        assert field.on_states == ["intake"]
        assert field.page == 1
        assert field.label == "Debtor 1 Name"
        assert field.required is True
        assert field.conditional_on is None
        assert field.value is None
        assert field.rule is None
        assert field.ingest_key is None
        assert field.binding is None
        assert field.repeat is None
        assert field.repeat_capacity is None
        assert field.row is None
        assert field.legal_review is False


class TestLoadSchema:
    """Test load_schema function"""

    def test_load_schema_form_test(self):
        """Test loading the form_test schema from JSON"""
        schema = load_schema("form_test")

        assert isinstance(schema, FormSchema)
        assert schema.form_type == "form_test"
        assert schema.template_filename == "b_107_0425-form.pdf"
        assert schema.template_version == "abc123"
        assert len(schema.fields) == 2

        # Check first field
        field1 = schema.fields[0]
        assert isinstance(field1, FieldSpec)
        assert field1.pdf_field == "Debtor 1"
        assert field1.type == "text"
        assert field1.source == "asked"
        assert field1.label == "Debtor 1 name"
        assert field1.required is True

        # Check second field
        field2 = schema.fields[1]
        assert isinstance(field2, FieldSpec)
        assert field2.pdf_field == "Debtor 2"
        assert field2.type == "text"
        assert field2.source == "asked"
        assert field2.label == "Debtor 2 name"
        assert field2.required is False
