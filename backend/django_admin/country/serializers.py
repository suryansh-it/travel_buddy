from rest_framework import serializers
from .models import Country, TravelApp, AppCategory, Review, AppScreenshot, EmergencyContact,LocalPhrase, UsefulTip

class TravelAppSerializer(serializers.ModelSerializer):
    platforms = serializers.SerializerMethodField()
    is_sponsored = serializers.BooleanField()

    class Meta:
        model = TravelApp
        fields = ['id', 'name', 'description', 'icon_url', 'ios_link', 'android_link', 'platforms'
                  , "screenshots", "reviews","is_sponsored", ]

    def get_platforms(self, obj):
        return {
            "download": obj.get_download_url(),
        }

class AppCategorySerializer(serializers.ModelSerializer):
    apps = TravelAppSerializer(many=True)  # Fetch related apps

    class Meta:
        model = AppCategory
        fields = ['name', 'apps']  # Each category will have a name and its apps

class CountrySerializer(serializers.ModelSerializer):
     # categories are added dynamically based on available apps
    curated_app_categories = serializers.SerializerMethodField() 
    flag = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = ['name', 'flag', 'description', 'curated_app_categories']

    def get_flag(self, obj):
        return obj.flag.url if obj.flag else None  # Ensure flag URL is returned properly


    def get_curated_app_categories(self, obj):
        """
        Get distinct categories from TravelApps related to the country.
        """
        categories = AppCategory.objects.filter(
            apps__country=obj
        ).distinct()
        
        return AppCategorySerializer(categories, many=True).data


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
        