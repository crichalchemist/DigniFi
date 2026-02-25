"""
Form 121 Generator Service.

Generates Official Bankruptcy Form 121: Your Statement About Your Social
Security Numbers. This form is filed SEPARATELY from the main petition
and kept under seal — only authorized court personnel may access it.

The full SSN appears exclusively on the sealed filing; all previews
and public-facing outputs use a masked representation.

Official form: form_b121.pdf
"""

import re
from typing import Any, Dict, Optional

from apps.intake.models import DebtorInfo, IntakeSession


# -- Constants --

SSN_DIGIT_PATTERN = re.compile(r'^\d{9}$')
SSN_FORMATTED_PATTERN = re.compile(r'^\d{3}-\d{2}-\d{4}$')
MASK_PREFIX = '***-**-'


# -- Pure helper functions (no side effects) --

def _format_ssn(raw_ssn: str) -> str:
    """
    Normalize an SSN to XXX-XX-XXXX format.

    Accepts either 9 bare digits ("123456789") or already-formatted
    ("123-45-6789"). Raises ValueError on any other shape.
    """
    cleaned = raw_ssn.strip()

    if SSN_FORMATTED_PATTERN.match(cleaned):
        return cleaned

    if SSN_DIGIT_PATTERN.match(cleaned):
        return f'{cleaned[:3]}-{cleaned[3:5]}-{cleaned[5:]}'

    raise ValueError(
        f'Invalid SSN format: expected 9 digits or XXX-XX-XXXX, got {len(cleaned)} characters'
    )


def _extract_last_four(formatted_ssn: str) -> str:
    """Return the last 4 digits from a formatted SSN (XXX-XX-XXXX)."""
    return formatted_ssn[-4:]


def _mask_ssn(formatted_ssn: str) -> str:
    """
    Mask all but the last 4 digits for safe display.

    "123-45-6789" -> "***-**-6789"
    """
    return f'{MASK_PREFIX}{_extract_last_four(formatted_ssn)}'


def _build_full_name(first_name: str, middle_name: str, last_name: str) -> str:
    """Assemble a legal full name, collapsing empty middle names."""
    parts = (first_name, middle_name, last_name)
    return ' '.join(p for p in parts if p)


def _build_form_121_data(
    debtor_name: str,
    ssn_full: str,
    ssn_last_four: str,
    has_previous_ssn: bool = False,
    previous_ssn: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build the complete Form 121 data structure.

    Pure function: deterministic output from given inputs.
    The `filed_separately` flag is always True — Form 121 is sealed.
    """
    return {
        'debtor_name': debtor_name,
        'case_number': '',  # Assigned by the court after filing
        'ssn_full': ssn_full,
        'ssn_last_four': ssn_last_four,
        'has_previous_ssn': has_previous_ssn,
        'previous_ssn': previous_ssn,
        'filed_separately': True,
    }


def _build_preview_data(
    debtor_name: str,
    ssn_masked: str,
    ssn_last_four: str,
    has_previous_ssn: bool = False,
) -> Dict[str, Any]:
    """
    Build a preview-safe Form 121 structure with masked SSN.

    The full SSN is never exposed in preview output.
    """
    return {
        'debtor_name': debtor_name,
        'case_number': '',
        'ssn_display': ssn_masked,
        'ssn_last_four': ssn_last_four,
        'has_previous_ssn': has_previous_ssn,
        'previous_ssn_display': '***-**-****' if has_previous_ssn else None,
        'filed_separately': True,
    }


def _extract_debtor_data(session: IntakeSession) -> Dict[str, Any]:
    """
    Extract debtor identity fields, handling missing DebtorInfo.

    Returns a dict of raw values suitable for building the form data.
    Raises Form121GenerationError when DebtorInfo is absent — SSN
    disclosure cannot proceed without identity data.
    """
    try:
        debtor: DebtorInfo = session.debtor_info
        formatted_ssn = _format_ssn(debtor.ssn)

        return {
            'debtor_name': _build_full_name(
                debtor.first_name,
                debtor.middle_name,
                debtor.last_name,
            ),
            'ssn_formatted': formatted_ssn,
            'ssn_last_four': _extract_last_four(formatted_ssn),
            'ssn_masked': _mask_ssn(formatted_ssn),
        }
    except DebtorInfo.DoesNotExist:
        raise Form121GenerationError(
            'DebtorInfo is required to generate Form 121 (SSN disclosure). '
            'Please complete the personal information step first.'
        )


class Form121GenerationError(Exception):
    """Raised when Form 121 generation cannot proceed."""


class Form121Generator:
    """
    Generate Form 121 — Your Statement About Your Social Security Numbers.

    This form is filed separately from the petition and kept under seal.
    Only the generate() method returns the full SSN (for the sealed filing);
    the preview() method always returns a masked representation.

    Official form: form_b121.pdf
    """

    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate the full Form 121 data including unmasked SSN.

        Intended only for the sealed court filing. The full SSN value
        should never be displayed in the UI — use preview() instead.

        Raises:
            Form121GenerationError: If DebtorInfo is missing.
        """
        raw = _extract_debtor_data(self.session)
        return _build_form_121_data(
            debtor_name=raw['debtor_name'],
            ssn_full=raw['ssn_formatted'],
            ssn_last_four=raw['ssn_last_four'],
        )

    def preview(self) -> Dict[str, Any]:
        """
        Generate a preview-safe representation with masked SSN.

        Suitable for on-screen review before filing. The full SSN
        is never included in the preview output.

        Raises:
            Form121GenerationError: If DebtorInfo is missing.
        """
        raw = _extract_debtor_data(self.session)

        preview_data = _build_preview_data(
            debtor_name=raw['debtor_name'],
            ssn_masked=raw['ssn_masked'],
            ssn_last_four=raw['ssn_last_four'],
        )

        return {
            'form_type': 'form_121',
            'form_name': 'Your Statement About Your Social Security Numbers',
            'preview': True,
            'data': preview_data,
            'upl_disclaimer': (
                'This is a preview of your SSN disclosure statement. '
                'This form is filed separately from your petition and '
                'kept under seal for your privacy. Only authorized court '
                'personnel may access it.'
            ),
        }
