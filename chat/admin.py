from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Connection, Message


# Register your models here.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    pass


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    pass


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    pass
