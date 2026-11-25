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
from apps.forms.registry import SSN_PATTERN
from apps.forms.services.answer_records import is_itin, is_nine_digits
from apps.forms.services.exemption_items import fits_description, fits_law
from apps.forms.services.means_fit import LIST_ANSWERS, merge_row_errors, shown_box_refusals

from .asset_lines import LINE_BY_KEY, PROPERTY_KINDS, WHO
from .claims import (
    PRIORITY_ANSWERS,
    account_last_4,
    is_form_108_lease,
    legacy_payments,
    ordered_debts,
)
from .exemptions import exempt_states
from .household import (
    MAX_AGE,
    MAX_MEMBERS,
    RELATIONSHIP_WORDS,
    count_family_size,
    count_fee_waiver_household,
)
from .income import ENTRY_KINDS, MAX_ENTRIES
from .means_test import (
    MAX_ROWS,
    MEANS_EXPLANATION_TOO_LONG,
    MEANS_POLISH_BLANK,
    MEANS_ROW_LISTED_TWICE,
    NOT_A_MEANS_ANSWER,
    PROPERTY_CHOICES,
)
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
    IntentionAnswers,
    PetitionAnswers,
    ScheduleIAnswers,
    SOFACreditorPayment,
    SOFAPriorIncome,
    SOFAReport,
    SpouseIncome,
)

User = get_user_model()


class DebtorInfoSerializer(serializers.ModelSerializer):
    """Serializer for debtor personal information (PII encrypted)."""

    # The SSN never comes back: the read says only whether the stored one is what Form 101 and
    # Complete take (`_needs_ssn`'s own pattern), so a loaded step 1 needn't ask for it again.
    ssn_saved = serializers.SerializerMethodField()

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
            "ssn_saved",
        ]
        extra_kwargs = {
            "ssn": {"write_only": True},  # Never return SSN in API responses
        }

    def get_ssn_saved(self, instance) -> bool:
        return bool(SSN_PATTERN.fullmatch((instance.ssn or "").strip()))

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
    electricity_heat_gas = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    water_sewer_garbage = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    phone_internet_cable = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    life_insurance = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    health_insurance = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=0
    )
    # Retired (3c4): a 0 sent on its own is Remove, and any other figure is dropped in validate.
    vehicle_payment = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), write_only=True, required=False
    )
    other_property_mortgages = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), write_only=True, required=False
    )
    utilities_specify = serializers.CharField(max_length=100, allow_blank=True, required=False)
    insurance_specify = serializers.CharField(max_length=100, allow_blank=True, required=False)
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
    "petition_answers",
    "schedule_i_answers",
    "intention_answers",
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


class PetitionAnswersField(serializers.DictField):
    """The filer's answers to Form 101's questions, read from the session's record.

    The ITIN and the other Social Security number never come back, as `DebtorInfo.ssn` never
    does: the read says only whether each is saved, so an echoed read can't overwrite them.
    """

    def get_attribute(self, instance):
        record = getattr(instance, "petition_answers", None)
        answers = record.get_answers() if record else {}
        # "Saved" means it will print and no detail is listed: the same predicates (PF2-5).
        saved = {
            "itin_saved": is_itin(answers.get("itin")),
            "other_ssn_saved": is_nine_digits(answers.get("other_ssn")),
        }
        return {
            **{k: v for k, v in answers.items() if k not in PetitionAnswers.SECRET_KEYS},
            **saved,
        }


def _save_petition_answers(session: IntakeSession, data: dict) -> None:
    """Set each answer sent; a null removes it (step 4b spec §7.1)."""
    record, _ = PetitionAnswers.objects.get_or_create(session=session)
    record.merge(data)
    record.save()
    session.petition_answers = record


def _petition_text_ok(value) -> bool:
    if not isinstance(value, str) or len(value) > PetitionAnswers.TEXT_CEILING:
        return False
    # Half of a surrogate pair can't be written as UTF-8, so every later read of the session
    # would fail to render: refuse it before anything is stored, as CharField does.
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _petition_value_ok(key: str, value) -> bool:
    if key in PetitionAnswers.YES_NO_KEYS:
        return isinstance(value, str) and value in ("yes", "no")
    if key in PetitionAnswers.CHOICE_KEYS:
        return isinstance(value, str) and value in PetitionAnswers.CHOICE_KEYS[key]
    if key in PetitionAnswers.SECRET_KEYS and value == "saved":
        return False
    return _petition_text_ok(value)


