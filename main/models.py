from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import EmailValidator


class User(AbstractUser):
    id = models.BigAutoField(primary_key=True)
    email = models.EmailField(blank=True, unique=True, validators=[EmailValidator(
        message="Please enter a valid email address."
    )])
    about = models.TextField()
    job = models.CharField(max_length=200)
    address = models.TextField()
    phone = PhoneNumberField(null=True, region="LB")
    date_of_registration = models.DateField(default=datetime.today)
    twitter_url = models.URLField(default="#")
    facebook_url = models.URLField(default="#")
    insta_url = models.URLField(default="#")
    linkedin_url = models.URLField(default="#")

    def __str__(self):
        return f"@{self.username}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_clearance(self):
        for user_group in self.groups.values_list('name', flat=True):
            return user_group
        if self.is_superuser:
            return 'System Administrator'


