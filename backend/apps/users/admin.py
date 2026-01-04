from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User


class UserAdmin(DjangoUserAdmin):
    list_display = (
        *DjangoUserAdmin.list_display,
        "phone",
        "agreed_to_upl_disclaimer",
        "created_at",
    )
    list_filter = (
        *DjangoUserAdmin.list_filter,
        "agreed_to_upl_disclaimer",
        "agreed_to_terms",
    )
    search_fields = (*DjangoUserAdmin.search_fields, "phone")

    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        (
            "DigniFi Specifics",
            {
                "fields": (
                    "phone",
                    "agreed_to_terms",
                    "agreed_to_upl_disclaimer",
                    "upl_disclaimer_agreed_at",
                )
            },
        ),
    )

    readonly_fields = ("upl_disclaimer_agreed_at", "created_at", "updated_at")


admin.site.register(User, UserAdmin)
