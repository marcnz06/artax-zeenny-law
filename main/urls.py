from django.urls import path, re_path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.views.static import serve

app_name = "main"

urlpatterns = [
    path("", views.index, name="index"),
    re_path(r'^media/(?P<path>.*)$', login_required(serve), {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^logs/(?P<path>.*)$', login_required(serve), {'document_root': settings.LOGGING_DIR}),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("login/", views.login_view, name="login"),
    path("register/", views.new_user, name="register"),
    path("confirm/<str:uidb64>/<str:token>/", views.confirm_email, name="verify_email"),
    path("users/<str:username>/", views.profile, name="profile"),
    path("change-password/", views.change_password, name="change_password"),
    path("logout/", views.logout_view, name="logout"),
    path('qrcode/<str:string_to_encode>/', views.generate_qr_code, name='generate_qr_code'),
    path('download_qr_code/<str:string_to_encode>/', views.download_qr_code, name='download_qr_code'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
