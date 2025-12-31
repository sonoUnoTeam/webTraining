from django.urls import path
from django.conf import settings
from . import views
from .views import CustomPasswordResetView,CustomPasswordResetConfirmView

from django.contrib.auth import views as auth_views
app_name = 'userApp'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('logout/', views.signout, name='logout'),
    path('signin/', views.signin, name='signin'),
    path('profile/<str:username>/', views.ProfileView.as_view(), name="profile"),
    path('changePassword/', views.MyPasswordChangeView.as_view(), name="changePassword"),
    path('changePassword/done/', views.MyPasswordResetDoneView.as_view(), name="passwordResetDone"),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    
     # Recuperación de contraseña
    path('password_reset/', CustomPasswordResetView.as_view(
        template_name="userApp/password_reset.html",
        email_template_name="userApp/password_reset_email.txt",
        html_email_template_name="userApp/password_reset_email.html",
        subject_template_name="userApp/password_reset_subject.txt"
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name="userApp/password_reset_done.html"), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(template_name="userApp/passwordChange.html"), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name="userApp/password_reset_complete.html"), name='password_reset_complete'),
]