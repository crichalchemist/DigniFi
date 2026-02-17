"""
Schedule A/B (Property) Generator Service.

Generates Official Bankruptcy Form 106A/B: Schedule of Assets - Real and Personal Property.

Part 1: Real Property
Part 2: Personal Property (35 categories)
Part 3: Summary totals

Official form: form_b106ab.pdf
11 U.S.C. § 521(a)(1)(B)(i) requires disclosure of ALL property.
"""

from decimal import Decimal
from typing import Dict, List, Any
from apps.intake.models import IntakeSession, AssetInfo


class ScheduleABGenerator:
    """
    Generate Schedule A/B (Property).

    Part 1: Real Property
    Part 2: Personal Property (35 categories)
    Part 3: Summary totals

    Official form: form_b106ab.pdf
    """

    def __init__(self, intake_session: IntakeSession):
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Schedule A/B data structure.

        Returns:
            dict: Complete Schedule A/B data with real/personal property breakdown
        """
        # Fetch all assets
        assets = list(self.session.assets.all())

        # Separate by type
        real_property = [a for a in assets if a.asset_type == 'real_property']
        personal_property = [a for a in assets if a.asset_type != 'real_property']

        # Calculate totals (using Decimal for precision)
        total_real = sum((a.current_value for a in real_property), Decimal('0.00'))
        total_personal = sum((a.current_value for a in personal_property), Decimal('0.00'))

        # Map personal property to Schedule A/B categories
        vehicles = [a for a in personal_property if a.asset_type == 'vehicle']
        bank_accounts = [a for a in personal_property if a.asset_type == 'bank_account']
        retirement_accounts = [a for a in personal_property if a.asset_type == 'retirement_account']
        # Map "other" asset type to household goods for Schedule A/B categorization
        household_goods = [a for a in personal_property if a.asset_type == 'other']

        return {
            # Part 1: Real Property
            'real_property': [
                {
                    'description': asset.description,
                    'address': getattr(asset, 'address', ''),
                    'current_value': asset.current_value,
                    'amount_owed': asset.amount_owed or Decimal('0.00'),
                    'equity': asset.current_value - (asset.amount_owed or Decimal('0.00'))
                }
                for asset in real_property
            ],
            'total_real_property_value': total_real,

            # Part 2: Personal Property
            'vehicles': [
                {
                    'description': asset.description,
                    'year': getattr(asset, 'year', ''),
                    'make': getattr(asset, 'make', ''),
                    'model': getattr(asset, 'model', ''),
                    'current_value': asset.current_value,
                    'amount_owed': asset.amount_owed or Decimal('0.00'),
                    'equity': asset.current_value - (asset.amount_owed or Decimal('0.00'))
                }
                for asset in vehicles
            ],
            'bank_accounts': [
                {
                    'institution': asset.description,
                    'account_type': getattr(asset, 'account_type', 'checking'),
                    'balance': asset.current_value
                }
                for asset in bank_accounts
            ],
            'retirement_accounts': [
                {
                    'institution': asset.description,
                    'account_type': getattr(asset, 'account_type', '401k/IRA'),
                    'balance': asset.current_value
                }
                for asset in retirement_accounts
            ],
            'household_goods': [
                {
                    'description': asset.description,
                    'current_value': asset.current_value
                }
                for asset in household_goods
            ],
            'total_personal_property_value': total_personal,

            # Part 3: Summary
            'total_value': total_real + total_personal
        }

    def preview(self) -> Dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()
