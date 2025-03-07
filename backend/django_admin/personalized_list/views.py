from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from services.qrcode_service import generate_qr_code

@api_view(['GET'])
def personalized_list_view(request):
    selected_apps = [
        {"name": "Google Maps", "description": "Navigation app", "platforms": ["iOS", "Android"], "icon": "maps.png"},
        {"name": "WhatsApp", "description": "Messaging app", "platforms": ["iOS", "Android"], "icon": "whatsapp.png"}
    ]
    return Response({"selected_apps": selected_apps})


@api_view(['POST'])
def generate_qr_code_view(request):
    app_links = request.data.get("app_links", [])
    qr_base64 = generate_qr_code.delay(app_links).get()
    return Response({"qr_code": qr_base64})
