from django.shortcuts import get_list_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from services.algolia_service import search_apps
from rest_framework.decorators import api_view
from country.models import Country
from country.serializers import CountrySerializer

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
    
    # Search countries by name or code
    countries = Country.objects.filter(name__icontains=query) | Country.objects.filter(code__icontains=query)

    results = [{"name": c.name, "code": c.code, "flag": c.flag.url if c.flag else None} for c in countries]

    return Response({"results": results})
