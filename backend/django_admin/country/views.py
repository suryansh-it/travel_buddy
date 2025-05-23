from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import generics
from .models import AppCategory, TravelApp, Country, EmergencyContact
from .serializers import AppCategorySerializer, TravelAppSerializer,CountrySerializer, EmergencyContactSerializer

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
        },
        "add_to_list_url": "/api/personalized_list/personalized-list/" # ✅ API to send selected apps
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
        Fetch all travel apps for a given country, ordered by is_sponsored.
        Optionally filter by category via ?category=Navigation
        """
        country_code = self.kwargs.get("country_code").upper()
        queryset = TravelApp.objects.filter(country__code=country_code)

        category_name = self.request.query_params.get("category")
        if category_name:
            queryset = queryset.filter(category__name__iexact=category_name)

        return queryset.order_by("-is_sponsored", "name")

@api_view(["GET"])
def emergency_contacts_view(request, country_code):
    country = get_object_or_404(Country, code=country_code.upper())
    contacts = EmergencyContact.objects.filter(country=country)
    serializer = EmergencyContactSerializer(contacts, many=True)
    return Response({"emergencies": serializer.data})