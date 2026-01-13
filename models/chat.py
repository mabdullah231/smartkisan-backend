from tortoise import fields 
from tortoise.models import Model


class Chat(Model):
    id = fields.IntField(pk=True)
    chat_name = fields.TextField(null=True)
    user = fields.ForeignKeyField("models.User", related_name="chats")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
  