from django.urls import path
from . import views

urlpatterns = [
    path("signin/", views.SignInView.as_view(), name="signin"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
]
