from django.contrib import admin
from .models import AuditLog


class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "user",
        "action",
        "resource_type",
        "upl_sensitive",
        "ip_address",
    )
    list_filter = ("upl_sensitive", "action", "resource_type", "timestamp")
    search_fields = ("user__username", "user__email", "action", "details", "ip_address")
    readonly_fields = (
        "timestamp",
        "user",
        "action",
        "resource_type",
        "resource_id",
        "upl_sensitive",
        "ip_address",
        "user_agent",
        "details",
    )
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of audit logs for compliance
        return False


admin.site.register(AuditLog, AuditLogAdmin)
