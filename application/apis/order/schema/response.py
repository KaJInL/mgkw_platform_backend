from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CreateOrderRes(BaseModel):
    """创建订单返回数据模型"""
    order_id: int = Field(description="订单ID", alias="orderId")

    class Config:
        from_attributes = True
        populate_by_name = True


class CancelOrderRes(BaseModel):
    """取消订单返回数据模型"""
    order_id: int = Field(description="订单ID", alias="orderId")
    message: str = Field(description="提示消息")

    class Config:
        from_attributes = True
        populate_by_name = True


class OrderItemRes(BaseModel):
    """订单项响应数据模型"""
    id: int = Field(description="订单项ID")
    order_id: int = Field(description="订单ID", alias="orderId")
    item_type: str = Field(description="订单项类型", alias="itemType")
    product_id: int = Field(description="商品ID", alias="productId")
    sku_id: Optional[int] = Field(None, description="SKU ID（当item_type为SKU时不为空）", alias="skuId")
    product_name: str = Field(description="商品名称", alias="productName")
    sku_name: Optional[str] = Field(None, description="SKU名称（当item_type为SKU时不为空）", alias="skuName")
    quantity: int = Field(description="数量")
    price: str = Field(description="单价（向后兼容字段）")
    unit_price: str = Field(description="单价", alias="unitPrice")
    total_price: str = Field(description="总价（单价 * 数量）", alias="totalPrice")
    created_at: datetime = Field(description="创建时间", alias="createdAt")
    updated_at: datetime = Field(description="更新时间", alias="updatedAt")

    class Config:
        from_attributes = True
        populate_by_name = True


class OrderDetail(BaseModel):
    """订单详情响应数据模型"""
    id: int = Field(description="订单ID")
    user_id: int = Field(description="用户ID", alias="userId")
    status: str = Field(description="订单状态")
    total_amount: str = Field(description="订单总金额", alias="totalAmount")
    pay_time: Optional[datetime] = Field(None, description="支付时间", alias="payTime")
    expire_time: Optional[datetime] = Field(None, description="订单过期时间", alias="expireTime")
    payment_type: Optional[str] = Field(None, description="支付类型", alias="paymentType")
    merchant_order_no: Optional[str] = Field(None, description="商家订单号", alias="merchantOrderNo")
    serial_no: Optional[str] = Field(None, description="流水号", alias="serialNo")
    remark: Optional[str] = Field(None, description="备注")
    created_at: datetime = Field(description="创建时间", alias="createdAt")
    updated_at: datetime = Field(description="更新时间", alias="updatedAt")
    items: List[OrderItemRes] = Field(description="订单项列表")

    class Config:
        from_attributes = True
        populate_by_name = True
