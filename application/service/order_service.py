from decimal import Decimal
from datetime import datetime, timedelta
import random
from typing import Any, Dict
from tortoise.transactions import atomic

from application.common.base import BaseService
from application.common.config import config
from application.common.exception.exception import HttpBusinessException
from application.common.exception.http_error_code_enum import HttpErrorCodeEnum

from application.common.models import Order, OrderItem, ProductType
from application.common.models.order import OrderStatus, OrderItemType, PaymentType
from application.core.redis_client import redis_client, TimeUnit
from application.core.logger_util import logger
from application.apis.order.schema.response import OrderDetail, OrderItemRes
from application.service.product_service import product_service
from application.service.order_item_service import order_item_service
from application.service.product_snap_shot_service import product_snap_shot_service
from application.common.tasks.celery_task.order_tasks import close_expired_order_task


class OrderService(BaseService[Order]):
    """订单服务"""

    # Redis 缓存键前缀
    CACHE_PREFIX = "order_detail"
    CACHE_ITEM_KEY = f"{CACHE_PREFIX}:item"

    # 缓存过期时间（30分钟）
    CACHE_EXPIRE = 30
    CACHE_UNIT = TimeUnit.MINUTES

    def _convert_decimal_to_str(self, obj: Any) -> Any:
        """
        递归地将字典或列表中的 Decimal 类型转换为字符串，以便 JSON 序列化
        :param obj: 要转换的对象
        :return: 转换后的对象
        """
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_decimal_to_str(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimal_to_str(item) for item in obj]
        else:
            return obj

    def _generate_merchant_order_no(self) -> str:
        """
        生成商家订单号
        格式：MGKW + 时间戳（YYYYMMDDHHmmssSSS，毫秒级）+ 随机6位数字
        :return: 商家订单号
        """
        now = datetime.now()
        # 格式化为：年月日时分秒 + 毫秒（3位）+ 随机6位数字
        date_part = now.strftime("%Y%m%d%H%M%S")
        millisecond = f"{now.microsecond // 1000:03d}"  # 转换为毫秒（3位）
        random_str = f"{random.randint(100000, 999999):06d}"  # 6位随机数
        return f"MGKW{date_part}{millisecond}{random_str}"

    def _generate_serial_no(self) -> str:
        """
        生成流水号（支付流水号）
        格式：SN + 时间戳（YYYYMMDDHHmmssSSS，毫秒级）+ 随机6位数字
        :return: 流水号
        """
        now = datetime.now()
        # 格式化为：年月日时分秒 + 毫秒（3位）+ 随机6位数字
        date_part = now.strftime("%Y%m%d%H%M%S")
        millisecond = f"{now.microsecond // 1000:03d}"  # 转换为毫秒（3位）
        random_str = f"{random.randint(100000, 999999):06d}"  # 6位随机数
        return f"SN{date_part}{millisecond}{random_str}"

    def _get_order_lock_key(self, order_id: int) -> str:
        """
        获取订单修改锁的key
        :param order_id: 订单ID
        :return: 锁的key
        """
        return f"order:modify:{order_id}"

    @atomic()
    async def create_order(self, user_id: int, product_id: int, sku_id: int) -> int:
        """
        创建订单
        :param user_id: 用户ID
        :param product_id: 商品ID
        :param sku_id: SKU ID
        :return: 订单ID
        """
        # 使用分布式锁防止重复下单（基于用户ID、商品ID和SKU ID）
        lock_key = f"order:create:{user_id}:{product_id}:{sku_id}"

        async with redis_client.lock(lock_key, expire=10, timeout=5.0):
            # 查询商品信息（包含SKU列表）
            product_with_sku_info = await product_service.get_by_id_with_skus(product_id)
            if not product_with_sku_info:
                raise HttpBusinessException(message="商品不存在")

            # 检查sku是否和这个product对应
            selected_sku = None
            for sku in product_with_sku_info.skus:
                if sku.id == sku_id:
                    selected_sku = sku
                    break

            if not selected_sku:
                raise HttpBusinessException(HttpErrorCodeEnum.SHOW_MESSAGE, message="商品SKU不存在")

            # 检查SKU是否启用
            if not selected_sku.is_enabled:
                raise HttpBusinessException(HttpErrorCodeEnum.SHOW_MESSAGE, message="商品SKU已下架")

            # 只有0是没有库存,-1为无限库存
            if selected_sku.stock == 0:
                raise HttpBusinessException(HttpErrorCodeEnum.SHOW_MESSAGE, message="商品库存不足")

            # 计算订单总金额（使用SKU价格）
            total_amount = Decimal(str(selected_sku.price))

            # 获取当前时间，确保后续计算使用同一个时间点
            now = datetime.now()
            # 计算订单过期时间（当前时间 + 配置的过期分钟数）
            expire_time = now + timedelta(minutes=config.order.expire_minutes)

            # 生成商家订单号
            merchant_order_no = self._generate_merchant_order_no()
            # 生成流水号
            serial_no = self._generate_serial_no()

            # 根据商品类型生成订单名称
            product_name = product_with_sku_info.name
            if product_with_sku_info.product_type == ProductType.DESIGN:
                order_name = f"{product_name} - 设计作品"
            elif product_with_sku_info.product_type == ProductType.VIP:
                order_name = f"{product_name} - 会员充值"
            else:  # ProductType.PHYSICAL
                order_name = product_name

            # 创建订单
            order = await self.model_class.create(
                user_id=user_id,
                name=order_name,
                status=OrderStatus.PENDING,
                total_amount=total_amount,
                expire_time=expire_time,
                payment_type=PaymentType.WECHAT,  # 默认微信支付
                merchant_order_no=merchant_order_no,
                serial_no=serial_no
            )
            logger.info(
                f"✅ 创建订单 {order.id}，用户 {user_id}，商品 {product_id}，SKU {sku_id}，订单号 {merchant_order_no}，流水号 {serial_no}")

            # 计算单价和总价
            unit_price = Decimal(str(selected_sku.price))
            quantity = 1
            total_price = unit_price * quantity

            item_type = OrderItemType.PHYSICAL
            if product_with_sku_info.product_type == ProductType.DESIGN:
                item_type = OrderItemType.DESIGN
            if product_with_sku_info.product_type == ProductType.VIP:
                item_type = OrderItemType.VIP

            # 创建订单项
            order_item = await order_item_service.model_class.create(
                order_id=order.id,
                item_type=item_type,
                product_id=product_id,
                sku_id=sku_id,
                product_name=product_with_sku_info.name,
                sku_name=selected_sku.name,
                quantity=quantity,
                price=unit_price,  # 保留 price 字段用于向后兼容
                unit_price=unit_price,
                total_price=total_price
            )
            logger.info(f"✅ 创建订单项 {order_item.id}，订单 {order.id}")

            # 创建商品快照（只存储商品信息）
            # 使用 model_dump 获取数据，然后转换 Decimal 为字符串以便 JSON 序列化
            product_snapshot_data = product_with_sku_info.model_dump()
            # 递归转换所有 Decimal 类型为字符串
            product_snapshot_data = self._convert_decimal_to_str(product_snapshot_data)

            await product_snap_shot_service.model_class.create(
                product_id=product_id,
                snapshot_json=product_snapshot_data
            )
            logger.info(f"✅ 创建商品快照，商品 {product_id}")

            # 触发延迟任务，在订单过期时自动关闭订单
            # 计算延迟时间（秒）：订单过期时间 - 当前时间
            delay_seconds = int((expire_time - now).total_seconds())
            if delay_seconds > 0:
                close_expired_order_task.apply_async(
                    args=[order.id],
                    countdown=delay_seconds
                )
                logger.info(
                    f"✅ 已设置订单 {order.id} 延迟关闭任务，将在 {delay_seconds} 秒（{delay_seconds // 60} 分钟）后执行")
            else:
                logger.warning(f"⚠️ 订单 {order.id} 过期时间已过，不设置延迟任务")

            # 缓存订单详情（创建订单后立即查询所有订单项进行缓存）
            await self._cache_order_detail_after_create(order.id)

            return order.id

    async def _cache_order_detail_after_create(self, order_id: int):
        """
        创建订单后缓存订单详情
        :param order_id: 订单ID
        """
        try:
            # 查询订单
            order = await self.get_by_id(order_id)
            if not order:
                return

            # 查询订单项列表
            order_items = await order_item_service.model_class.filter(order_id=order_id).all()

            # 转换为字典格式
            order_dict = order.to_dict()
            order_items_list = [item.to_dict() for item in order_items]

            # 组装订单详情数据
            order_detail_data = {
                **order_dict,
                "items": order_items_list
            }

            # 保存到缓存
            cache_key = f"{self.CACHE_ITEM_KEY}:{order_id}"
            await redis_client.set(
                cache_key,
                order_detail_data,
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
            logger.info(f"💾 已缓存订单详情 {order_id}")
        except Exception as e:
            logger.error(f"❌ 缓存订单详情失败 {order_id}: {e}")

    @atomic()
    async def close_order(self, order_id: int, user_id: int = None) -> bool:
        """
        关闭订单（将状态改为CANCELLED，用户主动取消）
        使用全局订单修改锁，防止与支付操作并发冲突
        :param order_id: 订单ID
        :param user_id: 用户ID（可选，如果提供则验证订单归属）
        :return: 是否成功关闭
        """
        # 使用全局订单修改锁，防止与支付操作并发冲突
        lock_key = self._get_order_lock_key(order_id)

        async with redis_client.lock(lock_key, expire=10, timeout=5.0):
            # 查询订单
            order = await self.get_by_id(order_id)
            if not order:
                raise HttpBusinessException(HttpErrorCodeEnum.SHOW_MESSAGE, message="订单不存在")

            # 验证订单归属（如果提供了用户ID）
            if user_id is not None and order.user_id != user_id:
                raise HttpBusinessException(HttpErrorCodeEnum.SHOW_MESSAGE, message="无权操作该订单")

            # 检查订单状态，只有待支付状态的订单才能被关闭
            if order.status != OrderStatus.PENDING:
                logger.warning(f"⚠️ 订单 {order_id} 状态为 {order.status}，不能关闭")
                return False

            # 更新订单状态为已取消
            await self.update_by_id(order_id, {"status": OrderStatus.CANCELLED})
            logger.info(f"✅ 关闭订单 {order_id}（用户取消）")

            return True

    @atomic()
    async def close_timeout_order(self, order_id: int) -> bool:
        """
        关闭超时订单（将状态改为TIMEOUT_CLOSED，系统自动关闭）
        使用全局订单修改锁，防止与支付操作并发冲突
        :param order_id: 订单ID
        :return: 是否成功关闭
        """
        # 使用全局订单修改锁，防止与支付操作并发冲突
        lock_key = self._get_order_lock_key(order_id)

        async with redis_client.lock(lock_key, expire=10, timeout=5.0):
            # 查询订单
            order = await self.get_by_id(order_id)
            if not order:
                logger.warning(f"⚠️ 订单 {order_id} 不存在")
                return False

            # 检查订单状态，只有待支付状态的订单才能被超时关闭
            if order.status != OrderStatus.PENDING:
                logger.warning(f"⚠️ 订单 {order_id} 状态为 {order.status}，不能超时关闭")
                return False

            # 更新订单状态为超时关闭
            await self.update_by_id(order_id, {"status": OrderStatus.TIMEOUT_CLOSED})
            logger.info(f"✅ 关闭超时订单 {order_id}（系统自动关闭）")

            return True

    @atomic()
    async def mark_order_as_paid(
            self,
            order_id: int,
            pay_time: datetime = None,
            user_id: int = None,
            check_user_ownership: bool = False
    ) -> bool:
        """
        将订单标记为支付成功（将状态改为PAID）
        使用全局订单修改锁，防止与关闭订单等操作并发冲突
        
        :param order_id: 订单ID
        :param pay_time: 支付时间（可选，如果不提供则使用当前时间）
        :param user_id: 用户ID（当check_user_ownership为True时必填，用于验证订单归属）
        :param check_user_ownership: 是否校验订单归属，默认为False
        :return: 是否成功标记为已支付
        """
        # 使用全局订单修改锁，防止与关闭订单等操作并发冲突
        lock_key = self._get_order_lock_key(order_id)

        async with redis_client.lock(lock_key, expire=10, timeout=5.0):
            # 通过get_order_detail获取订单信息（如果需要校验用户归属，会在这里校验）
            try:
                order_detail = await self.get_order_detail(
                    order_id=order_id,
                    user_id=user_id,
                    check_user_ownership=check_user_ownership
                )
            except HttpBusinessException as e:
                # 如果是订单不存在或无权访问的异常，直接返回False
                logger.warning(f"⚠️ 获取订单详情失败 {order_id}: {e.message}")
                return False
            except Exception as e:
                logger.error(f"❌ 获取订单详情异常 {order_id}: {e}")
                return False

            # 从订单详情中获取订单状态
            order_status = order_detail.status
            # 检查订单状态，只有待支付状态的订单才能被标记为已支付
            if order_status != OrderStatus.PENDING:
                logger.warning(
                    f"⚠️ 订单 {order_id} 状态为 {order_status}，不能标记为已支付。"
                    f"只有待支付状态的订单才能被标记为已支付。"
                )
                return False

            # 准备更新数据
            update_data = {
                "status": OrderStatus.PAID
            }

            # 设置支付时间
            if pay_time:
                update_data["pay_time"] = pay_time
            else:
                update_data["pay_time"] = datetime.now()

            # 更新订单状态
            await self.update_by_id(order_id, update_data)
            logger.info(
                f"✅ 订单 {order_id} 已标记为支付成功"
                f"，支付时间: {update_data['pay_time']}"
            )

            # 清除订单详情缓存（因为订单状态已改变）
            try:
                cache_key = f"{self.CACHE_ITEM_KEY}:{order_id}"
                await redis_client.delete(cache_key)
                logger.debug(f"🗑️ 已清除订单详情缓存 {order_id}")
            except Exception as e:
                logger.error(f"❌ 清除订单详情缓存失败 {order_id}: {e}")

            return True

    async def get_order_detail(
            self,
            order_id: int,
            user_id: int = None,
            check_user_ownership: bool = False
    ) -> OrderDetail:
        """
        获取订单详情（包括订单信息和订单项列表）
        先查询缓存，没有的话再去数据库查询，最后写入缓存
        :param order_id: 订单ID
        :param user_id: 用户ID（当check_user_ownership为True时必填，用于验证订单归属）
        :param check_user_ownership: 是否校验订单归属，默认为False
        :return: 订单详情对象
        """
        # 卫语句：参数校验
        if check_user_ownership and user_id is None:
            raise ValueError("当check_user_ownership为True时，user_id参数必填")

        cache_key = f"{self.CACHE_ITEM_KEY}:{order_id}"

        # 先尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取订单详情 {order_id}")
            try:
                order_detail = OrderDetail.model_validate(cached_data)
                # 卫语句：校验用户归属（如果需要）
                if check_user_ownership and order_detail.user_id != user_id:
                    raise HttpBusinessException(HttpErrorCodeEnum.SHOW_MESSAGE, message="无权访问该订单")
                return order_detail
            except HttpBusinessException:
                # 如果是业务异常，直接抛出
                raise
            except Exception as e:
                # 其他异常（如解析失败），记录日志后继续从数据库查询
                logger.warning(f"⚠️ 从缓存解析订单详情失败 {order_id}: {e}，将从数据库查询")

        # 从数据库查询订单
        order = await self.get_by_id(order_id)
        # 卫语句：订单不存在
        if not order:
            raise HttpBusinessException(HttpErrorCodeEnum.SHOW_MESSAGE, message="订单不存在")

        # 卫语句：校验用户归属（如果需要）
        if check_user_ownership and order.user_id != user_id:
            raise HttpBusinessException(HttpErrorCodeEnum.SHOW_MESSAGE, message="无权访问该订单")

        # 查询订单项列表
        order_items = await order_item_service.model_class.filter(order_id=order_id).all()

        # 转换为字典格式
        order_dict = order.to_dict()
        order_items_list = [item.to_dict() for item in order_items]

        # 组装返回数据
        order_dict["items"] = order_items_list

        # 转换为OrderDetailRes对象
        order_detail = OrderDetail.model_validate(order_dict)

        # 保存到缓存（失败不影响主流程）
        try:
            await redis_client.set(
                cache_key,
                order_dict,
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
            logger.debug(f"💾 已缓存订单详情 {order_id}")
        except Exception as e:
            logger.error(f"❌ 缓存订单详情失败 {order_id}: {e}")

        return order_detail

    async def get_order_list(
            self,
            user_id: int,
            page_no: int = 1,
            page_size: int = 10
    ) :
        """
        获取用户的订单列表（分页）
        :param user_id: 用户ID
        :param page_no: 页码
        :param page_size: 每页数量
        :return: 包含订单列表、总数和是否有下一页的字典
        """
        # 构建查询条件：只查询指定用户的订单
        query = self.model_class.filter(user_id=user_id)
        
        # 使用分页方法查询订单列表，按创建时间倒序排序
        pagination_result = await self.paginate(
            query=query,
            page_no=page_no,
            page_size=page_size,
            order_by=["-created_at"]  # 按创建时间倒序
        )

        return pagination_result


order_service = OrderService()
