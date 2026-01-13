from tortoise import fields
from tortoise.models import Model
from datetime import datetime


class AI_Config(Model):
    id = fields.IntField(primary_key=True)
    api_key = fields.CharField(max_length=255)
    model_name = fields.CharField(max_length=255)
    prompt = fields.TextField(null = True)
