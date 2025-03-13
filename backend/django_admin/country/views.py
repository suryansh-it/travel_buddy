from django.shortcuts import get_list_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import generics
from .models import AppCategory, TravelApp
from .serializers import AppCategorySerializer, TravelAppSerializer

@api_view(['GET'])
def country_page_view(request, country_code):
    """
    Fetch travel apps and categories dynamically for the selected country.
    """
    categories = AppCategory.objects.all()
    apps = TravelApp.objects.all()

    data = {
        "country_header": {
            "flag": f"{country_code}.png",
            "name": country_code.upper(),
            "description": f"Explore top apps for {country_code.capitalize()}"
        },
        "curated_app_categories": [category.name for category in categories],
        "app_cards": [
            {
                "name": app.name,
                "description": app.description,
                "platforms": ["iOS" if app.ios_link else "", "Android" if app.android_link else ""],
                "icon": app.icon_url
            }
            for app in apps
        ],
        "search_filter": {
            "search_placeholder": "Search for apps...",
            "categories": [category.name for category in categories]
        },
        "selected_apps_panel": {
            "selected_apps": [],
            "generate_qr_button": "Generate QR Code"
        }
    }
    return Response(data)

# ✅ API to fetch all categories
class AppCategoryListView(generics.ListAPIView):
    queryset = AppCategory.objects.all()
    serializer_class = AppCategorySerializer

# ✅ API to fetch all travel apps (with optional filtering by category)
class TravelAppListView(generics.ListAPIView):
    serializer_class = TravelAppSerializer

    def get_queryset(self):
        """
        Fetch apps filtered by category if a query parameter is provided.
        Example: /api/apps/?category=Navigation
        """
        category_name = self.request.query_params.get('category', None)
        if category_name:
            return TravelApp.objects.filter(category__name=category_name)
        return TravelApp.objects.all()
