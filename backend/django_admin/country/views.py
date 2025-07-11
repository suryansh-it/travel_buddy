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
from .utils import safe_cache_get, safe_cache_set
from django.db.models import Prefetch

CACHE_TTL = 60*60  # 1h


@api_view(["GET"])
def country_page_view(request, country_code):
    key = f"country_page_{country_code.upper()}"
    data = safe_cache_get(key)
    if data is None:
        # 1) fetch the country
        country = get_object_or_404(Country, code=country_code.upper())

        # 2) build a queryset of *only* this country's apps,
        #    and select_related their category to avoid per-object queries:
        apps_qs = TravelApp.objects.filter(country=country).select_related("category")

        # 3) prefetch those apps into each category as 'apps_for_country'
        category_qs = AppCategory.objects.filter(apps__in=apps_qs).distinct().prefetch_related(
            Prefetch("apps", queryset=apps_qs, to_attr="apps_for_country")
        )

        # 4) Pass that category_qs into the serializer via context
        serializer = CountrySerializer(country, context={"categories_qs": category_qs})
        data = serializer.data

        # 5) your existing UI extras & caching
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
        safe_cache_set(key, data, CACHE_TTL)

    return Response(data)


# ✅ API to fetch all categories
# @method_decorator(cache_page(60 * 15), name="dispatch")  # 15m cache
class AppCategoryListView(generics.ListAPIView):
    queryset = AppCategory.objects.all()
    serializer_class = AppCategorySerializer


# ✅ API to fetch all travel apps (with optional filtering by category)

class TravelAppListView(generics.ListAPIView):
    serializer_class = TravelAppSerializer
    CACHE_TTL = 15*60

    def list(self, request, *args, **kwargs):
        cc = self.kwargs["country_code"].upper()
        key = f"country_apps_{cc}"
        apps_data = safe_cache_get(key)
        if apps_data is None:
            qs = TravelApp.objects.filter(country__code=cc)
            cat = request.query_params.get("category")
            if cat:
                qs = qs.filter(category__name__iexact=cat)
            qs = qs.order_by("-is_sponsored", "name")
            apps_data = TravelAppSerializer(qs, many=True).data
            safe_cache_set(key, apps_data, self.CACHE_TTL)
        return Response(apps_data)


@api_view(["GET"])
def country_essentials_view(request, country_code):
    key = f"country_essentials_{country_code.upper()}"
    essential = safe_cache_get(key)
    if essential is None:
        country = get_object_or_404(Country, code=country_code.upper())
        essential = EssentialsSerializer(country).data
        safe_cache_set(key, essential, 2*60*60)
    return Response(essential)