import json
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query, Request, Response, Header
from fastapi.responses import PlainTextResponse
from tortoise.transactions import atomic

from application.common.config import config
from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
from application.common.exception.exception import HttpBusinessException
from application.common.helper import ResponseHelper
from application.common.middleware.RequestContextMiddleware import get_ctx
from application.common.utils.WechatPayUtils import WechatPayUtils
from application.common.models import WechatPayment, WechatTradeState
from application.common.models.order import Order, OrderStatus
from application.common.models.user import AuthTypeEnum
from application.core.redis_client import redis_client, TimeUnit
from application.service.order_service import order_service
from application.service.account_service import account_service
from application.service.user_auth_service import user_auth_service
from application.service.payment_success_service import payment_success_service
from application.core.logger_util import logger
from tortoise import transactions

wechat = APIRouter()

# 微信支付缓存key前缀
WX_PAY_CACHE_KEY = "wx_pay:prepay_id"
WX_PAY_LOCK_KEY = "lock:wx_pay:prepay_id"
WX_PAY_CALLBACK_LOCK_KEY = "wx_pay:callback"
WX_PAY_CALLBACK_CLOSED_LOCK_KEY = "wx_pay:callback:closed"

# 缓存过期时间（30分钟，与订单过期时间一致）
PREPAY_ID_CACHE_EXPIRE = 30
PREPAY_ID_CACHE_UNIT = TimeUnit.MINUTES

# 分布式锁配置
PAYMENT_LOCK_EXPIRE = 10  # 创建支付订单锁过期时间（秒）
PAYMENT_LOCK_TIMEOUT = 5.0  # 创建支付订单锁等待超时（秒）
CALLBACK_LOCK_EXPIRE = 30  # 回调处理锁过期时间（秒）
CALLBACK_LOCK_TIMEOUT = 10.0  # 回调处理锁等待超时（秒）


