from django.urls import path
from .views import homepage_view, homepage_search_view, submit_country_suggestion, submit_feedback

urlpatterns = [
    path('', homepage_view, name='homepage'),
    path("search/", homepage_search_view, name="homepage_search"),
    path("suggest-country/", submit_country_suggestion, name="submit_country_suggestion"),
    path("feedback/", submit_feedback, name="submit_feedback"),
]