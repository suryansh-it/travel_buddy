# auth_app/urls.py

from django.urls import path, include
from .views import GoogleLogin, FacebookLogin
from dj_rest_auth.views import UserDetailsView

# SimpleJWT views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


urlpatterns = [
    # username/password login, logout, password reset, etc.
    path("", include("dj_rest_auth.urls")),

    # registration (sign-up) + email verification
    path("registration/", include("dj_rest_auth.registration.urls")),

     path("user/", UserDetailsView.as_view(), name="rest_user_details"),
      # social-login endpoints
    path("social/google/", GoogleLogin.as_view(), name="google_login"),
    path("social/facebook/", FacebookLogin.as_view(), name="facebook_login"),

     # add JWT endpoints:
    path("jwt/create/",  TokenObtainPairView.as_view(), name="jwt_create"),
    path("jwt/refresh/", TokenRefreshView.as_view(), name="jwt_refresh"),
    path("jwt/verify/",  TokenVerifyView.as_view(),  name="jwt_verify"),
]
