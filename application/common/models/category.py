from tortoise import fields

from application.common.base import DefaultModel


class Category(DefaultModel):
    """
    类目模型
    """
    name = fields.CharField(max_length=128, description="类目名称")
    parent_id = fields.IntField(null=True, description="父级类目ID，可为空，用于多级分类")
    top_parent_id = fields.IntField(null=True, description="顶级父类目ID")


class Series(DefaultModel):
    """
    系列模型
    """
    name = fields.CharField(max_length=128, description="系列名称")
    parent_id = fields.IntField(null=True, description="父级类目ID，可为空，用于多级系列")
    top_parent_id = fields.IntField(null=True, description="顶级父类目ID")
