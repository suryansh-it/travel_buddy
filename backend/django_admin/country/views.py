from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Prefetch

from .models import Country, AppCategory, TravelApp
from .serializers import CountrySerializer, EssentialsSerializer
from .utils import safe_cache_get, safe_cache_set

CACHE_TTL = 60 * 60  # 1h

@api_view(["GET"])
def country_page_view(request, country_code):
    cache_key = f"country_page_{country_code.upper()}"
    data = safe_cache_get(cache_key)
    if data is None:
        country = get_object_or_404(Country, code=country_code.upper())

        # Prefetch only the categories used by this country, and only this country's apps
        apps_qs = TravelApp.objects.filter(country=country).select_related("category")
        categories_qs = (
            AppCategory.objects
            .filter(apps__in=apps_qs)
            .distinct()
            .prefetch_related(
                Prefetch("apps", queryset=apps_qs, to_attr="apps_for_country")
            )
        )

        serializer = CountrySerializer(
            country,
            context={"categories_qs": categories_qs}
        )
        payload = serializer.data

        # Add UI-specific extras
        payload.update({
            "search_filter": {
                "search_placeholder": "Search for apps…",
                "categories": [c["name"] for c in payload["curated_app_categories"]],
            },
            "selected_apps_panel": {
                "selected_apps": [],
                "generate_qr_button": "Generate QR Code",
            },
            "add_to_list_url": "/api/personalized_list/personalized-list/",
        })

        safe_cache_set(cache_key, payload, CACHE_TTL)
        data = payload

    return Response(data)

@api_view(["GET"])
def country_essentials_view(request, country_code):
    cache_key = f"country_essentials_{country_code.upper()}"
    data = safe_cache_get(cache_key)
    if data is None:
        country = get_object_or_404(Country, code=country_code.upper())
        data = EssentialsSerializer(country).data
        safe_cache_set(cache_key, data, 2 * 60 * 60)
    return Response(data)
