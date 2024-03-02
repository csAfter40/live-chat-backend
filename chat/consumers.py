from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
import base64
from django.core.files.base import ContentFile
from .serializers import UserSerializer, SearchSerializer, RequestSerializer
from .models import User, Connection
from django.db.models import Q


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
        elif data_source == "search":
            self.receive_search(data)
        elif data_source == "request.connect":
            self.receive_request_connect(data)
        elif data_source == "request.list":
            self.receive_request_list(data)

        print("receive", json.dumps(data, indent=2))

    def delete_thumbnail(self):
        user = self.scope["user"]
        user.thumbnail.delete(save=True)
        serialized = UserSerializer(user)
        self.send_group(self.username, "thumbnail", serialized.data)

    def receive_request_connect(self, data):
        username = data["username"]
        try:
            receiver = User.objects.get(username=username)
        except User.DoesNotExist:
            print("Error: user not found")
            return
        connection, _ = Connection.objects.get_or_create(
            sender=self.scope["user"], receiver=receiver
        )
        print("connection instance: ", connection, "is created? ", _)
        serialized = RequestSerializer(connection)
        self.send_group(connection.sender.username, "request.connect", serialized.data)
        self.send_group(
            connection.receiver.username, "request.connect", serialized.data
        )

    def receive_search(self, data):
        query = data.get("query")
        users = User.objects.filter(
            Q(first_name__istartswith=query)
            | Q(last_name__istartswith=query)
            | Q(username__istartswith=query)
        ).exclude(username=self.username)
        # .annotate(
        #     pending_them=...
        #     pending_me=...
        #     connected=...
        # )
        serialized = SearchSerializer(users, many=True)

        # Send updated user data
        self.send_group(self.username, "search", serialized.data)

    def receive_request_list(self, data):
        user = self.scope["user"]
        connections = Connection.objects.filter(receiver=user, approved=False)
        serialized = RequestSerializer(connections, many=True)

        # Send updated user data
        self.send_group(self.username, "request.list", serialized.data)

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
