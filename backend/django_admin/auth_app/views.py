# auth_app/views.py

from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
# import any other adapters you need...

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter

class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

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
