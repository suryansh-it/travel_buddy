from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import generics
from .models import AppCategory, TravelApp, Country, EmergencyContact
from .serializers import AppCategorySerializer, TravelAppSerializer,CountrySerializer, EssentialsSerializer
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.utils.decorators import method_decorator
from django.core.cache import cache

CACHE_TTL = 60 * 60  # 1h

@api_view(["GET"])
def country_page_view(request, country_code):
    key = f"country_page_{country_code.upper()}"
    data = cache.get(key)
    if data is None:
        country = get_object_or_404(Country, code=country_code.upper())
        data = CountrySerializer(country).data
        # add your extra UI bits:
        data.update({
            "search_filter": {
                "search_placeholder": "Search for apps…",
                "categories": [c["name"] for c in data["curated_app_categories"]],
            },
            "selected_apps_panel": {
                "selected_apps": [],
                "generate_qr_button": "Generate QR Code",
            },
            "add_to_list_url": "/api/personalized_list/personalized-list/",
        })
        cache.set(key, data, CACHE_TTL)

    return Response(data)

# ✅ API to fetch all categories
# @method_decorator(cache_page(60 * 15), name="dispatch")  # 15m cache
class AppCategoryListView(generics.ListAPIView):
    queryset = AppCategory.objects.all()
    serializer_class = AppCategorySerializer


# ✅ API to fetch all travel apps (with optional filtering by category)

class TravelAppListView(generics.ListAPIView):
    serializer_class = TravelAppSerializer
    CACHE_TTL = 15 * 60  # 15m

    def list(self, request, *args, **kwargs):
        country_code = self.kwargs["country_code"].upper()
        key = f"country_apps_{country_code}"
        apps_data = cache.get(key)
        if apps_data is None:
            qs = TravelApp.objects.filter(country__code=country_code)
            # optional category filter
            cat = request.query_params.get("category")
            if cat:
                qs = qs.filter(category__name__iexact=cat)
            qs = qs.order_by("-is_sponsored", "name")
            apps_data = TravelAppSerializer(qs, many=True).data
            cache.set(key, apps_data, self.CACHE_TTL)

        return Response(apps_data)


@api_view(["GET"])
def country_essentials_view(request, country_code):
    key = f"country_essentials_{country_code.upper()}"
    essentials = cache.get(key)
    if essentials is None:
        country = get_object_or_404(Country, code=country_code.upper())
        essentials = EssentialsSerializer(country).data
        cache.set(key, essentials, 2 * 60 * 60)  # 2h
    return Response(essentials)