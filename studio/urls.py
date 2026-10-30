from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("programs/", views.programs, name="programs"),
    path("facilities/", views.facilities, name="facilities"),
    path("trainers/", views.trainers, name="trainers"),
    path("schedule/", views.schedule, name="schedule"),
    path("pricing/", views.pricing, name="pricing"),
    path("contact/", views.contact, name="contact"),
    path("newsletter/", views.newsletter_signup, name="newsletter_signup"),
    path("register/", views.register, name="register"),
    path("login/", views.FitZoneLoginView.as_view(), name="login"),
    path("admin/login/", views.AdminLoginView.as_view(), name="admin_login"),
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html",
        email_template_name="registration/password_reset_email.html",
        subject_template_name="registration/password_reset_subject.txt",
        success_url=reverse_lazy("password_reset_done"),
    ), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="registration/password_reset_confirm.html",
        success_url=reverse_lazy("password_reset_complete"),
    ), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/reports/", views.admin_reports, name="admin_reports"),
    path("admin/<slug:resource>/", views.manage_list, name="admin_manage_list"),
    path("admin/<slug:resource>/new/", views.manage_form, name="admin_manage_new"),
    path("admin/<slug:resource>/<int:pk>/edit/", views.manage_form, name="admin_manage_edit"),
    path("admin/<slug:resource>/<int:pk>/delete/", views.manage_delete, name="admin_manage_delete"),
    path("book/<int:class_id>/", views.book_class, name="book_class"),
    path("booking/<int:booking_id>/cancel/", views.cancel_booking, name="cancel_booking"),
    path("subscribe/<int:plan_id>/", views.subscribe, name="subscribe"),
    path("manage/<slug:resource>/", views.manage_list, name="manage_list"),
    path("manage/<slug:resource>/new/", views.manage_form, name="manage_new"),
    path("manage/<slug:resource>/<int:pk>/edit/", views.manage_form, name="manage_edit"),
    path("manage/<slug:resource>/<int:pk>/delete/", views.manage_delete, name="manage_delete"),
]
