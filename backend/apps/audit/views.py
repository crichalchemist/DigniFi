from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PageNumberPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["action", "resource_type", "upl_sensitive"]
    search_fields = ["action", "details", "user__username", "user__email"]
    ordering_fields = ["timestamp", "action"]
    ordering = ["-timestamp"]

    # Audit trail is per-user and append-only: no cross-tenant reads, no edits/deletes.
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        """Scope audit records to the requesting user (prevents cross-tenant reads)."""
        return AuditLog.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Automatically set user and IP from request
        x_forwarded_for = self.request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = self.request.META.get("REMOTE_ADDR")

        serializer.save(
            user=self.request.user,
            ip_address=ip,
            user_agent=self.request.META.get("HTTP_USER_AGENT", ""),
        )
