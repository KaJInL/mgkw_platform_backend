from enum import StrEnum

from tortoise import fields

from application.common.base import DefaultModel
from application.common.constants.BoolEnum import BoolEnum


class ProductCheckState(StrEnum):
    PENDING = "PENDING"  # 待审核
    APPROVED = "APPROVED"  # 审核通过
    REJECTED = "REJECTED"  # 审核拒绝


class ProductType(StrEnum):
    PHYSICAL = "PHYSICAL"  # 实体商品
    DESIGN = "DESIGN"  # 设计作品授权
    VIP = "VIP"  # VIP 套餐


class Product(DefaultModel):
    name = fields.CharField(max_length=255, description="商品名称")
    subtitle = fields.CharField(max_length=255, null=True, description="商品副标题")
    cover_image = fields.CharField(max_length=500,null=True, description="商品封面图URL")
    image_urls = fields.JSONField(default=[], description="商品图片列表")
    video_url = fields.CharField(max_length=500, null=True, description="商品视频URL")
    description = fields.TextField(null=True, description="商品简介")
    detail_html = fields.TextField(null=True, description="商品详情富文本")
    category_id = fields.IntField(description="分类ID")
    series_id = fields.IntField(description="系列ID")
    is_published = fields.BooleanField(default=False, description="是否上架")
    creator_user_id = fields.IntField(description="商品创建者用户ID")
    check_state = fields.CharEnumField(ProductCheckState, default=ProductCheckState.PENDING,
                                       description="审核状态：PENDING, APPROVED,REJECTED")
    check_reason = fields.CharField(max_length=255, null=True, description="审核拒绝原因")
    checker_user_id = fields.IntField(null=True, description="审核管理员ID")
    checked_at = fields.DatetimeField(null=True, description="审核时间")
    is_deleted = fields.CharField(max_length=1, default="0", description="是否删除(0:否;1:是;")

    sort = fields.IntField(default=0, description="排序值")
    tags = fields.JSONField(default=[], description="商品标签列表")
    product_type = fields.CharEnumField(ProductType, default=ProductType.PHYSICAL,
                                        description="商品类型: PHYSICAL : 实体商品,DESIGN : 设计作品 ,VIP : 会员套餐")
    is_official = fields.CharEnumField(BoolEnum, default=BoolEnum.NO, description="是否自营: 1: 是 ; 1: 否;")

    class Meta:
        table = "product"
        table_description = "商品表"


class SKU(DefaultModel):
    product_id = fields.IntField(description="所属商品ID")
    name = fields.CharField(max_length=255, description="SKU名称")
    price = fields.DecimalField(max_digits=10, decimal_places=2, description="售价")
    original_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True, description="原价")
    stock = fields.IntField(default=0, description="库存数量")
    code = fields.CharField(max_length=100, null=True, description="商品编码")
    attributes = fields.JSONField(default={}, description="SKU属性")
    is_enabled = fields.BooleanField(default=True, description="是否启用")
    weight = fields.DecimalField(max_digits=10, decimal_places=2, null=True, description="重量")
    vip_plan_id = fields.IntField(null=True, description="会员套餐ID(当产品type为VIP时不为空)")
    design_license_plan_id = fields.IntField(null=True, description="设计授权方案ID(当产品type为DESIGN时不为空)")
    design_id = fields.IntField(null=True, description="设计作品ID(当产品type为DESIGN时不为空)")

    class Meta:
        table = "sku"
        table_description = "商品SKU表"


class ProductSnapshot(DefaultModel):
    product_id = fields.IntField(description="商品ID")
    snapshot_json = fields.JSONField(description="商品快照JSON")

    class Meta:
        table = "product_snapshot"
        table_description = "商品快照表"
