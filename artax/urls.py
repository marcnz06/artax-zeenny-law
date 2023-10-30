from django.urls import path, re_path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.views.static import serve


urlpatterns = [
    path("", views.index, name="index"),
    re_path(r'^media/(?P<path>.*)$', login_required(serve), {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^logs/(?P<path>.*)$', login_required(serve), {'document_root': settings.LOGGING_DIR}),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("login/", views.login_view, name="login"),
    path("register/", views.new_user, name="register"),
    path("confirm/<str:uidb64>/<str:token>/", views.confirm_email, name="verify_email"),
    path("profile/", views.profile, name="profile"),
    path("change-password/", views.change_password, name="change_password"),
    path("logout/", views.logout_view, name="logout"),
    path("books/new-record/", views.new_book, name="new_book"),
    path('books/summary/add/<int:book_id>/', views.change_book_summary, name='change_book_summary'),
    path('books/cover/add/<int:book_id>/', views.change_book_cover, name='change_book_cover'),
    path('books/summary/remove/<int:book_id>/', views.remove_book_summary, name='remove_book_summary'),
    path('books/cover/remove/<int:book_id>/', views.remove_book_cover, name='remove_book_cover'),
    path("books/queries/", views.book_queries, name="book_queries"),
    path("books/", views.all_books, name="all_books"),
    path("books/query-by/", views.query_books_by, name="query_books_by"),
    path("books/<int:book_id>/", views.show_book, name="show_book"),
    path("books/delete-record/<int:book_id>/", views.delete_book, name="delete_book"),
    path('books/qrcode/<str:string_to_encode>/', views.generate_qr_code, name='generate_qr_code'),
    path('download_qr_code/<str:string_to_encode>/', views.download_qr_code, name='download_qr_code'),
    path('books/report/', views.generate_pdf_report, name='generate_pdf_report')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
