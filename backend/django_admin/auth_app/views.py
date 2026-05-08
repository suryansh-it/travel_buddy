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


class BookmarkListView(APIView):
	"""Get all bookmarks for the current user, optionally filtered by type."""
	permission_classes = [IsAuthenticated]

	def get(self, request):
		bookmark_type = request.query_params.get('type')  # 'country' or 'app'
		
		bookmarks = Bookmark.objects.filter(user=request.user).order_by('-created_at')
		if bookmark_type:
			bookmarks = bookmarks.filter(bookmark_type=bookmark_type)
		
		from .serializers import BookmarkSerializer
		serializer = BookmarkSerializer(bookmarks, many=True)
		return Response(serializer.data, status=status.HTTP_200_OK)


class BookmarkCreateView(APIView):
	"""Create a new bookmark for a country or app."""
	permission_classes = [IsAuthenticated]

	def post(self, request):
		bookmark_type = request.data.get('bookmark_type')
		country_id = request.data.get('country_id')
		app_id = request.data.get('app_id')

		if not bookmark_type or bookmark_type not in ['country', 'app']:
			return Response(
				{"error": "Invalid bookmark_type. Must be 'country' or 'app'."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if bookmark_type == 'country' and not country_id:
			return Response(
				{"error": "country_id required for country bookmarks."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if bookmark_type == 'app' and not app_id:
			return Response(
				{"error": "app_id required for app bookmarks."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		try:
			country = None
			app = None
			if bookmark_type == 'country':
				from country.models import Country
				country = Country.objects.get(id=country_id)
			elif bookmark_type == 'app':
				from country.models import TravelApp
				app = TravelApp.objects.get(id=app_id)

			bookmark, created = Bookmark.objects.get_or_create(
				user=request.user,
				bookmark_type=bookmark_type,
				country=country,
				app=app,
			)

			if not created:
				return Response(
					{"error": "Bookmark already exists."},
					status=status.HTTP_400_BAD_REQUEST,
				)

			from .serializers import BookmarkSerializer
			serializer = BookmarkSerializer(bookmark)
			return Response(serializer.data, status=status.HTTP_201_CREATED)

		except (Country.DoesNotExist, TravelApp.DoesNotExist):
			return Response(
				{"error": "Country or App not found."},
				status=status.HTTP_404_NOT_FOUND,
			)


class BookmarkDeleteView(APIView):
	"""Delete a specific bookmark by ID."""
	permission_classes = [IsAuthenticated]

	def delete(self, request, bookmark_id):
		try:
			bookmark = Bookmark.objects.get(id=bookmark_id, user=request.user)
			bookmark.delete()
			return Response(status=status.HTTP_204_NO_CONTENT)
		except Bookmark.DoesNotExist:
			return Response(
				{"error": "Bookmark not found."},
				status=status.HTTP_404_NOT_FOUND,
			)


class UserProfileStatsView(APIView):
	"""Get user profile stats: visit history, bookmarks count, bundles count, etc."""
	permission_classes = [IsAuthenticated]

	def get(self, request):
		from country.models import CountryVisit
		user = request.user

		# Get visited countries (sorted by most recent visit)
		visited_countries = CountryVisit.objects.filter(
			visit_count__gt=0
		).order_by('-updated_at')[:10]  # Top 10 recently updated

		visited_data = [
			{
				"id": cv.country.id,
				"code": cv.country.code,
				"name": cv.country.name,
				"flag": cv.country.flag.url if cv.country.flag else None,
				"visits": cv.visit_count,
				"last_visited": cv.updated_at,
			}
			for cv in visited_countries
		]

		# Count user bookmarks by type
		bookmark_stats = Bookmark.objects.filter(user=user).values('bookmark_type').count()
		country_bookmarks = Bookmark.objects.filter(user=user, bookmark_type='country').count()
		app_bookmarks = Bookmark.objects.filter(user=user, bookmark_type='app').count()

		# Get recently bookmarked countries
		recent_bookmarks = Bookmark.objects.filter(
			user=user,
			bookmark_type='country'
		).order_by('-created_at')[:6]

		bookmarks_data = []
		for bm in recent_bookmarks:
			if bm.country:
				bookmarks_data.append({
					"id": bm.country.id,
					"code": bm.country.code,
					"name": bm.country.name,
					"flag": bm.country.flag.url if bm.country.flag else None,
					"bookmarked_at": bm.created_at,
				})

		return Response({
			"visited_countries": visited_data,
			"bookmark_stats": {
				"total": bookmark_stats,
				"countries": country_bookmarks,
				"apps": app_bookmarks,
			},
			"recent_bookmarks": bookmarks_data,
		}, status=status.HTTP_200_OK)

