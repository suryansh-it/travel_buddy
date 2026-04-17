# auth_app/views.py

from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from django.contrib.auth import get_user_model
from django.utils.text import slugify
import requests

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


def _build_unique_username(email, fallback_name="google-user"):
    base_name = slugify((email or "").split("@")[0]) or fallback_name
    base_name = base_name[:150]
    candidate = base_name
    suffix = 1

    while User.objects.filter(username=candidate).exists():
        trimmed = base_name[: max(1, 150 - len(str(suffix)) - 1)]
        candidate = f"{trimmed}-{suffix}"
        suffix += 1

    return candidate


class GoogleLogin(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        access_token = str(request.data.get("access_token") or "").strip()
        if not access_token:
            return Response(
                {"detail": "Google access token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            google_response = requests.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
        except requests.RequestException:
            return Response(
                {"detail": "Could not contact Google. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if google_response.status_code != 200:
            return Response(
                {"detail": "Google sign-in was not accepted. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        profile = google_response.json() if google_response.content else {}
        email = str(profile.get("email") or "").strip().lower()
        if not email:
            return Response(
                {"detail": "Google account did not return an email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        first_name = str(profile.get("given_name") or "").strip()
        last_name = str(profile.get("family_name") or "").strip()

        user = User.objects.filter(email__iexact=email).first()
        created = False

        if not user:
            user = User(
                username=_build_unique_username(email),
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.set_unusable_password()
            user.save()
            created = True
        else:
            update_fields = []
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                update_fields.append("first_name")
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                update_fields.append("last_name")
            if not user.username:
                user.username = _build_unique_username(email)
                update_fields.append("username")
            if update_fields:
                user.save(update_fields=update_fields)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "created": created,
                },
            },
            status=status.HTTP_200_OK,
        )

class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter

from country.models import Country

from .models import UserOriginPreference
from .serializers import UserOriginPreferenceSerializer

class DeleteUserView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"detail": "Account deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class UserOriginCountryPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pref, _ = UserOriginPreference.objects.get_or_create(user=request.user)
        serializer = UserOriginPreferenceSerializer(pref)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        code = str(request.data.get("origin_country_code") or "").strip().upper()

        pref, _ = UserOriginPreference.objects.get_or_create(user=request.user)
        if not code:
            pref.origin_country = None
            pref.save(update_fields=["origin_country", "updated_at"])
            return Response(UserOriginPreferenceSerializer(pref).data, status=status.HTTP_200_OK)

        country = Country.objects.filter(code=code).first()
        if not country:
            return Response(
                {"origin_country_code": ["Invalid country code."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pref.origin_country = country
        pref.save(update_fields=["origin_country", "updated_at"])
        return Response(UserOriginPreferenceSerializer(pref).data, status=status.HTTP_200_OK)

    def patch(self, request):
        return self.put(request)
