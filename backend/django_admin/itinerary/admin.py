from django.contrib import admin

from django.contrib import admin
from .models import Itinerary, Stop, LegSuggestionRule

@admin.register(Itinerary)
class ItineraryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    inlines = []

@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ['itinerary', 'name', 'stop_type', 'order']
    list_filter = ['stop_type', 'itinerary']

@admin.register(LegSuggestionRule)
class LegSuggestionRuleAdmin(admin.ModelAdmin):
    list_display = ['stop_type']
    filter_horizontal = ['categories']

