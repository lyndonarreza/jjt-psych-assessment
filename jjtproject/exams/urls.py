# exams/urls.py
from django.urls import path
from . import views

urlpatterns = [

    path("", views.list_exams_by_battery, name="list_exams"),
    path("complete/", views.exam_complete, name="exam_complete"),
    path('exams/save_essay/', views.save_essay_answer, name='save_essay_answer')


    
    


]
