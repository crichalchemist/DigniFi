"""
UPL-aware audit logging middleware for DigniFi.

This middleware logs all requests/responses for UPL compliance auditing.
"""

import logging
from .models import AuditLog

logger = logging.getLogger('dignifi.audit')


class AuditLoggingMiddleware:
    """
    Middleware that logs all requests for UPL compliance auditing.

    Logs:
    - User actions
    - IP addresses
    - Request paths
    - Response status codes
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request
        response = self.get_response(request)

        # Log the request if user is authenticated
        if request.user.is_authenticated:
            # Determine if this is a UPL-sensitive action
            upl_sensitive = self._is_upl_sensitive(request.path)

            # Log the action
            AuditLog.log_action(
                action=f"{request.method} {request.path}",
                user=request.user,
                resource_type="http_request",
                upl_sensitive=upl_sensitive,
                ip_address=self._get_client_ip(request),
                method=request.method,
                path=request.path,
                status_code=response.status_code
            )

        return response

    def _is_upl_sensitive(self, path: str) -> bool:
        """
        Determine if a request path involves UPL-sensitive operations.
        """
        upl_paths = [
            '/api/eligibility/',
            '/api/forms/',
            '/api/intake/',
            '/api/means-test/',
        ]
        return any(path.startswith(upl_path) for upl_path in upl_paths)

    def _get_client_ip(self, request):
        """
        Extract client IP address from request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
