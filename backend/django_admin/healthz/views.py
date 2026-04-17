# backend/django_admin/healthz/views.py

from django.http import HttpResponse

def healthz(request):
    """
    Simple healthcheck endpoint.
    Returns 200 OK and a tiny payload.
    """
    return HttpResponse("OK", content_type="text/plain")

