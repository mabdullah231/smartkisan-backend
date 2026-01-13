from tortoise import fields
from tortoise.models import Model


class Message(Model):
    id = fields.IntField(pk=True)
    question = fields.CharField(max_length=255)
    answer = fields.TextField()
    chat = fields.ForeignKeyField("models.Chat", related_name="messages")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)