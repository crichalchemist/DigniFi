"""
Serializers for intake models.

Provides Django REST Framework serializers for API endpoints, including
validation, nested relationships, and trauma-informed error messages.
"""

import json
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from rest_framework import serializers

from apps.districts.counties import ILND_COUNTIES
from apps.districts.dated_tables import fill_date
from apps.eligibility.cmi import answered_window, income_step_gaps, income_window
from apps.forms.services.exemption_items import fits_description, fits_law

from .asset_lines import LINE_BY_KEY, PROPERTY_KINDS, WHO
from .claims import PRIORITY_ANSWERS, account_last_4, legacy_payments, ordered_debts
from .household import (
    MAX_AGE,
    MAX_MEMBERS,
    RELATIONSHIP_WORDS,
    count_family_size,
    count_fee_waiver_household,
)
from .income import ENTRY_KINDS, MAX_ENTRIES
from .models import (
    HOME_PAYMENT_LINES,
    YES_NO,
    AssetInfo,
    AssetLineAnswers,
    ClaimAnswers,
    Codebtor,
    DebtInfo,
    DebtorInfo,
    ExecutoryContract,
    ExemptionAnswers,
    ExemptionClaim,
    ExpenseInfo,
    FilingFee,
    Household,
    IncomeDetail,
    IncomeInfo,
    IntakeSession,
    SOFACreditorPayment,
    SOFAPriorIncome,
    SOFAReport,
    SpouseIncome,
)

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
            raise serializers.ValidationError("Please enter a valid 9-digit Social Security Number")

        return ssn_clean

    def validate_state(self, value):
        """Validate state is 2-letter uppercase code."""
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError("Please enter a valid 2-letter state code")
        return value.upper()


def _amount() -> serializers.DecimalField:
    """One Income step amount: zero or more, within the column, null while unanswered."""
    return serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )


class IncomeEntrySerializer(serializers.Serializer):
    """One business or rental entry on the Income step (3e2 spec §4.2).

    Every answer may be missing, for Complete to name; only a value no answer can have is
    refused.
    """

    id = serializers.IntegerField(required=False, allow_null=True)
    kind = serializers.ChoiceField(choices=ENTRY_KINDS, allow_null=True, required=False)
    description = serializers.CharField(
        max_length=200, allow_null=True, allow_blank=True, required=False
    )
    gross = _amount()
    expenses = _amount()
    current_gross = _amount()
    current_expenses = _amount()


# What IncomeInfo and SpouseIncome share beyond the ten (3e2 spec §4), named for both Metas.
_INCOME_DETAIL_FIELDS = [
    "monthly_rental_income",
    "monthly_interest_and_dividends",
    *IncomeDetail.CURRENT_FIELDS,
    "business_and_rental",
    "income_now_different",
    "assistance_answer",
    "cash_assistance_kind",
    "cash_assistance_amount",
    "noncash_assistance_kind",
    "noncash_assistance_value",
    *IncomeDetail.DEDUCTION_FIELDS,
    "payroll_other_specify",
]


class IncomeDetailSerializer(serializers.ModelSerializer):
    """The 3e2 answers both income serializers carry (3e2 spec §4).

    monthly_rental_income is the legacy net figure: returned, never written.
    """

    # Explicit field declarations — EncryptedDecimalField confuses DRF's auto-mapper
    monthly_rental_income = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    monthly_interest_and_dividends = _amount()
    current_monthly_gross_wages = _amount()
    current_monthly_overtime = _amount()
    current_monthly_tips = _amount()
    current_monthly_interest_and_dividends = _amount()
    current_monthly_pension = _amount()
    current_monthly_social_security = _amount()
    current_monthly_unemployment = _amount()
    current_monthly_child_support = _amount()
    current_monthly_alimony = _amount()
    current_monthly_other_income = _amount()
    cash_assistance_amount = _amount()
    noncash_assistance_value = _amount()
    payroll_tax = _amount()
    payroll_mandatory_retirement = _amount()
    payroll_voluntary_retirement = _amount()
    payroll_retirement_loan = _amount()
    payroll_insurance = _amount()
    payroll_support = _amount()
    payroll_union_dues = _amount()
    payroll_other = _amount()
    income_now_different = serializers.ChoiceField(choices=YES_NO, allow_null=True, required=False)
    assistance_answer = serializers.ChoiceField(choices=YES_NO, allow_null=True, required=False)
    cash_assistance_kind = serializers.CharField(max_length=100, allow_blank=True, required=False)
    noncash_assistance_kind = serializers.CharField(
        max_length=100, allow_blank=True, required=False
    )
    payroll_other_specify = serializers.CharField(max_length=100, allow_blank=True, required=False)
    business_and_rental = serializers.ListField(
        child=IncomeEntrySerializer(),
        allow_null=True,
        required=False,
        max_length=MAX_ENTRIES,
        write_only=True,
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["business_and_rental"] = instance.get_entries()
        return data


class IncomeInfoSerializer(IncomeDetailSerializer):
    """Serializer for income information, stored by source (forms step 2 spec §5.5).

    monthly_income, the total saved before step 2, is read-only: the Income step shows it
    while asking the filer to split it. marital_status is Form 122A-1 line 1's answer: one of
    its four answers, or null while unanswered (3e1 spec §3.3).
    """

    total_monthly_income = serializers.SerializerMethodField()
    answered_window = serializers.SerializerMethodField()
    marital_status = serializers.ChoiceField(
        choices=IncomeInfo.MARITAL_ANSWERS, allow_null=True, required=False
    )
    # Explicit field declarations — EncryptedDecimalField confuses DRF's auto-mapper
    monthly_gross_wages = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_overtime = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_tips = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_pension = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_social_security = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_unemployment = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_child_support = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_alimony = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_other_income = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )

    class Meta:
        model = IncomeInfo
        fields = [
            "marital_status",
            *IncomeInfo.SOURCE_FIELDS,
            *_INCOME_DETAIL_FIELDS,
            "income_period_end",
            "answered_window",
            "monthly_income",
            "total_monthly_income",
            "created_at",
        ]
        read_only_fields = [
            "created_at",
            "income_period_end",
            "answered_window",
            "monthly_income",
            "total_monthly_income",
        ]

    def get_total_monthly_income(self, obj):
        """Return the ten amounts added up, or None when the filer gave none of them."""
        return obj.calculate_total_monthly_income()

    def get_answered_window(self, obj):
        """The six months the filer last confirmed on the Income step, or None before then."""
        if obj.income_period_end is None:
            return None
        start, end = answered_window(obj.income_period_end)
        return {"start": start.isoformat(), "end": end.isoformat()}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["monthly_income"] = instance.get_monthly_income()
        return data


