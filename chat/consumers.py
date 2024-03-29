from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
import base64
from django.core.files.base import ContentFile
from .serializers import (
    UserSerializer,
    SearchSerializer,
    RequestSerializer,
    FriendSerializer,
    MessageSerializer,
)
from .models import User, Connection, Message
from django.db.models import Q, Exists, OuterRef
from django.db.models.functions import Coalesce


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
        elif data_source == "request.accept":
            self.receive_request_accept(data)
        elif data_source == "friend.list":
            self.receive_friend_list(data)
        elif data_source == "message.send":
            self.receive_message_send(data)
        elif data_source == "message.list":
            self.receive_message_list(data)
        elif data_source == "message.type":
            self.receive_message_type(data)
        elif data_source == "typing.on":
            self.receive_typing_on(data)

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
        serialized = RequestSerializer(connection)
        self.send_group(connection.sender.username, "request.connect", serialized.data)
        self.send_group(
            connection.receiver.username, "request.connect", serialized.data
        )

    def receive_search(self, data):
        user = self.scope["user"]
        query = data.get("query")
        users = (
            User.objects.filter(
                Q(first_name__istartswith=query)
                | Q(last_name__istartswith=query)
                | Q(username__istartswith=query)
            )
            .exclude(username=self.username)
            .annotate(
                pending_them=Exists(
                    Connection.objects.filter(
                        sender=user, receiver=OuterRef("id"), approved=False
                    )
                ),
                pending_me=Exists(
                    Connection.objects.filter(
                        sender=OuterRef("id"), receiver=user, approved=False
                    )
                ),
                connected=Exists(
                    Connection.objects.filter(
                        Q(sender=OuterRef("id"), receiver=user)
                        | Q(receiver=OuterRef("id"), sender=user),
                        approved=True,
                    )
                ),
            )
        )
        serialized = SearchSerializer(users, many=True)

        self.send_group(self.username, "search", serialized.data)

    def receive_typing_on(self, data):
        friend = data.get("friend")
        self.send_group(
            friend["username"],
            "typing.on",
            {"friend_username": self.scope["user"].username},
        )

    def receive_message_type(self, data):
        user = self.scope["user"]
        recipient_username = data.get("username")

        data = {"username": user.username}
        self.send_group(recipient_username, "message.type", data)

    def receive_message_list(self, data):
        connectionId = data.get("connectionId")
        page = data.get("page")
        page_size = 12
        try:
            connection = Connection.objects.get(pk=connectionId)
        except Connection.DoesNotExist:
            print(f"Connection pk={connectionId} does not exist")
            return

        messages = Message.objects.filter(connection=connection).order_by("-created")[
            page * page_size : (page + 1) * page_size
        ]
        messages_count = Message.objects.filter(connection=connection).count()
        serialized = MessageSerializer(messages, many=True)
        data = {
            "messages": serialized.data,
            "next": page + 1 if messages_count > page * page_size else None,
        }
        self.send_group(self.username, "message.list", data)

    def receive_message_send(self, data):
        user = self.scope["user"]
        connectionId = data.get("connectionId")
        messageText = data.get("messageText")
        try:
            connection = Connection.objects.get(pk=connectionId)
        except Connection.DoesNotExist:
            print("Error: connection object not found")
            return
        message = Message.objects.create(
            connection=connection, sender=user, text=messageText
        )
        serialized = MessageSerializer(message)
        self.send_group(connection.sender.username, "message.send", serialized.data)
        self.send_group(connection.receiver.username, "message.send", serialized.data)

    def receive_friend_list(self, data):
        user = self.scope["user"]
        # latest message subquery
        latest_message = Message.objects.filter(connection=OuterRef("id")).order_by(
            "-created"
        )[:1]
        connections = (
            Connection.objects.filter(Q(receiver=user) | Q(sender=user), approved=True)
            .annotate(
                latest_text=latest_message.values("text"),
                latest_created=latest_message.values("created"),
            )
            .order_by(Coalesce("latest_created", "updated").desc())
        )
        serialized = FriendSerializer(connections, context={"user": user}, many=True)
        self.send_group(self.username, "friend.list", serialized.data)

    def receive_request_list(self, data):
        user = self.scope["user"]
        connections = Connection.objects.filter(receiver=user, approved=False)
        serialized = RequestSerializer(connections, many=True)
        self.send_group(self.username, "request.list", serialized.data)

    def receive_request_accept(self, data):
        request_id = data.get("id")
        user = self.scope["user"]
        connection = Connection.objects.get(pk=request_id)
        connection.approved = True
        connection.save()
        connection.refresh_from_db()
        serialized = RequestSerializer(connection)
        self.send_group(self.username, "request.accept", serialized.data)
        # send updated connections list
        connections = Connection.objects.filter(receiver=user, approved=False)
        serialized = RequestSerializer(connections, many=True)
        self.send_group(self.username, "request.list", serialized.data)
        self.receive_friend_list(data)  # refresh friend list for the user
        # refresh friend's friends list
        serialized_friend = FriendSerializer(
            connection, context={"user": connection.sender}
        )
        self.send_group(
            connection.sender.username, "friend.new", serialized_friend.data
        )

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
        # error occurs when type is removed!!
        # data.pop("type")
        """
        return data: 
            - source: where it originated from
            - data: data as a dict
        """
        self.send(text_data=json.dumps(data))
