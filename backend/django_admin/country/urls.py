from django.urls import path
from .views import country_page_view, AppCategoryListView, TravelAppListView, emergency_contacts_view

urlpatterns = [
    path("<str:country_code>/", country_page_view, name="country_page"),
    path("<str:country_code>/categories/", AppCategoryListView.as_view(), name="country_categories"),  # ✅ Country-specific categories
    path("<str:country_code>/apps/", TravelAppListView.as_view(), name="country_apps"),  # ✅ Country-specific apps
    path("<str:country_code>/emergency/", emergency_contacts_view, name="emergency_contacts"),

]

