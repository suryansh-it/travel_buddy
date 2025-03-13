from rest_framework import serializers
from .models import AppCategory, TravelApp

class AppCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AppCategory
        fields = '__all__'

class TravelAppSerializer(serializers.ModelSerializer):
    category = AppCategorySerializer(read_only=True)

    class Meta:
        model = TravelApp
        fields = '__all__'
