from rest_framework import serializers
from .models import AppCategory, TravelApp,Country

class AppCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AppCategory
        fields = '__all__'

class TravelAppSerializer(serializers.ModelSerializer):
    category = AppCategorySerializer(read_only=True)

    class Meta:
        model = TravelApp
        fields = '__all__'

class CountrySerializer(serializers.ModelSerializer):
    apps = TravelAppSerializer(many=True, read_only=True, source="travelapp_set")

    class Meta:
        model = Country
        fields = ["id", "name", "code", "flag", "description", "apps"]