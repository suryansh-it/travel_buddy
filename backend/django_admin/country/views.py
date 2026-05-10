from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import generics
from .models import AppCategory, TravelApp, Country, CountryVisit, EmergencyContact, OriginCountryAssistance, CountryServiceProvider
from .serializers import AppCategorySerializer, TravelAppSerializer, CountrySerializer, EssentialsSerializer
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.utils.decorators import method_decorator
from django.core.cache import cache
from .utils import safe_cache_get, safe_cache_set
from django.db.models import Prefetch
from django.db.models import F
from django.db import transaction
from urllib.parse import quote, urlparse, parse_qs, urlencode
from collections import Counter
from pathlib import Path
import csv
import re
import json
import time
import random
import threading


CACHE_TTL = 60 * 60  # 1h

POPULAR_COUNTRIES_LIMIT = 6
POPULAR_COUNTRY_FALLBACK_CODES = ["TH", "FR", "US", "JP", "AU", "IT"]

# Freshness windows
TRAVEL_UPDATES_FRESH_TTL = 10 * 60          # 10 min fresh window
TRAVEL_WEATHER_FRESH_TTL = 30 * 60         # 30 min fresh window
TRAVELER_INSIGHTS_FRESH_TTL = 12 * 60 * 60 # 12h fresh window

# Storage TTLs (keep stale payload available for quick responses)
TRAVEL_UPDATES_STORAGE_TTL = 6 * 60 * 60   # 6h
TRAVELER_INSIGHTS_STORAGE_TTL = 24 * 60 * 60  # 24h

# Cooldowns and locks to avoid duplicate/storm refreshes
TRAVEL_UPDATES_REFRESH_COOLDOWN = 5 * 60   # 5 min
TRAVELER_INSIGHTS_REFRESH_COOLDOWN = 30 * 60  # 30 min
REFRESH_LOCK_TTL = 120

# Hard per-source hourly call caps (defensive limits for free sources)
SOURCE_HOURLY_CAPS = {
    "google_news": 180,
    "eonet": 120,
    "gov_state": 120,
    "gov_cdc": 120,
    "google_play": 120,
    "apple_app_store": 120,
    "reddit": 120,
}


def _now_ts():
    return int(time.time())


def _payload_fetched_at(payload):
    if not isinstance(payload, dict):
        return 0
    return int(payload.get("_meta", {}).get("fetched_at") or 0)


def _is_fresh(payload, ttl_seconds):
    fetched_at = _payload_fetched_at(payload)
    if fetched_at <= 0:
        return False
    return (_now_ts() - fetched_at) < ttl_seconds


def _source_hour_key(source):
    return f"source_hourly_calls:{source}:{_now_ts() // 3600}"


def _reserve_source_call(source):
    """Best-effort source hourly limiter. Returns True if call is allowed."""
    cap = SOURCE_HOURLY_CAPS.get(source)
    if not cap:
        return True

    key = _source_hour_key(source)
    try:
        # Seed key if missing and keep slightly beyond the hour boundary.
        cache.add(key, 0, timeout=3900)
        current = cache.incr(key)
        return int(current) <= int(cap)
    except Exception:
        # Fail open to avoid hard outages if cache backend has issues.
        return True


def _with_refresh_lock(lock_key):
    try:
        return cache.add(lock_key, 1, timeout=REFRESH_LOCK_TTL)
    except Exception:
        return True


def _set_cooldown(cooldown_key, cooldown_seconds):
    try:
        cache.set(cooldown_key, _now_ts(), timeout=cooldown_seconds)
    except Exception:
        pass


def _cooldown_active(cooldown_key):
    try:
        return cache.get(cooldown_key) is not None
    except Exception:
        return False


def _run_async_with_jitter(refresh_callable, lock_key, cooldown_key, cooldown_seconds, jitter_max_seconds=12):
    """Run refresh callable in a daemon thread with jitter, lock, and cooldown safeguards."""
    if _cooldown_active(cooldown_key):
        return False
    if not _with_refresh_lock(lock_key):
        return False

    def _runner():
        try:
            # Jitter prevents synchronized thundering herd.
            time.sleep(random.uniform(0.25, float(jitter_max_seconds)))
            refresh_callable()
            _set_cooldown(cooldown_key, cooldown_seconds)
        except Exception:
            # Intentionally swallow; stale payload will continue serving.
            pass

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    return True


def _record_country_visit(country):
    with transaction.atomic():
        visit_stats, _ = CountryVisit.objects.select_for_update().get_or_create(
            country=country,
            defaults={"visit_count": 0},
        )
        CountryVisit.objects.filter(pk=visit_stats.pk).update(
            visit_count=F("visit_count") + 1,
        )


def _serialize_country_card(country, visit_count=0):
    return {
        "code": country.code,
        "name": country.name,
        "description": country.description or "",
        "flag": country.flag.url if country.flag else None,
        "visit_count": int(visit_count or 0),
    }


SERVICE_SECTION_META = {
    "esim": {"title": "eSIM & Connectivity", "icon": "bolt", "accent": "from-cyan-500 to-blue-500", "border": "border-cyan-200", "badge": "bg-cyan-100 text-cyan-700"},
    "insurance": {"title": "Travel Insurance", "icon": "shield", "accent": "from-rose-500 to-orange-500", "border": "border-rose-200", "badge": "bg-rose-100 text-rose-700"},
    "booking": {"title": "Booking Platforms", "icon": "hotel", "accent": "from-emerald-500 to-teal-500", "border": "border-emerald-200", "badge": "bg-emerald-100 text-emerald-700"},
    "utilities": {"title": "Other Useful Services", "icon": "globe", "accent": "from-violet-500 to-fuchsia-500", "border": "border-violet-200", "badge": "bg-violet-100 text-violet-700"},
}


def _serialize_service_provider(provider):
    return {
        "id": provider.id,
        "name": provider.name,
        "priceFrom": provider.price_from,
        "coverage": provider.coverage,
        "support": provider.support,
        "refund": provider.refund,
        "site": provider.site,
        "isFeatured": provider.is_featured,
        "notes": provider.notes,
    }