class SpouseIncomeSerializer(IncomeDetailSerializer):
    """The spouse's monthly income by the filer's ten sources (3e1 spec §5.2).

    A blank box is null, never $0 unless typed.
    """

    # Explicit field declarations — EncryptedDecimalField confuses DRF's auto-mapper
    monthly_gross_wages = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_overtime = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_tips = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_pension = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_social_security = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_unemployment = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_child_support = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_alimony = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )
    monthly_other_income = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), allow_null=True, required=False
    )

    class Meta:
        model = SpouseIncome
        fields = [*SpouseIncome.SOURCE_FIELDS, *_INCOME_DETAIL_FIELDS]


class ExpenseInfoSerializer(serializers.ModelSerializer):
    """Serializer for monthly expense information."""

    total_monthly_expenses = serializers.SerializerMethodField()
    # Explicit field declarations — EncryptedDecimalField confuses DRF's auto-mapper
    rent_or_mortgage = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    utilities = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    home_maintenance = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    vehicle_insurance = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    vehicle_maintenance = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    food_and_groceries = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    clothing = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    medical_expenses = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    childcare = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    child_support_paid = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    insurance_not_deducted = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    other_expenses = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    real_estate_taxes = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    home_insurance = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    hoa_dues = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    personal_care = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    entertainment = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    charitable_contributions = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    taxes_not_deducted = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    support_others = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    other_property_taxes = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    other_property_insurance = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    other_property_upkeep = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    other_property_hoa_dues = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    # Retired (3c4): a 0 sent on its own is Remove, and any other figure is dropped in validate.
    vehicle_payment = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), write_only=True, required=False
    )
    other_property_mortgages = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), write_only=True, required=False
    )
    taxes_specify = serializers.CharField(max_length=100, allow_blank=True, required=False)
    support_others_specify = serializers.CharField(max_length=100, allow_blank=True, required=False)
    other_expenses_specify = serializers.CharField(max_length=100, allow_blank=True, required=False)
    expenses_include_others = serializers.ChoiceField(
        choices=YES_NO, allow_null=True, required=False
    )

    class Meta:
        model = ExpenseInfo
        fields = [
            "data_source",
            *ExpenseInfo.AMOUNT_FIELDS,
            *ExpenseInfo.LEGACY_FIELDS,
            *ExpenseInfo.SPECIFY_FIELDS,
            "expenses_include_others",
            "total_monthly_expenses",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "total_monthly_expenses"]

    def validate(self, attrs):
        """Keep a retired figure only when it is 0 and the body holds nothing else (Remove sends
        exactly {field: 0}). Sent beside any other key, as an older wizard's step 4 save does
        with every amount, it is dropped whatever its value, so a stored figure survives."""
        only_retired = all(key in ExpenseInfo.LEGACY_FIELDS for key in attrs)
        for field in ExpenseInfo.LEGACY_FIELDS:
            if field in attrs and (attrs[field] != 0 or not only_retired):
                del attrs[field]
        return attrs

    def get_total_monthly_expenses(self, obj):
        """Calculate and return total monthly expenses."""
        return obj.calculate_total_monthly_expenses()


_TEXT = {"max_length": 200, "required": False, "allow_blank": True, "allow_null": True}


class AssetDetailsSerializer(serializers.Serializer):
    """What a line's rows ask beyond a description and a value (3b spec §3.1).

    Every key is optional and nullable. A row's details are replaced whole on a save.
    """

    kind = serializers.CharField(**_TEXT)
    street = serializers.CharField(**_TEXT)
    street_2 = serializers.CharField(**_TEXT)
    city = serializers.CharField(**_TEXT)
    state = serializers.CharField(**_TEXT)
    zip = serializers.CharField(**_TEXT)
    county = serializers.CharField(**_TEXT)
    property_kinds = serializers.ListField(
        child=serializers.ChoiceField(choices=PROPERTY_KINDS), required=False, allow_null=True
    )
    other_kind = serializers.CharField(**_TEXT)
    nature = serializers.CharField(**_TEXT)
    who = serializers.ChoiceField(choices=WHO, required=False, allow_null=True)
    lives_here = serializers.ChoiceField(choices=YES_NO, required=False, allow_null=True)
    community = serializers.BooleanField(required=False, allow_null=True)
    other_info = serializers.CharField(**_TEXT)
    make = serializers.CharField(**_TEXT)
    model = serializers.CharField(**_TEXT)
    year = serializers.CharField(**_TEXT)
    mileage = serializers.CharField(**_TEXT)
    percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal(0),
        max_value=Decimal(100),
        required=False,
        allow_null=True,
    )
    beneficiary = serializers.CharField(**_TEXT)
    has_personal_info = serializers.BooleanField(required=False, allow_null=True)
    value_unknown = serializers.BooleanField(required=False, allow_null=True)
    entire_unknown = serializers.BooleanField(required=False, allow_null=True)

    def validate(self, attrs):
        # The column is JSON, which has no decimal: percent is stored as a string.
        if attrs.get("percent") is not None:
            attrs["percent"] = str(attrs["percent"])
        return attrs


