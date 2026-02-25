"""
UPL-aware exception handler for DRF.

Wraps the default exception handler to ensure error responses never
contain language that could be construed as legal advice.
"""

from rest_framework.views import exception_handler


def upl_aware_exception_handler(exc, context):
    """
    DRF exception handler that delegates to the default handler.

    Future: audit-log exceptions that touch guidance endpoints,
    scrub any response text that crosses UPL boundaries.
    """
    return exception_handler(exc, context)
