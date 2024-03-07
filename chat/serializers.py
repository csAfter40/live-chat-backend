from rest_framework import serializers
from .models import User, Connection, Message


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
        if obj.pending_them:
            return "pending-them"
        elif obj.pending_me:
            return "pending-me"
        elif obj.connected:
            return "connected"
        else:
            return "not-connected"


class RequestSerializer(serializers.ModelSerializer):
    sender = UserSerializer()
    receiver = UserSerializer()

    class Meta:
        model = Connection
        fields = ["id", "sender", "receiver", "created"]


class FriendSerializer(serializers.ModelSerializer):

    friend = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()

    class Meta:
        model = Connection
        fields = ["id", "friend", "preview", "updated"]

    def get_friend(self, obj):
        if obj.sender.username == self.context["user"].username:
            return UserSerializer(obj.receiver).data
        return UserSerializer(obj.sender).data

    def get_preview(self, obj):
        return "New connection"


class MessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Message
        fields = ["id", "connection", "sender", "text", "created"]