class AssetInfoSerializer(serializers.ModelSerializer):
    """Serializer for one Schedule A/B row (encrypted values).

    A per-item create needs a line; a row inside a session save may have none, so an old
    row round-trips (NestedAssetInfoSerializer).
    """

    line_required = True

    # Explicit field declarations — EncryptedDecimalField confuses DRF's auto-mapper
    ab_line = serializers.ChoiceField(choices=list(LINE_BY_KEY), required=False, allow_null=True)
    details = AssetDetailsSerializer(required=False)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    current_value = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal(0), required=False, allow_null=True
    )
    entire_value = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal(0), required=False, allow_null=True
    )

    class Meta:
        model = AssetInfo
        fields = [
            "id",
            "session",
            "ab_line",
            "details",
            "description",
            "current_value",
            "entire_value",
            "asset_type",
            "data_source",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "asset_type", "created_at", "updated_at"]

    def _stored_row(self, attrs):
        """The row this save updates: the instance, or a nested row's stored row by id."""
        if self.instance is not None:
            return self.instance
        row_id = attrs.get("id")
        session = getattr(getattr(self.parent, "parent", None), "instance", None)
        if row_id is None or session is None:
            return None
        return AssetInfo.objects.filter(pk=row_id, session=session).first()

    def validate(self, attrs):
        stored = self._stored_row(attrs)
        if self.line_required:
            # The per-item path never makes (or turns a row into) an old row with no line.
            creating = self.instance is None
            if (creating and not attrs.get("ab_line")) or (
                "ab_line" in attrs and not attrs["ab_line"]
            ):
                raise serializers.ValidationError({"ab_line": "Say which line this is on."})
        line_key = attrs["ab_line"] if "ab_line" in attrs else getattr(stored, "ab_line", None)
        details_sent = attrs.get("details") is not None
        if details_sent:
            details = attrs["details"]
        else:
            details = stored.get_details() if stored is not None else {}
        # A kind must sit on the row's line, whichever of the two a save changes.
        kind = details.get("kind")
        if kind and (details_sent or "ab_line" in attrs):
            line = LINE_BY_KEY.get(line_key)
            if line is None or kind not in dict(line.kinds):
                raise serializers.ValidationError(
                    {"details": {"kind": "That kind isn't on this line."}}
                )
        # A figure sent (or already stored) with its "I don't know the value" flag keeps the figure.
        changed = details_sent
        for flag, figure in (
            ("value_unknown", "current_value"),
            ("entire_unknown", "entire_value"),
        ):
            sent = attrs[figure] if figure in attrs else getattr(stored, figure, None)
            if sent is not None and details.get(flag):
                details[flag] = False
                changed = True
        if changed:
            attrs["details"] = json.dumps(details)
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["details"] = instance.get_details()
        return data


class AddressAnswersMixin(serializers.Serializer):
    """The address a debt, contract or codebtor row carries: declared once, here (3c3).

    A state saves as typed, upper-cased, up to two characters (R7): Complete judges whether it
    is two letters, so one half-typed row never refuses the whole list.
    """

    street_address = serializers.CharField(max_length=255, allow_blank=True, required=False)
    street_2 = serializers.CharField(max_length=255, allow_blank=True, required=False)
    city = serializers.CharField(max_length=100, allow_blank=True, required=False)
    state = serializers.CharField(max_length=2, allow_blank=True, required=False)
    zip_code = serializers.CharField(max_length=10, allow_blank=True, required=False)
    outside_us = serializers.BooleanField(required=False)

    def validate_state(self, value):
        return value.strip().upper()


class _StoredJSONField(serializers.Field):
    """A column the model keeps as JSON text. The reply shows the parsed value.

    get_attribute reads the model's get_<name>(); to_representation returns that as it is.
    """

    def get_attribute(self, instance):
        return getattr(instance, f"get_{self.field_name}")()

    def to_representation(self, value):
        return value


class LienField(_StoredJSONField):
    """null, or {"kinds": [...], "other": str}: kinds in DebtInfo.LIEN_KINDS' order."""

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Expected an object.")
        kinds = serializers.ListField(
            child=serializers.ChoiceField(choices=list(DebtInfo.LIEN_KINDS))
        ).run_validation(data.get("kinds", []))
        other = serializers.CharField(max_length=255, allow_blank=True).run_validation(
            data.get("other", "")
        )
        return {"kinds": [k for k in DebtInfo.LIEN_KINDS if k in kinds], "other": other}


class ClaimStatusField(_StoredJSONField):
    """null, or a list of DebtInfo.CLAIM_STATUSES in that order. [] is "None of these"."""

    def to_internal_value(self, data):
        statuses = serializers.ListField(
            child=serializers.ChoiceField(choices=list(DebtInfo.CLAIM_STATUSES))
        ).run_validation(data)
        return [s for s in DebtInfo.CLAIM_STATUSES if s in statuses]


class NoticePartySerializer(serializers.Serializer):
    """One person or office to notify about a debt (Schedules D and E/F Part 2)."""

    id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=255, allow_blank=True, required=False)
    street_address = serializers.CharField(max_length=255, allow_blank=True, required=False)
    street_2 = serializers.CharField(max_length=255, allow_blank=True, required=False)
    city = serializers.CharField(max_length=100, allow_blank=True, required=False)
    state = serializers.CharField(max_length=2, allow_blank=True, required=False)
    zip_code = serializers.CharField(max_length=10, allow_blank=True, required=False)
    last_4 = serializers.CharField(max_length=4, allow_blank=True, required=False)
    outside_us = serializers.BooleanField(required=False)

    def validate_state(self, value):
        return value.strip().upper()


class NoticePartiesField(_StoredJSONField):
    """null, or at most DebtInfo.MAX_NOTICE_PARTIES rows. Ids are given on save."""

    def to_internal_value(self, data):
        return serializers.ListField(
            child=NoticePartySerializer(), max_length=DebtInfo.MAX_NOTICE_PARTIES
        ).run_validation(data)


