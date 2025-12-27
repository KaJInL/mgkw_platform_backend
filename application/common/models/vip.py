from tortoise import fields

from application.common.base import DefaultModel


class VIPPlan(DefaultModel):
    name = fields.CharField(max_length=255, description="会员套餐名称")
    days = fields.IntField(description="套餐有效期天数")
    price = fields.DecimalField(max_digits=10, decimal_places=2, description="价格")
    privileges = fields.TextField(null=True, description="会员权益列表富文本")
    bg_image_url = fields.CharField(max_length=500, null=True, description="会员卡背景图片URL")

    class Meta:
        table = "vip_plan"
        table_description = "VIP套餐表"


class UserVIP(DefaultModel):
    user_id = fields.IntField(description="用户ID")
    total_days = fields.IntField(default=0, description="累计会员天数")
    start_time = fields.DatetimeField(description="会员开始时间")
    end_time = fields.DatetimeField(description="会员结束时间")

    class Meta:
        table = "user_vip"
        table_description = "用户会员绑定表"