@atomic()
@wechat.get("/payment/wechat/create")
async def create_wechat_payment(
        order_id: int = Query(..., description="订单ID", gt=0, alias="orderId")
):
    """
    创建微信支付订单
    
    返回微信支付所需的参数，包括 prepay_id 等
    """
    try:
        # 获取当前登录用户信息（包含授权信息，已缓存）
        login_user_info = await account_service.get_login_user_info()
        user_id = login_user_info.user.id

        # 从缓存的授权信息中获取微信 openid
        openid = None
        for user_auth in login_user_info.auths:
            if user_auth.auth_type == AuthTypeEnum.WECHAT_MINI_PROGRAM.value:
                openid = user_auth.openid
                break

        if not openid:
            return ResponseHelper.error_with_error_code(HttpErrorCodeEnum.UNAUTHORIZED)

        # 使用分布式锁防止重复创建支付订单
        # 注意：锁的 key 和数据缓存的 key 要分开，避免 aioredlock 的锁 UUID 覆盖数据
        lock_key = f"{WX_PAY_LOCK_KEY}:{user_id}:{order_id}"
        cache_key = f"{WX_PAY_CACHE_KEY}:{user_id}:{order_id}"
        
        async with redis_client.lock(lock_key, expire=PAYMENT_LOCK_EXPIRE, timeout=PAYMENT_LOCK_TIMEOUT):
            # 先从 Redis 获取已缓存的 prepay_id
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"从缓存获取支付参数 - 订单ID: {order_id}")
                return ResponseHelper.success(cached_data)

            # 查询订单信息
            order_detail = await order_service.get_order_detail(order_id)
            if not order_detail:
                return ResponseHelper.error(
                    HttpErrorCodeEnum.SHOW_MESSAGE.code,
                    "订单不存在"
                )

            # 验证订单状态
            if order_detail.status != OrderStatus.PENDING:
                return ResponseHelper.error(
                    HttpErrorCodeEnum.SHOW_MESSAGE.code,
                    f"订单状态异常，当前状态：{order_detail.status}"
                )
            now = datetime.now(timezone.utc)
            # 检查订单是否过期（如果订单有过期时间）
            if hasattr(order_detail, 'expire_time') and order_detail.expire_time:
                if order_detail.expire_time.astimezone(timezone.utc) < now:
                    logger.warning(f"订单已过期 - 订单ID: {order_id}, 过期时间: {order_detail.expire_time}")
                    return ResponseHelper.error(
                        HttpErrorCodeEnum.SHOW_MESSAGE.code,
                        "订单已过期，请重新下单"
                    )

            # 验证订单归属
            if order_detail.user_id != user_id:
                return ResponseHelper.error(
                    HttpErrorCodeEnum.SHOW_MESSAGE.code,
                    "无权操作该订单"
                )

            # 构建订单描述（最多127个字符）
            order_des = ""
            for item in order_detail.items:
                item_desc = f"{item.product_name}"
                if item.sku_name:
                    item_desc += f"-{item.sku_name}"
                item_desc += ";"
                # 检查长度，确保不超过127个字符
                if len(order_des + item_desc) > 127:
                    order_des = order_des[:124] + "..."
                    break
                order_des += item_desc

            if not order_des:
                order_des = "商品订单"

            # 将订单金额转换为分（微信支付要求）
            total_amount = Decimal(order_detail.total_amount)
            total_in_cents = int(total_amount * 100)
            if config.debug_mode:
                total_in_cents = 1
                logger.info(f"微信支付测试模式 - 订单ID: {order_id}, 金额: {total_amount}")

            if total_in_cents <= 0:
                return ResponseHelper.error(
                    HttpErrorCodeEnum.SHOW_MESSAGE.code,
                    "订单金额无效"
                )

            # 调用微信支付API创建订单
            try:
                result = await WechatPayUtils.create_jsapi_order_with_expire(
                    description=order_des,
                    out_trade_no=order_detail.merchant_order_no,
                    total=total_in_cents,
                    openid=openid,
                    expire_minutes=30,
                    attach=f"order_id:{order_id}"  # 附加订单ID，方便回调时关联
                )
            except Exception as e:
                logger.error(f"创建微信支付订单失败 - 订单ID: {order_id}, 错误: {e}")
                return ResponseHelper.error(
                    HttpErrorCodeEnum.SHOW_MESSAGE.code,
                    f"创建支付订单失败: {str(e)}"
                )

            prepay_id = result.get("prepay_id")
            if not prepay_id:
                logger.error(f"微信支付返回数据缺少prepay_id - 订单ID: {order_id}, 响应: {result}")
                return ResponseHelper.error(
                    HttpErrorCodeEnum.SHOW_MESSAGE.code,
                    "创建支付订单失败：未获取到prepay_id"
                )

            # 创建或更新支付记录
            wechat_payment = await WechatPayment.get_or_none(out_trade_no=order_detail.merchant_order_no)
            if wechat_payment:
                # 如果记录已存在，更新基本信息
                logger.info(f"支付记录已存在，更新信息 - 商户订单号: {order_detail.merchant_order_no}")
                wechat_payment.order_id = order_id
                wechat_payment.openid = openid
                wechat_payment.total_amount = total_amount
                # 如果不是最终状态，重置为未支付
                if wechat_payment.trade_state not in [WechatTradeState.SUCCESS]:
                    wechat_payment.trade_state = WechatTradeState.NOTPAY
                await wechat_payment.save()
            else:
                # 创建新记录
                logger.info(f"创建支付记录 - 商户订单号: {order_detail.merchant_order_no}")
                await WechatPayment.create(
                    order_id=order_id,
                    mchid="",  # 会在回调时更新
                    out_trade_no=order_detail.merchant_order_no,
                    transaction_id=None,  # 支付成功后更新
                    trade_type=None,  # 会在回调时更新
                    trade_state=WechatTradeState.NOTPAY,  # 未支付
                    openid=openid,
                    total_amount=total_amount
                )

            # 构建小程序支付所需参数
            time_stamp = str(int(datetime.now().timestamp()))  # 秒级时间戳（10位）
            nonce_str = WechatPayUtils.generate_nonce_str(32)
            package_str = f"prepay_id={prepay_id}"

            appid = WechatPayUtils.appid
            if not appid:
                return ResponseHelper.error(
                    HttpErrorCodeEnum.SHOW_MESSAGE.code,
                    "微信支付配置错误：缺少appid"
                )

            pay_sign = WechatPayUtils.generate_miniprogram_pay_sign(
                appid=appid,
                time_stamp=time_stamp,
                nonce_str=nonce_str,
                package=package_str
            )

            # 构建返回数据（包含小程序支付所需的参数）
            payment_data = {
                "prepayId": prepay_id,
                "timeStamp": time_stamp,
                "nonceStr": nonce_str,
                "package": package_str,
                "signType": "RSA",
                "paySign": pay_sign
            }

            # 缓存支付参数到 Redis（30分钟，与订单过期时间一致）
            await redis_client.set(
                cache_key,
                payment_data,
                time=PREPAY_ID_CACHE_EXPIRE,
                unit=PREPAY_ID_CACHE_UNIT
            )

            logger.info(f"✅ 创建微信支付订单成功 - 订单ID: {order_id}, prepay_id: {prepay_id}")
            return ResponseHelper.success(payment_data)

    except HttpBusinessException:
        raise
    except Exception as e:
        logger.exception(f"创建微信支付订单异常 - 订单ID: {order_id}")
        return ResponseHelper.error(
            HttpErrorCodeEnum.SHOW_MESSAGE.code,
            f"创建支付订单失败: {str(e)}"
        )


