from django.contrib import admin

from .models import UserOriginPreference


@admin.register(UserOriginPreference)
class UserOriginPreferenceAdmin(admin.ModelAdmin):
	list_display = ("user", "origin_country", "updated_at")
	search_fields = ("user__username", "user__email", "origin_country__code", "origin_country__name")
	list_filter = ("origin_country", "updated_at")
