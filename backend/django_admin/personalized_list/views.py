from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
import qrcode
from io import BytesIO
import base64

@api_view(['GET'])
def personalized_list_view(request):
    selected_apps = [
        {"name": "Google Maps", "description": "Navigation app", "platforms": ["iOS", "Android"], "icon": "maps.png"},
        {"name": "WhatsApp", "description": "Messaging app", "platforms": ["iOS", "Android"], "icon": "whatsapp.png"}
    ]
    return Response({"selected_apps": selected_apps})