def _petition_rows_ok(key: str, rows) -> bool:
    if not isinstance(rows, list):
        return False
    cap = PetitionAnswers.LIST_CAPS.get(key, PetitionAnswers.ROW_CEILING)
    if len(rows) > cap:
        return False
    allowed = PetitionAnswers.LIST_KEYS[key]
    for row in rows:
        if not isinstance(row, dict):
            return False
        for cell_key, cell in row.items():
            if cell_key == "_key":
                continue
            if cell_key not in allowed:
                return False
            if cell is not None and not _petition_text_ok(cell):
                return False
    return True


class ScheduleIAnswersField(serializers.DictField):
    """The filer's answers to Schedule I lines 1, 11 and 13 and Schedule J line 24, read from the
    session's record, with the date of the last change (read-only)."""

    def get_attribute(self, instance):
        record = getattr(instance, "schedule_i_answers", None)
        if record is None:
            return {"answered_on": None}
        return {**record.get_answers(), "answered_on": record.answered_on}


class IntentionAnswersField(serializers.DictField):
    """The filer's Form 108 choices, read from the session's record, with the date of the last
    change (read-only)."""

    def get_attribute(self, instance):
        record = getattr(instance, "intention_answers", None)
        if record is None:
            return {"answered_on": None}
        return {**record.get_answers(), "answered_on": record.answered_on}


def _save_schedule_i_answers(session: IntakeSession, data: dict) -> None:
    """Set each answer sent; a null removes it (4c)."""
    record, _ = ScheduleIAnswers.objects.get_or_create(session=session)
    record.merge(data)
    record.save()
    session.schedule_i_answers = record


def _save_intention_answers(session: IntakeSession, data: dict) -> None:
    """Replace each top key sent, then keep only the ids still in scope (R-PRUNE): the confirmed
    secured debts and the leases Form 108 asks about. Called after the save's debts are written
    (R-SAVE-ORDER). confirmed() is a fresh query, so it sees those debts, never the prefetch; a
    session save never writes contracts, so their prefetch holds."""
    secured_ids = {d.pk for d in session.debts.confirmed() if d.is_secured}
    lease_ids = {c.pk for c in session.executory_contracts.all() if is_form_108_lease(c)}
    record, _ = IntentionAnswers.objects.get_or_create(session=session)
    record.merge(data, secured_ids, lease_ids)
    record.save()
    session.intention_answers = record


# An id is a debt's or a contract's pk: digits with no leading zero, below 10 ** 10 (4e-R17).
_INTENTION_ID = re.compile(r"[1-9][0-9]{0,9}")
_INTENTION_ENTRY_KEYS = {"secured": ("intention", "explain"), "leases": ("assumed",)}


def _intention_value_ok(cell: str, value) -> bool:
    if not isinstance(value, str):
        return False
    if cell == "intention":
        return value in IntentionAnswers.INTENTIONS
    if cell == "assumed":
        return value in IntentionAnswers.ASSUMED
    if len(value) > IntentionAnswers.TEXT_CEILING:
        return False
    # Half of a surrogate pair can't be written as UTF-8, so every later read of the session
    # would fail to render: refuse it before anything is stored, as for Form 101's texts.
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _intention_entries_ok(key: str, entries) -> bool:
    """A top key's object: at most ROW_CEILING ids, each an object of its own cells."""
    if not isinstance(entries, dict) or len(entries) > IntentionAnswers.ROW_CEILING:
        return False
    allowed = _INTENTION_ENTRY_KEYS[key]
    for row_id, entry in entries.items():
        if _INTENTION_ID.fullmatch(row_id) is None or not isinstance(entry, dict):
            return False
        for cell, value in entry.items():
            if cell not in allowed or not _intention_value_ok(cell, value):
                return False
    return True


# ASCII digits only: Python's \d also takes other scripts' digits, which no form prints.
_SCHEDULE_I_AMOUNT = re.compile(r"[0-9]+(\.[0-9]{1,2})?")


