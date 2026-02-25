"""
User serializers for registration and profile retrieval.

Registration requires explicit UPL disclaimer agreement — the DB enforces
consistency between agreed_to_upl_disclaimer and upl_disclaimer_agreed_at
via a CheckConstraint.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Register a new user with required UPL disclaimer agreement."""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    agreed_to_upl_disclaimer = serializers.BooleanField(required=True)
    agreed_to_terms = serializers.BooleanField(required=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "password",
            "agreed_to_upl_disclaimer",
            "agreed_to_terms",
        )
        read_only_fields = ("id",)
        extra_kwargs = {
            "email": {"required": True},
        }

    def validate_email(self, value: str) -> str:
        normalized = value.lower().strip()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return normalized

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate_agreed_to_upl_disclaimer(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "You must acknowledge that this platform provides legal "
                "information, not legal advice, before continuing."
            )
        return value

    def validate_agreed_to_terms(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "You must agree to the Terms of Service to create an account."
            )
        return value

    def create(self, validated_data: dict) -> User:
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            agreed_to_upl_disclaimer=True,
            agreed_to_terms=True,
            upl_disclaimer_agreed_at=timezone.now(),
        )


class UserProfileSerializer(serializers.ModelSerializer):
    """Read-only profile for the authenticated user."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "agreed_to_upl_disclaimer",
            "upl_disclaimer_agreed_at",
            "created_at",
        )
        read_only_fields = fields
