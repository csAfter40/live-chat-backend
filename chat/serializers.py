from rest_framework import serializers
from .models import User


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