def _schedule_i_value_ok(key: str, value) -> bool:
    if not isinstance(value, str):
        return False
    if key in ScheduleIAnswers.CHOICE_KEYS:
        return value in ScheduleIAnswers.CHOICE_KEYS[key]
    if key in ScheduleIAnswers.YES_NO_KEYS:
        return value in ("yes", "no")
    if key in ScheduleIAnswers.AMOUNT_KEYS:
        # What DecimalField(12, 2) holds: below 10 ** 10, by value, so leading zeros pass.
        return _SCHEDULE_I_AMOUNT.fullmatch(value) is not None and Decimal(value) < 10**10
    # A text may be as long as its box's measured cap, which the browser's box allows: line 24's
    # is above the flat ceiling.
    if len(value) > max(ScheduleIAnswers.TEXT_CEILING, ScheduleIAnswers.TEXT_LIMITS.get(key, 0)):
        return False
    # Half of a surrogate pair can't be written as UTF-8, so every later read of the session
    # would fail to render: refuse it before anything is stored, as for Form 101's texts.
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


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
    petition_answers = PetitionAnswersField(required=False)
    schedule_i_answers = ScheduleIAnswersField(required=False)
    intention_answers = IntentionAnswersField(required=False)
    debts = NestedDebtInfoSerializer(many=True, required=False)
    household = HouseholdSerializer(required=False, allow_null=True)
    spouse_income = SpouseIncomeSerializer(required=False, allow_null=True)

    district_name = serializers.CharField(source="district.name", read_only=True)
    income_window = serializers.SerializerMethodField()
    legacy_payments = serializers.SerializerMethodField()
    paystub_employer_name = serializers.SerializerMethodField()
    intention_exempt = serializers.SerializerMethodField()

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
            "petition_answers",
            "schedule_i_answers",
            "intention_answers",
            "debts",
            "household",
            "spouse_income",
            "income_window",
            "legacy_payments",
            "paystub_employer_name",
            "intention_exempt",
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
            "paystub_employer_name",
            "intention_exempt",
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

    PETITION_READ_ONLY = ("answered_on", "itin_saved", "other_ssn_saved")

    def validate_petition_answers(self, sent):
        """Check each key and its shape; a message names the key, never the value."""
        answers = {}
        for key, value in sent.items():
            if key in self.PETITION_READ_ONLY:
                continue  # echoed by a read or set by the server; never written from a body
            if key not in PetitionAnswers.KEYS:
                raise serializers.ValidationError(f"Not a petition answer: {key}.")
            if value is not None:
                if key in PetitionAnswers.LIST_KEYS:
                    ok = _petition_rows_ok(key, value)
                    if ok:
                        value = [{k: v for k, v in row.items() if k != "_key"} for row in value]
                else:
                    ok = _petition_value_ok(key, value)
                if not ok:
                    raise serializers.ValidationError(f"Check the answer for {key}.")
            answers[key] = value
        return answers

    def validate_schedule_i_answers(self, sent):
        """Check each key and its shape; a message names the key, never the value. A text over
        its cap is stored: the gap list names it (B47)."""
        answers = {}
        for key, value in sent.items():
            if key == "answered_on":
                continue  # echoed by a read or set by the server; never written from a body
            if key not in ScheduleIAnswers.KEYS:
                raise serializers.ValidationError(f"Not a Schedule I answer: {key}.")
            if value is not None and not _schedule_i_value_ok(key, value):
                raise serializers.ValidationError(f"Check the answer for {key}.")
            answers[key] = value
        return answers

    def validate_intention_answers(self, sent):
        """Check every key before any write, as MeansTestAnswers.merge does. A message names the
        top key, never an id or a value (Ruling F12)."""
        answers = {}
        for key, value in sent.items():
            if key == "answered_on":
                continue  # echoed by a read or set by the server; never written from a body
            if key not in IntentionAnswers.KEYS:
                raise serializers.ValidationError(f"Not an intention answer: {key}.")
            if value is not None and not _intention_entries_ok(key, value):
                raise serializers.ValidationError(f"Check the answer for {key}.")
            answers[key] = value
        return answers

    def get_intention_exempt(self, obj) -> dict:
        """Each secured debt's Form 108 exempt state, by id (R-EXEMPT, 4e-R6)."""
        return {str(pk): state for pk, state in exempt_states(obj).items()}

    def get_paystub_employer_name(self, obj) -> str:
        """The employer name read from a pay stub, shown beside the box and never saved into it
        (4c-R10); "" without one. Read from the prefetched rows, in Python."""
        for aggregate in obj.ingested_aggregates.all():
            if aggregate.ingest_key == "paystub.employer_name":
                return aggregate.value.strip()
        return ""

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
        petition_answers_data = validated_data.pop("petition_answers", None)
        schedule_i_answers_data = validated_data.pop("schedule_i_answers", None)
        intention_answers_data = validated_data.pop("intention_answers", None)

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

        if petition_answers_data:
            _save_petition_answers(session, petition_answers_data)

        if schedule_i_answers_data:
            _save_schedule_i_answers(session, schedule_i_answers_data)

        # Create assets
        for asset_data in assets_data:
            AssetInfo.objects.create(session=session, **asset_data)

        # Create debts, after the assets so a link is checked against them
        _save_rows_by_id(session, DebtInfo, debts_data, scoped={"secured_by_id": AssetInfo})

        # After the debts, so the prune sees the ones this save made (R-SAVE-ORDER)
        if intention_answers_data:
            _save_intention_answers(session, intention_answers_data)

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
        if validated_data.get("petition_answers") == {}:
            # Only echoed read-only keys, or nothing: no answer to save, so nothing reopens.
            del validated_data["petition_answers"]
        if validated_data.get("schedule_i_answers") == {}:
            # Only an echoed answered_on, or nothing: no answer to save, so nothing reopens.
            del validated_data["schedule_i_answers"]
        if validated_data.get("intention_answers") == {}:
            # Only an echoed answered_on, or nothing: no answer to save, so nothing reopens.
            del validated_data["intention_answers"]
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
        petition_answers_data = validated_data.pop("petition_answers", None)
        schedule_i_answers_data = validated_data.pop("schedule_i_answers", None)
        intention_answers_data = validated_data.pop("intention_answers", None)

        # Update session fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or create nested objects
        if debtor_data:
            # The reply reads the row just saved, not the copy loaded with the session
            instance.debtor_info, _ = DebtorInfo.objects.update_or_create(
                session=instance, defaults=debtor_data
            )

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

        if petition_answers_data is not None:
            _save_petition_answers(instance, petition_answers_data)

        if schedule_i_answers_data is not None:
            _save_schedule_i_answers(instance, schedule_i_answers_data)

        # The response lists a sent list in sent order, so the wizard can pair each row it
        # sent with its id (DIG-273). Every other read sorts as to_representation says.
        instance.sent_rows = {}
        if assets_data is not None:
            instance.sent_rows["assets"] = _save_rows_by_id(instance, AssetInfo, assets_data)

        if debts_data is not None:
            instance.sent_rows["debts"] = _save_rows_by_id(
                instance, DebtInfo, debts_data, scoped={"secured_by_id": AssetInfo}
            )

        # Last, after the debts: the prune must see the debts this save wrote, so a debt made
        # secured keeps its choice and a debt deleted keeps none (R-SAVE-ORDER).
        if intention_answers_data is not None:
            _save_intention_answers(instance, intention_answers_data)

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


