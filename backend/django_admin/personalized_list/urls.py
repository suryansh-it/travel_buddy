from django.urls import path
from .views import personalized_list_view, generate_qr_code

urlpatterns = [
    path('', personalized_list_view, name='personalized_list'),
    path('generate_qr/', generate_qr_code, name='generate_qr_code')
]