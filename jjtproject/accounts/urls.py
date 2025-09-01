from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
 
    path('consent/', views.examinee_consent, name='examinee_consent'),
    path('register/', views.examinee_registration, name='examinee_registration'),
    path('change-password/', views.change_password, name='change_password'),
    path('check-examinee/', views.check_examinee_exists, name='check_examinee'),
    path('instructions/', views.exam_instructions, name='exam_instructions'),
    path('start-exam/', views.start_exam, name='start_exam'),


    # Staff login
    path("staff-login/", auth_views.LoginView.as_view(
        template_name="accounts/staff_login.html",
        redirect_authenticated_user=True
    ), name="staff_login"),

    # ✅ Alias for templates that expect 'login'
    path("login/", auth_views.LoginView.as_view(
        template_name="accounts/staff_login.html",
        redirect_authenticated_user=True
    ), name="login"),

    # Logout
    path("logout/", auth_views.LogoutView.as_view(next_page="staff_login"), name="logout"),

    path("logout/", auth_views.LogoutView.as_view(next_page="staff_login"), name="logout"),


]
