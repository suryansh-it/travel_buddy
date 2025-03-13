

# Register your models here.
from django.contrib import admin
from .models import Country, AppCategory, TravelApp

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "flag")
    search_fields = ("name", "code")


@admin.register(AppCategory)
class AppCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(TravelApp)
class TravelAppAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "country", "ios_link", "android_link")
    list_filter = ("category", "country")
    search_fields = ("name", "country__name", "category__name")
