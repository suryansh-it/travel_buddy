from django.shortcuts import get_list_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import json
import uuid
from django.conf import settings
from country.models import TravelApp
from .serializers import TravelAppSerializer
import io
from PIL import Image
from django.http import HttpResponse
import base64
# from personalized_list.models import App  # Assuming App model exists
from services.qrcode_service import generate_qr_code  # Import the QR service
from .tasks import redis_client
from rest_framework import status


class PersonalAppListView(APIView):
    """
    API to create and retrieve a temporary personal app list.
    """

    def post(self, request):
        """
        Store selected apps in Redis with a unique session ID.
        """
        selected_app_ids = request.data.get("selected_apps", [])

        if not selected_app_ids:
            return Response({"error": "No apps selected"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate if apps exist in DB
        valid_apps = TravelApp.objects.filter(id__in=selected_app_ids)
        if not valid_apps.exists():
            return Response({"error": "Invalid apps selected"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a unique session ID
        session_id = str(uuid.uuid4())

        # Serialize app data and store in Redis (expires in 24 hours)
        serialized_apps = TravelAppSerializer(valid_apps, many=True).data
        redis_client.setex(session_id, 86400, json.dumps(serialized_apps))

        return Response({
            "session_id": session_id,
            "message": "Apps added successfully!",
            "selected_apps": serialized_apps
        }, status=status.HTTP_201_CREATED)

    def get(self, request, session_id):
        """
        Retrieve selected apps using session ID.
        """
        selected_apps_json = redis_client.get(session_id)

        if not selected_apps_json:
            return Response({"error": "Session not found or expired"}, status=status.HTTP_404_NOT_FOUND)

        selected_apps = json.loads(selected_apps_json)

        return Response({"session_id": session_id, "selected_apps": selected_apps}, status=status.HTTP_200_OK)


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

        selected_app_dicts = json.loads(selected_apps_json)
        selected_app_ids = [app["id"] for app in selected_app_dicts]  # Extract only IDs
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

        selected_app_dicts = json.loads(selected_apps_json)
        selected_app_ids = [app["id"] for app in selected_app_dicts]  # Extract only IDs
        apps = TravelApp.objects.filter(id__in=selected_app_ids)

        app_list_text = "\n".join([f"{app.name} - {app.description} (Download: {app.ios_link if app.ios_link else app.android_link})" for app in apps])

        response = Response(app_list_text, content_type="text/plain")
        response["Content-Disposition"] = f"attachment; filename=app_list_{session_id}.txt"
        return response


class DownloadQRCodeView(APIView):
    """
    API to download the QR code as an image.
    """

    def get(self, request, session_id):
        """
        Serve the QR code as a downloadable image.
        """
        selected_apps_json = redis_client.get(session_id)

        if not selected_apps_json:
            return Response({"error": "Session not found or expired"}, status=status.HTTP_404_NOT_FOUND)

    
         # Just generate QR code from session_id
        qr_data = {"session_id": session_id}
        qr_base64 = generate_qr_code(qr_data)  # Regenerate the QR code


        # Convert Base64 to an image
        qr_image_data = base64.b64decode(qr_base64)
        image = Image.open(io.BytesIO(qr_image_data))

        # Serve as a downloadable PNG file
        response = HttpResponse(content_type="image/png")
        response["Content-Disposition"] = f'attachment; filename="qr_code_{session_id}.png"'
        image.save(response, "PNG")
        return response