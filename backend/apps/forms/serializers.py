"""
Serializers for bankruptcy form generation.

Provides serializers for generated forms and form data.
"""

from rest_framework import serializers

from .models import GeneratedForm


class GeneratedFormSerializer(serializers.ModelSerializer):
    """
    Serializer for generated bankruptcy forms.

    Returns form metadata only. The printed values (field_values) are encrypted
    and never leave the server; download fills the PDF from them.
    """

    form_type_display = serializers.CharField(source="get_form_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

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
            "generated_by",
            "generated_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "generated_by",
            "generated_at",
            "updated_at",
            "form_type_display",
            "status_display",
        ]
