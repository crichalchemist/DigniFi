"""
Schedule C (Property Claimed as Exempt) Generator Service.

Generates Official Bankruptcy Form 106C: The Property You Claim as Exempt.

Applies Illinois state exemptions per 735 ILCS 5/12-901 et seq:
- $15,000 homestead (principal residence) - 735 ILCS 5/12-901
- $4,000 wildcard (any personal property) - 735 ILCS 5/12-1001(b)
- $2,400 motor vehicle - 735 ILCS 5/12-1001(c)
- 100% necessary clothing - 735 ILCS 5/12-1001(a)
- 100% retirement benefits - 735 ILCS 5/12-1006

Official form: form_b106c_0425-form.pdf
"""

from decimal import Decimal
from typing import Any
import json
from pathlib import Path
from functools import reduce

from apps.intake.models import IntakeSession, AssetInfo


# Sentinel for unlimited exemption display value
_UNLIMITED_DISPLAY = Decimal('999999.99')

# Maps AssetInfo.asset_type to exemption fixture property_type
_ASSET_TO_EXEMPTION: dict[str, str] = {
    'real_property': 'homestead',
    'vehicle': 'vehicle',
    'retirement_account': 'retirement',
    'bank_account': 'wildcard',
    'other': 'wildcard',
}


def _load_exemptions_from_fixture(fixture_path: Path) -> dict[str, dict[str, Any]]:
    """Parse exemption fixture JSON into a lookup keyed by property_type."""
    with open(fixture_path) as f:
        raw = json.load(f)
    return {entry['property_type']: entry for entry in raw}


def _compute_equity(asset: AssetInfo) -> Decimal:
    """Calculate equity as current value minus amount owed."""
    return asset.current_value - (asset.amount_owed or Decimal('0.00'))


def _apply_exemption(
    asset: AssetInfo,
    exemptions: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Match an asset to its Illinois exemption and compute the claim.

    Returns None when equity is non-positive or no matching exemption exists.
    """
    equity = _compute_equity(asset)
    if equity <= Decimal('0.00'):
        return None

    exemption_type = _ASSET_TO_EXEMPTION.get(asset.asset_type, 'wildcard')
    exemption_data = exemptions.get(exemption_type)
    if exemption_data is None:
        return None

    is_unlimited = exemption_data['is_unlimited']

    if is_unlimited:
        amount_claimed = equity
    else:
        exemption_limit = Decimal(exemption_data['amount'])
        amount_claimed = min(equity, exemption_limit)

    return {
        'property_description': asset.description,
        'statute': exemption_data['statute'],
        'statute_description': exemption_data['description'],
        'amount_claimed': amount_claimed,
        'amount_available': (
            _UNLIMITED_DISPLAY if is_unlimited
            else Decimal(exemption_data['amount'])
        ),
        'current_value': asset.current_value,
        'equity': equity,
        'is_fully_exempt': is_unlimited or equity <= Decimal(exemption_data['amount']),
    }


class ScheduleCGenerator:
    """
    Generate Schedule C (Property Claimed as Exempt).

    Applies Illinois state exemptions per 735 ILCS 5/12-901 et seq.
    Loads exemption data from JSON fixture at instance creation time
    (not module import time) for testability.

    Official form: form_b106c_0425-form.pdf
    """

    EXEMPTIONS_FILE: Path = (
        Path(__file__).parent.parent / 'fixtures' / 'illinois_exemptions_2024.json'
    )

    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session
        self._exemptions = _load_exemptions_from_fixture(self.EXEMPTIONS_FILE)

    def generate(self) -> dict[str, Any]:
        """
        Generate Schedule C data with applied exemptions.

        Each asset with positive equity is matched to its best available
        Illinois exemption. The amount claimed is capped at the exemption
        limit (or full equity for unlimited exemptions).
        """
        assets = list(self.session.assets.all())

        exemptions = [
            result
            for asset in assets
            if (result := _apply_exemption(asset, self._exemptions)) is not None
        ]

        total_claimed = reduce(
            lambda acc, e: acc + e['amount_claimed'],
            exemptions,
            Decimal('0.00'),
        )

        return {
            'exemptions': exemptions,
            'total_claimed': total_claimed,
        }

    def preview(self) -> dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()
