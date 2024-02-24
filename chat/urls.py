from django.urls import path
from . import views

urlpatterns = [path("signin/", views.SignInView.as_view(), name="signin")]