@api_view(["POST"])
def country_visit_view(request, country_code):
    country = get_object_or_404(Country, code=country_code.upper())
    _record_country_visit(country)
    stats = CountryVisit.objects.filter(country=country).values_list("visit_count", flat=True).first() or 0
    return Response(_serialize_country_card(country, stats))


@api_view(["GET"])
def popular_countries_view(request):
    limit = request.query_params.get("limit") or POPULAR_COUNTRIES_LIMIT
    try:
        limit = max(1, min(int(limit), POPULAR_COUNTRIES_LIMIT))
    except (TypeError, ValueError):
        limit = POPULAR_COUNTRIES_LIMIT

    visits = list(
        CountryVisit.objects.select_related("country")
        .filter(visit_count__gt=0)
        .order_by("-visit_count", "country__name")[:limit]
    )

    seen_codes = []
    payload = []
    for item in visits:
        seen_codes.append(item.country.code)
        payload.append(_serialize_country_card(item.country, item.visit_count))

    if len(payload) < limit:
        fallback_countries = list(
            Country.objects.filter(code__in=POPULAR_COUNTRY_FALLBACK_CODES)
            .exclude(code__in=seen_codes)
            .order_by("name")[: limit - len(payload)]
        )
        payload.extend(_serialize_country_card(country, 0) for country in fallback_countries)

    return Response(payload)


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


@api_view(["GET"])
def country_services_view(request, country_code):
    country = get_object_or_404(Country, code=country_code.upper())
    visit_count = CountryVisit.objects.filter(country=country).values_list("visit_count", flat=True).first() or 0
    providers = CountryServiceProvider.objects.filter(country=country).order_by("section", "-is_featured", "name")
    grouped = {key: [] for key in SERVICE_SECTION_META.keys()}

    for provider in providers:
        grouped.setdefault(provider.section, []).append(_serialize_service_provider(provider))

    sections = []
    for key in ["esim", "insurance", "booking", "utilities"]:
        meta = SERVICE_SECTION_META[key]
        sections.append(
            {
                "key": key,
                "title": meta["title"],
                "icon": meta["icon"],
                "accent": meta["accent"],
                "border": meta["border"],
                "badge": meta["badge"],
                "providers": grouped.get(key, []),
            }
        )

    return Response(
        {
            "country": _serialize_country_card(country, visit_count),
            "sections": sections,
        }
    )


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
    country_code = country_code.upper()
    origin_code = str(request.query_params.get("origin_country") or "").strip().upper()
    key = f"country_essentials_{country_code}"
    essential = safe_cache_get(key)
    if essential is None:
        country = get_object_or_404(Country, code=country_code)
        essential = EssentialsSerializer(country).data
        essential["embassy_contacts"] = _load_embassy_contacts(country_code)
        safe_cache_set(key, essential, 2*60*60)
    elif "embassy_contacts" not in essential:
        essential["embassy_contacts"] = _load_embassy_contacts(country_code)
        safe_cache_set(key, essential, 2*60*60)

    payload = dict(essential)
    payload["origin_assistance"] = _get_or_fetch_origin_assistance(origin_code)
    return Response(payload)


ORIGIN_ASSISTANCE_SEED = {
    "US": {
        "label": "U.S. Department of State",
        "emergency_phone": "+1-888-407-4747",
        "emergency_phone_intl": "+1-202-501-4444",
        "consular_address": "2201 C St NW, Washington, DC 20520, USA",
        "website": "https://travel.state.gov/content/travel/en/international-travel/emergencies.html",
        "mission_finder": "https://www.usembassy.gov/",
        "source": "curated_seed",
    },
    "IN": {
        "label": "India Ministry of External Affairs",
        "emergency_phone": "+91-11-23012113",
        "emergency_phone_intl": "",
        "consular_address": "South Block, Raisina Hill, New Delhi 110011, India",
        "website": "https://www.mea.gov.in/consular-services.htm",
        "mission_finder": "https://www.mea.gov.in/indian-missions-abroad-new.htm",
        "source": "curated_seed",
    },
    "GB": {
        "label": "UK Foreign, Commonwealth & Development Office",
        "emergency_phone": "+44-20-7008-5000",
        "emergency_phone_intl": "",
        "consular_address": "King Charles St, London SW1A 2AH, United Kingdom",
        "website": "https://www.gov.uk/guidance/get-help-if-youre-abroad",
        "mission_finder": "https://www.gov.uk/world/embassies",
        "source": "curated_seed",
    },
    "AU": {
        "label": "Australian Consular Services",
        "emergency_phone": "+61-2-6261-3305",
        "emergency_phone_intl": "",
        "consular_address": "R.G. Casey Building, John McEwen Cres, Barton ACT 0221, Australia",
        "website": "https://www.smartraveller.gov.au/consular-services",
        "mission_finder": "https://www.smartraveller.gov.au/consular-services/where-get-consular-assistance",
        "source": "curated_seed",
    },
    "CA": {
        "label": "Global Affairs Canada",
        "emergency_phone": "+1-613-996-8885",
        "emergency_phone_intl": "",
        "consular_address": "125 Sussex Dr, Ottawa, ON K1A 0G2, Canada",
        "website": "https://travel.gc.ca/assistance/emergency-assistance",
        "mission_finder": "https://travel.gc.ca/assistance/embassies-consulates",
        "source": "curated_seed",
    },
}


def _serialize_origin_assistance(profile):
    if not profile:
        return None
    return {
        "label": profile.label,
        "emergency_phone": profile.emergency_phone,
        "emergency_phone_intl": profile.emergency_phone_intl,
        "consular_address": profile.consular_address,
        "website": profile.website,
        "mission_finder": profile.mission_finder,
        "source": profile.source,
    }


