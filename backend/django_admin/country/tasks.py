from celery import shared_task
from django.db.models import Q

from .models import Country, TravelApp
from .utils import safe_cache_get, safe_cache_set
from .views import refresh_country_travel_updates, refresh_app_traveler_insight

# Conservative defaults to stay within free-source limits.
COUNTRY_BATCH_SIZE = 8
INSIGHTS_APP_BATCH_SIZE = 20


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def refresh_travel_updates_batch(self):
    """Refresh travel headlines cache for a rotating subset of countries."""
    countries = list(Country.objects.order_by("code"))
    if not countries:
        return {"countries_refreshed": 0}

    total = len(countries)
    start = safe_cache_get("travel_updates_cursor") or 0
    if not isinstance(start, int):
        start = 0

    refreshed = 0
    for i in range(min(COUNTRY_BATCH_SIZE, total)):
        idx = (start + i) % total
        country = countries[idx]
        try:
            refresh_country_travel_updates(country)
            refreshed += 1
        except Exception:
            continue

    next_cursor = (start + COUNTRY_BATCH_SIZE) % total
    safe_cache_set("travel_updates_cursor", next_cursor, 7 * 24 * 60 * 60)

    return {"countries_refreshed": refreshed, "total_countries": total}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def refresh_traveler_insights_batch(self):
    """Refresh traveler insights cache for a rotating subset of apps with store links."""
    apps = list(
        TravelApp.objects.select_related("country")
        .filter(Q(android_link__isnull=False) | Q(ios_link__isnull=False))
        .exclude(Q(android_link="") & Q(ios_link=""))
        .order_by("country__code", "name")
    )

    if not apps:
        return {"apps_refreshed": 0}

    total = len(apps)
    start = safe_cache_get("traveler_insights_cursor") or 0
    if not isinstance(start, int):
        start = 0

    refreshed = 0
    for i in range(min(INSIGHTS_APP_BATCH_SIZE, total)):
        idx = (start + i) % total
        app = apps[idx]
        try:
            refresh_app_traveler_insight(app)
            refreshed += 1
        except Exception:
            continue

    next_cursor = (start + INSIGHTS_APP_BATCH_SIZE) % total
    safe_cache_set("traveler_insights_cursor", next_cursor, 7 * 24 * 60 * 60)

    return {"apps_refreshed": refreshed, "total_apps": total}
