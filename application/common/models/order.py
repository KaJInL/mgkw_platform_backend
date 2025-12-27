from enum import Enum, StrEnum

from tortoise import fields

from application.common.base import DefaultModel


class OrderStatus(str, Enum):
    PENDING = "pending"  # 待支付
    PAID = "paid"  # 已支付
    CANCELLED = "cancelled"  # 已取消
    TIMEOUT_CLOSED = "timeout_closed"  # 超时关闭


class PaymentType(str, Enum):
    WECHAT = "wechat"  # 微信支付


class Order(DefaultModel):
    user_id = fields.IntField(description="用户ID")
    status = fields.CharEnumField(OrderStatus, default=OrderStatus.PENDING, description="订单状态")
    total_amount = fields.DecimalField(max_digits=10, decimal_places=2, description="订单总金额")
    pay_time = fields.DatetimeField(null=True, description="支付时间")
    expire_time = fields.DatetimeField(null=True, description="订单过期时间（待支付订单超过此时间将自动取消）")
    payment_type = fields.CharEnumField(PaymentType, null=True, description="支付类型")
    merchant_order_no = fields.CharField(max_length=64, null=True, unique=True,
                                         description="商家订单号（平台自己的订单号）")
    serial_no = fields.CharField(max_length=64, null=True, unique=True, description="流水号（支付流水号）")
    remark = fields.TextField(null=True, description="备注")

    class Meta:
        table = "order"
        table_description = "订单表"


class OrderItemType(StrEnum):
    PHYSICAL = "physical"  # 普通商品
    VIP = "vip"  # vip
    DESIGN = "design"  # 设计作品授权


class OrderItem(DefaultModel):
    order_id = fields.IntField(description="订单ID")
    item_type = fields.CharEnumField(OrderItemType, description="订单项类型")
    product_id = fields.IntField(description="商品ID")
    sku_id = fields.IntField(null=True, description="SKU ID（当item_type为SKU时不为空）")
    product_name = fields.CharField(max_length=255, description="商品名称")
    sku_name = fields.CharField(max_length=255, null=True, description="SKU名称（当item_type为SKU时不为空）")
    quantity = fields.IntField(default=1, description="数量")
    price = fields.DecimalField(max_digits=10, decimal_places=2, description="单价")
    unit_price = fields.DecimalField(max_digits=10, decimal_places=2, description="单价")
    total_price = fields.DecimalField(max_digits=10, decimal_places=2, description="总价（单价 * 数量）")

    class Meta:
        table = "order_item"
        table_description = "订单项表"
