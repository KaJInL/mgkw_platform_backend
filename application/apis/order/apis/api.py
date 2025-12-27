from fastapi import APIRouter, Query

from application.apis.order.schema.request import CreateOrderReq
from application.apis.order.schema.response import OrderDetail, CreateOrderRes, CancelOrderRes
from application.common.helper import ResponseHelper
from application.common.schema import BaseResponse
from application.service.account_service import account_service
from application.service.order_service import order_service

order = APIRouter()


@order.post(
    "/order/create",
    summary="创建订单",
    response_model=BaseResponse[CreateOrderRes]
)
async def create_order(req: CreateOrderReq):
    """
    创建订单
    
    根据商品ID和SKU ID创建订单，系统会自动：
    - 生成商家订单号（merchant_order_no）
    - 生成流水号（serial_no）
    - 设置订单过期时间
    - 创建订单项
    - 创建商品快照
    - 设置延迟关闭任务
    """
    login_user_info = await account_service.get_login_user_info()
    user_id = login_user_info.user.id
    order_id = await order_service.create_order(
        user_id=user_id,
        product_id=req.product_id,
        sku_id=req.sku_id
    )
    return ResponseHelper.success({"order_id": order_id})


@order.get(
    "/order/detail",
    summary="获取订单详情",
    response_model=BaseResponse[OrderDetail]
)
async def get_order_detail(
    order_id: int = Query(..., description="订单ID", gt=0, alias="orderId")
):
    """
    获取订单详情
    """
    login_user_info = await account_service.get_login_user_info()
    user_id = login_user_info.user.id
    order_detail = await order_service.get_order_detail(
        order_id=order_id,
        user_id=user_id,
        check_user_ownership=True
    )
    return ResponseHelper.success(order_detail)


@order.post(
    "/order/cancel",
    summary="取消订单",
    response_model=BaseResponse[CancelOrderRes]
)
async def cancel_order(
    order_id: int = Query(..., description="订单ID", gt=0, alias="orderId")
):
    """
    取消订单
    
    用户主动取消订单，只能取消自己的待支付订单。
    订单状态将变为 CANCELLED（已取消）。
    """
    login_user_info = await account_service.get_login_user_info()
    user_id = login_user_info.user.id
    
    # 调用取消订单服务（会自动验证订单归属和状态）
    success = await order_service.close_order(order_id, user_id=user_id)
    
    if success:
        return ResponseHelper.success({"order_id": order_id, "message": "订单已取消"})
    else:
        from application.common.exception.exception import HttpBusinessException
        from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
        raise HttpBusinessException(
            HttpErrorCodeEnum.SHOW_MESSAGE,
            message="订单状态不允许取消，只能取消待支付状态的订单"
        )