def _fetch_origin_assistance_from_wikidata(country_code):
    from urllib.request import Request, urlopen

    query = f'''
    SELECT ?countryLabel ?ministryLabel ?website ?phone ?hqLabel WHERE {{
      ?country wdt:P297 "{country_code}".
      OPTIONAL {{ ?ministry wdt:P31/wdt:P279* wd:Q83307; wdt:P17 ?country. }}
      OPTIONAL {{ ?ministry wdt:P856 ?website. }}
      OPTIONAL {{ ?ministry wdt:P1329 ?phone. }}
      OPTIONAL {{ ?ministry wdt:P159 ?hq. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 3
    '''

    endpoint = f"https://query.wikidata.org/sparql?format=json&query={quote(query)}"
    req = Request(endpoint, headers={"Accept": "application/sparql-results+json", "User-Agent": "TripBozo/1.0 (origin-assistance)"})

    with urlopen(req, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    bindings = payload.get("results", {}).get("bindings", [])
    if not bindings:
        return None

    row = bindings[0]
    label = row.get("ministryLabel", {}).get("value") or row.get("countryLabel", {}).get("value") or f"{country_code} Foreign Affairs"
    website = row.get("website", {}).get("value", "")
    phone = row.get("phone", {}).get("value", "")
    hq = row.get("hqLabel", {}).get("value", "")

    if not any([label, website, phone, hq]):
        return None

    return {
        "label": label,
        "emergency_phone": phone,
        "emergency_phone_intl": "",
        "consular_address": hq,
        "website": website,
        "mission_finder": "",
        "source": "wikidata",
    }


def _fetch_origin_assistance_from_nominatim(country_name):
    """Fallback source using OSM Nominatim POI metadata for foreign affairs offices."""
    from urllib.request import Request, urlopen

    if not country_name:
        return None

    params = urlencode(
        {
            "q": f"Ministry of Foreign Affairs {country_name}",
            "format": "jsonv2",
            "limit": 5,
            "addressdetails": 1,
            "extratags": 1,
            "namedetails": 1,
        }
    )
    endpoint = f"https://nominatim.openstreetmap.org/search?{params}"
    req = Request(
        endpoint,
        headers={
            "Accept": "application/json",
            "User-Agent": "TripBozo/1.0 (origin-assistance)",
        },
    )

    with urlopen(req, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, list) or not payload:
        return None

    country_key = re.sub(r"[^a-z]", "", country_name.lower())
    best = None
    best_score = -1

    for item in payload:
        display_name = str(item.get("display_name") or "")
        lowered = display_name.lower()
        extratags = item.get("extratags") or {}
        website = str(extratags.get("website") or extratags.get("contact:website") or "").strip()
        phone = str(extratags.get("phone") or extratags.get("contact:phone") or "").strip()
        name = str((item.get("namedetails") or {}).get("name") or item.get("name") or "").strip()

        score = 0
        if re.search(r"foreign|external|diplomat|consular|embassy", lowered):
            score += 3
        if country_key and country_key in re.sub(r"[^a-z]", "", lowered):
            score += 2
        if website:
            score += 2
        if phone:
            score += 1

        if score > best_score:
            best_score = score
            best = {
                "label": name or f"{country_name} Foreign Affairs",
                "emergency_phone": phone,
                "emergency_phone_intl": "",
                "consular_address": display_name,
                "website": website,
                "mission_finder": website,
                "source": "osm_nominatim",
            }

    if not best:
        return None

    if not any([best.get("label"), best.get("website"), best.get("emergency_phone"), best.get("consular_address")]):
        return None
    return best


def _get_or_fetch_origin_assistance(origin_code):
    if not origin_code:
        return None

    country = Country.objects.filter(code=origin_code).first()
    if not country:
        return None

    existing = OriginCountryAssistance.objects.filter(country=country).first()
    if existing:
        return _serialize_origin_assistance(existing)

    fetched = ORIGIN_ASSISTANCE_SEED.get(origin_code)
    if fetched is None:
        try:
            fetched = _fetch_origin_assistance_from_wikidata(origin_code)
        except Exception:
            fetched = None

    # Second web fallback: OSM Nominatim, useful when Wikidata is sparse.
    if fetched is None:
        try:
            fetched = _fetch_origin_assistance_from_nominatim(country.name)
        except Exception:
            fetched = None

    if not fetched:
        return None

    profile = OriginCountryAssistance.objects.create(
        country=country,
        label=fetched.get("label") or f"{country.name} Foreign Affairs",
        emergency_phone=fetched.get("emergency_phone") or "",
        emergency_phone_intl=fetched.get("emergency_phone_intl") or "",
        consular_address=fetched.get("consular_address") or "",
        website=fetched.get("website") or "",
        mission_finder=fetched.get("mission_finder") or "",
        source=fetched.get("source") or "",
    )
    return _serialize_origin_assistance(profile)


def _load_embassy_contacts(country_code):
    """Load and normalize embassy address/phone pairs for a destination country."""
    csv_path = Path(__file__).resolve().parent / "management" / "commands" / "embassy_contacts.csv"
    if not csv_path.exists():
        return []

    grouped = {}
    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_country = str(row.get("country_code") or "").strip().upper()
                if row_country != country_code:
                    continue

                raw_name = str(row.get("name") or "").strip()
                raw_value = str(row.get("phone") or "").strip()
                origin_country = str(row.get("description") or "").strip()
                if not (raw_name and raw_value):
                    continue

                kind = ""
                if raw_name.lower().endswith(" address"):
                    kind = "address"
                elif raw_name.lower().endswith(" phone"):
                    kind = "phone"

                base_name = re.sub(r"\s+(Address|Phone)$", "", raw_name, flags=re.IGNORECASE).strip()
                key = f"{origin_country.lower()}::{base_name.lower()}"
                entry = grouped.setdefault(
                    key,
                    {
                        "name": base_name or raw_name,
                        "origin_country": origin_country,
                        "address": "",
                        "phone": "",
                    },
                )

                if kind == "address":
                    entry["address"] = raw_value
                elif kind == "phone":
                    entry["phone"] = raw_value
                else:
                    # Fallback if the row label format changes.
                    if not entry["phone"]:
                        entry["phone"] = raw_value

    except Exception:
        return []

    contacts = list(grouped.values())
    contacts.sort(key=lambda item: (item.get("origin_country") or "", item.get("name") or ""))
    return contacts


def _strip_xml_text(value=""):
    return (
        str(value)
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )


def _extract_rss_tag(xml, tag):
    match = re.search(rf"<{tag}>([\s\S]*?)</{tag}>", xml, re.IGNORECASE)
    if not match:
        return ""
    value = match.group(1)
    value = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", value)
    value = re.sub(r"<[^>]*>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return _strip_xml_text(value)


def _classify_update(title="", description=""):
    text = f"{title} {description}".lower()
    if re.search(r"storm|weather|hurricane|typhoon|cyclone|flood|wildfire|earthquake", text):
        return "Weather / emergency"
    if re.search(r"emergency|warning|advisory|security|protest|unrest|disruption", text):
        return "Travel alert"
    if re.search(r"festival|holiday|parade|celebration|carnival|event", text):
        return "Festival / crowd"
    return "Travel news"


def _summarize_impact(items):
    text = " ".join([f"{i.get('title', '')} {i.get('description', '')}".lower() for i in items])
    if re.search(r"storm|weather|hurricane|typhoon|cyclone|flood|wildfire|earthquake|emergency|warning|advisory", text):
        return {
            "label": "Monitor closely",
            "note": "There are travel-impacting alerts in the latest news scan. Check timing before booking or leaving.",
        }
    if re.search(r"festival|holiday|parade|celebration|carnival|event", text):
        return {
            "label": "Expect crowds",
            "note": "Festivals and major events may affect prices, traffic, and hotel availability.",
        }
    return {
        "label": "Travel window looks open",
        "note": "No major disruption signals surfaced in the latest travel news scan.",
    }


def _weather_code_info(code):
    mapping = {
        0: ("Clear sky", "☀️"),
        1: ("Mostly clear", "🌤️"),
        2: ("Partly cloudy", "⛅"),
        3: ("Overcast", "☁️"),
        45: ("Fog", "🌫️"),
        48: ("Rime fog", "🌫️"),
        51: ("Light drizzle", "🌦️"),
        53: ("Drizzle", "🌦️"),
        55: ("Heavy drizzle", "🌧️"),
        56: ("Freezing drizzle", "🌧️"),
        57: ("Freezing drizzle", "🌧️"),
        61: ("Light rain", "🌧️"),
        63: ("Rain", "🌧️"),
        65: ("Heavy rain", "🌧️"),
        66: ("Freezing rain", "🌧️"),
        67: ("Freezing rain", "🌧️"),
        71: ("Light snow", "🌨️"),
        73: ("Snow", "🌨️"),
        75: ("Heavy snow", "🌨️"),
        77: ("Snow grains", "🌨️"),
        80: ("Rain showers", "🌦️"),
        81: ("Rain showers", "🌧️"),
        82: ("Violent rain showers", "⛈️"),
        85: ("Snow showers", "🌨️"),
        86: ("Heavy snow showers", "🌨️"),
        95: ("Thunderstorm", "⛈️"),
        96: ("Thunderstorm with hail", "⛈️"),
        99: ("Thunderstorm with hail", "⛈️"),
    }
    return mapping.get(int(code) if str(code).isdigit() else -1, ("Weather", "🌡️"))


def _temperature_band_condition(temp_value):
    try:
        temp = float(temp_value)
    except Exception:
        return None

    if temp >= 34:
        return "Very hot conditions"
    if temp >= 27:
        return "Warm conditions"
    if temp >= 18:
        return "Mild conditions"
    if temp >= 10:
        return "Cool conditions"
    return "Cold conditions"


def _fetch_country_weather(country_name, country_code=None):
    from urllib.request import Request, urlopen

    country_payload = None
    endpoints = []
    if country_code:
        endpoints.append(f"https://restcountries.com/v3.1/alpha/{quote(str(country_code))}")
    endpoints.append(f"https://restcountries.com/v3.1/name/{quote(str(country_name))}?fullText=true")

    for endpoint in endpoints:
        try:
            req = Request(endpoint, headers={"Accept": "application/json", "User-Agent": "TripBozo/1.0 (travel-updates)"})
            with urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8", errors="ignore"))
            if isinstance(payload, list) and payload:
                country_payload = payload[0]
                break
            if isinstance(payload, dict):
                country_payload = payload
                break
        except Exception:
            continue

    if not isinstance(country_payload, dict):
        return {}

    latlng = country_payload.get("latlng") or []
    if not isinstance(latlng, list) or len(latlng) < 2:
        return {
            "location": str(country_name).strip(),
            "condition": "Weather unavailable",
            "conditions": ["Weather unavailable"],
            "emoji": "🌡️",
            "source": "restcountries",
        }

    latitude, longitude = latlng[0], latlng[1]
    # Sample multiple points around the country's centroid to approximate country-wide conditions.
    sample_points = [
        (latitude, longitude),
        (max(-60.0, min(75.0, latitude + 2.5)), longitude),
        (max(-60.0, min(75.0, latitude - 2.5)), longitude),
        (latitude, max(-179.0, min(179.0, longitude + 3.0))),
        (latitude, max(-179.0, min(179.0, longitude - 3.0))),
    ]

    weather_conditions = []
    climate_conditions = []
    primary_condition = None
    primary_emoji = "🌤️"
    wind_speeds = []

    for idx, (sample_lat, sample_lon) in enumerate(sample_points):
        weather_url = (
            "https://api.open-meteo.com/v1/forecast?"
            f"latitude={sample_lat}&longitude={sample_lon}&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto"
        )

        try:
            req = Request(weather_url, headers={"Accept": "application/json", "User-Agent": "TripBozo/1.0 (travel-updates)"})
            with urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8", errors="ignore"))
        except Exception:
            continue

        current = payload.get("current") or {}
        weather_code = current.get("weather_code")
        weather_text, weather_emoji = _weather_code_info(weather_code)
        if weather_text:
            weather_conditions.append(weather_text)
        climate_band = _temperature_band_condition(current.get("temperature_2m"))
        if climate_band:
            climate_conditions.append(climate_band)

        wind_speed = current.get("wind_speed_10m")
        if isinstance(wind_speed, (int, float)):
            wind_speeds.append(wind_speed)

        if idx == 0:
            primary_condition = weather_text
            primary_emoji = weather_emoji

    ordered = []
    seen = set()
    for condition in weather_conditions + climate_conditions:
        key = str(condition or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(str(condition).strip())

    if not ordered:
        ordered = ["Weather unavailable"]

    if not primary_condition:
        primary_condition = ordered[0]

    return {
        "location": str(country_name).strip(),
        "condition": primary_condition,
        "conditions": ordered[:6],
        "emoji": primary_emoji,
        "windSpeed": round(sum(wind_speeds) / len(wind_speeds), 1) if wind_speeds else None,
        "source": "open-meteo",
    }


def _phrase_pattern(phrase):
    parts = [re.escape(part) for part in str(phrase).strip().split() if part]
    if not parts:
        return None
    separator = r"\s+"
    return rf"\b{separator.join(parts)}\b"


def _country_focus_terms(country_name, country_code=None):
    base_terms = [str(country_name).strip()]
    alias_map = {
        "united states": ["usa", "u.s.", "us", "america", "united states"],
        "united kingdom": ["uk", "u.k.", "britain", "great britain", "united kingdom"],
        "south korea": ["korea", "republic of korea", "south korea"],
        "north korea": ["dprk", "north korea"],
        "united arab emirates": ["uae", "u.a.e.", "emirates", "united arab emirates"],
        "czech republic": ["czechia", "czech republic"],
        "ivory coast": ["cote d'ivoire", "ivory coast"],
    }

    normalized = str(country_name).strip().lower()
    for alias in alias_map.get(normalized, []):
        if alias.lower() not in [term.lower() for term in base_terms]:
            base_terms.append(alias)

    if country_code:
        code = str(country_code).strip().lower()
        if code and code not in [term.lower() for term in base_terms]:
            base_terms.append(code)

    return base_terms


def _text_contains_any(text, phrases):
    haystack = str(text or "")
    for phrase in phrases:
        pattern = _phrase_pattern(phrase)
        if pattern and re.search(pattern, haystack, re.IGNORECASE):
            return True
    return False


def _normalize_update_key(item):
    title = re.sub(r"\s+", " ", str(item.get("title", "")).strip()).lower()
    link = re.sub(r"\s+", " ", str(item.get("link", "")).strip()).lower()
    return f"{title}|{link}"


def _badge_priority(item):
    badge = str(item.get("badge") or "").strip().lower()
    priorities = {
        "government advisory": 6,
        "weather / emergency": 5,
        "travel alert": 4,
        "festival / crowd": 3,
        "travel news": 2,
    }
    return priorities.get(badge, 1)


def _merge_update_items(items):
    merged = {}
    for item in items:
        if not item.get("title"):
            continue
        key = _normalize_update_key(item)
        if key not in merged:
            merged[key] = item
            continue

        current = merged[key]
        incoming_relevance = int(item.get("relevance", 0))
        current_relevance = int(current.get("relevance", 0))
        incoming_priority = _badge_priority(item)
        current_priority = _badge_priority(current)

        if incoming_relevance > current_relevance:
            merged[key] = item
        elif incoming_relevance == current_relevance and incoming_priority > current_priority:
            merged[key] = item
    return list(merged.values())


def _country_terms_with_aliases(country_name, country_code=None):
    terms = _country_focus_terms(country_name, country_code)
    expanded = list(terms)
    for term in terms:
        for part in str(term).replace("/", " ").replace("-", " ").split():
            if len(part) > 2 and part.lower() not in [existing.lower() for existing in expanded]:
                expanded.append(part)
    return expanded


def _query_country_updates(country_name, country_code=None, label="Travel news", keywords=None, source_name="google_news"):
    from urllib.request import Request, urlopen

    if not _reserve_source_call(source_name):
        return []

    keywords = [str(keyword).strip() for keyword in (keywords or []) if str(keyword).strip()]
    if keywords:
        keyword_group = " OR ".join([f'"{keyword}"' if " " in keyword else keyword for keyword in keywords])
        query = f'"{country_name}" ({keyword_group})'
    else:
        query = f'"{country_name}"'
    rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
    req = Request(rss_url, headers={"Accept": "application/rss+xml, application/xml, text/xml"})

    try:
        with urlopen(req, timeout=8) as response:
            xml = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    country_terms = _country_terms_with_aliases(country_name, country_code)
    items = []
    for match in re.finditer(r"<item>([\s\S]*?)</item>", xml):
        chunk = match.group(1)
        title = _extract_rss_tag(chunk, "title")
        if not title:
            continue
        link = _extract_rss_tag(chunk, "link")
        description = _extract_rss_tag(chunk, "description")
        pub_date = _extract_rss_tag(chunk, "pubDate")
        haystack = f"{title} {description}"

        title_has_country = _text_contains_any(title, country_terms)
        description_has_country = _text_contains_any(description, country_terms)
        if not (title_has_country or description_has_country):
            continue

        relevance = 0
        if title_has_country:
            relevance += 4
        if description_has_country:
            relevance += 2
        if re.search(r"travel|tourism|tourist|airport|visa|flight|rail|weather|storm|festival|event|parade|holiday|emergency|advisory|alert|warning|caution|disruption|strike|closure|delay", haystack, re.IGNORECASE):
            relevance += 1

        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "pubDate": pub_date,
                "badge": label,
                "relevance": relevance,
                "source": source_name,
            }
        )
        if len(items) >= 10:
            break

    return items


def _fetch_gov_advisories(country_name, country_code=None):
    from urllib.request import Request, urlopen

    country_terms = _country_terms_with_aliases(country_name, country_code)
    travel_alert_regex = re.compile(
        r"travel|advisory|alert|warning|security|health|outbreak|entry|visa|border|restriction|closure|evacuation",
        re.IGNORECASE,
    )

    sources = [
        {
            "name": "gov_state",
            "url": "https://travel.state.gov/_res/rss/TAsTWs.xml",
            "source_label": "U.S. State Dept",
        },
        {
            "name": "gov_cdc",
            "url": "https://wwwnc.cdc.gov/travel/rss/notices",
            "source_label": "CDC Travel Notices",
        },
    ]

    items = []
    for source in sources:
        if not _reserve_source_call(source["name"]):
            continue

        try:
            req = Request(
                source["url"],
                headers={
                    "Accept": "application/rss+xml, application/xml, text/xml",
                    "User-Agent": "TripBozo/1.0 (travel-updates)",
                },
            )
            with urlopen(req, timeout=8) as response:
                xml = response.read().decode("utf-8", errors="ignore")
        except Exception:
            continue

        for match in re.finditer(r"<item>([\s\S]*?)</item>", xml):
            chunk = match.group(1)
            title = _extract_rss_tag(chunk, "title")
            if not title:
                continue
            link = _extract_rss_tag(chunk, "link")
            description = _extract_rss_tag(chunk, "description")
            pub_date = _extract_rss_tag(chunk, "pubDate")

            haystack = f"{title} {description}"
            title_has_country = _text_contains_any(title, country_terms)
            description_has_country = _text_contains_any(description, country_terms)
            if not (title_has_country or description_has_country):
                continue

            relevance = 0
            if title_has_country:
                relevance += 5
            if description_has_country:
                relevance += 3
            if travel_alert_regex.search(haystack):
                relevance += 2

            items.append(
                {
                    "title": title,
                    "link": link,
                    "description": description,
                    "pubDate": pub_date,
                    "badge": "Government advisory",
                    "relevance": relevance,
                    "source": source["source_label"],
                }
            )

            if len(items) >= 12:
                break

    return items


def _fetch_eonet_updates(country_name, country_code=None):
    from urllib.request import Request, urlopen

    if not _reserve_source_call("eonet"):
        return []

    endpoint = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=50"
    req = Request(endpoint, headers={"Accept": "application/json", "User-Agent": "TripBozo/1.0 (travel-updates)"})

    try:
        with urlopen(req, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
    except Exception:
        return []

    country_terms = _country_terms_with_aliases(country_name, country_code)
    items = []
    for event in payload.get("events", [])[:50]:
        title = str(event.get("title") or "").strip()
        description = str(event.get("description") or "").strip()
        if not title and not description:
            continue

        haystack = f"{title} {description} {json.dumps(event.get('categories', []), ensure_ascii=False)}"
        if not _text_contains_any(haystack, country_terms):
            continue

        categories = event.get("categories") or []
        category_names = " ".join([str(cat.get("title") or cat.get("id") or "") for cat in categories])
        badge = "Weather / emergency"
        if re.search(r"fire|wildfire|volcano|earthquake|flood|storm|drought|landslide|cyclone|typhoon", f"{title} {description} {category_names}", re.IGNORECASE):
            badge = "Weather / emergency"
        elif re.search(r"ash|eruption|smoke|eruption", f"{title} {description} {category_names}", re.IGNORECASE):
            badge = "Weather / emergency"

        items.append(
            {
                "title": title,
                "link": str(event.get("link") or "https://eonet.gsfc.nasa.gov/").strip(),
                "description": description,
                "pubDate": str(event.get("geometry", [{}])[0].get("date") or "").strip(),
                "badge": badge,
                "relevance": 5,
                "source": "eonet",
            }
        )

    return items[:10]


def _fetch_travel_updates(country_name, country_code=None):
    google_news_items = []
    google_news_items.extend(
        _query_country_updates(
            country_name,
            country_code,
            label="Travel news",
            keywords=["travel", "tourism", "tourist", "airport", "visa", "flight", "rail", "advisory"],
            source_name="google_news",
        )
    )
    google_news_items.extend(
        _query_country_updates(
            country_name,
            country_code,
            label="Weather / emergency",
            keywords=["weather", "climate", "storm", "flood", "cyclone", "typhoon", "earthquake", "wildfire", "heatwave", "warning", "alert"],
            source_name="google_news",
        )
    )
    google_news_items.extend(
        _query_country_updates(
            country_name,
            country_code,
            label="Festival / crowd",
            keywords=["festival", "event", "parade", "holiday", "concert", "carnival", "fair", "tourist season"],
            source_name="google_news",
        )
    )

    eonet_items = _fetch_eonet_updates(country_name, country_code)
    gov_advisory_items = _fetch_gov_advisories(country_name, country_code)

    items = _merge_update_items(google_news_items + eonet_items + gov_advisory_items)
    items = sorted(items, key=lambda x: x.get("relevance", 0), reverse=True)

    for item in items:
        item.pop("relevance", None)

    return items[:8]


def _extract_android_app_id(url):
    if not url:
        return None
    try:
        parsed = urlparse(url)
        app_id = parse_qs(parsed.query).get("id", [None])[0]
        return app_id
    except Exception:
        return None


def _extract_ios_app_id(url):
    if not url:
        return None
    match = re.search(r"/id(\d+)", str(url))
    return match.group(1) if match else None


def _tokenize_review_words(reviews):
    text = " ".join([str(r.get("text", "")) for r in reviews]).lower()
    words = re.findall(r"[a-z]{4,}", text)
    stop = {
        "this", "that", "with", "from", "have", "very", "about", "just", "only", "they", "them",
        "would", "could", "there", "their", "really", "after", "before", "while", "where", "which",
        "travel", "app", "apps", "trip", "trips", "user", "users", "using", "used", "useful",
    }
    return [w for w in words if w not in stop]


def _fetch_reddit_mentions(app, country_name):
    from urllib.request import Request, urlopen

    if not _reserve_source_call("reddit"):
        return []

    queries = [
        f'{app.name} {country_name}',
        f'{app.name} travel',
        f'{app.name} reviews',
    ]

    mentions = []
    for query in queries:
        search_url = (
            "https://www.reddit.com/search.json?q="
            + quote(query)
            + "&sort=new&limit=10&t=year"
        )
        req = Request(
            search_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "TripBozo/1.0 (traveler-insights)",
            },
        )

        try:
            with urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8", errors="ignore"))
        except Exception:
            continue

        for child in payload.get("data", {}).get("children", [])[:5]:
            data = child.get("data", {})
            title = str(data.get("title") or "").strip()
            body = str(data.get("selftext") or data.get("body") or "").strip()
            score = data.get("score") or 0
            text = f"{title} {body}".strip()
            if not text:
                continue
            mentions.append(
                {
                    "text": text,
                    "score": score,
                    "source": "reddit",
                }
            )

        if len(mentions) >= 10:
            break

    return mentions[:20]


def _fetch_apple_reviews(app):
    from urllib.request import Request, urlopen

    ios_app_id = _extract_ios_app_id(app.ios_link)
    if not ios_app_id or not _reserve_source_call("apple_app_store"):
        return []

    reviews = []
    # Public customer reviews RSS feed (free, unauthenticated).
    for page in (1, 2):
        rss_url = f"https://itunes.apple.com/rss/customerreviews/page={page}/id{ios_app_id}/sortby=mostrecent/json"
        req = Request(
            rss_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "TripBozo/1.0 (traveler-insights)",
            },
        )

        try:
            with urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8", errors="ignore"))
        except Exception:
            continue

        entries = payload.get("feed", {}).get("entry", []) or []
        # The first item is often app metadata; skip it if present.
        for entry in entries[1:] if len(entries) > 1 else entries:
            title = str(entry.get("title", {}).get("label") or "").strip()
            content = str(entry.get("content", {}).get("label") or "").strip()
            rating = entry.get("im:rating", {}).get("label")
            if not content:
                continue
            reviews.append(
                {
                    "text": f"{title} {content}".strip(),
                    "rating": int(rating) if str(rating).isdigit() else None,
                    "source": "apple_app_store",
                }
            )

        if len(reviews) >= 20:
            break

    return reviews[:20]


