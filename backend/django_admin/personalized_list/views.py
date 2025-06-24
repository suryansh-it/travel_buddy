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
    items = []
    for a in apps:
        items.append({
            'name': a.get('name', 'App'),
            'android_link': a.get('android_link', None),
            'ios_link':     a.get('ios_link',     None),
        })
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
import json, requests
from datetime import datetime
from .tasks import redis_client
from django.conf import settings
from country.models import TravelApp
from .serializers import TravelAppSerializer
from django.contrib.staticfiles import finders



import json, base64, requests
from datetime import datetime
from django.http import HttpResponse
from django.conf import settings
from django.contrib.staticfiles import finders
from rest_framework import status
from rest_framework.views import APIView
from django.db import transaction
from country.models import Country  # adjust your imports as needed
from country.models import EmergencyContact, LocalPhrase, UsefulTip
from personalized_list.models import TravelApp
from personalized_list.serializers import TravelAppSerializer

class DownloadAppListTextView(APIView):
    """
    API to download the selected app list as a single self-contained HTML page
    (all icons & logos embedded as data:URIs) so it works offline.
    """
    def get(self, request, session_id):
        selected_apps_json = redis_client.get(session_id)
        if not selected_apps_json:
            return HttpResponse(
                "<h1>Bundle Not Found</h1><p>Your session has expired or does not exist.</p>",
                status=status.HTTP_404_NOT_FOUND,
                content_type="text/html"
            )

        selected_app_dicts = json.loads(selected_apps_json)
        app_ids = [app["id"] for app in selected_app_dicts]
        apps_qs = TravelApp.objects.filter(id__in=app_ids)
        apps_data = TravelAppSerializer(apps_qs, many=True).data

        # — embed & resize logo omitted —

        # Build HTML
        html_parts = [f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Your Travel App Bundle • TripBozo</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ margin:0; padding:0; font-family:sans-serif; background:#f7fafc; color:#333; }}
    .container {{ width:90%; max-width:600px; margin:2rem auto; padding:1rem; background:white;
                 border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1); }}
    header {{ text-align:center; margin-bottom:2rem; }}
    header h1 {{ font-size:1.5rem; color:#2ad2c9; margin:0; }} 
    .app-card {{ display:flex; align-items:center; justify-content:space-between;
                padding:1rem 0; border-bottom:1px solid #eee; flex-wrap:wrap; }}
    .app-card:last-child {{ border-bottom:none; }}
    .app-info {{ display:flex; align-items:center; gap:1rem; flex:1 1 auto; min-width:0; }}
    .app-info img {{ width:48px; height:48px; border-radius:8px; object-fit:cover; background:#e0e0e0; }}
    .app-details {{ display:flex; flex-direction:column; flex:1 1 auto; min-width:0; }}
    .app-name {{ margin:0; font-size:1.125rem; color:#222; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
    .app-buttons {{ display:flex; gap:0.5rem; flex-shrink:0; }}
    .app-buttons a {{ text-decoration:none; padding:0.5rem 1rem; border-radius:4px; font-size:0.875rem; color:white; white-space:nowrap; }}
    .android-btn {{ background:#3ddc84; }}
    .ios-btn     {{ background:#000; }}
    footer {{ text-align:center; margin-top:2rem; font-size:0.75rem; color:#999; }}
    @media (max-width:480px) {{
      .app-card {{ flex-direction:column; align-items:flex-start; }}
      .app-buttons {{ margin-top:0.75rem; width:100%; justify-content:flex-start; flex-wrap:wrap; }}
      .app-buttons a {{ flex:1 1 45%; text-align:center; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>tripbozo</h1>
    </header>
"""]

        for app in apps_data:
            # embed icon
            icon_data_uri = ""
            if app.get("icon_url"):
                try:
                    resp = requests.get(app["icon_url"], timeout=3)
                    if resp.status_code == 200:
                        mime = "png" if app["icon_url"].lower().endswith(".png") else "jpeg"
                        b64 = base64.b64encode(resp.content).decode()
                        icon_data_uri = f"data:image/{mime};base64,{b64}"
                except:
                    pass
            if not icon_data_uri:
                icon_data_uri = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHdpZHRoPSc0OScgaGVpZ2h0PSc0OSc+PC9zdmc+"

            android = app.get("android_link","")
            ios     = app.get("ios_link","")

            html_parts.append(f"""
    <div class="app-card">
      <div class="app-info">
        <img src="{icon_data_uri}" alt="{app['name']} icon">
        <div class="app-details">
          <p class="app-name">{app['name']}</p>
        </div>
      </div>
      <div class="app-buttons">
        {f'<a href="{android}" class="android-btn" target="_blank">Android</a>' if android else ''}
        {f'<a href="{ios}"     class="ios-btn"     target="_blank">iOS</a>'     if ios     else ''}
      </div>
    </div>
""")

        year = datetime.now().year
        html_parts.append(f"""
    <footer>© {year} TripBozo — All rights reserved.</footer>
  </div>
</body>
</html>
""")

        return HttpResponse("".join(html_parts), content_type="text/html")


class DownloadQRCodeView(APIView):
    """
    API to download the QR code as an image.
    """

    def get(self, request, session_id):
        selected_apps_json = redis_client.get(session_id)

        if not selected_apps_json:
            return Response({"error": "Session not found or expired"}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Match the same logic as GenerateQRCodeView
        base_url = settings.FRONTEND_URL
        shareable_url = f"{base_url}/bundle-redirect/{session_id}"

        # ✅ Generate QR Code from shareable URL
        qr_base64 = generate_qr_code([shareable_url])
        
        # Convert Base64 to image
        qr_image_data = base64.b64decode(qr_base64)
        image = Image.open(io.BytesIO(qr_image_data))

        # Serve as downloadable file
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
