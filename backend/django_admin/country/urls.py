from django.urls import path
from .views import (
    country_page_view,
    country_visit_view,
    popular_countries_view,
    AppCategoryListView,
    TravelAppListView,
    country_essentials_view,
    country_services_view,
    country_travel_updates_view,
    app_traveler_insights_view,
)

urlpatterns = [
    path("popular/", popular_countries_view, name="popular_countries"),
    path("<str:country_code>/visit/", country_visit_view, name="country_visit"),
    path("<str:country_code>/", country_page_view, name="country_page"),
    path("<str:country_code>/categories/", AppCategoryListView.as_view(), name="country_categories"),  # ✅ Country-specific categories
    path("<str:country_code>/apps/", TravelAppListView.as_view(), name="country_apps"),  # ✅ Country-specific apps
    
    path("<str:country_code>/essentials/", country_essentials_view, name="country_essentials"),
    path("<str:country_code>/services/", country_services_view, name="country_services"),
    path("<str:country_code>/travel-updates/", country_travel_updates_view, name="country_travel_updates"),
    path("<str:country_code>/apps/<int:app_id>/insights/", app_traveler_insights_view, name="app_traveler_insights"),
]