LAW_AND_OTHER_LAW_REFUSAL = "Choose a law or type another law, not both."
FAIR_MARKET_VALUE_AMOUNT_REFUSAL = "A claim of the full fair market value takes no dollar amount."
NO_CLAIMS_AND_CLAIMS_REFUSAL = "You can't be claiming no property and also claim property."


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
            errors["other_law"] = [LAW_AND_OTHER_LAW_REFUSAL]
        if law is not None and law not in self.context.get("law_keys", ()):
            errors["law"] = ["This law is not on the list of laws."]
        if attrs.get("amount_kind") == "fair_market_value" and attrs.get("amount") is not None:
            errors["amount"] = [FAIR_MARKET_VALUE_AMOUNT_REFUSAL]
        if other_law.strip() and not fits_law(other_law):
            errors["other_law"] = ["This law doesn't fit in its box on Schedule C."]
        short = attrs.get("short_description") or ""
        if short.strip() and not fits_description(short):
            errors["short_description"] = ["This description doesn't fit in its box on Schedule C."]
        if "short_description" in attrs and not short.strip():
            # Spec 5.2 / P8: null unless the item's name doesn't fit.
            attrs["short_description"] = None
        if attrs.get("amount") is not None and attrs["amount"] == 0:
            # "-0" passes min_value=0: store the zero without its sign, so no form prints -0.00.
            attrs["amount"] = Decimal("0.00")
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
            raise serializers.ValidationError({"no_claims": [NO_CLAIMS_AND_CLAIMS_REFUSAL]})
        return attrs


