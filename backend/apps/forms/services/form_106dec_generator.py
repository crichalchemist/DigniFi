"""
Form 106Dec (Declaration About an Individual Debtor's Schedules) Generator.

The declaration is the oath page accompanying all bankruptcy schedules.
The debtor swears under penalty of perjury that the information in the
filed schedules is true and correct.

Official form: form_b106dec.pdf
"""

from datetime import date
from typing import Any

from apps.intake.models import IntakeSession, DebtorInfo


# Standard declaration text per Official Form 106Dec
_DECLARATION_TEXT = (
    "I declare under penalty of perjury that the information provided "
    "in this petition is true and correct."
)

# Schedules that 106Dec covers for a standard Chapter 7 individual filing
_STANDARD_SCHEDULES: tuple[str, ...] = (
    'A/B',
    'C',
    'D',
    'E/F',
    'I',
    'J',
    '106Sum',
)


def _build_debtor_full_name(debtor: DebtorInfo) -> str:
    """Compose full name from debtor info, including middle name when present."""
    parts = (debtor.first_name, debtor.middle_name, debtor.last_name)
    return ' '.join(part for part in parts if part)


def _build_declaration_data(
    debtor_name: str,
    signature_date: str,
) -> dict[str, Any]:
    """Construct the declaration data dict from pure values."""
    return {
        'debtor_name': debtor_name,
        'case_number': '',  # Empty until assigned by court
        'declaration_text': _DECLARATION_TEXT,
        'penalty_of_perjury': True,
        'signature_date': signature_date,
        'schedules_declared': list(_STANDARD_SCHEDULES),
    }


class Form106DecGenerator:
    """
    Generate Form 106Dec (Declaration About an Individual Debtor's Schedules).

    Pulls debtor identity from DebtorInfo and produces the declaration
    data structure for PDF population. The declaration is a required
    signature page for all individual Chapter 7 filings.

    Official form: form_b106dec.pdf
    """

    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> dict[str, Any]:
        """
        Generate Form 106Dec data.

        Returns dict with debtor_name, case_number, declaration_text,
        penalty_of_perjury, signature_date, and schedules_declared.
        Handles missing DebtorInfo gracefully with empty debtor name.
        """
        debtor_name = self._resolve_debtor_name()
        signature_date = date.today().isoformat()

        return _build_declaration_data(debtor_name, signature_date)

    def preview(self) -> dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()

    def _resolve_debtor_name(self) -> str:
        """Extract full name from session's DebtorInfo, defaulting to empty string."""
        try:
            debtor = self.session.debtor_info
        except DebtorInfo.DoesNotExist:
            return ''

        return _build_debtor_full_name(debtor)