def _build_insight_from_reviews(app, reviews):
    ratings = [r.get("rating") for r in reviews if isinstance(r.get("rating"), (int, float))]
    avg_rating = (sum(ratings) / len(ratings)) if ratings else None
    review_count = len(reviews)

    positive_terms = [
        "easy", "simple", "reliable", "fast", "helpful", "accurate", "smooth", "excellent", "great", "useful",
        "intuitive", "clear", "stable", "offline", "translation", "navigation", "booking", "support",
    ]
    negative_terms = [
        "bug", "crash", "slow", "expensive", "ads", "subscription", "confusing", "problem", "issue",
        "stuck", "error", "drain", "battery", "privacy", "tracking", "limited", "inaccurate",
    ]

    text_blob = " ".join([str(r.get("text", "")) for r in reviews]).lower()
    pos_hits = sum(text_blob.count(term) for term in positive_terms)
    neg_hits = sum(text_blob.count(term) for term in negative_terms)

    sentiment_score = pos_hits - neg_hits
    if avg_rating is not None:
        sentiment_score += (avg_rating - 3.0) * 2.5

    if sentiment_score >= 6:
        summary = "Recent traveler reviews are strongly positive, with users highlighting dependable day-to-day performance."
    elif sentiment_score >= 1:
        summary = "Recent traveler feedback is mostly positive, with practical value for planning and movement on-trip."
    elif sentiment_score <= -4:
        summary = "Recent traveler reviews are mixed to cautious; validate reliability for your specific use case before relying on it."
    else:
        summary = "Recent traveler sentiment is mixed, with useful strengths but some recurring pain points."

    frequent = Counter(_tokenize_review_words(reviews))
    top_words = [w for w, _ in frequent.most_common(25)]

    pros = []
    cons = []

    if any(w in top_words for w in ["offline", "map", "maps"]):
        pros.append("Travelers often mention offline or map-related usefulness while navigating.")
    if any(w in top_words for w in ["easy", "simple", "intuitive"]):
        pros.append("Users frequently describe setup and everyday usage as easy.")
    if any(w in top_words for w in ["fast", "quick", "smooth", "reliable"]):
        pros.append("Many reviews call out stable and fast performance in common workflows.")
    if avg_rating and avg_rating >= 4.2:
        pros.append("Review ratings trend high for recent traveler usage.")

    if any(w in top_words for w in ["ads", "subscription", "premium", "expensive"]):
        cons.append("Cost-related friction appears in reviews (ads/subscription or pricing concerns).")
    if any(w in top_words for w in ["bug", "crash", "error", "issue", "slow"]):
        cons.append("Some travelers report stability/performance issues in specific scenarios.")
    if any(w in top_words for w in ["privacy", "tracking", "permission"]):
        cons.append("A subset of reviews mention privacy/permission concerns.")

    if not pros:
        pros = [
            "Travelers report practical value for core on-trip tasks.",
            "Recent feedback suggests useful day-to-day functionality.",
        ]
    if not cons:
        cons = [
            "Compare with one backup option in the same category before travel.",
            "Check local compatibility and feature availability in your destination.",
        ]

    confidence = 52
    if avg_rating is not None:
        if avg_rating >= 4.6:
            confidence += 20
        elif avg_rating >= 4.2:
            confidence += 15
        elif avg_rating >= 3.8:
            confidence += 8
    if review_count >= 80:
        confidence += 15
    elif review_count >= 30:
        confidence += 10
    elif review_count >= 10:
        confidence += 6
    confidence = max(45, min(96, int(round(confidence))))

    if confidence >= 82:
        confidence_label = "High confidence"
    elif confidence >= 68:
        confidence_label = "Moderate confidence"
    else:
        confidence_label = "Emerging confidence"

    return {
        "summary": summary,
        "pros": pros[:3],
        "cons": cons[:3],
        "confidence": confidence,
        "confidenceLabel": confidence_label,
        "lastUpdatedText": "Live reviews",
        "source": {
            "live": True,
            "reviewCount": review_count,
            "avgRating": round(avg_rating, 2) if avg_rating is not None else None,
        },
    }