@wechat.post("/payment/wechat/notify", response_class=PlainTextResponse)
async def wechat_pay_callback(
        request: Request,
        wechatpay_signature: str = Header(..., alias="Wechatpay-Signature", description="微信支付签名"),
        wechatpay_timestamp: str = Header(..., alias="Wechatpay-Timestamp", description="时间戳"),
        wechatpay_nonce: str = Header(..., alias="Wechatpay-Nonce", description="随机字符串"),
        wechatpay_serial: str = Header(..., alias="Wechatpay-Serial", description="证书序列号")
):
    """
    微信支付回调通知接口
    
    接收微信支付的回调通知，验证签名并处理支付结果
    支持幂等性处理，避免重复处理相同的回调
    """
    out_trade_no = None
    transaction_id = None

    try:
        # 获取请求体
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8')

        logger.info("收到微信支付回调通知")
        logger.debug(f"请求头 - Signature: {wechatpay_signature[:20]}...")
        logger.debug(f"请求头 - Timestamp: {wechatpay_timestamp}")
        logger.debug(f"请求头 - Nonce: {wechatpay_nonce}")
        logger.debug(f"请求头 - Serial: {wechatpay_serial}")
        logger.debug(f"请求体长度: {len(body_str)} 字符")

        # 验证签名（使用类方法）
        is_valid = WechatPayUtils.verify_callback_signature(
            timestamp=wechatpay_timestamp,
            nonce=wechatpay_nonce,
            body=body_str,
            signature=wechatpay_signature,
            serial_no=wechatpay_serial
        )

        if not is_valid:
            logger.error("微信支付回调签名验证失败")
            return Response(content="签名验证失败", status_code=400)

        logger.info("微信支付回调签名验证成功")

        # 解析请求体
        try:
            callback_data = json.loads(body_str)
        except json.JSONDecodeError as e:
            logger.error(f"解析回调数据JSON失败: {e}, 原始数据: {body_str[:200]}")
            return Response(content="JSON解析失败", status_code=400)

        event_type = callback_data.get("event_type")
        resource = callback_data.get("resource")

        # 验证必要字段
        if not event_type or not resource:
            logger.error("微信支付回调数据缺少必要字段")
            return Response(content="缺少必要字段", status_code=400)

        ciphertext = resource.get("ciphertext")
        nonce = resource.get("nonce")
        associated_data = resource.get("associated_data", "")
        original_type = resource.get("original_type", "")
        
        if not ciphertext or not nonce:
            logger.error("微信支付回调resource字段不完整")
            return Response(content="resource字段不完整", status_code=400)

        # 记录完整的resource信息用于调试（注意：不记录ciphertext的完整内容，只记录长度）
        resource_for_log = {
            "ciphertext": f"[长度: {len(ciphertext) if ciphertext else 0}]",
            "nonce": nonce,
            "associated_data": associated_data,
            "original_type": original_type
        }
        logger.info(f"回调resource信息: {json.dumps(resource_for_log, ensure_ascii=False)}")
        logger.info(f"回调resource原始值 - associated_data: '{associated_data}' (类型: {type(associated_data)}), original_type: '{original_type}'")
        logger.info(f"nonce原始值: '{nonce}' (长度: {len(nonce)})")
        
        # 确保 associated_data 是字符串类型
        if associated_data is None:
            associated_data = ""
        
        # 尝试不同的 associated_data 值进行解密
        # 根据微信支付文档，associated_data 可能为空字符串或 "transaction"
        associated_data_candidates = []
        
        # 1. 如果 resource.associated_data 存在且不为空，优先使用
        if associated_data:
            associated_data_candidates.append(associated_data)
        
        # 2. 如果 resource.associated_data 为空，尝试使用 original_type
        if not associated_data and original_type:
            associated_data_candidates.append(original_type)
        
        # 3. 如果两者都为空，尝试使用 "transaction"（支付通知的默认值）
        if not associated_data_candidates:
            associated_data_candidates.append("transaction")
        
        # 4. 最后尝试空字符串
        if "" not in associated_data_candidates:
            associated_data_candidates.append("")
        
        # 尝试每个候选值进行解密
        decrypted_data = None
        last_error = None
        
        for candidate in associated_data_candidates:
            logger.info(f"尝试解密 - associated_data: '{candidate}' (长度: {len(candidate)})")
            try:
                decrypted_data = WechatPayUtils.decrypt_callback_resource(
                    ciphertext=ciphertext,
                    nonce=nonce,
                    associated_data=candidate
                )
                logger.info(f"解密成功 - 使用的associated_data: '{candidate}'")
                break
            except Exception as e:
                last_error = e
                logger.warning(f"解密失败 - associated_data: '{candidate}', 错误: {e}")
                continue
        
        if decrypted_data is None:
            logger.error(f"所有associated_data候选值都解密失败，最后一个错误: {last_error}")
            return Response(content=f"解密失败: {str(last_error)}", status_code=400)

        # 提取关键信息用于日志
        out_trade_no = decrypted_data.get("out_trade_no")
        transaction_id = decrypted_data.get("transaction_id")
        logger.info(f"解密成功 - 商户订单号: {out_trade_no}, 微信订单号: {transaction_id}, 事件类型: {event_type}")

        # 处理支付结果
        try:
            if event_type == "TRANSACTION.SUCCESS":
                # 支付成功
                await handle_payment_success(decrypted_data)
                logger.info(f"✅ 支付成功回调处理完成 - 商户订单号: {out_trade_no}, 微信订单号: {transaction_id}")
            elif event_type == "TRANSACTION.CLOSED":
                # 订单关闭
                await handle_payment_closed(decrypted_data)
                logger.info(f"✅ 订单关闭回调处理完成 - 商户订单号: {out_trade_no}")
            else:
                logger.warning(f"未处理的回调事件类型: {event_type}, 商户订单号: {out_trade_no}, 微信订单号: {transaction_id}")
        except Exception as handle_error:
            logger.exception(f"处理回调业务逻辑失败 - 商户订单号: {out_trade_no}, 微信订单号: {transaction_id}")
            # 即使处理失败，也要返回500让微信重试
            return Response(content=f"处理失败: {str(handle_error)}", status_code=500)

        # 返回成功响应（微信要求返回200状态码和SUCCESS字符串）
        return Response(content="SUCCESS", status_code=200)

    except Exception as e:
        logger.exception(f"处理微信支付回调异常 - 商户订单号: {out_trade_no}, 微信订单号: {transaction_id}")
        # 返回500状态码，让微信重试
        return Response(content=f"处理异常: {str(e)}", status_code=500)


