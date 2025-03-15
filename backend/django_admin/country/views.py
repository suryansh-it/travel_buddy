from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import generics
from .models import AppCategory, TravelApp, Country
from .serializers import AppCategorySerializer, TravelAppSerializer,CountrySerializer

@api_view(['GET'])
def country_page_view(request, country_code):
    country = get_object_or_404(Country, code=country_code.upper())

    # Serialize the country with its categories & apps
    serializer = CountrySerializer(country)

    # Add extra UI-related fields
    data = serializer.data
    data.update({
        "search_filter": {
            "search_placeholder": "Search for apps...",
            "categories": [category["name"] for category in data["curated_app_categories"]]
        },
        "selected_apps_panel": {
            "selected_apps": [],
            "generate_qr_button": "Generate QR Code"
        }
    })

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
