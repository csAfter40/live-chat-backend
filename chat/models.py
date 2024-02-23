from django.contrib.auth.models import AbstractUser
from django.db import models


def upload_thumbnail(instance, filename):
    path = f"thumbnails/{instance.username}"
    if "." in filename:
        extension = filename.split(".")[-1]
        path = path + "." + extension
    return path


class User(AbstractUser):
    thumbnail = models.ImageField(upload_to=upload_thumbnail, null=True, blank=True)


# Create your models here.