def parse_rfc3339_time(time_str: str) -> Optional[datetime]:
    """
    解析RFC3339格式的时间字符串（简化版）
    
    :param time_str: RFC3339格式的时间字符串，如：2018-06-08T10:34:56+08:00
    :return: datetime对象，解析失败返回None
    """
    if not time_str:
        return None

    try:
        # 处理 Z 格式（UTC时间）
        if time_str.endswith('Z'):
            time_str = time_str[:-1] + '+00:00'
        # 尝试使用 fromisoformat（Python 3.7+支持）
        return datetime.fromisoformat(time_str)
    except (ValueError, AttributeError):
        try:
            # 如果失败，简单处理：移除时区信息，只保留日期时间部分
            if '+' in time_str:
                time_str = time_str.split('+')[0]
            elif time_str.endswith('Z'):
                time_str = time_str[:-1]
            time_str = time_str.replace('T', ' ').split('.')[0]
            return datetime.strptime(time_str[:19], '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None


async def handle_payment_success(payment_data: dict):
    """
    处理支付成功回调（支持幂等性处理，使用分布式锁和数据库事务）
    
    :param payment_data: 解密后的支付数据
    """
    out_trade_no = payment_data.get("out_trade_no")
    transaction_id = payment_data.get("transaction_id")

    if not out_trade_no or not transaction_id:
        raise ValueError("缺少必要字段：out_trade_no 或 transaction_id")

    logger.info(f"处理支付成功回调 - 商户订单号: {out_trade_no}, 微信订单号: {transaction_id}")

    # 使用分布式锁防止并发处理同一个回调
    lock_key = f"{WX_PAY_CALLBACK_LOCK_KEY}:{transaction_id}"
    
    try:
        async with redis_client.lock(lock_key, expire=CALLBACK_LOCK_EXPIRE, timeout=CALLBACK_LOCK_TIMEOUT):
            # 幂等性检查 - 先检查 transaction_id（微信唯一订单号）
            existing = await WechatPayment.get_or_none(
                transaction_id=transaction_id,
                trade_state=WechatTradeState.SUCCESS
            )
            if existing:
                logger.info(f"订单已处理过（幂等性检查1）- 商户订单号: {out_trade_no}, 微信订单号: {transaction_id}")
                return

            # 再检查 out_trade_no 是否已经支付成功
            existing_by_trade_no = await WechatPayment.get_or_none(
                out_trade_no=out_trade_no,
                trade_state=WechatTradeState.SUCCESS
            )
            if existing_by_trade_no:
                # 如果存在且已支付，但 transaction_id 不同，说明有问题
                if existing_by_trade_no.transaction_id and existing_by_trade_no.transaction_id != transaction_id:
                    logger.error(
                        f"订单号冲突 - 商户订单号: {out_trade_no} 已关联微信订单: {existing_by_trade_no.transaction_id}, "
                        f"新的微信订单: {transaction_id}"
                    )
                    raise ValueError(f"订单号冲突：{out_trade_no}")
                logger.info(f"订单已处理过（幂等性检查2）- 商户订单号: {out_trade_no}")
                return

            # 提取数据
            amount_info = payment_data.get("amount", {})
            payer = payment_data.get("payer", {})
            
            # 解析支付时间
            pay_time = parse_rfc3339_time(payment_data.get("success_time")) or datetime.now()

            # 使用数据库事务确保数据一致性
            async with transactions.in_transaction():
                # 查找支付记录
                wechat_payment = await WechatPayment.get_or_none(out_trade_no=out_trade_no)

                if wechat_payment:
                    # 更新现有记录
                    logger.info(f"更新支付记录 - 商户订单号: {out_trade_no}")
                    
                    # 更新支付信息
                    wechat_payment.transaction_id = transaction_id
                    wechat_payment.trade_state = WechatTradeState.SUCCESS
                    wechat_payment.trade_state_desc = payment_data.get("trade_state_desc", "支付成功")
                    wechat_payment.success_time = payment_data.get("success_time")
                    wechat_payment.bank_type = payment_data.get("bank_type", "")
                    wechat_payment.trade_type = payment_data.get("trade_type", "")
                    wechat_payment.mchid = payment_data.get("mchid", "")
                    
                    # 更新金额信息
                    payer_total = amount_info.get("payer_total", 0)
                    if payer_total > 0:
                        wechat_payment.payer_total = Decimal(str(payer_total / 100))
                    
                    await wechat_payment.save()
                    order_id = wechat_payment.order_id

                # 更新订单状态
                if order_id:
                    logger.info(f"开始更新订单状态 - 订单ID: {order_id}")
                    success = await payment_success_service.on_payment_success(
                        order_id=order_id,
                        pay_time=pay_time
                    )
                    if success:
                        logger.info(f"✅ 订单已更新为已支付 - 订单ID: {order_id}, 商户订单号: {out_trade_no}")
                    else:
                        logger.error(f"❌ 订单状态更新失败 - 订单ID: {order_id}, 商户订单号: {out_trade_no}")
                        raise ValueError(f"订单状态更新失败：订单ID {order_id}")
                else:
                    logger.error(f"❌ 支付记录缺少订单ID - 商户订单号: {out_trade_no}, 微信订单号: {transaction_id}")
                    raise ValueError(f"支付记录缺少订单ID：{out_trade_no}")
                    
    except Exception as lock_error:
        if "Lock timeout" in str(lock_error) or "Failed to acquire" in str(lock_error):
            logger.warning(f"获取锁超时，可能正在处理中 - 商户订单号: {out_trade_no}, 微信订单号: {transaction_id}")
            # 再次检查是否已经处理成功
            existing = await WechatPayment.get_or_none(
                transaction_id=transaction_id,
                trade_state=WechatTradeState.SUCCESS
            )
            if existing:
                logger.info(f"订单已由其他进程处理成功 - 商户订单号: {out_trade_no}")
                return
        raise


async def handle_payment_closed(payment_data: dict):
    """
    处理订单关闭回调（支持幂等性处理，使用分布式锁）
    
    :param payment_data: 解密后的支付数据
    """
    out_trade_no = payment_data.get("out_trade_no")
    transaction_id = payment_data.get("transaction_id")
    
    if not out_trade_no:
        raise ValueError("缺少商户订单号")

    logger.info(f"处理订单关闭回调 - 商户订单号: {out_trade_no}, 微信订单号: {transaction_id}")

    # 使用分布式锁防止并发处理
    lock_key = f"{WX_PAY_CALLBACK_CLOSED_LOCK_KEY}:{out_trade_no}"
    
    try:
        async with redis_client.lock(lock_key, expire=PAYMENT_LOCK_EXPIRE, timeout=PAYMENT_LOCK_TIMEOUT):
            # 查询支付记录
            wechat_payment = await WechatPayment.get_or_none(out_trade_no=out_trade_no)
            
            if not wechat_payment:
                logger.warning(f"支付记录不存在 - 商户订单号: {out_trade_no}")
                return
            
            # 幂等性检查
            if wechat_payment.trade_state == WechatTradeState.CLOSED:
                logger.info(f"订单已关闭（幂等性）- 商户订单号: {out_trade_no}")
                return
            
            # 如果订单已支付成功，不应该再关闭
            if wechat_payment.trade_state == WechatTradeState.SUCCESS:
                logger.warning(f"订单已支付成功，忽略关闭回调 - 商户订单号: {out_trade_no}")
                return
            
            # 更新订单状态为关闭
            wechat_payment.trade_state = WechatTradeState.CLOSED
            wechat_payment.trade_state_desc = payment_data.get("trade_state_desc", "订单已关闭")
            if transaction_id:
                wechat_payment.transaction_id = transaction_id
            await wechat_payment.save()
            
            logger.info(f"✅ 订单已关闭 - 商户订单号: {out_trade_no}")
            
    except Exception as lock_error:
        if "Lock timeout" in str(lock_error) or "Failed to acquire" in str(lock_error):
            logger.warning(f"获取锁超时，可能正在处理中 - 商户订单号: {out_trade_no}")
            # 再次检查是否已经处理
            existing = await WechatPayment.get_or_none(out_trade_no=out_trade_no)
            if existing and existing.trade_state == WechatTradeState.CLOSED:
                logger.info(f"订单已由其他进程关闭 - 商户订单号: {out_trade_no}")
                return
        raise
