from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view

@api_view(['GET'])
def country_page_view(request, country_code):
    data={
        "country_header": {
            "flag": f"{country_code}.png",
            "name": country_code.upper(),
            "description": f"Explore top apps for {country_code.capitalize()}"
        },
        "curated_app_categories": [
            "Navigation",
            "Communication",
            "Finance",
            "Transport",
            "Accommodation"
        ],
        "app_cards": [
            {"name": "Google Maps", "description": "Navigation app", "platforms": ["iOS", "Android"], "icon": "maps.png"},
            {"name": "WhatsApp", "description": "Messaging app", "platforms": ["iOS", "Android"], "icon": "whatsapp.png"},
            {"name": "PayPal", "description": "Online payments", "platforms": ["iOS", "Android"], "icon": "paypal.png"}
        ],
        "search_filter": {
            "search_placeholder": "Search for apps...",
            "categories": ["Navigation", "Communication", "Finance"]
        },
        "selected_apps_panel": {
            "selected_apps": [],
            "generate_qr_button": "Generate QR Code"
        }
    }
    return Response(data)

    