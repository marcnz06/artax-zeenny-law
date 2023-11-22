from django.urls import path
from .views import *

app_name = "books"

urlpatterns = [
    path("new-record/", new_book, name="new_book"),
    path('summary/add/<int:book_id>/', change_book_summary, name='change_book_summary'),
    path('cover/add/<int:book_id>/', change_book_cover, name='change_book_cover'),
    path('summary/remove/<int:book_id>/', remove_book_summary, name='remove_book_summary'),
    path('cover/remove/<int:book_id>/', remove_book_cover, name='remove_book_cover'),
    path("queries/", book_queries, name="book_queries"),
    path("", all_books, name="all_books"),
    path("query-by/", query_books_by, name="query_books_by"),
    path("<int:book_id>/", show_book, name="show_book"),
    path("delete-record/<int:book_id>/", delete_book, name="delete_book"),
    path("report/", report, name="report"),
]