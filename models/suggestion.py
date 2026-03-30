from tortoise import fields
from tortoise.models import Model


class UserSuggestion(Model):
    """
    One row per user per calendar day (advice_date). Updated when Gemini regenerates
    (e.g. up to 4 times per day); updated_at reflects the last run.
    """

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="suggestions",
        on_delete=fields.CASCADE,
    )
    advice_date = fields.DateField(index=True)
    eng_title = fields.CharField(max_length=512)
    ur_title = fields.CharField(max_length=512)
    eng_description = fields.TextField()
    ur_description = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_suggestion"
        unique_together = (("user", "advice_date"),)
