from django.urls import path
from .views import country_page_view

urlpatterns = [
    path('<str:country_code>/', country_page_view, name='country_page')
]