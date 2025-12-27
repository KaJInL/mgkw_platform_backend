from tortoise import fields

from application.common.base import DefaultModel


class SysConf(DefaultModel):
    sys_key = fields.CharField(max_length=50, unique=True, description="配置 key")
    sys_value = fields.TextField(description="配置 value")
    description = fields.CharField(null=True,max_length=255, default="", description="描述")

    class Meta:
        table = "sys_conf"
        table_description = "系统配置表"
