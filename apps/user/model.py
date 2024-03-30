from tortoise.models import Model
from tortoise import fields


class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=16, null=False, unique=True, index=True)
    hashed_password = fields.CharField(max_length=512, null=False)
    email = fields.CharField(max_length=350, null=False)
    llm_api_config_baseurl = fields.CharField(max_length=512, default=None, null=True)
    llm_api_config_key = fields.CharField(max_length=512, default=None, null=True)
