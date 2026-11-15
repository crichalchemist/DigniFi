"""
Serializers for bankruptcy form generation.

Provides serializers for generated forms and form data.
"""

import json

from rest_framework import serializers

from .models import GeneratedForm
from .services.pdf_filler import parts_of

# Form 122A-1's CheckBox1 choice for "above" in form_122a1.json; box 1 is "/No Abuse".
PRESUMPTION_BOX = "/Presumption of abuse applies"


class GeneratedFormSerializer(serializers.ModelSerializer):
    """
    Serializer for generated bankruptcy forms.

    Returns form metadata only. The printed values (field_values) are encrypted
    and never leave the server; download fills the PDF from them.
    """

    form_type_display = serializers.CharField(source="get_form_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    stored_box_2 = serializers.SerializerMethodField()

    def get_stored_box_2(self, obj):
        """Whether a filed 122A-1 stored box 2, read live from its stored document (H52).

        None for every other row, and for a filed 122A-1 with nothing stored. A document with
        no form part reads as not box 2.
        """
        if obj.form_type != "form_122a1" or obj.status != "filed" or not obj.field_values:
            return None
        for part in parts_of(json.loads(obj.field_values)):
            if part.get("kind") == "form":
                return part["values"].get("CheckBox1") == PRESUMPTION_BOX
        return False

    class Meta:
        model = GeneratedForm
        fields = [
            "id",
            "session",
            "form_type",
            "form_type_display",
            "status",
            "status_display",
            "pdf_file_path",
            "filed_before_means_test",
            "stored_box_2",
            "generated_by",
            "generated_at",
            "updated_at",
        ]
        read_only_fields = [
            "filed_before_means_test",
            "id",
            "generated_by",
            "generated_at",
            "updated_at",
            "form_type_display",
            "status_display",
        ]
