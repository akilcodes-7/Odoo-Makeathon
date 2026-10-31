from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.index, name="index"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.EmailLoginView.as_view(), name="login"),
    path("logout/", views.PostOnlyLogoutView.as_view(), name="logout"),
    path("password-reset/", views.GenericPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", views.ResetDoneView.as_view(), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", views.ResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset/complete/", views.ResetCompleteView.as_view(), name="password_reset_complete"),
]
