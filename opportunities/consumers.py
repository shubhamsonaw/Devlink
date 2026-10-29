# import json

# from channels.db import database_sync_to_async
# from channels.generic.websocket import AsyncWebsocketConsumer

# from django.contrib.auth.models import User

# from .models import Message


# class ChatConsumer(AsyncWebsocketConsumer):

#     async def connect(self):

#         self.username = self.scope["url_route"]["kwargs"]["username"]

#         users = sorted([
#             self.scope["user"].username,
#             self.username
#         ])

#         self.room_name = f"chat_{users[0]}_{users[1]}"

#         await self.channel_layer.group_add(
#             self.room_name,
#             self.channel_name
#         )

#         await self.accept()


#     async def disconnect(self, close_code):

#         await self.channel_layer.group_discard(
#             self.room_name,
#             self.channel_name
#         )


#     async def receive(self, text_data):

#         data = json.loads(text_data)

#         message = data["message"]
#         sender_username = data["sender"]

#         sender = await database_sync_to_async(User.objects.get)(
#             username=sender_username
#         )

#         receiver = await database_sync_to_async(User.objects.get)(
#             username=self.username
#         )

#         # SAVE MESSAGE TO DATABASE
#         saved_message = await database_sync_to_async(
#             Message.objects.create
#         )(
#             sender=sender,
#             receiver=receiver,
#             content=message,
#         )

#         await self.channel_layer.group_send(
#             self.room_name,
#             {
#                 "type": "chat_message",
#                 "message": saved_message.content,
#                 "sender": sender.username,
#             }
#         )


#     async def chat_message(self, event):

#         await self.send(text_data=json.dumps({
#             "message": event["message"],
#             "sender": event["sender"],
#         }))


import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        self.other_username = self.scope["url_route"]["kwargs"]["username"]
        self.other_user_id = await self.get_connected_user_id(self.other_username)
        if self.other_user_id is None:
            await self.close(code=4403)
            return

        user_ids = sorted((self.user.pk, self.other_user_id))
        self.room_group_name = f"chat_{user_ids[0]}_{user_ids[1]}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (TypeError, json.JSONDecodeError):
            return

        if not isinstance(data, dict):
            return
        content = data.get("message", "")
        if not isinstance(content, str):
            return
        content = content.strip()
        if not content or len(content) > 5000:
            return

        saved_message = await self.save_message(content)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": saved_message["content"],
                "sender_id": saved_message["sender_id"],
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender_id": event["sender_id"],
        }))

    @database_sync_to_async
    def get_connected_user_id(self, username):
        from django.contrib.auth import get_user_model
        from .models import Connection

        User = get_user_model()
        other_user = User.objects.filter(username=username).only("id").first()
        if other_user is None or other_user.pk == self.user.pk:
            return None
        connected = Connection.objects.filter(
            user1_id=self.user.pk, user2_id=other_user.pk
        ).exists() or Connection.objects.filter(
            user1_id=other_user.pk, user2_id=self.user.pk
        ).exists()
        return other_user.pk if connected else None

    @database_sync_to_async
    def save_message(self, content):
        from django.contrib.auth import get_user_model
        from .models import Message

        User = get_user_model()
        sender = User.objects.get(pk=self.user.pk)
        receiver = User.objects.get(pk=self.other_user_id)
        message = Message.objects.create(sender=sender, receiver=receiver, content=content)
        return {"content": message.content, "sender_id": sender.pk}
