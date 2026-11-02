"""
Serializers for intake models.

Provides Django REST Framework serializers for API endpoints, including
validation, nested relationships, and trauma-informed error messages.
"""

import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from rest_framework import serializers

from apps.districts.counties import ILND_COUNTIES
from apps.districts.dated_tables import fill_date
from apps.eligibility.cmi import income_step_gaps, income_window

from .household import (
    MAX_AGE,
    MAX_MEMBERS,
    RELATIONSHIP_WORDS,
    count_family_size,
    count_fee_waiver_household,
)
from .income import ENTRY_KINDS, MAX_ENTRIES
from .models import (
    YES_NO,
    AssetInfo,
    Codebtor,
    DebtInfo,
    DebtorInfo,
    ExecutoryContract,
    ExpenseInfo,
    FeeWaiverApplication,
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
            "monthly_income",
            "total_monthly_income",
            "created_at",
        ]
        read_only_fields = [
            "created_at",
            "income_period_end",
            "monthly_income",
            "total_monthly_income",
        ]

    def get_total_monthly_income(self, obj):
        """Return the ten amounts added up, or None when the filer gave none of them."""
        return obj.calculate_total_monthly_income()

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
    vehicle_payment = serializers.DecimalField(
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
    # Explicit field declarations — EncryptedDecimalField confuses DRF's auto-mapper
    current_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    amount_owed = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=0
    )

    class Meta:
        model = AssetInfo
        fields = [
            "id",
            "session",
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
        }

    def get_equity(self, obj):
        """Return calculated equity (current_value - amount_owed)."""
        return obj.equity


class DebtInfoSerializer(serializers.ModelSerializer):
    """Serializer for debt/creditor information (trauma-informed language)."""

    # Explicit field declaration — EncryptedDecimalField confuses DRF's auto-mapper
    amount_owed = serializers.DecimalField(max_digits=12, decimal_places=2)
    source_document_name = serializers.SerializerMethodField()

    class Meta:
        model = DebtInfo
        fields = [
            "id",
            "session",
            "data_source",
            "creditor_name",
            "debt_type",
            "priority_classification",
            "account_number",
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
        ]
        read_only_fields = ["id", "created_at", "updated_at", "is_draft", "source_document_name"]
        extra_kwargs = {
            "account_number": {"write_only": True},  # Don't expose account numbers
        }

    def get_source_document_name(self, obj) -> str | None:
        if obj.source_document:
            return obj.source_document.original_filename
        return None


class NestedAssetInfoSerializer(AssetInfoSerializer):
    """An asset row inside a session save.

    The id is writable so a row the wizard loaded updates in place. AssetViewSet keeps
    the base serializer, so per-item create never accepts a client id.
    """

    id = serializers.IntegerField(required=False)


class NestedDebtInfoSerializer(DebtInfoSerializer):
    """A debt row inside a session save. See NestedAssetInfoSerializer."""

    id = serializers.IntegerField(required=False)


def _save_rows_by_id(session, model, rows) -> list:
    """Save a session's nested assets or debts, or its contracts or codebtors list, by id.

    A row whose id is one of this session's rows updates only the fields it sent, so
    what the browser never received (account numbers, the scanned-bill link)
    survives. Any other row is created on this session, so a client-sent
    ``session`` or another user's id never touches another session. Stored rows the
    payload left out are deleted. Returns the saved rows in payload order, each with its id.
    """
    existing = {row.pk: row for row in model.objects.filter(session=session)}
    kept = set()
    saved = []
    for data in rows:
        data.pop("session", None)
        row = existing.get(data.pop("id", None))
        if row is None:
            saved.append(model.objects.create(session=session, **data))
            continue
        for attr, value in data.items():
            setattr(row, attr, value)
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
    "debts",
    "household",
    "spouse_income",
}


class IntakeSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for intake session with nested related data.

    Provides full session data including debtor info, income, expenses, assets, debts.
    """

    debtor_info = DebtorInfoSerializer(required=False, allow_null=True)
    income_info = IncomeInfoSerializer(required=False, allow_null=True)
    expense_info = ExpenseInfoSerializer(required=False, allow_null=True)
    assets = NestedAssetInfoSerializer(many=True, required=False)
    debts = NestedDebtInfoSerializer(many=True, required=False)
    household = HouseholdSerializer(required=False, allow_null=True)
    spouse_income = SpouseIncomeSerializer(required=False, allow_null=True)

    district_name = serializers.CharField(source="district.name", read_only=True)
    income_window = serializers.SerializerMethodField()

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
            "household",
            "spouse_income",
            "income_window",
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
        ]

    def get_income_window(self, obj) -> dict:
        """The six full months before today, which the Income step's figures cover."""
        start, end = income_window(fill_date())
        return {"start": start.isoformat(), "end": end.isoformat()}

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
            ExpenseInfo.objects.update_or_create(session=instance, defaults=expense_data)

        if household_data:
            _save_household(instance, household_data)

        if spouse_data:
            _save_spouse_income(instance, spouse_data)

        # The response lists a sent list in sent order, so the wizard can pair each row it
        # sent with its id (DIG-273). Every other read keeps model order.
        instance.sent_rows = {}
        if assets_data is not None:
            instance.sent_rows["assets"] = _save_rows_by_id(instance, AssetInfo, assets_data)

        if debts_data is not None:
            instance.sent_rows["debts"] = _save_rows_by_id(instance, DebtInfo, debts_data)

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for name, rows in getattr(instance, "sent_rows", {}).items():
            data[name] = self.fields[name].to_representation(rows)
        return data


class FeeWaiverApplicationSerializer(serializers.ModelSerializer):
    """The fee-waiver page's answers (forms step 2 spec §5.7).

    The old income, expenses and benefits answers are no longer written, so they are not
    fields here. Take-home pay and the non-cash answer are required, so a page that sent
    either under another name gets a 400 instead of losing it.
    """

    # Explicit field declaration — EncryptedDecimalField confuses DRF's auto-mapper.
    # Zero or more and within the column, like every amount the filer types.
    monthly_take_home_pay = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0")
    )
    # The model allows empty, for rows saved before the question existed. allow_null makes a
    # form-encoded request that leaves the answer out read as empty, not as No (DIG-193), and
    # validate() refuses the empty answer.
    receives_noncash_assistance = serializers.BooleanField(allow_null=True)
    # The "What kind?" answer: each kind is a non-blank line of text.
    benefit_types = serializers.ListField(
        child=serializers.CharField(max_length=255), required=False
    )
    # Remove the auto-generated UniqueValidator on session so that a second POST
    # from the same session passes validation — perform_create uses update_or_create
    # to handle the upsert safely.
    session = serializers.PrimaryKeyRelatedField(
        queryset=IntakeSession.objects.all(), validators=[]
    )

    class Meta:
        model = FeeWaiverApplication
        fields = [
            "id",
            "session",
            "household_size",
            "monthly_take_home_pay",
            "receives_noncash_assistance",
            "benefit_types",
            "cannot_pay_full",
            "cannot_pay_installments",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def validate(self, attrs):
        """A Yes to non-cash help needs "What kind?" answered, and a No keeps no kind.

        The answer is required on create and can't be sent empty: Form 103B line 3 prints a
        stored answer as a sworn Yes or No (DIG-193). A PATCH may send only one of the two, so
        the other is the stored one, which is empty on a row saved before the question; a kind
        sent there needs a Yes first.
        """
        required = self.fields["receives_noncash_assistance"].error_messages["required"]
        if attrs.get("receives_noncash_assistance") is None and (
            self.instance is None or "receives_noncash_assistance" in attrs
        ):
            raise serializers.ValidationError({"receives_noncash_assistance": [required]})
        answer = attrs.get(
            "receives_noncash_assistance",
            getattr(self.instance, "receives_noncash_assistance", None),
        )
        if answer is None and attrs.get("benefit_types"):
            raise serializers.ValidationError({"receives_noncash_assistance": [required]})
        if answer is False:
            attrs["benefit_types"] = []
        elif answer and not attrs.get("benefit_types", getattr(self.instance, "benefit_types", [])):
            raise serializers.ValidationError(
                {"benefit_types": [self.fields["benefit_types"].error_messages["required"]]}
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


class ExecutoryContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutoryContract
        fields = ["id", "counterparty_name", "contract_type", "description"]


class CodebtorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Codebtor
        fields = [
            "id",
            "name",
            "street_address",
            "city",
            "state",
            "zip_code",
            "relationship",
        ]


class ExecutoryContractRowSerializer(ExecutoryContractSerializer):
    """A contract row in the Contracts step's list save.

    The id is writable so a row the wizard loaded updates in place. The single-contract
    POST keeps the base serializer, so it never accepts a client id.
    """

    id = serializers.IntegerField(required=False)


class CodebtorRowSerializer(CodebtorSerializer):
    """A codebtor row in the Codebtors step's list save. See ExecutoryContractRowSerializer."""

    id = serializers.IntegerField(required=False)
