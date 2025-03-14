# This ensures Celery auto-discovers tasks inside apps.

import os
from celery import Celery
from celery.schedules import crontab
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_admin.settings")

app = Celery("django_admin")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# the task runs automatically every day at midnight!
#Automatically deletes expired Redis sessions.
app.conf.beat_schedule = {
    "clean_expired_sessions_daily": {
        "task": "personalized_list.tasks.clean_expired_sessions",
        "schedule": crontab(minute=0, hour=0),  # Runs at midnight every day
    }
}