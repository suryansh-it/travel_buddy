from django.urls import path

from .views import AdminOptionsView, AdminRecordIngestView, AdminSummaryView

urlpatterns = [
    path("summary/", AdminSummaryView.as_view(), name="admin_summary"),
    path("options/", AdminOptionsView.as_view(), name="admin_options"),
    path("ingest/", AdminRecordIngestView.as_view(), name="admin_ingest"),
]