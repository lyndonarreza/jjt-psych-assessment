from django.urls import path
from . import views

urlpatterns = [
    path("ping/", views.ping, name="responses_ping"),
    path("start/<int:exam_id>/", views.start_attempt, name="responses_start_attempt"),
    path("save/", views.save_answer, name="responses_save_answer"),
    path("submit/<int:attempt_id>/", views.submit_attempt, name="responses_submit_attempt"),
]
