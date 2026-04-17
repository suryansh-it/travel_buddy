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
from urllib.parse import quote, urlparse, parse_qs
from collections import Counter
import re
import json
import time
import random
import threading


CACHE_TTL = 60 * 60  # 1h

# Freshness windows
TRAVEL_UPDATES_FRESH_TTL = 10 * 60          # 10 min fresh window
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


def _strip_xml_text(value=""):
    return (
        str(value)
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )


def _extract_rss_tag(xml, tag):
    match = re.search(rf"<{tag}>([\\s\\S]*?)</{tag}>", xml, re.IGNORECASE)
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


def _fetch_travel_updates(country_name):
    from urllib.request import Request, urlopen

    if not _reserve_source_call("google_news"):
        return []

    query = f'"{country_name}" travel tourism weather emergency storm festival advisory'
    rss_url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"

    req = Request(rss_url, headers={"Accept": "application/rss+xml, application/xml, text/xml"})
    with urlopen(req, timeout=8) as response:
        xml = response.read().decode("utf-8", errors="ignore")
    country_regex = re.compile(rf"\\b{re.escape(country_name)}\\b", re.IGNORECASE)

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
        relevance = 0

        if country_regex.search(haystack):
            relevance += 4
        if country_regex.search(title):
            relevance += 2
        if re.search(r"travel|tourism|tourist|airport|visa|flight|rail|weather|storm|festival|emergency|advisory", haystack, re.IGNORECASE):
            relevance += 1

        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "pubDate": pub_date,
                "badge": _classify_update(title, description),
                "relevance": relevance,
            }
        )

        if len(items) >= 16:
            break

    items = sorted(items, key=lambda x: x["relevance"], reverse=True)
    country_matched = [i for i in items if i["relevance"] >= 4]
    final_items = (country_matched if country_matched else items)[:6]

    for item in final_items:
        item.pop("relevance", None)

    return final_items


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
    updates = _fetch_travel_updates(country.name)
    payload = {
        "updates": updates,
        "signal": _summarize_impact(updates),
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
        if not _is_fresh(payload, TRAVEL_UPDATES_FRESH_TTL):
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