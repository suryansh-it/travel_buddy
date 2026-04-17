from rest_framework import serializers
from country.models import TravelApp, Country, AppCategory

class AppCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AppCategory
        fields = ["id", "name"]

class TravelAppSerializer(serializers.ModelSerializer):
    categories = AppCategorySerializer(many=True, read_only=True)

    class Meta:
        model = TravelApp
        fields = ["id", "name", "description", "icon_url", "ios_link", "android_link", "categories"]

class CountrySerializer(serializers.ModelSerializer):
    apps = TravelAppSerializer(many=True, read_only=True, source="travelapp_set")

    class Meta:
        model = Country
        fields = ["id", "name", "code", "flag", "description", "apps"]
