from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from services.qrcode_service import generate_qr_code
import uuid
import json
import redis
from django.conf import settings
from django.shortcuts import get_list_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from qrcode import make as qr_make
from io import BytesIO
import base64
# from apps.models import App  # Assuming App model exists

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