class DebtInfoSerializer(AddressAnswersMixin, serializers.ModelSerializer):
    """Serializer for debt/creditor information (trauma-informed language).

    This is the per-item path (POST/PATCH /debts/): it never sets a link or a JSON answer
    (R6). NestedDebtInfoSerializer is their only writer.
    """

    # Explicit field declaration — EncryptedDecimalField confuses DRF's auto-mapper
    amount_owed = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    creditor_name = serializers.CharField(max_length=255)
    monthly_payment = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal(0), required=False, allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    collateral_description = serializers.CharField(required=False, allow_blank=True)
    source_document_name = serializers.SerializerMethodField()
    account_last_4 = serializers.SerializerMethodField()
    secured_by = serializers.IntegerField(source="secured_by_id", read_only=True)
    home_payment_line = serializers.ChoiceField(
        choices=list(HOME_PAYMENT_LINES), allow_null=True, required=False
    )
    collateral_who = serializers.ChoiceField(choices=list(WHO), allow_null=True, required=False)
    offset_answer = serializers.ChoiceField(choices=list(YES_NO), allow_null=True, required=False)
    priority_answer = serializers.ChoiceField(
        choices=list(PRIORITY_ANSWERS), allow_null=True, required=False
    )
    priority_other = serializers.CharField(
        max_length=DebtInfo.PRIORITY_OTHER_MAX_LENGTH,
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    priority_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        allow_null=True,
        required=False,
    )
    nonpriority_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        allow_null=True,
        required=False,
    )
    past_due_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        allow_null=True,
        required=False,
    )
    community_debt = serializers.ChoiceField(choices=["yes"], allow_blank=True, required=False)
    date_incurred = serializers.CharField(
        max_length=DebtInfo.DATE_INCURRED_MAX_LENGTH,
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    lien = LienField(read_only=True)
    claim_status = ClaimStatusField(read_only=True)
    notice_parties = NoticePartiesField(read_only=True)

    class Meta:
        model = DebtInfo
        fields = [
            "id",
            "session",
            "data_source",
            "creditor_name",
            "debt_type",
            "account_number",
            "account_last_4",
            "amount_owed",
            "monthly_payment",
            "is_in_collections",
            "is_secured",
            "collateral_description",
            "notes",
            "created_at",
            "updated_at",
            "is_draft",
            "source_document_name",
            "street_address",
            "street_2",
            "city",
            "state",
            "zip_code",
            "outside_us",
            "secured_by",
            "home_payment_line",
            "collateral_who",
            "offset_answer",
            "priority_answer",
            "priority_other",
            "priority_amount",
            "nonpriority_amount",
            "past_due_amount",
            "community_debt",
            "date_incurred",
            "lien",
            "claim_status",
            "notice_parties",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "is_draft", "source_document_name"]
        extra_kwargs = {
            "account_number": {"write_only": True},  # Don't expose account numbers
        }

    def get_source_document_name(self, obj) -> str | None:
        if obj.source_document:
            return obj.source_document.original_filename
        return None

    def get_account_last_4(self, obj) -> str:
        return account_last_4(obj.account_number)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # A link to a row now on another session is dead: AssetViewSet can move a row after
        # the link was made (R6).
        if instance.secured_by_id and instance.secured_by.session_id != instance.session_id:
            data["secured_by"] = None
        return data


class NestedAssetInfoSerializer(AssetInfoSerializer):
    """An asset row inside a session save.

    The id is writable so a row the wizard loaded updates in place. AssetViewSet keeps
    the base serializer, so per-item create never accepts a client id.
    """

    id = serializers.IntegerField(required=False)
    line_required = False


class NestedDebtInfoSerializer(DebtInfoSerializer):
    """A debt row inside a session save. See NestedAssetInfoSerializer.

    The only writer of a link and of the JSON answers. A half-filled row saves: the name and
    type may be blank (the wizard sends a blank amount as 0).
    """

    id = serializers.IntegerField(required=False)
    creditor_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    debt_type = serializers.ChoiceField(
        choices=DebtInfo.DEBT_TYPE_CHOICES, required=False, allow_blank=True
    )
    secured_by = serializers.IntegerField(source="secured_by_id", required=False, allow_null=True)
    lien = LienField(required=False, allow_null=True)
    claim_status = ClaimStatusField(required=False, allow_null=True)
    notice_parties = NoticePartiesField(required=False, allow_null=True)


def _assign(row, data) -> None:
    """Set a row's answers. The one place a JSON column is encoded.

    Each key of the model's JSON_ANSWERS is stored with json.dumps (a None stays None), a
    notice_parties key goes through store_notice_parties, and any other key is set as it is.
    """
    json_answers = getattr(type(row), "JSON_ANSWERS", ())
    for attr, value in data.items():
        if attr == "notice_parties":
            row.store_notice_parties(value)
        elif attr in json_answers:
            setattr(row, attr, None if value is None else json.dumps(value))
        else:
            setattr(row, attr, value)


def _save_rows_by_id(session, model, rows, scoped=None) -> list:
    """Save a session's nested assets or debts, or its contracts or codebtors list, by id.

    A row whose id is one of this session's rows updates only the fields it sent, so
    what the browser never received (account numbers, the scanned-bill link)
    survives. Any other row is created on this session, so a client-sent
    ``session`` or another user's id never touches another session. Stored rows the
    payload left out are deleted. Returns the saved rows in payload order, each with its id.

    ``scoped`` maps a foreign-key attname to its model, such as ``{"secured_by_id":
    AssetInfo}``. A row that sends one of those keys with an id no row of that model has on
    this session stores None, so a foreign id is never kept or echoed; a key the row didn't
    send is left alone. The answers a model keeps as JSON go through ``_assign``.
    """
    existing = {row.pk: row for row in model.objects.filter(session=session)}
    live = {
        attname: set(related.objects.filter(session=session).values_list("pk", flat=True))
        for attname, related in (scoped or {}).items()
    }
    kept = set()
    saved = []
    for data in rows:
        data.pop("session", None)
        for attname, ids in live.items():
            if data.get(attname) is not None and data[attname] not in ids:
                data[attname] = None
        row = existing.get(data.pop("id", None))
        if row is None:
            row = model(session=session)
            _assign(row, data)
            row.save()
            saved.append(row)
            continue
        _assign(row, data)
        row.save()
        kept.add(row.pk)
        saved.append(row)
    model.objects.filter(pk__in=existing.keys() - kept).delete()
    return saved


class HouseholdMemberSerializer(serializers.Serializer):
    """One person on the household list (3e1 spec §4.2).

    Every answer may be missing, for Complete to name; only a value no answer can have is
    refused.
    """

    id = serializers.IntegerField(required=False, allow_null=True)
    relationship = serializers.ChoiceField(
        choices=list(RELATIONSHIP_WORDS), allow_null=True, required=False
    )
    age = serializers.IntegerField(min_value=0, max_value=MAX_AGE, allow_null=True, required=False)
    lives_with_you = serializers.BooleanField(allow_null=True, required=False)
    claimed_or_supported = serializers.BooleanField(allow_null=True, required=False)
    spouse_is_dependent = serializers.BooleanField(allow_null=True, required=False)


class HouseholdSerializer(serializers.ModelSerializer):
    """The filer's county and household list. A save sets only the keys it sends.

    family_size (122A-1 line 13) and fee_waiver_household_size (103B line 1) are read-only
    counts, null while the Income step leaves a gap (3e1 spec §4.4).
    """

    county = serializers.ChoiceField(choices=list(ILND_COUNTIES), allow_null=True, required=False)
    # write_only, because to_representation reads the stored JSON: ListField would iterate
    # its string, and the child would add spouse_is_dependent to every row.
    members = serializers.ListField(
        child=HouseholdMemberSerializer(),
        allow_null=True,
        required=False,
        max_length=MAX_MEMBERS,
        write_only=True,
    )
    family_size = serializers.SerializerMethodField()
    fee_waiver_household_size = serializers.SerializerMethodField()

    class Meta:
        model = Household
        fields = ["county", "members", "family_size", "fee_waiver_household_size"]

    def get_family_size(self, obj: Household) -> int | None:
        if income_step_gaps(obj.session):
            return None
        return count_family_size(obj.get_members())

    def get_fee_waiver_household_size(self, obj: Household) -> int | None:
        if income_step_gaps(obj.session):
            return None
        return count_fee_waiver_household(obj.get_members(), obj.session.income_info.marital_status)

    def validate_members(self, rows):
        if rows is None:
            return rows
        if sum(row.get("relationship") == "spouse" for row in rows) > 1:
            raise serializers.ValidationError("Only one person on the list can be your spouse.")
        if any(
            row.get("relationship") != "spouse" and row.get("spouse_is_dependent") is not None
            for row in rows
        ):
            raise serializers.ValidationError(
                "Only your spouse's row answers whether your spouse is a dependent."
            )
        return rows

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["members"] = instance.get_members()
        return data


def _save_household(session: IntakeSession, data: dict) -> Household:
    """Save a session's household, setting only the keys sent (3e1 spec §4.5).

    The session's cached household is pointed at the row saved, so the reply reads what this
    save stored rather than the copy select_related cached before it.
    """
    household, _ = Household.objects.get_or_create(session=session)
    if "county" in data:
        household.county = data["county"]
    if "members" in data:
        household.store_members(data["members"])
    household.save()
    session.household = household
    return household


def _save_income_row(model, session: IntakeSession, data: dict):
    """Save one person's income row, setting only the keys sent (3e2 spec §4.2).

    A list that isn't null replaces the legacy net rental figure, which is then cleared.
    """
    row = model.objects.filter(session=session).first() or model(session=session)
    for key, value in data.items():
        if key == "business_and_rental":
            row.store_entries(value)
            if value is not None:
                row.monthly_rental_income = None
        else:
            setattr(row, key, value)
    row.save()
    return row


def _save_income(session: IntakeSession, data: dict) -> IncomeInfo:
    """Save a session's income row; the session's cached relation points at the row saved."""
    session.income_info = _save_income_row(IncomeInfo, session, data)
    return session.income_info


def _save_spouse_income(session: IntakeSession, data: dict) -> SpouseIncome:
    """Save a session's spouse income row; the cached relation points at the row saved."""
    session.spouse_income = _save_income_row(SpouseIncome, session, data)
    return session.spouse_income


# The intake sections a session save can carry (spec §5.3).
_INTAKE_DATA = {
    "debtor_info",
    "income_info",
    "expense_info",
    "assets",
    "asset_lines",
    "claim_answers",
    "debts",
    "household",
    "spouse_income",
}


class AssetLinesField(serializers.DictField):
    """The filer's Yes and No for each Schedule A/B line, read from the session's record."""

    def get_attribute(self, instance):
        record = getattr(instance, "asset_lines", None)
        return record.get_answers() if record else {}


def _save_asset_lines(session: IntakeSession, data: dict) -> None:
    """Set each answer sent; a null clears it (3b spec §3.3)."""
    record, _ = AssetLineAnswers.objects.get_or_create(session=session)
    record.merge(data)
    record.save()
    session.asset_lines = record


class ClaimAnswersField(serializers.DictField):
    """The filer's own answers to Schedules D, E/F, G and H, read from the session's record."""

    def get_attribute(self, instance):
        record = getattr(instance, "claim_answers", None)
        return record.get_answers() if record else {}


def _save_claim_answers(session: IntakeSession, data: dict) -> None:
    """Set each answer sent; a null clears it (3c3 spec §7.1)."""
    record, _ = ClaimAnswers.objects.get_or_create(session=session)
    record.merge(data)
    record.save()
    session.claim_answers = record


_LINE_4_FIGURE = re.compile(r"[0-9]{1,9}(\.[0-9]{1,2})?")


def _is_line_4_figure(value) -> bool:
    """A plain figure: ASCII digits with at most two places, 12 characters at most. Decimal would
    also read "1_000" and full-width digits, which the browser's Number reads as NaN."""
    return isinstance(value, str) and _LINE_4_FIGURE.fullmatch(value) is not None


_CLAIM_YES_NO = (
    "contracts_answer",
    "codebtors_answer",
    "community_lived",
    "community_spouse_lived_with",
)


class IntakeSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for intake session with nested related data.

    Provides full session data including debtor info, income, expenses, assets, debts.
    """

    debtor_info = DebtorInfoSerializer(required=False, allow_null=True)
    income_info = IncomeInfoSerializer(required=False, allow_null=True)
    expense_info = ExpenseInfoSerializer(required=False, allow_null=True)
    assets = NestedAssetInfoSerializer(many=True, required=False)
    asset_lines = AssetLinesField(
        child=serializers.ChoiceField(choices=["yes", "no"], allow_null=True), required=False
    )
    claim_answers = ClaimAnswersField(required=False)
    debts = NestedDebtInfoSerializer(many=True, required=False)
    household = HouseholdSerializer(required=False, allow_null=True)
    spouse_income = SpouseIncomeSerializer(required=False, allow_null=True)

    district_name = serializers.CharField(source="district.name", read_only=True)
    income_window = serializers.SerializerMethodField()
    legacy_payments = serializers.SerializerMethodField()

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
            "asset_lines",
            "claim_answers",
            "debts",
            "household",
            "spouse_income",
            "income_window",
            "legacy_payments",
            "created_at",
            "completed_at",
        ]
        # Only the complete and update_step actions set status and current_step (DIG-151).
        read_only_fields = [
            "id",
            "user",
            "status",
            "current_step",
            "created_at",
            "completed_at",
            "district_name",
            "income_window",
            "legacy_payments",
        ]

    def validate_asset_lines(self, answers):
        unknown = [key for key in answers if key not in LINE_BY_KEY]
        if unknown:
            raise serializers.ValidationError(f"Not a line of Schedule A/B: {unknown[0]}.")
        return answers

    def validate_claim_answers(self, sent):
        """Check each key and its shape; a message names the key, never the value."""
        answers = {}
        for key, value in sent.items():
            if key not in ClaimAnswers.KEYS:
                raise serializers.ValidationError(f"Not a claim answer: {key}.")
            if value is not None:
                if key == "community_spouse_state" and isinstance(value, str):
                    value = value.strip().upper()
                if key == "no_debts":
                    ok = value is True
                elif key == "line_4_both_confirmed":
                    ok = _is_line_4_figure(value)
                elif key in _CLAIM_YES_NO:
                    ok = isinstance(value, str) and value in ("yes", "no")
                elif key == "community_spouse_outside_us":
                    ok = isinstance(value, bool)
                else:
                    ok = isinstance(value, str) and len(value) <= ClaimAnswers.TEXT_LIMITS[key]
                if not ok:
                    raise serializers.ValidationError(f"Check the answer for {key}.")
            answers[key] = value
        return answers

    def get_income_window(self, obj) -> dict:
        """The six full months before today, which the Income step's figures cover."""
        start, end = income_window(fill_date())
        return {"start": start.isoformat(), "end": end.isoformat()}

    def get_legacy_payments(self, obj) -> dict:
        """The car and other-property payments typed before they moved to the links (3c4 R6)."""
        return legacy_payments(obj)

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
        household_data = validated_data.pop("household", None)
        spouse_data = validated_data.pop("spouse_income", None)
        asset_lines_data = validated_data.pop("asset_lines", None)
        claim_answers_data = validated_data.pop("claim_answers", None)

        # Create session
        session = IntakeSession.objects.create(**validated_data)

        # Create related objects
        if debtor_data:
            DebtorInfo.objects.create(session=session, **debtor_data)

        if income_data:
            _save_income(session, income_data)

        if expense_data:
            ExpenseInfo.objects.create(session=session, **expense_data)

        if household_data:
            _save_household(session, household_data)

        if spouse_data:
            _save_spouse_income(session, spouse_data)

        if asset_lines_data is not None:
            _save_asset_lines(session, asset_lines_data)

        if claim_answers_data is not None:
            _save_claim_answers(session, claim_answers_data)

        # Create assets
        for asset_data in assets_data:
            AssetInfo.objects.create(session=session, **asset_data)

        # Create debts, after the assets so a link is checked against them
        _save_rows_by_id(session, DebtInfo, debts_data, scoped={"secured_by_id": AssetInfo})

        return session

    def update(self, instance, validated_data):
        """
        Update intake session with nested related data.

        Updates or creates debtor_info, income_info, expense_info, household and spouse_income.
        Saves assets/debts by id (see _save_rows_by_id).
        A household save sets only the keys sent (see _save_household).
        Saving any of them reopens a completed intake. The session is pointed at the income and
        spouse rows saved, so the reply reads what this save stored rather than the copies
        select_related cached before it.
        """
        if _INTAKE_DATA.intersection(validated_data):
            instance.reopen()

        debtor_data = validated_data.pop("debtor_info", None)
        income_data = validated_data.pop("income_info", None)
        expense_data = validated_data.pop("expense_info", None)
        assets_data = validated_data.pop("assets", None)
        debts_data = validated_data.pop("debts", None)
        household_data = validated_data.pop("household", None)
        spouse_data = validated_data.pop("spouse_income", None)
        asset_lines_data = validated_data.pop("asset_lines", None)
        claim_answers_data = validated_data.pop("claim_answers", None)

        # Update session fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or create nested objects
        if debtor_data:
            DebtorInfo.objects.update_or_create(session=instance, defaults=debtor_data)

        if income_data:
            _save_income(instance, income_data)

        # An empty body still creates the record with its $0 defaults, so the filer can
        # complete (DIG-153). The wizard sends all 13 amounts, a blank box as 0.
        if expense_data is not None:
            instance.expense_info, _ = ExpenseInfo.objects.update_or_create(
                session=instance, defaults=expense_data
            )

        if household_data:
            _save_household(instance, household_data)

        if spouse_data:
            _save_spouse_income(instance, spouse_data)

        if asset_lines_data is not None:
            _save_asset_lines(instance, asset_lines_data)

        if claim_answers_data is not None:
            _save_claim_answers(instance, claim_answers_data)

        # The response lists a sent list in sent order, so the wizard can pair each row it
        # sent with its id (DIG-273). Every other read sorts as to_representation says.
        instance.sent_rows = {}
        if assets_data is not None:
            instance.sent_rows["assets"] = _save_rows_by_id(instance, AssetInfo, assets_data)

        if debts_data is not None:
            instance.sent_rows["debts"] = _save_rows_by_id(
                instance, DebtInfo, debts_data, scoped={"secured_by_id": AssetInfo}
            )

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Neither table has a Meta.ordering (each sort key is ciphertext): assets read by id, and
        # debts by creditor name, then id, as Schedules D and E/F list them (3c spec §6.2).
        data["assets"] = sorted(data["assets"], key=lambda row: row["id"])
        data["debts"] = self.fields["debts"].to_representation(
            ordered_debts(instance.debts.select_related("secured_by"))
        )
        for name, rows in getattr(instance, "sent_rows", {}).items():
            data[name] = self.fields[name].to_representation(rows)
        return data


class FilingFeeSerializer(serializers.Serializer):
    """The filing-fee page's answers (3f spec §6.5). A PUT sets only the keys it sends.
    DRF drops an unknown key silently, so validate() refuses it by name: a page that sent
    an answer under the wrong name gets a 400 instead of losing it."""

    payment_choice = serializers.ChoiceField(choices=FilingFee.PAYMENT_CHOICES, required=False)
    income_change_answer = serializers.ChoiceField(choices=YES_NO, allow_null=True, required=False)
    others_covered_answer = serializers.ChoiceField(choices=YES_NO, allow_null=True, required=False)
    expense_change_answer = serializers.ChoiceField(choices=YES_NO, allow_null=True, required=False)
    income_change_explanation = serializers.CharField(
        max_length=FilingFee.TEXT_LIMITS["income_change_explanation"],
        allow_blank=True,
        required=False,
    )
    installments_explanation = serializers.CharField(
        max_length=FilingFee.TEXT_LIMITS["installments_explanation"],
        allow_blank=True,
        required=False,
    )
    others_covered_who = serializers.CharField(
        max_length=FilingFee.TEXT_LIMITS["others_covered_who"], allow_blank=True, required=False
    )
    expense_change_explanation = serializers.CharField(
        max_length=FilingFee.TEXT_LIMITS["expense_change_explanation"],
        allow_blank=True,
        required=False,
    )

    def validate(self, attrs):
        unknown = sorted(set(self.initial_data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError(
                {name: ["This is not one of the filing-fee answers."] for name in unknown}
            )
        return attrs


class ExemptionClaimSerializer(serializers.Serializer):
    """One claim on Schedule C's page (3g1 spec §5.3). Every answer may be missing, for the
    page's gaps to name; only a value no answer can have is refused. The catalog's law keys
    come in through the context (`law_keys`), so a law not on the list in force is a 400."""

    id = serializers.IntegerField(required=False, allow_null=True)
    asset = serializers.IntegerField(required=False, allow_null=True)
    law = serializers.CharField(max_length=40, required=False, allow_null=True)
    other_law = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
    amount_kind = serializers.ChoiceField(
        choices=ExemptionClaim.AMOUNT_KINDS, required=False, allow_null=True
    )
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True
    )
    short_description = serializers.CharField(
        max_length=60, required=False, allow_null=True, allow_blank=True
    )

    def to_internal_value(self, data):
        # A ListField child has no initial_data, so validate() can't see an unknown key.
        if isinstance(data, dict):
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise serializers.ValidationError(
                    {name: ["This is not one of a claim's answers."] for name in unknown}
                )
        return super().to_internal_value(data)

    def validate(self, attrs):
        law = attrs.get("law")
        other_law = attrs.get("other_law") or ""
        errors = {}
        if law is not None and other_law.strip():
            errors["other_law"] = ["Choose a law or type another law, not both."]
        if law is not None and law not in self.context.get("law_keys", ()):
            errors["law"] = ["This law is not on the list of laws."]
        if attrs.get("amount_kind") == "fair_market_value" and attrs.get("amount") is not None:
            errors["amount"] = ["A claim of the full fair market value takes no dollar amount."]
        if other_law.strip() and not fits_law(other_law):
            errors["other_law"] = ["This law doesn't fit in its box on Schedule C."]
        short = attrs.get("short_description") or ""
        if short.strip() and not fits_description(short):
            errors["short_description"] = ["This description doesn't fit in its box on Schedule C."]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class ExemptionsSerializer(serializers.Serializer):
    """Schedule C's page answers (3g1 spec §5.3). A PUT sets only the keys it sends; DRF drops
    an unknown key silently, so validate() refuses it by name."""

    line_1 = serializers.ChoiceField(
        choices=ExemptionAnswers.LINE_1_ANSWERS, required=False, allow_null=True
    )
    line_3 = serializers.ChoiceField(choices=["yes", "no"], required=False, allow_null=True)
    line_3_1 = serializers.ChoiceField(choices=["yes", "no"], required=False, allow_null=True)
    no_claims = serializers.BooleanField(required=False)
    claims = serializers.ListField(child=ExemptionClaimSerializer(), required=False, max_length=100)

    def validate(self, attrs):
        unknown = sorted(set(self.initial_data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError(
                {name: ["This is not one of the exemptions answers."] for name in unknown}
            )
        if attrs.get("no_claims") and attrs.get("claims"):
            raise serializers.ValidationError(
                {"no_claims": ["You can't be claiming no property and also claim property."]}
            )
        return attrs


class SOFAPriorIncomeSerializer(serializers.ModelSerializer):
    """Prior income row for SOFA Form 107 Part 1."""

    gross_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))

    class Meta:
        model = SOFAPriorIncome
        fields = ["id", "year", "source", "gross_amount"]


class SOFACreditorPaymentSerializer(serializers.ModelSerializer):
    """Creditor payment row for SOFA Form 107 Part 2."""

    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))

    class Meta:
        model = SOFACreditorPayment
        fields = ["id", "creditor_name", "total_paid", "dates_of_payments"]


