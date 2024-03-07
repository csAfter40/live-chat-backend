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


class Connection(models.Model):
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_connections"
    )
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_connections"
    )
    approved = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}"


class Message(models.Model):
    connection = models.ForeignKey(
        Connection, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.username} -> {self.text}"
