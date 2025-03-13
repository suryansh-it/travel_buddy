from django.urls import path
from .views import homepage_view, homepage_search_view

urlpatterns = [
    path('', homepage_view, name='homepage'),
    path("search/", homepage_search_view, name="homepage_search"),
]