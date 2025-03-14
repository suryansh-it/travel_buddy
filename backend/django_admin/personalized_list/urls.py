from django.urls import path
from .views import (
    PersonalAppListView,
    GenerateQRCodeView,
    DownloadQRCodeView,
    DownloadAppListTextView
)

urlpatterns = [
    # Create and retrieve personalized app lists
    path("personalized-list/", PersonalAppListView.as_view(), name="personal_app_list"),
    path("personalized-list/<str:session_id>/", PersonalAppListView.as_view(), name="retrieve_personal_list"),

    # Generate QR Code
    path("personalized-list/qr/<str:session_id>/", GenerateQRCodeView.as_view(), name="generate_qr_code"),

    # Download QR Code as an image
    path("personalized-list/download-qr/<str:session_id>/", DownloadQRCodeView.as_view(), name="download_qr_code"),

    # Download selected app list as a text file
    path("personalized-list/download-text/<str:session_id>/", DownloadAppListTextView.as_view(), name="download_app_list_text"),
]