class SOFAReportSerializer(serializers.ModelSerializer):
    """SOFA report with nested prior income and creditor payment rows."""

    prior_income = SOFAPriorIncomeSerializer(many=True, required=False)
    creditor_payments = SOFACreditorPaymentSerializer(many=True, required=False)

    class Meta:
        model = SOFAReport
        fields = [
            "id",
            "session",
            "has_prior_income",
            "has_creditor_payments",
            "has_business",
            "prior_income",
            "creditor_payments",
        ]
        read_only_fields = ["id", "session"]

    def create(self, validated_data):
        prior_income_data = validated_data.pop("prior_income", [])
        creditor_payment_data = validated_data.pop("creditor_payments", [])
        report = SOFAReport.objects.create(**validated_data)
        for item in prior_income_data:
            SOFAPriorIncome.objects.create(report=report, **item)
        for item in creditor_payment_data:
            SOFACreditorPayment.objects.create(report=report, **item)
        return report

    def update(self, instance, validated_data):
        prior_income_data = validated_data.pop("prior_income", None)
        creditor_payment_data = validated_data.pop("creditor_payments", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if prior_income_data is not None:
            instance.prior_income.all().delete()
            for item in prior_income_data:
                SOFAPriorIncome.objects.create(report=instance, **item)

        if creditor_payment_data is not None:
            instance.creditor_payments.all().delete()
            for item in creditor_payment_data:
                SOFACreditorPayment.objects.create(report=instance, **item)

        return instance


class BulkAnswerItemSerializer(serializers.Serializer):
    form_type = serializers.CharField(max_length=50)
    binding = serializers.CharField(max_length=200)
    value = serializers.CharField(allow_blank=True)

    def _coerce_field_value(self, field, value):
        if value == "" and field.null:
            return None
        return field.to_python(value)

    def validate(self, data):
        binding = data.get("binding", "")
        value = data.get("value", "")

        if not (binding.startswith("answer:") or binding.startswith("sofa.")):
            raise serializers.ValidationError(
                {"binding": "Invalid binding prefix. Must start with 'answer:' or 'sofa.'"}
            )

        if binding.startswith("sofa."):
            field_key = binding[5:]
            if "[" in field_key and "]." in field_key:
                match = re.match(r"([a-z_]+)\[(\d+)\]\.(.*)", field_key)
                if match:
                    coll_name, idx_str, attr = match.groups()
                    idx = int(idx_str)
                    if idx >= 50:
                        raise serializers.ValidationError(
                            {"binding": f"Index {idx} exceeds maximum allowed array size of 50."}
                        )
                    try:
                        related_field = SOFAReport._meta.get_field(coll_name)
                        related_model = related_field.related_model
                        if related_model is None:
                            raise serializers.ValidationError(
                                {
                                    "binding": f"Invalid array binding. Collection {coll_name} does not exist."
                                }
                            )
                        field = related_model._meta.get_field(attr)
                        data["value"] = self._coerce_field_value(field, value)
                        data["parsed_array_binding"] = (coll_name, idx, attr)
                    except FieldDoesNotExist:
                        raise serializers.ValidationError(
                            {"binding": f"Unknown related field: {coll_name} or {attr}"}
                        ) from None
                    except Exception as e:
                        raise serializers.ValidationError(
                            {"value": f"Invalid value for {coll_name}[].{attr}: {str(e)}"}
                        ) from e
                else:
                    raise serializers.ValidationError({"binding": "Invalid array binding format"})
            else:
                try:
                    field = SOFAReport._meta.get_field(field_key)
                    data["value"] = self._coerce_field_value(field, value)
                except FieldDoesNotExist:
                    raise serializers.ValidationError(
                        {"binding": f"Unknown SOFAReport field: {field_key}"}
                    ) from None
                except Exception as e:
                    raise serializers.ValidationError(
                        {"value": f"Invalid value for {field_key}: {str(e)}"}
                    ) from e

        return data


class BulkAnswerPayloadSerializer(serializers.Serializer):
    answers = BulkAnswerItemSerializer(many=True)


def _live_foreign_key(instance, name, model):
    """The row a contract's link names, or None when it is dead (R6).

    Dead means null, or a row now on another session (AssetViewSet and DebtViewSet can move a
    row after the link was made). The stored column is not rewritten.
    """
    pk = getattr(instance, f"{name}_id")
    if pk is not None and model.objects.filter(pk=pk, session_id=instance.session_id).exists():
        return pk
    return None


class CodebtorLinksField(_StoredJSONField):
    """A list of {kind, id}, kind in Codebtor.LINK_KINDS. Live entries are kept on save."""

    def to_internal_value(self, data):
        entries = serializers.ListField(child=serializers.DictField()).run_validation(data)
        links = []
        for entry in entries:
            if set(entry) != {"kind", "id"}:
                raise serializers.ValidationError("Each link has a kind and an id.")
            kind = serializers.ChoiceField(choices=list(Codebtor.LINK_KINDS)).run_validation(
                entry["kind"]
            )
            link_id = serializers.IntegerField().run_validation(entry["id"])
            links.append({"kind": kind, "id": link_id})
        return links


class ExecutoryContractSerializer(AddressAnswersMixin, serializers.ModelSerializer):
    """The single-contract POST and the GET the wizard reads.

    The links are read-only here (R6): ExecutoryContractRowSerializer is their only writer.
    """

    # The old columns' auto-mapped kwargs, declared because the columns are encrypted now; the
    # width that bounds an undone migration lives here.
    counterparty_name = serializers.CharField(max_length=255)
    contract_type = serializers.ChoiceField(choices=ExecutoryContract.CONTRACT_TYPE_CHOICES)
    description = serializers.CharField(required=False, allow_blank=True)
    lease_kind = serializers.ChoiceField(
        choices=list(ExecutoryContract.LEASE_KINDS), allow_null=True, required=False
    )
    monthly_payment = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal(0), required=False, allow_null=True
    )
    owes_now = serializers.ChoiceField(choices=list(YES_NO), allow_null=True, required=False)
    vehicle_asset = serializers.IntegerField(source="vehicle_asset_id", read_only=True)
    owed_debt = serializers.IntegerField(source="owed_debt_id", read_only=True)

    class Meta:
        model = ExecutoryContract
        fields = [
            "id",
            "counterparty_name",
            "contract_type",
            "description",
            "street_address",
            "street_2",
            "city",
            "state",
            "zip_code",
            "outside_us",
            "lease_kind",
            "monthly_payment",
            "owes_now",
            "vehicle_asset",
            "owed_debt",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["vehicle_asset"] = _live_foreign_key(instance, "vehicle_asset", AssetInfo)
        data["owed_debt"] = _live_foreign_key(instance, "owed_debt", DebtInfo)
        return data


class CodebtorSerializer(AddressAnswersMixin, serializers.ModelSerializer):
    """The single-codebtor POST and the GET the wizard reads. Its links are read-only (R6)."""

    name = serializers.CharField(max_length=255)
    relationship = serializers.ChoiceField(choices=Codebtor.RELATIONSHIP_CHOICES, required=False)
    links = CodebtorLinksField(read_only=True)

    class Meta:
        model = Codebtor
        fields = [
            "id",
            "name",
            "street_address",
            "street_2",
            "city",
            "state",
            "zip_code",
            "outside_us",
            "relationship",
            "links",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # A link to a debt or contract that is gone, or now on another session, is dropped.
        debts = set(
            DebtInfo.objects.filter(session_id=instance.session_id).values_list("pk", flat=True)
        )
        contracts = set(
            ExecutoryContract.objects.filter(session_id=instance.session_id).values_list(
                "pk", flat=True
            )
        )
        live = {"debt": debts, "contract": contracts}
        data["links"] = [link for link in data["links"] if link["id"] in live.get(link["kind"], ())]
        return data


class ExecutoryContractRowSerializer(ExecutoryContractSerializer):
    """A contract row in the Contracts step's list save.

    The id is writable so a row the wizard loaded updates in place. The single-contract
    POST keeps the base serializer, so it never accepts a client id. A half-filled row
    saves: the name and type may be blank, and the two links are writable.
    """

    id = serializers.IntegerField(required=False)
    counterparty_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    contract_type = serializers.ChoiceField(
        choices=ExecutoryContract.CONTRACT_TYPE_CHOICES, required=False, allow_blank=True
    )
    vehicle_asset = serializers.IntegerField(
        source="vehicle_asset_id", required=False, allow_null=True
    )
    owed_debt = serializers.IntegerField(source="owed_debt_id", required=False, allow_null=True)


class CodebtorRowSerializer(CodebtorSerializer):
    """A codebtor row in the Codebtors step's list save. See ExecutoryContractRowSerializer."""

    id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    relationship = serializers.ChoiceField(
        choices=Codebtor.RELATIONSHIP_CHOICES, required=False, allow_blank=True
    )
    links = CodebtorLinksField(required=False)

    def validate(self, attrs):
        """Keep the links that name one of this session's debts or contracts, once each."""
        if "links" not in attrs:
            return attrs
        session = self.context["session"]
        live = {
            "debt": set(session.debts.values_list("pk", flat=True)),
            "contract": set(session.executory_contracts.values_list("pk", flat=True)),
        }
        kept = []
        for link in attrs["links"]:
            if link["id"] in live[link["kind"]] and link not in kept:
                kept.append(link)
        attrs["links"] = kept
        return attrs
