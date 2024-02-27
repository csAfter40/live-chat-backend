from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
import base64
from django.core.files.base import ContentFile
from .serializers import UserSerializer


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            return
        # save username to use as a group name for this user
        self.username = user.username
        # Join this user to a group with their username
        async_to_sync(self.channel_layer.group_add)(self.username, self.channel_name)
        self.accept()

    def disconnect(self, code):
        # Leave group/room
        async_to_sync(self.channel_layer.group_discard)(
            self.username, self.channel_name
        )

    # Handle requests

    def receive(self, text_data=None, bytes_data=None):
        # receive message from websocket
        data = json.loads(text_data)
        data_source = data.get("source")

        if data_source == "thumbnail":
            self.receive_thumbnail(data)

        # print("receive", json.dumps(data, indent=2))

    def delete_thumbnail(self):
        user = self.scope["user"]
        user.thumbnail.delete(save=True)
        serialized = UserSerializer(user)
        self.send_group(self.username, "thumbnail", serialized.data)

    def receive_thumbnail(self, data):
        user = self.scope["user"]
        # convert base64 data to django content file
        image_str = data.get("base64")
        if not image_str:
            self.delete_thumbnail()
            return
        image = ContentFile(base64.b64decode(image_str))
        # update thumbnail field
        filename = data.get("filename")
        user.thumbnail.save(filename, image, save=True)
        # Serialize user
        serialized = UserSerializer(user)
        # Send updated user data
        self.send_group(self.username, "thumbnail", serialized.data)

    def send_group(self, group, source, data):
        response = {"type": "broadcast_group", "source": source, "data": data}
        async_to_sync(self.channel_layer.group_send)(group, response)

    def broadcast_group(self, data):
        """
        data:
            - type: "broadcast_group"
            - source: where it originated from
            - data: data as a dict
        """
        data.pop("type")
        """
        return data: 
            - source: where it originated from
            - data: data as a dict
        """
        self.send(text_data=json.dumps(data))