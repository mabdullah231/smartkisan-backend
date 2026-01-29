from tortoise import fields
from tortoise.models import Model


class APIConfig(Model):
    id = fields.IntField(pk=True)

    # e.g. "gemini", "openai", "weather"
    category = fields.CharField(max_length=50)

    # e.g. "Gemini API", "Open-Meteo", "OpenWeatherMap"
    provider = fields.CharField(max_length=100)

    api_key = fields.CharField(max_length=512, null=True)

    base_url = fields.CharField(max_length=255, null=True)

    extra_config = fields.JSONField(null=True)
    # example:
    # {
    #   "model": "gemini-1.5-flash",
    #   "units": "metric",
    #   "language": "en"
    # }

    is_active = fields.BooleanField(default=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
