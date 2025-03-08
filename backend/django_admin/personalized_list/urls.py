from django.urls import path
from .views import PersonalAppListView, GenerateQRCodeView

urlpatterns = [
    path("api/personal-list/", PersonalAppListView.as_view(), name="create_personal_list"),
    path("api/personal-list/<str:session_id>/", PersonalAppListView.as_view(), name="get_personal_list"),
    path("api/personal-list/<str:session_id>/qr/", GenerateQRCodeView.as_view(), name="generate_qr"),
]