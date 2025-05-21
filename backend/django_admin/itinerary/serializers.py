from rest_framework import serializers
from country.serializers import TravelAppSerializer
from .models import Itinerary, Stop, LegSuggestionRule

class StopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stop
        fields = ['id', 'name', 'stop_type', 'order']

class ItinerarySerializer(serializers.ModelSerializer):
    stops = StopSerializer(many=True)
    class Meta:
        model = Itinerary
        fields = ['id', 'name', 'stops']

class LegSuggestionSerializer(serializers.Serializer):
    stop_id = serializers.IntegerField()
    suggestions = TravelAppSerializer(many=True)
