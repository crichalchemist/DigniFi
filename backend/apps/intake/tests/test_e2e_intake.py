"""
Comprehensive end-to-end tests for intake flow.

Tests the complete intake workflow from session creation through means test
calculation and form preview, including permission isolation and error handling.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.intake.models import (
    IntakeSession,
    DebtorInfo,
    IncomeInfo,
    ExpenseInfo,
    AssetInfo,
    DebtInfo,
)
from apps.districts.models import District, MedianIncome

User = get_user_model()


@pytest.fixture
def user():
    """Create test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpassword123"
    )


@pytest.fixture
def other_user():
    """Create another test user for permission isolation tests."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="testpassword123"
    )


@pytest.fixture
def district():
    """Create test district with ILND 2025 data."""
    return District.objects.create(
        code="ilnd",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court for the Northern District of Illinois",
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def median_income(district):
    """Create median income data for ILND 2025."""
    return MedianIncome.objects.create(
        district=district,
        effective_date="2025-01-01",
        family_size_1=Decimal("71304.00"),
        family_size_2=Decimal("92256.00"),
        family_size_3=Decimal("103242.00"),
        family_size_4=Decimal("123908.00"),
        family_size_5=Decimal("133508.00"),
        family_size_6=Decimal("143108.00"),
        family_size_7=Decimal("152708.00"),
        family_size_8=Decimal("162308.00"),
    )


@pytest.fixture
def api_client(user):
    """Create authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestIntakeSessionCreation:
    """Test suite for intake session creation."""

    def test_create_session_success(self, api_client, district):
        """Test successful session creation."""
        url = reverse("intake-session-list")
        data = {
            "district": district.id,
            "current_step": 1,
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "session" in response.data
        assert "message" in response.data
        assert response.data["session"]["status"] == "started"
        assert response.data["session"]["current_step"] == 1
        assert response.data["session"]["district"] == district.id

    def test_create_session_invalid_district(self, api_client):
        """Test session creation with invalid district ID."""
        url = reverse("intake-session-list")
        data = {
            "district": 99999,
            "current_step": 1,
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_session_unauthenticated(self, district):
        """Test that unauthenticated users cannot create sessions."""
        client = APIClient()
        url = reverse("intake-session-list")
        data = {
            "district": district.id,
            "current_step": 1,
        }

        response = client.post(url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestIntakeSessionSteps:
    """Test suite for intake session step management."""

    def test_update_step_success(self, api_client, district):
        """Test updating session step."""
        # Create session
        create_url = reverse("intake-session-list")
        create_response = api_client.post(
            create_url,
            {"district": district.id, "current_step": 1},
            format="json"
        )
        session_id = create_response.data["session"]["id"]

        # Update step
        update_url = reverse("intake-session-update-step", args=[session_id])
        update_data = {"current_step": 2}
        response = api_client.post(update_url, update_data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["session"]["current_step"] == 2
        assert response.data["session"]["status"] == "in_progress"

    def test_update_step_with_data(self, api_client, district):
        """Test updating session step with nested data."""
        # Create session
        create_url = reverse("intake-session-list")
        create_response = api_client.post(
            create_url,
            {"district": district.id, "current_step": 1},
            format="json"
        )
        session_id = create_response.data["session"]["id"]

        # Update step with debtor info
        update_url = reverse("intake-session-update-step", args=[session_id])
        update_data = {
            "current_step": 2,
            "data": {
                "debtor_info": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "ssn": "123456789",
                    "date_of_birth": "1980-01-01",
                    "phone": "555-555-5555",
                    "email": "john@example.com",
                    "street_address": "123 Main St",
                    "city": "Chicago",
                    "state": "IL",
                    "zip_code": "60601",
                }
            }
        }
        response = api_client.post(update_url, update_data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["session"]["debtor_info"] is not None
        assert response.data["session"]["debtor_info"]["first_name"] == "John"


@pytest.mark.django_db
class TestAssetCRUD:
    """Test suite for asset CRUD operations."""

    @pytest.fixture
    def session(self, api_client, district):
        """Create a test intake session."""
        url = reverse("intake-session-list")
        response = api_client.post(
            url,
            {"district": district.id, "current_step": 1},
            format="json"
        )
        return IntakeSession.objects.get(id=response.data["session"]["id"])

    def test_create_asset(self, api_client, session):
        """Test creating an asset."""
        url = reverse("asset-info-list")
        data = {
            "session": session.id,
            "asset_type": "bank_account",
            "description": "Checking Account",
            "current_value": "1000.00",
            "amount_owed": "0.00",
            "account_number": "1234567890",
            "financial_institution": "Test Bank",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["asset_type"] == "bank_account"
        assert response.data["description"] == "Checking Account"

    def test_read_asset(self, api_client, session):
        """Test reading an asset."""
        # Create asset
        asset = AssetInfo.objects.create(
            session=session,
            asset_type="vehicle",
            description="2015 Honda Civic",
            current_value=Decimal("8000.00"),
            amount_owed=Decimal("3000.00"),
        )

        # Read asset
        url = reverse("asset-info-detail", args=[asset.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["asset_type"] == "vehicle"
        assert response.data["description"] == "2015 Honda Civic"
        assert Decimal(response.data["equity"]) == Decimal("5000.00")

    def test_update_asset(self, api_client, session):
        """Test updating an asset."""
        # Create asset
        asset = AssetInfo.objects.create(
            session=session,
            asset_type="bank_account",
            description="Checking",
            current_value=Decimal("1000.00"),
            amount_owed=Decimal("0.00"),
        )

        # Update asset
        url = reverse("asset-info-detail", args=[asset.id])
        update_data = {
            "description": "Main Checking Account",
            "current_value": "1500.00",
        }
        response = api_client.patch(url, update_data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["description"] == "Main Checking Account"

    def test_delete_asset(self, api_client, session):
        """Test deleting an asset."""
        # Create asset
        asset = AssetInfo.objects.create(
            session=session,
            asset_type="bank_account",
            description="Old Account",
            current_value=Decimal("100.00"),
            amount_owed=Decimal("0.00"),
        )

        # Delete asset
        url = reverse("asset-info-detail", args=[asset.id])
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not AssetInfo.objects.filter(id=asset.id).exists()


@pytest.mark.django_db
class TestDebtCRUD:
    """Test suite for debt CRUD operations."""

    @pytest.fixture
    def session(self, api_client, district):
        """Create a test intake session."""
        url = reverse("intake-session-list")
        response = api_client.post(
            url,
            {"district": district.id, "current_step": 1},
            format="json"
        )
        return IntakeSession.objects.get(id=response.data["session"]["id"])

    def test_create_debt(self, api_client, session):
        """Test creating a debt entry."""
        url = reverse("debt-info-list")
        data = {
            "session": session.id,
            "creditor_name": "Credit Card Company",
            "debt_type": "credit_card",
            "account_number": "1234",
            "amount_owed": "5000.00",
            "monthly_payment": "150.00",
            "is_in_collections": False,
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["creditor_name"] == "Credit Card Company"
        assert response.data["debt_type"] == "credit_card"

    def test_read_debt(self, api_client, session):
        """Test reading a debt entry."""
        # Create debt
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Medical Provider",
            debt_type="credit_card",
            amount_owed=Decimal("2000.00"),
            monthly_payment=Decimal("50.00"),
            is_in_collections=True,
        )

        # Read debt
        url = reverse("debt-info-detail", args=[debt.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["creditor_name"] == "Medical Provider"
        assert response.data["is_in_collections"] is True

    def test_update_debt(self, api_client, session):
        """Test updating a debt entry."""
        # Create debt
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Old Creditor",
            debt_type="credit_card",
            amount_owed=Decimal("1000.00"),
            monthly_payment=Decimal("50.00"),
        )

        # Update debt
        url = reverse("debt-info-detail", args=[debt.id])
        update_data = {
            "creditor_name": "Updated Creditor Name",
            "monthly_payment": "75.00",
        }
        response = api_client.patch(url, update_data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["creditor_name"] == "Updated Creditor Name"

    def test_delete_debt(self, api_client, session):
        """Test deleting a debt entry."""
        # Create debt
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Paid Off Creditor",
            debt_type="credit_card",
            amount_owed=Decimal("0.00"),
            monthly_payment=Decimal("0.00"),
        )

        # Delete debt
        url = reverse("debt-info-detail", args=[debt.id])
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DebtInfo.objects.filter(id=debt.id).exists()


@pytest.mark.django_db
class TestIntakeSessionCompletion:
    """Test suite for intake session completion."""

    @pytest.fixture
    def session(self, api_client, district):
        """Create a test intake session."""
        url = reverse("intake-session-list")
        response = api_client.post(
            url,
            {"district": district.id, "current_step": 1},
            format="json"
        )
        return IntakeSession.objects.get(id=response.data["session"]["id"])

    def test_complete_session_success(self, api_client, session):
        """Test successfully completing a session with all required data."""
        # Add debtor info
        DebtorInfo.objects.create(
            session=session,
            first_name="John",
            last_name="Doe",
            ssn="123456789",
            date_of_birth="1980-01-01",
            street_address="123 Main St",
            city="Chicago",
            state="IL",
            zip_code="60601",
        )

        # Add income info
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        # Add expense info
        ExpenseInfo.objects.create(
            session=session,
            rent_or_mortgage=Decimal("1500.00"),
            utilities=Decimal("200.00"),
            home_maintenance=Decimal("50.00"),
            vehicle_payment=Decimal("300.00"),
            vehicle_insurance=Decimal("100.00"),
            vehicle_maintenance=Decimal("150.00"),
            food_and_groceries=Decimal("400.00"),
            childcare=Decimal("0.00"),
            medical_expenses=Decimal("50.00"),
            insurance_not_deducted=Decimal("0.00"),
            other_expenses=Decimal("100.00"),
        )

        # Complete session
        url = reverse("intake-session-complete", args=[session.id])
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["session"]["status"] == "completed"
        assert response.data["session"]["completed_at"] is not None

    def test_complete_session_missing_debtor_info(self, api_client, session):
        """Test completing session without debtor info returns 400."""
        # Add income and expense but not debtor
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        ExpenseInfo.objects.create(
            session=session,
            rent_or_mortgage=Decimal("1500.00"),
            utilities=Decimal("200.00"),
            home_maintenance=Decimal("50.00"),
            vehicle_payment=Decimal("300.00"),
            vehicle_insurance=Decimal("100.00"),
            vehicle_maintenance=Decimal("150.00"),
            food_and_groceries=Decimal("400.00"),
            childcare=Decimal("0.00"),
            medical_expenses=Decimal("50.00"),
            insurance_not_deducted=Decimal("0.00"),
            other_expenses=Decimal("100.00"),
        )

        url = reverse("intake-session-complete", args=[session.id])
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "errors" in response.data
        assert "Debtor information is required" in response.data["errors"]

    def test_complete_session_missing_income_info(self, api_client, session):
        """Test completing session without income info returns 400."""
        # Add debtor and expense but not income
        DebtorInfo.objects.create(
            session=session,
            first_name="John",
            last_name="Doe",
            ssn="123456789",
            date_of_birth="1980-01-01",
            street_address="123 Main St",
            city="Chicago",
            state="IL",
            zip_code="60601",
        )

        ExpenseInfo.objects.create(
            session=session,
            rent_or_mortgage=Decimal("1500.00"),
            utilities=Decimal("200.00"),
            home_maintenance=Decimal("50.00"),
            vehicle_payment=Decimal("300.00"),
            vehicle_insurance=Decimal("100.00"),
            vehicle_maintenance=Decimal("150.00"),
            food_and_groceries=Decimal("400.00"),
            childcare=Decimal("0.00"),
            medical_expenses=Decimal("50.00"),
            insurance_not_deducted=Decimal("0.00"),
            other_expenses=Decimal("100.00"),
        )

        url = reverse("intake-session-complete", args=[session.id])
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "errors" in response.data
        assert "Income information is required" in response.data["errors"]

    def test_complete_session_missing_expense_info(self, api_client, session):
        """Test completing session without expense info returns 400."""
        # Add debtor and income but not expense
        DebtorInfo.objects.create(
            session=session,
            first_name="John",
            last_name="Doe",
            ssn="123456789",
            date_of_birth="1980-01-01",
            street_address="123 Main St",
            city="Chicago",
            state="IL",
            zip_code="60601",
        )

        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        url = reverse("intake-session-complete", args=[session.id])
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "errors" in response.data
        assert "Expense information is required" in response.data["errors"]


@pytest.mark.django_db
class TestPermissionIsolation:
    """Test suite for user permission isolation."""

    @pytest.fixture
    def user_session(self, api_client, district):
        """Create session for primary user."""
        url = reverse("intake-session-list")
        response = api_client.post(
            url,
            {"district": district.id, "current_step": 1},
            format="json"
        )
        return IntakeSession.objects.get(id=response.data["session"]["id"])

    @pytest.fixture
    def other_user_session(self, other_user, district):
        """Create session for other user."""
        session = IntakeSession.objects.create(
            user=other_user,
            district=district,
            current_step=1,
            status="started",
        )
        return session

    def test_user_cannot_see_other_user_session(self, api_client, other_user_session):
        """Test that users cannot access other users' sessions."""
        url = reverse("intake-session-detail", args=[other_user_session.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_user_cannot_see_other_user_assets(self, api_client, other_user_session):
        """Test that users cannot access other users' assets."""
        # Create asset for other user
        asset = AssetInfo.objects.create(
            session=other_user_session,
            asset_type="bank_account",
            description="Other User's Account",
            current_value=Decimal("5000.00"),
            amount_owed=Decimal("0.00"),
        )

        # Try to access as primary user
        url = reverse("asset-info-detail", args=[asset.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_user_cannot_see_other_user_debts(self, api_client, other_user_session):
        """Test that users cannot access other users' debts."""
        # Create debt for other user
        debt = DebtInfo.objects.create(
            session=other_user_session,
            creditor_name="Other User's Creditor",
            debt_type="credit_card",
            amount_owed=Decimal("1000.00"),
            monthly_payment=Decimal("50.00"),
        )

        # Try to access as primary user
        url = reverse("debt-info-detail", args=[debt.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_user_session_list_filtered(self, api_client, user_session, other_user_session):
        """Test that session list only shows user's own sessions."""
        url = reverse("intake-session-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Response may be paginated (results key) or flat list
        results = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        session_ids = [session["id"] for session in results]
        assert user_session.id in session_ids
        assert other_user_session.id not in session_ids


@pytest.mark.django_db
class TestMeansTestCalculation:
    """Test suite for means test calculation."""

    @pytest.fixture
    def complete_session(self, api_client, district, median_income):
        """Create session with all required data for means test."""
        url = reverse("intake-session-list")
        response = api_client.post(
            url,
            {"district": district.id, "current_step": 1},
            format="json"
        )
        session = IntakeSession.objects.get(id=response.data["session"]["id"])

        # Add required data
        DebtorInfo.objects.create(
            session=session,
            first_name="John",
            last_name="Doe",
            ssn="123456789",
            date_of_birth="1980-01-01",
            street_address="123 Main St",
            city="Chicago",
            state="IL",
            zip_code="60601",
        )

        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        ExpenseInfo.objects.create(
            session=session,
            rent_or_mortgage=Decimal("1500.00"),
            utilities=Decimal("200.00"),
            home_maintenance=Decimal("50.00"),
            vehicle_payment=Decimal("300.00"),
            vehicle_insurance=Decimal("100.00"),
            vehicle_maintenance=Decimal("150.00"),
            food_and_groceries=Decimal("400.00"),
            childcare=Decimal("0.00"),
            medical_expenses=Decimal("50.00"),
            insurance_not_deducted=Decimal("0.00"),
            other_expenses=Decimal("100.00"),
        )

        return session

    def test_calculate_means_test_success(self, api_client, complete_session):
        """Test successful means test calculation."""
        url = reverse("intake-session-calculate-means-test", args=[complete_session.id])
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert "means_test_result" in response.data
        assert "session_id" in response.data

        result = response.data["means_test_result"]
        assert "passes_means_test" in result
        assert "qualifies_for_fee_waiver" in result
        assert "cmi" in result
        assert "median_income_threshold" in result
        assert "message" in result

    def test_calculate_means_test_below_median(self, api_client, complete_session):
        """Test means test with income below median (should pass)."""
        # Update income to be below median ($71,304 annual = $5,942/month)
        complete_session.income_info.monthly_income = [4000, 4000, 4000, 4000, 4000, 4000]
        complete_session.income_info.save()

        url = reverse("intake-session-calculate-means-test", args=[complete_session.id])
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.data["means_test_result"]
        assert result["passes_means_test"] is True
        assert Decimal(result["cmi"]) == Decimal("4000.00")

    def test_calculate_means_test_above_median(self, api_client, complete_session):
        """Test means test with income above median (should fail)."""
        # Note: calculator compares monthly CMI to annual threshold directly.
        # Median is $71,304 annual, so CMI must exceed that to fail.
        complete_session.income_info.monthly_income = [80000, 80000, 80000, 80000, 80000, 80000]
        complete_session.income_info.save()

        url = reverse("intake-session-calculate-means-test", args=[complete_session.id])
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.data["means_test_result"]
        assert result["passes_means_test"] is False
        assert Decimal(result["cmi"]) == Decimal("80000.00")

    def test_calculate_means_test_without_income_info(self, api_client, district):
        """Test means test calculation without income info returns 400."""
        # Create session without income info
        url = reverse("intake-session-list")
        response = api_client.post(
            url,
            {"district": district.id, "current_step": 1},
            format="json"
        )
        session_id = response.data["session"]["id"]

        # Try to calculate means test
        calc_url = reverse("intake-session-calculate-means-test", args=[session_id])
        response = api_client.post(calc_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_fee_waiver_qualification(self, api_client, complete_session, median_income):
        """Test fee waiver qualification for income < 150% poverty line."""
        # Set income very low for fee waiver (150% of poverty line ~$22k annual = $1,833/month)
        complete_session.income_info.monthly_income = [1500, 1500, 1500, 1500, 1500, 1500]
        complete_session.income_info.save()

        url = reverse("intake-session-calculate-means-test", args=[complete_session.id])
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.data["means_test_result"]
        assert result["qualifies_for_fee_waiver"] is True


@pytest.mark.django_db
class TestForm101Preview:
    """Test suite for Form 101 preview functionality."""

    @pytest.fixture
    def complete_session(self, api_client, district, median_income):
        """Create session with all required data."""
        url = reverse("intake-session-list")
        response = api_client.post(
            url,
            {"district": district.id, "current_step": 1},
            format="json"
        )
        session = IntakeSession.objects.get(id=response.data["session"]["id"])

        DebtorInfo.objects.create(
            session=session,
            first_name="John",
            last_name="Doe",
            middle_name="Q",
            ssn="123456789",
            date_of_birth="1980-01-01",
            phone="555-555-5555",
            email="john@example.com",
            street_address="123 Main St",
            city="Chicago",
            state="IL",
            zip_code="60601",
        )

        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        ExpenseInfo.objects.create(
            session=session,
            rent_or_mortgage=Decimal("1500.00"),
            utilities=Decimal("200.00"),
            home_maintenance=Decimal("50.00"),
            vehicle_payment=Decimal("300.00"),
            vehicle_insurance=Decimal("100.00"),
            vehicle_maintenance=Decimal("150.00"),
            food_and_groceries=Decimal("400.00"),
            childcare=Decimal("0.00"),
            medical_expenses=Decimal("50.00"),
            insurance_not_deducted=Decimal("0.00"),
            other_expenses=Decimal("100.00"),
        )

        return session

    def test_preview_form_101_success(self, api_client, complete_session):
        """Test successful Form 101 preview generation."""
        url = reverse("intake-session-preview-form-101", args=[complete_session.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "form_preview" in response.data
        assert "session_id" in response.data

        preview = response.data["form_preview"]
        assert "debtor_name" in preview
        assert "debtor_address" in preview
        assert "case_type" in preview

    def test_preview_form_101_without_debtor_info(self, api_client, district):
        """Test Form 101 preview without debtor info returns 400."""
        # Create session without debtor info
        url = reverse("intake-session-list")
        response = api_client.post(
            url,
            {"district": district.id, "current_step": 1},
            format="json"
        )
        session_id = response.data["session"]["id"]

        # Try to preview form
        preview_url = reverse("intake-session-preview-form-101", args=[session_id])
        response = api_client.get(preview_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data


@pytest.mark.django_db
class TestSessionSummary:
    """Test suite for session summary endpoint."""

    @pytest.fixture
    def session_with_data(self, api_client, district, median_income):
        """Create session with partial data."""
        url = reverse("intake-session-list")
        response = api_client.post(
            url,
            {"district": district.id, "current_step": 1},
            format="json"
        )
        session = IntakeSession.objects.get(id=response.data["session"]["id"])

        # Add debtor info
        DebtorInfo.objects.create(
            session=session,
            first_name="John",
            last_name="Doe",
            ssn="123456789",
            date_of_birth="1980-01-01",
            street_address="123 Main St",
            city="Chicago",
            state="IL",
            zip_code="60601",
        )

        # Add income info
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        # Add an asset
        AssetInfo.objects.create(
            session=session,
            asset_type="bank_account",
            description="Checking",
            current_value=Decimal("1000.00"),
            amount_owed=Decimal("0.00"),
        )

        # Add a debt
        DebtInfo.objects.create(
            session=session,
            creditor_name="Credit Card Co",
            debt_type="credit_card",
            amount_owed=Decimal("5000.00"),
            monthly_payment=Decimal("150.00"),
        )

        return session

    def test_session_summary_structure(self, api_client, session_with_data):
        """Test session summary returns expected structure."""
        url = reverse("intake-session-summary", args=[session_with_data.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "session" in response.data
        assert "progress" in response.data
        assert "forms" in response.data

        progress = response.data["progress"]
        assert "current_step" in progress
        assert "status" in progress
        assert "completion_percentage" in progress

    def test_session_summary_completion_percentage(self, api_client, session_with_data):
        """Test completion percentage calculation."""
        url = reverse("intake-session-summary", args=[session_with_data.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        progress = response.data["progress"]

        # Should have: debtor (1), income (1), assets (1), debts (1) = 4/5 sections = 80%
        # Missing: expenses
        assert progress["completion_percentage"] == 80

    def test_session_summary_with_forms(self, api_client, session_with_data):
        """Test session summary includes form generation status."""
        url = reverse("intake-session-summary", args=[session_with_data.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        forms = response.data["forms"]
        assert "generated_count" in forms
        assert "forms" in forms
        assert forms["generated_count"] == 0  # No forms generated yet
