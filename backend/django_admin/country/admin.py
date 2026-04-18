from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Country, AppCategory, TravelApp, AppScreenshot, Review, 
    OriginCountryAssistance, EmergencyContact, LocalPhrase, UsefulTip
)
from django.urls import reverse

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'flag_preview', 'description')
    search_fields = ('name', 'code')
    list_filter = ('name',)
    
    def flag_preview(self, obj):
        if obj.flag:
            return format_html('<img src="{}" width="40" height="25" style="border:1px solid #ddd"/>', obj.flag.url)
        return "No Flag"
    flag_preview.short_description = "Flag"



@admin.register(AppCategory)
class AppCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(TravelApp)
class TravelAppAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'country', 'supports_foreign_cards', 'works_offline', "is_sponsored")
    search_fields = ('name', 'category__name', 'country__name',)
    list_filter = ('category', 'country', 'supports_foreign_cards', 'works_offline',  "is_sponsored")
    list_editable = ('supports_foreign_cards', 'works_offline')
    raw_id_fields = ('category', 'country')  # Optimized selection for large data
    ordering = ("-is_sponsored", "name")  # bring sponsored to top

@admin.register(AppScreenshot)
class AppScreenshotAdmin(admin.ModelAdmin):
    list_display = ('app', 'image_preview')

    def image_preview(self, obj):
        return format_html('<img src="{}" width="100" height="60" style="border:1px solid #ddd"/>', obj.image_url)
    image_preview.short_description = "Screenshot"

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('app', 'user_id', 'rating', 'created_at')
    search_fields = ('app__name', 'user_id')
    list_filter = ('rating', 'created_at')


@admin.register(OriginCountryAssistance)
class OriginCountryAssistanceAdmin(admin.ModelAdmin):
    list_display = ('country', 'label', 'emergency_phone', 'website', 'source', 'fetched_at')
    search_fields = ('country__code', 'country__name', 'label', 'source')
    list_filter = ('source', 'fetched_at')

@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ('country', 'name', 'phone', 'email', 'description')
    search_fields = ('country__name', 'name', 'phone')
    list_filter = ('country',)
    raw_id_fields = ('country',)

@admin.register(LocalPhrase)
class LocalPhraseAdmin(admin.ModelAdmin):
    list_display = ('country', 'original', 'translation', 'context_note')
    search_fields = ('country__name', 'original', 'translation')
    list_filter = ('country',)
    raw_id_fields = ('country',)

@admin.register(UsefulTip)
class UsefulTipAdmin(admin.ModelAdmin):
    list_display = ('country', 'tip')
    search_fields = ('country__name', 'tip')
    list_filter = ('country',)
    raw_id_fields = ('country',)
