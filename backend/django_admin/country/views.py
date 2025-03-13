from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import generics
from .models import AppCategory, TravelApp, Country
from .serializers import AppCategorySerializer, TravelAppSerializer,CountrySerializer

@api_view(['GET'])
def country_page_view(request, country_code):
    country = get_object_or_404(Country, code=country_code.upper())
    serializer = CountrySerializer(country)

    # Fetch all categories available in this country
    categories = AppCategory.objects.filter(apps__country=country).distinct()

    # Fetch all apps for this country
    apps = TravelApp.objects.filter(country=country)

    data = {
        "country_header": {
            "flag": country.flag.url if country.flag else None,
            "name": country.name,
            "description": country.description
        },
        "curated_app_categories": [category.name for category in categories],
        "app_cards": [
            {
                "name": app.name,
                "description": app.description,
                "platforms": ["iOS" if app.ios_link else None, "Android" if app.android_link else None],
                "icon": app.icon_url,
                "ios_link": app.ios_link,
                "android_link": app.android_link,
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
    return Response(serializer.data)

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
