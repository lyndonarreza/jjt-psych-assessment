from django.urls import path
from . import views


urlpatterns = [
    path("", views.dashboard_home, name="dashboard_home"),
    path("reports/", views.reports, name="dashboard_reports"),
    path("reports/export.csv", views.reports_export_csv, name="reports_export_csv"),
    path("report/<int:attempt_id>/pdf/", views.report_pdf, name="dashboard_report_pdf"),
    path("attempt/<int:attempt_id>/tests/", views.view_attempt_tests, name="dashboard_attempt_tests"),
]