NOT_A_MEANS_CHOICE = "This is not one of the answers to this question."
NOT_A_PAYMENTS_LEFT = "Payments left is a whole number from 0 to 59, or 60 or more."
NOT_A_VEHICLE = "This doesn't name a vehicle."
NOT_A_ROW = "This doesn't name a row of this list."
OWN_VEHICLE_ON_AMOUNTS_OWED = (
    "A loan on your Amounts Owed step can't be secured by your own vehicle."
)
DEBT_SENT_TWICE = "Each debt can be sent only once in a save."
ROW_NEEDS_ITS_ID = "Each debt's answers need the debt's id."
DIFFERENT_VEHICLES = "Vehicle 1 and Vehicle 2 must be different vehicles."
NOT_IN_THIS_SAVE = "This names a vehicle that isn't in this save."

SIXTY_OR_MORE = "60_or_more"
_ROW_REF = r"^(spouse|new)-[1-9][0-9]{0,9}$"
_VEHICLE_REF = r"^(asset|spouse|new)-[1-9][0-9]{0,9}$"
_FILER_VEHICLE_REF = r"asset-[1-9][0-9]{0,9}"
MAX_ID = 2147483647  # the largest id a database integer column holds


def _within_max_id(ref):
    return int(ref.rsplit("-", 1)[1]) <= MAX_ID