def _merge_review_sources(app, country_name):
    sources = []

    live_reviews = _fetch_live_reviews(app)
    if live_reviews:
        sources.extend(live_reviews)

    reddit_mentions = _fetch_reddit_mentions(app, country_name)
    if reddit_mentions:
        sources.extend(reddit_mentions)

    return sources


def _fetch_live_reviews(app):
    reviews = []

    android_app_id = _extract_android_app_id(app.android_link)
    ios_app_id = _extract_ios_app_id(app.ios_link)

    if android_app_id and _reserve_source_call("google_play"):
        try:
            from google_play_scraper import Sort, reviews as gp_reviews

            result, _ = gp_reviews(
                android_app_id,
                lang="en",
                country="us",
                sort=Sort.NEWEST,
                count=40,
            )
            for entry in result or []:
                text = str(entry.get("content") or "").strip()
                if not text:
                    continue
                reviews.append(
                    {
                        "text": text,
                        "rating": entry.get("score"),
                        "source": "google_play",
                    }
                )
        except Exception:
            pass

    apple_reviews = _fetch_apple_reviews(app)
    if apple_reviews:
        reviews.extend(apple_reviews)

    return reviews[:80]


def _fallback_insight(app):
    rating = 0
    try:
        rating = float(getattr(app, "rating", 0) or 0)
    except Exception:
        rating = 0

    summary = (
        "Live traveler reviews are not currently available for this app; showing baseline confidence from existing metadata."
    )
    confidence = 64 if rating >= 4.2 else 55

    return {
        "summary": summary,
        "pros": [
            "App is included in destination-curated recommendations.",
            "Useful for common travel workflows in this country context.",
        ],
        "cons": [
            "Live review feed unavailable for this app at the moment.",
            "Compare with alternatives before relying fully on it.",
        ],
        "confidence": confidence,
        "confidenceLabel": "Moderate confidence" if confidence >= 60 else "Emerging confidence",
        "lastUpdatedText": "Metadata fallback",
        "source": {
            "live": False,
            "reviewCount": 0,
            "avgRating": rating if rating else None,
        },
    }


