from rest_framework import serializers
from .models import User, Connection


def capitalize_all(sentence):
    words = sentence.split()
    capitalized_words = [word.capitalize() for word in words]
    return " ".join(capitalized_words)


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "full_name", "thumbnail"]

    def get_full_name(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}"
        return capitalize_all(full_name)


class SignUpUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "thumbnail",
            "password",
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        instance = self.Meta.model(**validated_data)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance


class SearchSerializer(UserSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["username", "full_name", "thumbnail", "status"]

    def get_status(self, obj):
        return "not-connected"


class RequestSerializer(serializers.ModelSerializer):
    sender = UserSerializer()
    receiver = UserSerializer()

    class Meta:
        model = Connection
        fields = ["id", "sender", "receiver", "created"]
