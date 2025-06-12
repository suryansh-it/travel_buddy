from django.shortcuts import get_list_or_404, render
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


@api_view(['GET'])
def get_bundle_urls(request, session_id):
    """
    Return the list of store URLs for a given session ID as JSON.
    """
    data = redis_client.get(session_id)
    if not data:
        return Response({'urls': []}, status=status.HTTP_404_NOT_FOUND)

    apps = json.loads(data)
    urls = [
        a.get('android_link') or a.get('ios_link')
        for a in apps
        if a.get('android_link') or a.get('ios_link')
    ]
    return Response({'urls': urls})



class InitSessionView(APIView):
    """
    API to initialize a new session and store it in Redis.
    """

    def post(self, request):
        """
        Generate a session ID and store an empty app list in Redis (expires in 24 hours).
        """
        session_id = str(uuid.uuid4())  # Generate unique session ID
        redis_client.setex(session_id, 86400, json.dumps([]))  # Store empty list in Redis
        
        return Response({"session_id": session_id, "message": "Session initialized successfully!"}, status=status.HTTP_201_CREATED)



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
        shareable_url = f"{base_url}/bundle-redirect/{session_id}"

                # Generate QR Code from the single shareable URL
        qr_base64 = generate_qr_code([shareable_url])

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

        html = ["<html><head><meta charset='utf-8'><title>Your App Bundle</title></head><body>"]
        html.append("<h1>Your Travel App Bundle</h1><ul>")
        for app in apps:
            android = f"<a href='{app.android_link}'>Android</a>" if app.android_link else ""
            ios     = f"<a href='{app.ios_link}'>iOS</a>"     if app.ios_link     else ""
            html.append(f"<li><strong>{app.name}</strong>: {android} {ios}</li>")
        html.append("</ul></body></html>")

        response = HttpResponse("".join(html), content_type="text/html")
        response["Content-Disposition"] = f"attachment; filename=bundle_{session_id}.html"
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
    


class EmbedSnippetView(APIView):
    """
    Returns an embeddable <iframe> snippet for a given session.
    """
    def get(self, request, session_id):
        # (Optional) verify the session exists
        if not redis_client.exists(session_id):
            return Response({"error": "Session not found"}, status=404)

        iframe_src = f"{settings.FRONTEND_URL}/bundle/{session_id}/"
        snippet = (
            f'<iframe '
            f'src="{iframe_src}" '
            f'width="320" height="480" '
            f'style="border:none;overflow:hidden" '
            f'allowfullscreen>'
            f'</iframe>'
        )
        return Response({"embed_snippet": snippet})


def bundle_preview(request, session_id):
    apps_json = redis_client.get(session_id)
    if not apps_json:
        return render(request, "404.html", status=404)

    apps_data = json.loads(apps_json)
    app_ids = [a['id'] for a in apps_data]
    apps = TravelApp.objects.filter(id__in=app_ids)

    serializer = TravelAppSerializer(apps, many=True)
    qr_data = {"session_id": session_id}
    qr_b64 = generate_qr_code(qr_data)

    return render(request, "bundle_preview.html", {
        "apps": serializer.data,
        "qr_code": qr_b64,
        "session_id": session_id,
    })



# personalized_list/views.py

from django.shortcuts import render
from .tasks import redis_client
import json

def bundle_auto_redirect(request, session_id):
    """
    After scanning the QR, this page will open each store link in turn.
    """
    apps_json = redis_client.get(session_id)
    if not apps_json:
        return render(request, "404.html", status=404)

    apps_data = json.loads(apps_json)
    urls = []
    for a in apps_data:
        # prefer Android, otherwise iOS
        if a.get('android_link'):
            urls.append(a['android_link'])
        elif a.get('ios_link'):
            urls.append(a['ios_link'])

    return render(request, "bundle_auto_redirect.html", {
        "urls": json.dumps(urls)
    })