def refresh_country_travel_updates(country):
    """Refresh and cache travel updates payload for a country object."""
    updates = _fetch_travel_updates(country.name, country.code)
    weather = _fetch_country_weather(country.name, country.code)
    payload = {
        "updates": updates,
        "signal": _summarize_impact(updates),
        "weather": weather,
        "_meta": {"fetched_at": _now_ts()},
    }
    key = f"country_travel_updates_{country.code.upper()}"
    safe_cache_set(key, payload, TRAVEL_UPDATES_STORAGE_TTL)
    return payload


def refresh_app_traveler_insight(app):
    """Refresh and cache traveler insight payload for a TravelApp object."""
    country_code = app.country.code.upper()
    country_name = app.country.name

    reviews = _merge_review_sources(app, country_name)
    insight = _build_insight_from_reviews(app, reviews) if reviews else _fallback_insight(app)
    insight["_meta"] = {"fetched_at": _now_ts()}

    key = f"app_traveler_insights_{country_code}_{app.id}"
    safe_cache_set(key, insight, TRAVELER_INSIGHTS_STORAGE_TTL)
    return insight


@api_view(["GET"])
def country_travel_updates_view(request, country_code):
    cc = country_code.upper()
    key = f"country_travel_updates_{cc}"
    payload = safe_cache_get(key)
    country = None

    if payload is None:
        country = get_object_or_404(Country, code=cc)
        try:
            payload = refresh_country_travel_updates(country)
        except Exception:
            payload = {"updates": [], "signal": _summarize_impact([]), "_meta": {"fetched_at": 0}}
    else:
        has_updates = isinstance(payload, dict) and bool(payload.get("updates"))
        if not has_updates:
            country = get_object_or_404(Country, code=cc)
            try:
                payload = refresh_country_travel_updates(country)
            except Exception:
                pass
        elif not _is_fresh(payload, TRAVEL_UPDATES_FRESH_TTL):
            country = get_object_or_404(Country, code=cc)
            lock_key = f"refresh_lock:travel_updates:{cc}"
            cooldown_key = f"refresh_cooldown:travel_updates:{cc}"
            _run_async_with_jitter(
                lambda: refresh_country_travel_updates(country),
                lock_key=lock_key,
                cooldown_key=cooldown_key,
                cooldown_seconds=TRAVEL_UPDATES_REFRESH_COOLDOWN,
                jitter_max_seconds=10,
            )
    return Response(
        {
            "updates": payload.get("updates", []) if isinstance(payload, dict) else [],
            "signal": payload.get("signal", _summarize_impact([])) if isinstance(payload, dict) else _summarize_impact([]),
            "weather": payload.get("weather", {}) if isinstance(payload, dict) else {},
        }
    )


@api_view(["GET"])
def app_traveler_insights_view(request, country_code, app_id):
    cc = country_code.upper()
    app = get_object_or_404(TravelApp, id=app_id, country__code=cc)

    key = f"app_traveler_insights_{cc}_{app.id}"
    insight = safe_cache_get(key)
    if insight is None:
        insight = refresh_app_traveler_insight(app)
    else:
        if not _is_fresh(insight, TRAVELER_INSIGHTS_FRESH_TTL):
            lock_key = f"refresh_lock:traveler_insights:{cc}:{app.id}"
            cooldown_key = f"refresh_cooldown:traveler_insights:{cc}:{app.id}"
            _run_async_with_jitter(
                lambda: refresh_app_traveler_insight(app),
                lock_key=lock_key,
                cooldown_key=cooldown_key,
                cooldown_seconds=TRAVELER_INSIGHTS_REFRESH_COOLDOWN,
                jitter_max_seconds=15,
            )

    public_insight = dict(insight or {})
    public_insight.pop("_meta", None)
    return Response(public_insight)