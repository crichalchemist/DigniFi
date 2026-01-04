from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "username",
            "action",
            "resource_type",
            "resource_id",
            "upl_sensitive",
            "timestamp",
            "ip_address",
            "details",
        ]
        read_only_fields = ["timestamp", "ip_address", "user"]
