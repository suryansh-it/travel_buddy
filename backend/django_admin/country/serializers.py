from rest_framework import serializers
from .models import Country, TravelApp, AppCategory, Review, AppScreenshot, EmergencyContact,LocalPhrase, UsefulTip

class TravelAppSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    platforms = serializers.SerializerMethodField()
    is_sponsored = serializers.BooleanField()

    class Meta:
        model = TravelApp
        fields = ['id', 'name', 'description', 'icon_url', 'ios_link', 'android_link', 'platforms'
                  , "screenshots", "reviews","is_sponsored","category", ]

    def get_platforms(self, obj):
        return {
            "download": obj.get_download_url(),
        }

class AppCategorySerializer(serializers.ModelSerializer):
    apps = serializers.SerializerMethodField()

    class Meta:
        model = AppCategory
        fields = ['name', 'apps']

    def get_apps(self, category):
        # Prefer the prefetched list 'apps_for_country' if it exists,
        # otherwise fall back to the default related manager.
        apps_qs = getattr(category, 'apps_for_country', None)
        if apps_qs is None:
            apps_qs = category.apps.all().select_related('category')
        return TravelAppSerializer(apps_qs, many=True).data

class CountrySerializer(serializers.ModelSerializer):
     # categories are added dynamically based on available apps
    curated_app_categories = serializers.SerializerMethodField() 
    flag = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = ['code','name', 'flag', 'description', 'curated_app_categories']

    def get_flag(self, obj):
        return obj.flag.url if obj.flag else None  # Ensure flag URL is returned properly


    def get_curated_app_categories(self, obj):
        # pull in the prefetch q we shoved into context
        category_qs = self.context.get("categories_qs", [])
        # now serialize using your existing AppCategorySerializer
        # but that serializer must read from apps_for_country if present
        return AppCategorySerializer(category_qs, many=True).data


class AppScreenshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppScreenshot
        fields = ["image_url"]

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["user_id", "rating", "review_text", "created_at"]


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ["name", "phone", "email", "description"]


class LocalPhraseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalPhrase
        fields = ["original", "translation", "context_note"]

class UsefulTipSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsefulTip
        fields = ["tip"]

class EssentialsSerializer(serializers.ModelSerializer):
    emergencies = EmergencyContactSerializer(many=True)
    phrases     = LocalPhraseSerializer(many=True)
    tips        = UsefulTipSerializer(many=True)

    class Meta:
        model  = Country
        fields = ["code", "name", "emergencies", "phrases", "tips"]
        