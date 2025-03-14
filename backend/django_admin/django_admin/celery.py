# This ensures Celery auto-discovers tasks inside apps.

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")

app = Celery("django_admin")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
