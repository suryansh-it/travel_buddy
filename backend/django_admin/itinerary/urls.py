from django.urls import path
from .views import LegSuggestionsView

urlpatterns = [
    path('<int:itinerary_id>/leg-suggestions/', LegSuggestionsView.as_view(), name='leg_suggestions'),
]
