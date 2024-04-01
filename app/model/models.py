from tortoise.models import Model
from tortoise import fields


class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=255, null=False, unique=True, index=True)
    hashed_password = fields.CharField(max_length=255, null=False)
    email = fields.CharField(max_length=255, null=False)
    llm_api_config_baseurl = fields.CharField(max_length=255, default=None, null=True)
    llm_api_config_key = fields.CharField(max_length=255, default=None, null=True)
    
    class Meta:
        table = "users"


class Dataset(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    user = fields.ForeignKeyField('models.User', related_name='datasets')
    samples_json_filename = fields.CharField(max_length=255, null=False)
    db_dirname = fields.CharField(max_length=255, null=False, default="databases")
    tables_json_filename = fields.CharField(max_length=255, null=True, default=None)

    class Meta:
        table = "datasets"


class Sample(Model):
    id = fields.IntField(pk=True)
    attributes = fields.JSONField()
    dataset = fields.ForeignKeyField('models.Dataset', related_name='samples')

    class Meta:
        table = "samples"
        

class DatasetAttr(Model):
    id = fields.IntField(pk=True)
    dataset = fields.ForeignKeyField('models.Dataset', related_name='attrs')
    user = fields.ForeignKeyField('models.User', related_name='attrs')
    attr_name = fields.CharField(max_length=255)

    class Meta:
        table = "dataset_attrs"


class DatasetMetric(Model):
    id = fields.IntField(pk=True)
    dataset = fields.ForeignKeyField('models.Dataset', related_name='metrics')
    user = fields.ForeignKeyField('models.User', related_name='metrics')
    rule_definition = fields.TextField()
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)

    class Meta:
        table = "dataset_metrics"
        

class Evaluation(Model):
    id = fields.IntField(pk=True)
    dataset = fields.ForeignKeyField('models.Dataset', related_name='evaluations')
    sample = fields.ForeignKeyField('models.Sample', related_name='evaluations')
    prediction = fields.CharField(max_length=512)
    metric_values = fields.JSONField()
    user = fields.ForeignKeyField('models.User', related_name='evaluations')
    evaluation_identifier = fields.CharField(max_length=255, null=False) # NOTE: Checking unique for specific user

    class Meta:
        table = "evaluations"
