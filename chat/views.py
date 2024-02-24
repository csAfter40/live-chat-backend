from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer


def get_auth_for_user(user):
    tokens = RefreshToken.for_user(user)
    return {"user": UserSerializer(user).data}


class SignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        print(username, password)
        if not username or not password:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(username=username, password=password)
        print("user: ", user)
        if not user:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        user_data = get_auth_for_user(user)
        return Response(user_data)
