from django.contrib import admin

from .models import UserCountrySuggestion, UserFeedback, UserOriginPreference, Bookmark


@admin.register(UserOriginPreference)
class UserOriginPreferenceAdmin(admin.ModelAdmin):
	list_display = ("user", "origin_country", "updated_at")
	search_fields = ("user__username", "user__email", "origin_country__code", "origin_country__name")
	list_filter = ("origin_country", "updated_at")


@admin.register(UserCountrySuggestion)
class UserCountrySuggestionAdmin(admin.ModelAdmin):
	list_display = ("user", "country", "user_email", "created_at")
	search_fields = ("user__username", "user__email", "country", "message")
	list_filter = ("created_at",)


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
	list_display = ("user", "name", "user_email", "created_at")
	search_fields = ("user__username", "user__email", "name", "message")
	list_filter = ("created_at",)


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
	list_display = ("user", "bookmark_type", "country", "app", "created_at")
	search_fields = ("user__username", "user__email", "country__name", "country__code", "app__name")
	list_filter = ("bookmark_type", "created_at")
	readonly_fields = ("created_at",)

