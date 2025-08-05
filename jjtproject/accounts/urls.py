from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.examinee_login, name='examinee_login'),
    path('consent/', views.examinee_consent, name='examinee_consent'),
    path('register/', views.examinee_registration, name='examinee_registration'),
    path('change-password/', views.change_password, name='change_password'),
    path('check-examinee/', views.check_examinee_exists, name='check_examinee'),
    path('instructions/', views.exam_instructions, name='exam_instructions'),
    path('start-exam/', views.start_exam, name='start_exam'),


]
