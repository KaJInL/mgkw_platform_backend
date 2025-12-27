from enum import Enum

from tortoise import fields

from application.common.base import DefaultModel
from application.common.constants import BoolEnum


class DesignState(str, Enum):
    DRAFT = "DRAFT"  # 草稿
    PENDING = "PENDING"  # 待审核
    APPROVED = "APPROVED"  # 审核通过
    REJECTED = "REJECTED"  # 拒绝
    BOUGHT_OUT = "BOUGHT_OUT"  # 买断


class Design(DefaultModel):
    """
       设计作品模型
       """
    id = fields.IntField(pk=True)
    user_id = fields.IntField(description="设计师用户ID")
    title = fields.CharField(max_length=256, description="作品标题")
    description = fields.TextField(null=True, description="作品描述")
    detail = fields.TextField(null=True, description="作品详情富文本")
    category_id = fields.IntField(null=True, description="所属类目ID")
    series_id = fields.IntField(null=True, description="所属系列ID")
    product_id = fields.IntField(unique=True, null=True, description="所属产品ID")
    tags = fields.JSONField(default=[], description="作品标签列表")
    images = fields.JSONField(default=[], description="作品高清展示图片数组（存储图片URL列表）")
    is_official = fields.CharEnumField(BoolEnum, default=BoolEnum.NO,
                                       description="是否为公司自营设计(如果是公司内部设计师设计的作品则为自营)")
    model_3d_url = fields.TextField(null=True, description="3D 模型文件URL")
    resource_url = fields.TextField(null=True, description="设计全部素材的URL链接")
    state = fields.CharEnumField(DesignState, default=DesignState.DRAFT, description="作品状态")
    is_deleted = fields.CharField(max_length=1, default="0", description="是否删除(0:否;1:是;")


class LicenseType(str, Enum):
    """
    授权类型
    """
    NORMAL = "normal"
    BUYOUT = "buyout"
    COMMERCIAL = "commercial"


class DesignLicensePlan(DefaultModel):
    """
    设计授权方案模型
    固定三种授权类型：普通授权、买断授权、商业授权
    """
    license_type = fields.CharEnumField(LicenseType, description="授权类型")
    description = fields.TextField(null=True, description="授权方案描述")
    base_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True, description="基础定价")

    class Meta:
        table = "design_license_plan"
        table_description = "设计授权方案表"


class UserDesignLicense(DefaultModel):
    user_id = fields.IntField(description="用户ID")
    design_id = fields.IntField(description="设计作品ID")
    license_type = fields.CharEnumField(LicenseType, description="授权类型")
    is_buyout = fields.BooleanField(default=False, description="是否买断")

    class Meta:
        table = "user_design_license"
        table_description = "用户设计授权绑定表"
