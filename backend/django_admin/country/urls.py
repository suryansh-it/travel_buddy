from django.urls import path
from .views import country_page_view, AppCategoryListView, TravelAppListView

urlpatterns = [
    path("<str:country_code>/", country_page_view, name="country_page"),
    path("categories/", AppCategoryListView.as_view(), name="categories"),
    path("apps/", TravelAppListView.as_view(), name="apps"),
]