class _MeansAmount(serializers.DecimalField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        # "-0" passes min_value=0: store the zero without its sign, so no form prints -0.00.
        return Decimal("0.00") if value == 0 else value


class PaymentsLeftField(serializers.Field):
    """A whole number 0-59, or "60_or_more"; stored as that text, read back as an int or the text."""

    default_error_messages = {"invalid": NOT_A_PAYMENTS_LEFT}

    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail("invalid")
        if isinstance(data, int) and 0 <= data <= 59:
            return str(data)
        if data == SIXTY_OR_MORE:
            return SIXTY_OR_MORE
        self.fail("invalid")

    def to_representation(self, value):
        return value if value == SIXTY_OR_MORE else int(value)


class VehicleClaimsField(serializers.DictField):
    """The filer's vehicle claims by Schedule A/B reference, each yes, no or null."""

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        bad = {
            key: [NOT_A_VEHICLE]
            for key in value
            if not (re.fullmatch(_FILER_VEHICLE_REF, key) and _within_max_id(key))
        }
        if bad:
            raise serializers.ValidationError(bad)
        return value


def _means_choice():
    return serializers.ChoiceField(
        choices=YES_NO,
        required=False,
        allow_null=True,
        error_messages={"invalid_choice": NOT_A_MEANS_CHOICE},
    )


def _means_amount():
    return _MeansAmount(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )


def _means_words(max_length):
    return serializers.CharField(
        max_length=max_length, required=False, allow_null=True, allow_blank=True
    )


def _means_ref(pattern, message):
    def in_range(value):
        if re.fullmatch(pattern, value) and not _within_max_id(value):
            raise serializers.ValidationError(message)

    return serializers.RegexField(
        pattern,
        required=False,
        allow_null=True,
        error_messages={"invalid": message},
        validators=[in_range],
    )


class _MeansRow(serializers.Serializer):
    """A row of one of the page's lists; an unknown key is refused by name."""

    def to_internal_value(self, data):
        # A ListField child has no initial_data, so validate() can't see an unknown key.
        if isinstance(data, dict):
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise serializers.ValidationError({name: [NOT_A_MEANS_ANSWER] for name in unknown})
        return super().to_internal_value(data)


# A row's words are measured against the form's boxes in MeansTestSerializer.validate (or under
# the lock), and only while the answers show the box (F1); the rows check only their caps.
class Line3RowSerializer(_MeansRow):
    purpose = _means_words(200)
    amount = _means_amount()


class SpouseVehicleSerializer(_MeansRow):
    ref = _means_ref(_ROW_REF, NOT_A_ROW)
    description = _means_words(200)
    leased = _means_choice()
    claimed = _means_choice()


def _refuse_repeated_refs(rows):
    refs = [row["ref"] for row in rows or [] if row.get("ref")]
    if len(refs) != len(set(refs)):
        raise serializers.ValidationError([MEANS_ROW_LISTED_TWICE])


class _PerDebtAnswersSerializer(_MeansRow):
    payments_left = PaymentsLeftField(required=False, allow_null=True)
    payment_changes = _means_choice()
    total_60_months = _means_amount()
    taxes_or_insurance = _means_choice()
    necessary_for_support = _means_choice()
    cure = _means_amount()


class SpouseLoanSerializer(_PerDebtAnswersSerializer):
    ref = _means_ref(_ROW_REF, NOT_A_ROW)
    on_amounts_owed = _means_choice()
    debt = serializers.IntegerField(min_value=1, max_value=MAX_ID, required=False, allow_null=True)
    creditor = _means_words(200)
    secured_by = serializers.CharField(required=False, allow_null=True)
    property = _means_words(200)
    payment = _means_amount()

    def validate_secured_by(self, value):
        if value is None or value in PROPERTY_CHOICES:
            return value
        if not (re.fullmatch(_VEHICLE_REF, value) and _within_max_id(value)):
            raise serializers.ValidationError(NOT_A_VEHICLE)
        return value

    def validate(self, attrs):
        secured = attrs.get("secured_by")
        if attrs.get("on_amounts_owed") == "yes" and secured and secured.startswith("asset-"):
            raise serializers.ValidationError({"secured_by": [OWN_VEHICLE_ON_AMOUNTS_OWED]})
        return attrs


class DebtAnswersSerializer(_PerDebtAnswersSerializer):
    id = serializers.IntegerField(min_value=1, max_value=MAX_ID, required=False, allow_null=True)

    def to_internal_value(self, data):
        result = super().to_internal_value(data)
        # partial=True reaches a ListField's rows, so `required` can't enforce the id.
        if result.get("id") is None:
            raise serializers.ValidationError({"id": [ROW_NEEDS_ITS_ID]})
        return result


class CircumstanceSerializer(_MeansRow):
    happened = _means_words(450)
    change = _means_words(450)
    choices = _means_words(450)
    papers = _means_words(450)
    amount = _means_amount()
    explanation = serializers.CharField(
        max_length=2000, required=False, allow_null=True, allow_blank=True
    )
    original_explanation = serializers.CharField(
        max_length=2000, required=False, allow_null=True, allow_blank=True
    )

    def validate_explanation(self, value):
        if value is None or not value.strip():
            return None
        return value

    def validate_original_explanation(self, value):
        if value is None or not value.strip():
            return None
        return value


class MeansTestSerializer(serializers.Serializer):
    """The Form 122A-2 page's answers (3h2 spec §8.4), used with partial=True. Every shape and
    fit check that reads nothing stored; null clears an answer. DRF drops an unknown key
    silently, so validate() refuses it by name."""

    line_3_answer = _means_choice()
    line_3_rows = serializers.ListField(
        child=Line3RowSerializer(), required=False, allow_null=True, max_length=MAX_ROWS
    )
    spouse_vehicles_answer = _means_choice()
    spouse_vehicles = serializers.ListField(
        child=SpouseVehicleSerializer(), required=False, allow_null=True, max_length=MAX_ROWS
    )
    spouse_loans_answer = _means_choice()
    spouse_loans = serializers.ListField(
        child=SpouseLoanSerializer(), required=False, allow_null=True, max_length=MAX_ROWS
    )
    vehicle_claims = VehicleClaimsField(
        child=serializers.ChoiceField(
            choices=YES_NO, allow_null=True, error_messages={"invalid_choice": NOT_A_MEANS_CHOICE}
        ),
        required=False,
        allow_null=True,
    )
    vehicle_choice = serializers.ListField(
        child=_means_ref(_VEHICLE_REF, NOT_A_VEHICLE),
        required=False,
        allow_null=True,
        min_length=2,
        max_length=2,
    )
    line_15_answer = _means_choice()
    line_15_amount = _means_amount()
    line_16 = _means_amount()
    line_17 = _means_amount()
    line_18 = _means_amount()
    line_19 = _means_amount()
    line_20 = _means_amount()
    line_21 = _means_amount()
    line_22_answer = _means_choice()
    line_22_amount = _means_amount()
    line_23 = _means_amount()
    line_25_answer = _means_choice()
    line_25_health = _means_amount()
    line_25_disability = _means_amount()
    line_25_hsa = _means_amount()
    line_25_spends = _means_choice()
    line_25_actual = _means_amount()
    line_26_answer = _means_choice()
    line_26_amount = _means_amount()
    line_27_answer = _means_choice()
    line_27_amount = _means_amount()
    line_28_answer = _means_choice()
    line_28_amount = _means_amount()
    line_29_answer = _means_choice()
    line_29_amount = _means_amount()
    line_30_answer = _means_choice()
    line_30_amount = _means_amount()
    line_31_answer = _means_choice()
    line_31_amount = _means_amount()
    line_34_answer = _means_choice()
    line_36_answer = _means_choice()
    line_36_payment = _means_amount()
    line_43_answer = _means_choice()
    line_43_circumstances = serializers.ListField(
        child=CircumstanceSerializer(), required=False, allow_null=True, max_length=MAX_ROWS
    )
    # One row per counted secured debt, which can be more than MAX_ROWS: no max_length.
    debts = serializers.ListField(child=DebtAnswersSerializer(), required=False, allow_null=True)

    def validate_spouse_vehicles(self, value):
        _refuse_repeated_refs(value)
        return value

    def validate_spouse_loans(self, value):
        _refuse_repeated_refs(value)
        return value

    def validate_vehicle_choice(self, value):
        if value and value[0] is not None and value[0] == value[1]:
            raise serializers.ValidationError(DIFFERENT_VEHICLES)
        return value

    def validate_debts(self, value):
        seen = set()
        errors = {}
        for index, row in enumerate(value or []):
            if row["id"] in seen:
                errors[index] = {"id": [DEBT_SENT_TWICE]}
            seen.add(row["id"])
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate(self, attrs):
        unknown = sorted(set(self.initial_data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError({name: [NOT_A_MEANS_ANSWER] for name in unknown})
        # R14: a new-<n> reference must name a spouse vehicle sent in this same request.
        sent = {row.get("ref") for row in attrs.get("spouse_vehicles") or []}
        errors = {}
        loan_errors = {
            index: {"secured_by": [NOT_IN_THIS_SAVE]}
            for index, loan in enumerate(attrs.get("spouse_loans") or [])
            if (loan.get("secured_by") or "").startswith("new-") and loan["secured_by"] not in sent
        }
        if loan_errors:
            errors["spouse_loans"] = loan_errors
        choice = attrs.get("vehicle_choice") or []
        if any(ref and ref.startswith("new-") and ref not in sent for ref in choice):
            errors["vehicle_choice"] = [NOT_IN_THIS_SAVE]
        # F1: a list sent with its answer is measured here; one sent without it (or an answer
        # sent without its rows) waits for save_means_answers, which reads the stored half.
        measured = [key for key, answer in LIST_ANSWERS.items() if key in attrs and answer in attrs]
        merge_row_errors(errors, shown_box_refusals(attrs, measured, together=False))
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class PolishRequestSerializer(serializers.Serializer):
    """The line 43 polish's body (3h4 R4): the box's words and nothing else. An unknown key is
    refused by name, as a row of the page is."""

    explanation = serializers.CharField(
        max_length=2000,
        required=True,
        allow_null=False,
        error_messages={
            "required": MEANS_POLISH_BLANK,
            "null": MEANS_POLISH_BLANK,
            "blank": MEANS_POLISH_BLANK,
            "max_length": MEANS_EXPLANATION_TOO_LONG,
        },
    )

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise serializers.ValidationError({name: [NOT_A_MEANS_ANSWER] for name in unknown})
        return super().to_internal_value(data)


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
