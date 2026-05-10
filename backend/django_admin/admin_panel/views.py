import csv
import io

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from auth_app.models import Bookmark, UserCountrySuggestion, UserFeedback
from country.models import (
    AppCategory,
    Country,
    CountryServiceProvider,
    CountryVisit,
    EmergencyContact,
    LocalPhrase,
    OriginCountryAssistance,
    TravelApp,
    UsefulTip,
)


User = get_user_model()
ADMIN_PANEL_EMAIL = str(getattr(settings, "ADMIN_PANEL_EMAIL", "bozotrip@gmail.com") or "").strip().lower()


def _is_admin(user):
    user_email = str(getattr(user, "email", "") or "").strip().lower()
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser or user_email == ADMIN_PANEL_EMAIL))


def _admin_guard(request):
    if not _is_admin(request.user):
        raise PermissionDenied("Admin access required.")


def _clean(value, default=""):
    return str(value).strip() if value is not None else default


def _clean_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _resolve_country(code_or_name):
    value = _clean(code_or_name)
    if not value:
        return None
    country = Country.objects.filter(code__iexact=value.upper()).first()
    if country:
        return country
    return Country.objects.filter(name__iexact=value).first()


def _serialize_country(country, visit_count=0):
    return {
        "id": country.id,
        "code": country.code,
        "name": country.name,
        "description": country.description or "",
        "flag": country.flag.url if country.flag else None,
        "visit_count": int(visit_count or 0),
    }


def _serialize_provider(provider):
    return {
        "id": provider.id,
        "country": provider.country.code,
        "section": provider.section,
        "name": provider.name,
        "price_from": provider.price_from,
        "coverage": provider.coverage,
        "support": provider.support,
        "refund": provider.refund,
        "site": provider.site,
        "is_featured": provider.is_featured,
        "notes": provider.notes,
    }


def _top_bookmarks(field_name):
    rows = (
        Bookmark.objects.filter(**{f"{field_name}__isnull": False})
        .values(f"{field_name}__id", f"{field_name}__code", f"{field_name}__name")
        .annotate(total=Count("id"))
        .order_by("-total", f"{field_name}__name")[:8]
    )
    return [
        {
            "id": row.get(f"{field_name}__id"),
            "code": row.get(f"{field_name}__code"),
            "name": row.get(f"{field_name}__name"),
            "total": row.get("total", 0),
        }
        for row in rows
    ]


class AdminSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _admin_guard(request)

        return Response(
            {
                "stats": {
                    "countries": Country.objects.count(),
                    "app_categories": AppCategory.objects.count(),
                    "travel_apps": TravelApp.objects.count(),
                    "service_providers": CountryServiceProvider.objects.count(),
                    "emergency_contacts": EmergencyContact.objects.count(),
                    "local_phrases": LocalPhrase.objects.count(),
                    "useful_tips": UsefulTip.objects.count(),
                    "origin_assistance_profiles": OriginCountryAssistance.objects.count(),
                    "bookmarks": Bookmark.objects.count(),
                    "feedback": UserFeedback.objects.count(),
                    "suggestions": UserCountrySuggestion.objects.count(),
                    "users": User.objects.count(),
                },
                "popular_countries": [
                    _serialize_country(item.country, item.visit_count)
                    for item in CountryVisit.objects.select_related("country").order_by("-visit_count", "country__name")[:10]
                ],
                "top_country_bookmarks": _top_bookmarks("country"),
                "top_app_bookmarks": _top_bookmarks("app"),
                "latest_feedback": list(
                    UserFeedback.objects.select_related("user").order_by("-created_at")
                    .values("id", "name", "message", "user_email", "created_at")[:10]
                ),
                "latest_suggestions": list(
                    UserCountrySuggestion.objects.select_related("user").order_by("-created_at")
                    .values("id", "country", "message", "user_email", "user_name", "created_at")[:10]
                ),
            },
            status=status.HTTP_200_OK,
        )


class AdminOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _admin_guard(request)

        return Response(
            {
                "countries": list(Country.objects.order_by("name").values("id", "code", "name")),
                "categories": list(AppCategory.objects.order_by("name").values("id", "name")),
                "service_sections": [
                    {"value": "esim", "label": "eSIM & Connectivity"},
                    {"value": "insurance", "label": "Travel Insurance"},
                    {"value": "booking", "label": "Booking Platforms"},
                    {"value": "utilities", "label": "Other Useful Services"},
                ],
                "resources": [
                    "country",
                    "app_category",
                    "travel_app",
                    "service_provider",
                    "emergency_contact",
                    "local_phrase",
                    "useful_tip",
                    "origin_assistance",
                ],
            },
            status=status.HTTP_200_OK,
        )


class AdminRecordIngestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _admin_guard(request)

        resource = _clean(request.data.get("resource")).lower()
        if not resource:
            raise ValidationError({"resource": "This field is required."})

        file_obj = request.FILES.get("file")
        if file_obj is not None:
            return self._ingest_csv(resource, file_obj)

        payload = request.data.get("data", request.data)
        if isinstance(payload, str):
            try:
                import json
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if not isinstance(payload, dict):
            raise ValidationError({"data": "Expected an object payload."})

        record, created = self._save_record(resource, payload)
        return Response(
            {
                "mode": "single",
                "resource": resource,
                "created": created,
                "record": record,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def _ingest_csv(self, resource, file_obj):
        decoded = io.TextIOWrapper(file_obj, encoding="utf-8-sig")
        reader = csv.DictReader(decoded)
        created = 0
        updated = 0
        skipped = 0
        errors = []

        with transaction.atomic():
            for index, row in enumerate(reader, start=2):
                try:
                    _, was_created = self._save_record(resource, row)
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                except Exception as exc:
                    skipped += 1
                    errors.append({"row": index, "detail": str(exc)})

        return Response(
            {
                "mode": "csv",
                "resource": resource,
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "errors": errors[:20],
            },
            status=status.HTTP_200_OK,
        )

    def _save_record(self, resource, payload):
        if resource == "country":
            return self._save_country(payload)
        if resource == "app_category":
            return self._save_category(payload)
        if resource == "travel_app":
            return self._save_travel_app(payload)
        if resource == "service_provider":
            return self._save_service_provider(payload)
        if resource == "emergency_contact":
            return self._save_emergency_contact(payload)
        if resource == "local_phrase":
            return self._save_local_phrase(payload)
        if resource == "useful_tip":
            return self._save_useful_tip(payload)
        if resource == "origin_assistance":
            return self._save_origin_assistance(payload)
        raise ValidationError({"resource": f"Unsupported resource '{resource}'."})

    def _save_country(self, payload):
        code = _clean(payload.get("code")).upper()
        name = _clean(payload.get("name"))
        if not code or not name:
            raise ValidationError({"code": "Country code and name are required."})

        country = Country.objects.filter(code__iexact=code).first()
        created = country is None
        if country is None:
            country = Country(code=code)

        country.name = name
        country.description = _clean(payload.get("description"))
        flag_file = payload.get("flag") if hasattr(payload, "get") else None
        if flag_file:
            country.flag = flag_file
        country.save()
        return _serialize_country(country), created

    def _save_category(self, payload):
        name = _clean(payload.get("name"))
        if not name:
            raise ValidationError({"name": "Category name is required."})
        category, created = AppCategory.objects.update_or_create(
            name=name,
            defaults={"description": _clean(payload.get("description"))},
        )
        return {"id": category.id, "name": category.name, "description": category.description or ""}, created

    def _save_travel_app(self, payload):
        name = _clean(payload.get("name"))
        country = _resolve_country(payload.get("country_code") or payload.get("country"))
        category_name = _clean(payload.get("category_name") or payload.get("category"))
        if not (name and country and category_name):
            raise ValidationError({"detail": "Travel apps require name, country_code and category_name."})

        category, _ = AppCategory.objects.get_or_create(name=category_name, defaults={"description": _clean(payload.get("category_description"))})
        app, created = TravelApp.objects.update_or_create(
            name=name,
            country=country,
            defaults={
                "category": category,
                "description": _clean(payload.get("description")),
                "icon_url": _clean(payload.get("icon_url")),
                "android_link": _clean(payload.get("android_link")),
                "ios_link": _clean(payload.get("ios_link")),
                "website_link": _clean(payload.get("website_link")),
                "affiliate_url": _clean(payload.get("affiliate_url")),
                "is_sponsored": _clean_bool(payload.get("is_sponsored") or payload.get("isSponsored")),
                "supports_foreign_cards": _clean_bool(payload.get("supports_foreign_cards") or payload.get("supportsForeignCards")),
                "works_offline": _clean_bool(payload.get("works_offline") or payload.get("worksOffline")),
            },
        )
        return {"id": app.id, "name": app.name, "country": app.country.code, "category": app.category.name}, created

    def _save_service_provider(self, payload):
        name = _clean(payload.get("name"))
        section = _clean(payload.get("section")).lower()
        country = _resolve_country(payload.get("country_code") or payload.get("country"))
        allowed_sections = {choice[0] for choice in CountryServiceProvider.SECTION_CHOICES}
        if section not in allowed_sections:
            raise ValidationError({"section": f"Section must be one of: {', '.join(sorted(allowed_sections))}."})
        if not (name and country):
            raise ValidationError({"detail": "Service providers require name and country_code."})

        provider, created = CountryServiceProvider.objects.update_or_create(
            country=country,
            section=section,
            name=name,
            defaults={
                "price_from": _clean(payload.get("price_from") or payload.get("priceFrom")),
                "coverage": _clean(payload.get("coverage")),
                "support": _clean(payload.get("support")),
                "refund": _clean(payload.get("refund")),
                "site": _clean(payload.get("site")),
                "is_featured": _clean_bool(payload.get("is_featured") or payload.get("isFeatured")),
                "notes": _clean(payload.get("notes")),
            },
        )
        return _serialize_provider(provider), created

    def _save_emergency_contact(self, payload):
        country = _resolve_country(payload.get("country_code") or payload.get("country"))
        name = _clean(payload.get("name"))
        phone = _clean(payload.get("phone"))
        if not (country and name and phone):
            raise ValidationError({"detail": "Emergency contacts require country_code, name and phone."})
        contact, created = EmergencyContact.objects.update_or_create(
            country=country,
            name=name,
            defaults={
                "phone": phone,
                "email": _clean(payload.get("email")),
                "description": _clean(payload.get("description")),
            },
        )
        return {"id": contact.id, "country": country.code, "name": contact.name, "phone": contact.phone}, created

    def _save_local_phrase(self, payload):
        country = _resolve_country(payload.get("country_code") or payload.get("country"))
        original = _clean(payload.get("original"))
        if not (country and original):
            raise ValidationError({"detail": "Local phrases require country_code and original."})
        phrase, created = LocalPhrase.objects.update_or_create(
            country=country,
            original=original,
            defaults={
                "translation": _clean(payload.get("translation")),
                "context_note": _clean(payload.get("context_note")),
            },
        )
        return {"id": phrase.id, "country": country.code, "original": phrase.original}, created

    def _save_useful_tip(self, payload):
        country = _resolve_country(payload.get("country_code") or payload.get("country"))
        tip = _clean(payload.get("tip"))
        if not (country and tip):
            raise ValidationError({"detail": "Useful tips require country_code and tip."})
        tip_obj, created = UsefulTip.objects.get_or_create(country=country, tip=tip)
        return {"id": tip_obj.id, "country": country.code, "tip": tip_obj.tip}, created

    def _save_origin_assistance(self, payload):
        country = _resolve_country(payload.get("country_code") or payload.get("country"))
        label = _clean(payload.get("label"))
        if not (country and label):
            raise ValidationError({"detail": "Origin assistance requires country_code and label."})
        profile, created = OriginCountryAssistance.objects.update_or_create(
            country=country,
            defaults={
                "label": label,
                "emergency_phone": _clean(payload.get("emergency_phone")),
                "emergency_phone_intl": _clean(payload.get("emergency_phone_intl")),
                "consular_address": _clean(payload.get("consular_address")),
                "website": _clean(payload.get("website")),
                "mission_finder": _clean(payload.get("mission_finder")),
                "source": _clean(payload.get("source")),
            },
        )
        return {"id": profile.id, "country": country.code, "label": profile.label}, created