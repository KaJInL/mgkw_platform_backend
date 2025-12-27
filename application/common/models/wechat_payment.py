from enum import Enum

from tortoise import fields

from application.common.base import DefaultModel


class WechatTradeType(str, Enum):
    """微信支付交易类型"""
    JSAPI = "JSAPI"  # 公众号支付、小程序支付
    NATIVE = "NATIVE"  # Native支付
    APP = "APP"  # APP支付
    MICROPAY = "MICROPAY"  # 付款码支付
    MWEB = "MWEB"  # H5支付
    FACEPAY = "FACEPAY"  # 刷脸支付


class WechatTradeState(str, Enum):
    """微信支付交易状态"""
    SUCCESS = "SUCCESS"  # 支付成功
    REFUND = "REFUND"  # 转入退款
    NOTPAY = "NOTPAY"  # 未支付
    CLOSED = "CLOSED"  # 已关闭
    REVOKED = "REVOKED"  # 已撤销（仅付款码支付会返回）
    USERPAYING = "USERPAYING"  # 用户支付中（仅付款码支付会返回）
    PAYERROR = "PAYERROR"  # 支付失败（仅付款码支付会返回）


class WechatPayment(DefaultModel):
    """微信支付信息表"""
    order_id = fields.IntField(null=True, description="关联订单ID")
    mchid = fields.CharField(max_length=32, description="商户号")
    out_trade_no = fields.CharField(max_length=32, unique=True, description="商户订单号")
    transaction_id = fields.CharField(max_length=32, null=True, unique=True, description="微信支付订单号")
    trade_type = fields.CharEnumField(WechatTradeType, max_length=16, null=True, description="交易类型")
    trade_state = fields.CharEnumField(WechatTradeState, max_length=32, null=True, description="交易状态")
    trade_state_desc = fields.CharField(max_length=256, null=True, description="交易状态描述")
    bank_type = fields.CharField(max_length=64, null=True, description="银行类型")
    success_time = fields.CharField(max_length=64, null=True, description="支付完成时间（RFC3339格式）")
    openid = fields.CharField(max_length=128, null=True, description="用户标识")
    total_amount = fields.DecimalField(max_digits=10, decimal_places=2, null=True, description="订单总金额")
    payer_total = fields.DecimalField(max_digits=10, decimal_places=2, null=True, description="用户支付金额")

    class Meta:
        table = "wechat_payment"
        table_description = "微信支付信息表"
        indexes = [
            ("out_trade_no",),  # 商户订单号索引
            ("transaction_id",),  # 微信支付订单号索引
            ("order_id",),  # 订单ID索引
        ]

