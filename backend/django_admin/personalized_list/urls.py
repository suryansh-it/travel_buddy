from django.urls import path
from .views import (
    PersonalAppListView,
    GenerateQRCodeView,
    DownloadQRCodeView,
    DownloadAppListTextView,
    InitSessionView,
    EmbedSnippetView,
    bundle_preview,
)

urlpatterns = [

    path("init-session/", InitSessionView.as_view(), name="init_session"),
    # Create and retrieve personalized app lists
    path("", PersonalAppListView.as_view(), name="personal_app_list"),

  
    path("<str:session_id>/", PersonalAppListView.as_view(), name="retrieve_personal_list"),

    # Generate QR Code
    path("qr/<str:session_id>/", GenerateQRCodeView.as_view(), name="generate_qr_code"),

    # Download QR Code as an image
    path("download-qr/<str:session_id>/", DownloadQRCodeView.as_view(), name="download_qr_code"),

    # Download selected app list as a text file
    path("download-text/<str:session_id>/", DownloadAppListTextView.as_view(), name="download_app_list_text"),

     path("embed/<str:session_id>/", EmbedSnippetView.as_view(), name="embed_snippet"),
    path("bundle/<str:session_id>/", bundle_preview, name="bundle_preview"),
]
