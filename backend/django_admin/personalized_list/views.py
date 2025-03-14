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

        # Generate a shareable link
        base_url = settings.FRONTEND_URL
        shareable_url = f"{base_url}/personalized-list/{session_id}"

        # Generate QR Code
        qr_data = {"session_id": session_id, "apps": shareable_url}
        qr_base64 = generate_qr_code(qr_data)

        return Response({"qr_code": qr_base64, "selected_apps": serializer.data,"shareable_url": shareable_url}, status=status.HTTP_200_OK)
    

class DownloadAppListTextView(APIView):
    """
    API to download the selected app list as a text file.
    """

    def get(self, request, session_id):
        """
        Serve the selected app list as a downloadable text file.
        """
        selected_apps_json = redis_client.get(session_id)

        if not selected_apps_json:
            return Response({"error": "Session not found or expired"}, status=status.HTTP_404_NOT_FOUND)

        selected_app_ids = json.loads(selected_apps_json)
        apps = TravelApp.objects.filter(id__in=selected_app_ids)

        app_list_text = "\n".join([f"{app.name} - {app.description} (Download: {app.ios_link if app.ios_link else app.android_link})" for app in apps])

        response = Response(app_list_text, content_type="text/plain")
        response["Content-Disposition"] = f"attachment; filename=app_list_{session_id}.txt"
        return response
