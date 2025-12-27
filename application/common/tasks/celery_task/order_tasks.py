"""
订单相关 Celery 任务
"""
from application.common.decorators.run_async import run_async
from application.core.logger_util import logger
from application.common.tasks.celery_task.celery_app import celery_app


@celery_app.task(name="order.close_expired_order")
@run_async
async def close_expired_order_task(order_id: int) -> dict:
    """
    关闭过期订单任务
    
    Args:
        order_id: 订单ID
    
    Returns:
        处理结果字典
    """
    logger.info(f"开始关闭过期订单，订单ID: {order_id}")

    try:
        # 调用订单服务关闭超时订单
        from application.service.order_service import order_service
        success = await order_service.close_timeout_order(order_id)
        
        if success:
            logger.info(f"✅ 成功关闭超时订单 {order_id}")
            return {"success": True, "order_id": order_id, "message": "订单已超时关闭"}
        else:
            logger.warning(f"⚠️ 订单 {order_id} 超时关闭失败（可能订单状态已改变）")
            return {"success": False, "order_id": order_id, "message": "订单状态不允许超时关闭"}
            
    except Exception as e:
        logger.error(f"❌ 关闭订单 {order_id} 失败: {e}")
        raise

