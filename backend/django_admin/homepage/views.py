import logging
from django.shortcuts import get_list_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)
# from services.algolia_service import search_countries
from auth_app.models import UserCountrySuggestion, UserFeedback
from country.models import Country
from country.serializers import CountrySerializer
from django.urls import reverse  # ✅ For generating URLs dynamically

@api_view(['GET'])
def homepage_view(request):
    countries = Country.objects.all()
    serializer = CountrySerializer(countries, many=True)

    data = {
        "hero_section": {
            "search_placeholder": "Search for a country...",
            "cta_text": "Get Started"
        },
        "how_it_works": [
            "Choose a country",
            "Select the best travel apps",
            "Generate your QR code"
        ],
        "popular_destinations": serializer.data,
        "footer": {
            "about": "About Travel App Curator",
            "contact": "Contact Us",
            "privacy": "Privacy Policy",
            "social_links": [
                {"platform": "Twitter", "url": "https://twitter.com"},
                {"platform": "Facebook", "url": "https://facebook.com"}
            ]
        }
    }
    return Response(data)


@api_view(['GET'])
def homepage_search_view(request):
    query = request.GET.get("query", "").strip()

    if not query:
        return Response({"error": "Query parameter is required"}, status=400)

    # 🔍 Search countries by name or code in DB
    countries = Country.objects.filter(name__icontains=query) | Country.objects.filter(code__icontains=query)
    
    results = [
        {
            "name": c.name,
            "code": c.code,
            "flag": c.flag.url if c.flag else None,
            "url": reverse("country_page", kwargs={"country_code": c.code.lower()})  # ✅ Add URL to country page
        } 
        for c in countries
    ]
    return Response({"results": results})


@api_view(["POST"])
def submit_country_suggestion(request):
    """Handle country suggestions for authenticated users."""
    # Check if user is authenticated
    if not request.user or not request.user.is_authenticated:
        return Response(
            {"result": "error", "message": "You must be logged in to submit suggestions."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    country = str(request.data.get("country", "")).strip()
    message = str(request.data.get("message", "")).strip()

    if not country or not message:
        return Response(
            {"result": "error", "message": "Country and message are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user_email = request.user.email
    user_name = request.user.get_full_name() or request.user.username

    UserCountrySuggestion.objects.create(
        user=request.user,
        country=country,
        message=message,
        user_email=user_email,
        user_name=user_name,
    )
    
    return Response({"result": "success", "message": "Suggestion saved."}, status=status.HTTP_200_OK)


@api_view(["POST"])
def submit_feedback(request):
    """Handle feedback submissions via authenticated users."""
    if not request.user or not request.user.is_authenticated:
        return Response(
            {"result": "error", "message": "You must be logged in to submit feedback."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    name = str(request.data.get("name", "")).strip()
    message = str(request.data.get("message", "")).strip()

    if not message:
        return Response(
            {"result": "error", "message": "Feedback message is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user_email = request.user.email
    user_name = request.user.get_full_name() or request.user.username or name or "Traveler"

    UserFeedback.objects.create(
        user=request.user,
        name=user_name,
        message=message,
        user_email=user_email,
    )
    
    return Response({"result": "success", "message": "Feedback saved."}, status=status.HTTP_200_OK)


#----------- if implementing algolia search -------------
# @api_view(['GET'])
# def homepage_search_view(request):
#     query = request.GET.get("query", "").strip()

#     if not query:
#         return Response({"error": "Query parameter is required"}, status=400)

#     results = search_countries(query)  # Fetch from Algolia

#     return Response({"results": results})
