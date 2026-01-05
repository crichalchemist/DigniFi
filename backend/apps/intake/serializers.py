"""
Serializers for intake models.

Provides Django REST Framework serializers for API endpoints, including
validation, nested relationships, and trauma-informed error messages.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    IntakeSession,
    DebtorInfo,
    IncomeInfo,
    ExpenseInfo,
    AssetInfo,
    DebtInfo,
)
from apps.districts.models import District

User = get_user_model()


class DebtorInfoSerializer(serializers.ModelSerializer):
    """Serializer for debtor personal information (PII encrypted)."""

    class Meta:
        model = DebtorInfo
        fields = [
            "first_name",
            "last_name",
            "middle_name",
            "ssn",
            "date_of_birth",
            "phone",
            "email",
            "street_address",
            "city",
            "state",
            "zip_code",
        ]
        extra_kwargs = {
            "ssn": {"write_only": True},  # Never return SSN in API responses
        }

    def validate_ssn(self, value):
        """Validate SSN format (9 digits, no hyphens for storage)."""
        # Remove any hyphens or spaces
        ssn_clean = value.replace("-", "").replace(" ", "")

        if not ssn_clean.isdigit() or len(ssn_clean) != 9:
            raise serializers.ValidationError(
                "Please enter a valid 9-digit Social Security Number"
            )

        return ssn_clean

    def validate_state(self, value):
        """Validate state is 2-letter uppercase code."""
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError(
                "Please enter a valid 2-letter state code"
            )
        return value.upper()


class IncomeInfoSerializer(serializers.ModelSerializer):
    """Serializer for income information."""

    class Meta:
        model = IncomeInfo
        fields = [
            "marital_status",
            "number_of_dependents",
            "monthly_income",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate_monthly_income(self, value):
        """
        Validate monthly_income is a list of 6 positive numbers.

        Args:
            value: List of monthly income amounts

        Returns:
            list: Validated monthly income list

        Raises:
            ValidationError: If format is invalid
        """
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "Please provide income as a list of monthly amounts"
            )

        if len(value) != 6:
            raise serializers.ValidationError(
                "Please provide income for the last 6 months"
            )

        for i, amount in enumerate(value):
            try:
                float_amount = float(amount)
                if float_amount < 0:
                    raise serializers.ValidationError(
                        f"Income for month {i+1} cannot be negative"
                    )
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    f"Income for month {i+1} must be a valid number"
                )

        return value


class ExpenseInfoSerializer(serializers.ModelSerializer):
    """Serializer for monthly expense information."""

    total_monthly_expenses = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseInfo
        fields = [
            "data_source",
            "rent_or_mortgage",
            "utilities",
            "home_maintenance",
            "vehicle_payment",
            "vehicle_insurance",
            "vehicle_maintenance",
            "food_and_groceries",
            "clothing",
            "medical_expenses",
            "childcare",
            "child_support_paid",
            "insurance_not_deducted",
            "other_expenses",
            "total_monthly_expenses",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "total_monthly_expenses"]

    def get_total_monthly_expenses(self, obj):
        """Calculate and return total monthly expenses."""
        return obj.calculate_total_monthly_expenses()


class AssetInfoSerializer(serializers.ModelSerializer):
    """Serializer for asset information (encrypted values)."""

    equity = serializers.SerializerMethodField()

    class Meta:
        model = AssetInfo
        fields = [
            "id",
            "asset_type",
            "data_source",
            "description",
            "current_value",
            "amount_owed",
            "equity",
            "account_number",
            "financial_institution",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "equity"]
        extra_kwargs = {
            "account_number": {"write_only": True},  # Don't expose in responses
            "current_value": {"write_only": True},  # Encrypted, use equity instead
            "amount_owed": {"write_only": True},  # Encrypted
        }

    def get_equity(self, obj):
        """Return calculated equity (current_value - amount_owed)."""
        return obj.equity


class DebtInfoSerializer(serializers.ModelSerializer):
    """Serializer for debt/creditor information (trauma-informed language)."""

    class Meta:
        model = DebtInfo
        fields = [
            "id",
            "data_source",
            "creditor_name",
            "debt_type",
            "priority_classification",
            "account_number",
            "amount_owed",
            "monthly_payment",
            "is_in_collections",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "account_number": {"write_only": True},  # Don't expose account numbers
            "amount_owed": {"write_only": True},  # Encrypted PII
        }


class IntakeSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for intake session with nested related data.

    Provides full session data including debtor info, income, expenses, assets, debts.
    """

    debtor_info = DebtorInfoSerializer(required=False, allow_null=True)
    income_info = IncomeInfoSerializer(required=False, allow_null=True)
    expense_info = ExpenseInfoSerializer(required=False, allow_null=True)
    assets = AssetInfoSerializer(many=True, required=False)
    debts = DebtInfoSerializer(many=True, required=False)

    district_name = serializers.CharField(source="district.name", read_only=True)

    class Meta:
        model = IntakeSession
        fields = [
            "id",
            "user",
            "status",
            "current_step",
            "district",
            "district_name",
            "debtor_info",
            "income_info",
            "expense_info",
            "assets",
            "debts",
            "created_at",
            "completed_at",
        ]
        read_only_fields = ["id", "created_at", "completed_at", "district_name"]

    def create(self, validated_data):
        """
        Create intake session with nested related data.

        Handles creation of debtor_info, income_info, expense_info,
        and related assets/debts in a single transaction.
        """
        debtor_data = validated_data.pop("debtor_info", None)
        income_data = validated_data.pop("income_info", None)
        expense_data = validated_data.pop("expense_info", None)
        assets_data = validated_data.pop("assets", [])
        debts_data = validated_data.pop("debts", [])

        # Create session
        session = IntakeSession.objects.create(**validated_data)

        # Create related objects
        if debtor_data:
            DebtorInfo.objects.create(session=session, **debtor_data)

        if income_data:
            IncomeInfo.objects.create(session=session, **income_data)

        if expense_data:
            ExpenseInfo.objects.create(session=session, **expense_data)

        # Create assets
        for asset_data in assets_data:
            AssetInfo.objects.create(session=session, **asset_data)

        # Create debts
        for debt_data in debts_data:
            DebtInfo.objects.create(session=session, **debt_data)

        return session

    def update(self, instance, validated_data):
        """
        Update intake session with nested related data.

        Updates or creates debtor_info, income_info, expense_info.
        For assets/debts, replaces entire list (for simplicity in MVP).
        """
        debtor_data = validated_data.pop("debtor_info", None)
        income_data = validated_data.pop("income_info", None)
        expense_data = validated_data.pop("expense_info", None)
        assets_data = validated_data.pop("assets", None)
        debts_data = validated_data.pop("debts", None)

        # Update session fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or create nested objects
        if debtor_data:
            DebtorInfo.objects.update_or_create(session=instance, defaults=debtor_data)

        if income_data:
            IncomeInfo.objects.update_or_create(session=instance, defaults=income_data)

        if expense_data:
            ExpenseInfo.objects.update_or_create(
                session=instance, defaults=expense_data
            )

        # For MVP: Replace assets/debts entirely (future: partial updates)
        if assets_data is not None:
            instance.assets.all().delete()
            for asset_data in assets_data:
                AssetInfo.objects.create(session=instance, **asset_data)

        if debts_data is not None:
            instance.debts.all().delete()
            for debt_data in debts_data:
                DebtInfo.objects.create(session=instance, **debt_data)

        return instance
