from django.db import models
from datetime import datetime

from django_countries.fields import CountryField
from phonenumber_field import validators
from phonenumber_field.modelfields import PhoneNumberField
from main.models import User


class Case(models.Model):
    title = models.CharField(max_length=250)
    desc = models.CharField(max_length=250)
    file = models.ForeignKey('File', on_delete=models.PROTECT, related_name='cases')
    lead_attorney = models.ForeignKey(User, models.PROTECT, related_name="lead_attorney")
    date_of_registration = models.DateField(default=datetime.today)
    registrator = models.ForeignKey(User, models.SET_NULL, null=True, related_name="matter_registrator")
    last_editor = models.ForeignKey(User, models.SET_NULL, null=True, related_name="matter_latest_editor")
    last_edit_time = models.DateTimeField()


class File(models.Model):
    date_of_registration = models.DateField(default=datetime.today)
    registrator = models.ForeignKey(User, models.SET_NULL, null=True, related_name="file_registrator")
    last_editor = models.ForeignKey(User, models.SET_NULL, null=True, related_name="file_latest_editor")
    last_edit_time = models.DateTimeField()


class Client(models.Model):
    is_company = models.BooleanField()
    if not is_company:
        first_name = models.CharField(max_length=250)
        last_name = models.CharField(max_length=250)
        email = models.EmailField()
        phone1 = PhoneNumberField(null=True, region="LB")
        phone2 = PhoneNumberField(null=True, region="LB")
        phone3 = PhoneNumberField(null=True, region="LB")
        company = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, related_name="people")
        job_title = models.CharField(max_length=250)
        website = models.URLField(null=True, blank=True)
        description = models.TextField(null=True, blank=True)

    else:
        name = models.CharField(max_length=250)

    address = models.ForeignKey("Address", on_delete=models.PROTECT)
    date_of_registration = models.DateField(default=datetime.today)
    registrator = models.ForeignKey(User, models.SET_NULL, null=True, related_name="clt_registrator")
    last_editor = models.ForeignKey(User, models.SET_NULL, null=True, related_name="clt_latest_editor")
    last_edit_time = models.DateTimeField()


class Operation(models.Model):
    author = models.ForeignKey(User, models.PROTECT, related_name="author")
    status = models.ForeignKey("Status", models.PROTECT, related_name="status")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=3)
    currency = models.ForeignKey("Currency", models.PROTECT)
    date_of_registration = models.DateField(default=datetime.today)
    registrator = models.ForeignKey(User, models.SET_NULL, null=True, related_name="operation_registrator")


class Status(models.Model):
    name = models.CharField(max_length=50)
    img = models.ImageField()
    color = models.CharField(max_length=10)


class Currency(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50)
    symbol = models.CharField(max_length=50)


class Address(models.Model):
    street = models.CharField(max_length=250)
    building = models.CharField(max_length=150)
    region = models.CharField(max_length=100)
    floor = models.CharField(max_length=50)
    city = models.CharField(max_length=100)
    country = CountryField()
    google_maps_code = models.CharField(max_length=50)
    google_maps_link = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.city}, {self.street}, {self.building}, {self.floor}, {self.country}"

