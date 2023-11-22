from django.contrib import admin
from .models import Book, Location, Type, Author, Language

admin.site.register(Book)
admin.site.register(Location)
admin.site.register(Type)
admin.site.register(Author)
admin.site.register(Language)