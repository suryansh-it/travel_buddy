from rest_framework import serializers
from .models import Country, TravelApp, AppCategory, EmergencyContact, LocalPhrase, UsefulTip

class TravelAppSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    platforms = serializers.SerializerMethodField()
    is_sponsored = serializers.BooleanField()

    class Meta:
        model = TravelApp
        fields = [
            "id", "name", "description",
            "icon_url", "ios_link", "android_link",
            "platforms", "screenshots", "reviews",
            "is_sponsored", "category",
        ]

    def get_platforms(self, obj):
        return {
            "download": obj.get_download_url(),
        }

class AppCategorySerializer(serializers.ModelSerializer):
    # NOTE: this will use the prefetched 'apps_for_country' on each category
    apps = serializers.SerializerMethodField()

    class Meta:
        model = AppCategory
        fields = ["name", "apps"]

    def get_apps(self, category):
        # we expect the view to have prefetched apps into category.apps_for_country
        apps = getattr(category, "apps_for_country", [])
        return TravelAppSerializer(apps, many=True).data

class CountrySerializer(serializers.ModelSerializer):
    curated_app_categories = serializers.SerializerMethodField()
    flag = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = ["code", "name", "flag", "description", "curated_app_categories"]

    def get_flag(self, obj):
        return obj.flag.url if obj.flag else None

    def get_curated_app_categories(self, obj):
        # the view will inject prefetch_qs in the serializer context
        categories = self.context.get("categories_qs")
        return AppCategorySerializer(categories, many=True).data

class EssentialsSerializer(serializers.ModelSerializer):
    emergencies = serializers.StringRelatedField(many=True)
    phrases    = serializers.StringRelatedField(many=True)
    tips       = serializers.StringRelatedField(many=True)

    class Meta:
        model = Country
        fields = ["code", "name", "emergencies", "phrases", "tips"]
