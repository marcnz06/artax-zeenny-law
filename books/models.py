from dirtyfields import DirtyFieldsMixin
from django.db import models
from datetime import datetime
from main.models import User
import functools
import os


def custom_cover_filename(instance, filename, object):
    _, file_extension = os.path.splitext(filename)
    book_id = Book.objects.all().last().pk
    if book_id is None:
        book_id = 0
    filename = f"{instance.id if instance.id is not None else book_id + 1}-{object}{file_extension}"
    return f"{object}/{filename}"


class Book(models.Model, DirtyFieldsMixin):
    lib_id = models.CharField(max_length=50, default="ABC123")
    author = models.ForeignKey("Author", models.PROTECT, related_name="book")
    title = models.CharField(max_length=250)
    subject = models.TextField(null=True)
    type = models.ForeignKey("Type", models.PROTECT, related_name="book")
    section = models.CharField(max_length=250)
    location = models.ForeignKey("Location", models.PROTECT, related_name="book", null=True)
    publisher = models.CharField(max_length=250)
    publishing_date = models.CharField(max_length=250, null=True)
    purchase_date = models.DateField(null=True, blank=True)
    summary = models.FileField(upload_to=functools.partial(custom_cover_filename, object="summary"), blank=True, null=True)
    cover = models.ImageField(upload_to=functools.partial(custom_cover_filename, object="cover"), blank=True, null=True)
    isbn = models.CharField(max_length=14, blank=True, null=True)
    number_of_copies = models.IntegerField()
    language = models.ForeignKey("Language", models.SET_NULL, related_name="book", null=True)
    date_of_registration = models.DateField(default=datetime.today)
    registrator = models.ForeignKey(User, models.SET_NULL, null=True, related_name="book_registrator")
    last_editor = models.ForeignKey(User, models.SET_NULL, null=True, related_name="book_latest_editor")
    last_edit_time = models.DateTimeField()

    def __str__(self):
        return f"{self.title} by {self.author}"

    def serialize_report(self):
        return {
            'lib_id': self.lib_id,
            'author': self.author.name,
            'title': self.title,
            'type': self.type.code,
            'section': self.section,
            'location': self.location.code,
            'publisher': self.publisher,
            'publishing_date': self.publishing_date,
            'language': self.language.code,
        }


class Author(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name}"


class Type(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=3)

    def __str__(self):
        return f"{self.name} | Code: {self.code}"


class Location(models.Model):
    code = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.code}"


class Language(models.Model):
    name = models.CharField(max_length=250)
    code = models.CharField(max_length=3)

    def __str__(self):
        return f"{self.name} | Code: {self.code}"
