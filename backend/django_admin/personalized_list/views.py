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

@api_view(['POST'])
def generate_qr_code(request):
    data = request.data.get("app_links", [])
    qr = qrcode.make("\n".join(data))
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    return Response({"qr_code": qr_base64})

