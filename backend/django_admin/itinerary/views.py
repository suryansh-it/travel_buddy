

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Itinerary, LegSuggestionRule
from country.models import TravelApp
from .serializers import ItinerarySerializer, LegSuggestionSerializer

class LegSuggestionsView(APIView):
    """
    Given an itinerary ID, for each stop suggest top 3 apps.
    """
    def get(self, request, itinerary_id):
        try:
            itinerary = Itinerary.objects.get(pk=itinerary_id)
        except Itinerary.DoesNotExist:
            return Response({"error": "Itinerary not found"}, status=status.HTTP_404_NOT_FOUND)

        result = []
        for stop in itinerary.stops.all():
            # find rule
            try:
                rule = LegSuggestionRule.objects.get(stop_type=stop.stop_type)
                # collect apps in those categories, limit 3
                apps = TravelApp.objects.filter(
                    country__in=[app.country for app in TravelApp.objects.none()], # no country filter here
                    category__in=rule.categories.all()
                ).order_by('-rating')[:3]
            except LegSuggestionRule.DoesNotExist:
                apps = TravelApp.objects.none()

            result.append({
                "stop_id": stop.id,
                "suggestions": apps
            })

        serializer = LegSuggestionSerializer(result, many=True)
        return Response({"itinerary": ItinerarySerializer(itinerary).data,
                         "leg_suggestions": serializer.data})
