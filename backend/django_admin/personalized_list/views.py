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
from rest_framework.decorators import api_view


@api_view(['GET'])
def get_bundle_urls(request, session_id):
    data = redis_client.get(session_id)
    if not data:
        return Response({'items': []}, status=status.HTTP_404_NOT_FOUND)

    apps = json.loads(data)
    # now return list of {name, url}
    items = []
    for a in apps:
        url = a.get('android_link') or a.get('ios_link')
        if url:
            items.append({'name': a.get('name', 'App'), 'url': url})
    return Response({'items': items})



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
    

# views.py

from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
import json
from .tasks import redis_client
from django.conf import settings
from country.models import TravelApp
from .serializers import TravelAppSerializer

class DownloadAppListTextView(APIView):
    """
    API to download the selected app list as a styled HTML page.
    """
    def get(self, request, session_id):
        selected_apps_json = redis_client.get(session_id)
        if not selected_apps_json:
            return HttpResponse(
                "<h1>Bundle Not Found</h1><p>Your session has expired or does not exist.</p>",
                status=status.HTTP_404_NOT_FOUND,
                content_type="text/html"
            )

        # Deserialize and load the actual TravelApp objects
        selected_app_dicts = json.loads(selected_apps_json)
        app_ids = [app["id"] for app in selected_app_dicts]
        apps = TravelApp.objects.filter(id__in=app_ids)
        serializer = TravelAppSerializer(apps, many=True)
        apps_data = serializer.data

        # Build the HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Your Travel App Bundle • TripBozo</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ margin:0; padding:0; font-family:sans-serif; background:#f7fafc; color:#333; }}
    .container {{ max-width:600px; margin:2rem auto; padding:1rem; background:white;
                  border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1); }}
    header {{ text-align:center; margin-bottom:2rem; }}
    header img {{ height:50px; vertical-align:middle; }}
    header h1 {{ display:inline-block; margin:0 0 0 0.5rem; font-size:1.75rem; color:#2ad2c9; vertical-align:middle; }}
    .app-card {{ display:flex; align-items:center; justify-content:space-between;
                 padding:1rem 0; border-bottom:1px solid #eee; }}
    .app-card:last-child {{ border-bottom:none; }}
    .app-info {{ display:flex; align-items:center; gap:1rem; }}
    .app-info img {{ width:48px; height:48px; border-radius:8px; object-fit:cover; background:#e0e0e0; }}
    .app-details {{ display:flex; flex-direction:column; }}
    .app-name {{ margin:0; font-size:1.125rem; }}
    .app-category {{ margin:0; font-size:0.875rem; color:#666; }}
    .app-buttons a {{ text-decoration:none; margin-left:0.5rem; padding:0.5rem 1rem;
                      border-radius:4px; font-size:0.875rem; color:white; }}
    .android-btn {{ background:#3ddc84; }}
    .ios-btn {{ background:#000; }}
    footer {{ text-align:center; margin-top:2rem; font-size:0.75rem; color:#999; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <img src="{settings.FRONTEND_URL}/logo.png" alt="TripBozo Logo">
      <h1>Your App Bundle</h1>
    </header>
"""

        # Render each app as a card
        for app in apps_data:
            android = app.get("android_link")
            ios     = app.get("ios_link")
            icon    = app.get("icon_url") or "/file.svg"

            html += f'''
    <div class="app-card">
      <div class="app-info">
        <img src="{icon}" alt="{app["name"]} icon">
        <div class="app-details">
          <p class="app-name">{app["name"]}</p>
          <p class="app-category">{app.get("category","Uncategorized")}</p>
        </div>
      </div>
      <div class="app-buttons">
        {'<a href="'+android+'" class="android-btn" target="_blank">Android</a>' if android else ''}
        {'<a href="'+ios+'" class="ios-btn" target="_blank">iOS</a>' if ios else ''}
      </div>
    </div>
'''

        # Footer
        year = __import__('datetime').datetime.now().year
        html += f"""
    <footer>© {year} TripBozo — All rights reserved.</footer>
  </div>
</body>
</html>"""

        return HttpResponse(html, content_type="text/html")




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
