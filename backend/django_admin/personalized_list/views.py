from django.shortcuts import get_list_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import redis
import json
import uuid
from django.conf import settings
from country.models import TravelApp
from .serializers import TravelAppSerializer
# from personalized_list.models import App  # Assuming App model exists
from services.qrcode_service import generate_qr_code  # Import the QR service

# Redis connection for personal lists
redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB_PERSONAL_LISTS, decode_responses=True
)

class PersonalAppListView(APIView):
    """
    API to create and retrieve a temporary personal app list.
    """

    def post(self, request):
        """
        Store selected app IDs in Redis with a unique session ID.
        """
        selected_apps = request.data.get("selected_apps", [])

        if not selected_apps:
            return Response({"error": "No apps selected"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a unique session ID
        session_id = str(uuid.uuid4())

        # Store data in Redis (expires in 24 hours)
        redis_client.setex(session_id, 86400, json.dumps(selected_apps))

        return Response({"session_id": session_id}, status=status.HTTP_201_CREATED)
    

    def get(self, request, session_id):
        """
        Retrieve selected apps using session ID.
        """
        selected_apps_json = redis_client.get(session_id)

        if not selected_apps_json:
            return Response({"error": "Session not found or expired"}, status=status.HTTP_404_NOT_FOUND)

        selected_app_ids = json.loads(selected_apps_json)
        apps = TravelApp.objects.filter(id__in=selected_app_ids)

               # Serialize app data
        serializer = TravelAppSerializer(apps, many=True)

        return Response({"session_id": session_id, "selected_apps": serializer.data}, status=status.HTTP_200_OK)



class GenerateQRCodeView(APIView):
    """
    API to generate a QR code for the selected apps.
    """

    def get(self, request, session_id):
        """
        Generate and return a QR code for the selected app list.
        """
        selected_apps_json = redis_client.get(session_id)

        if not selected_apps_json:
            return Response({"error": "Session not found or expired"}, status=status.HTTP_404_NOT_FOUND)

        selected_app_ids = json.loads(selected_apps_json)
        apps = TravelApp.objects.filter(id__in=selected_app_ids)

                # Serialize app data
        serializer = TravelAppSerializer(apps, many=True)

        # Generate a URL with selected app details (could be a frontend deep link)
        app_links = [app.download_url for app in apps]  # Assuming download_url field exists
        qr_data = {"session_id": session_id, "apps": app_links}

        # Use the QR Code Service to generate the QR code
        qr_base64 = generate_qr_code(qr_data)

        return Response({"qr_code": qr_base64, "selected_apps": serializer.data}, status=status.HTTP_200_OK)