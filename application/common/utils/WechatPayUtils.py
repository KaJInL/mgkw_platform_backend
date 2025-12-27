"""
微信支付工具类
封装微信支付V3 API接口，包括JSAPI/小程序下单等功能
"""
import base64
import json
import time
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from urllib.parse import urlparse

import httpx
import os
import glob
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from Crypto.Cipher import AES

from application import config
from application.core.lifespan import logger


class WechatPayUtils:
    """微信支付V3工具类"""
    
    # 微信支付API域名
    API_DOMAIN = "https://api.mch.weixin.qq.com"
    API_DOMAIN_BACKUP = "https://api2.mch.weixin.qq.com"
    
    # JSAPI下单接口路径
    JSAPI_ORDER_PATH = "/v3/pay/transactions/jsapi"
    
    # 类变量：缓存配置和私钥（避免重复读取）
    appid: Optional[str] = None
    _mchid: Optional[str] = None
    _api_key: Optional[str] = None
    _private_key_path: Optional[str] = None
    _cert_serial_no: Optional[str] = None
    _notify_url: Optional[str] = None
    _private_key: Optional[rsa.RSAPrivateKey] = None
    _wechatpay_public_key: Optional[rsa.RSAPublicKey] = None  # 微信支付公钥（用于验签）
    _platform_cert_dir: Optional[str] = None  # 平台证书目录（保留用于兼容）
    _initialized: bool = False
    
    def __init__(self):
        """初始化微信支付工具类（实例方法，保持向后兼容）"""
        # 确保类变量已初始化
        self._ensure_initialized()
        # 为实例添加属性访问（向后兼容）
        self.appid = self.appid
        self.mchid = self._mchid
        self.api_key = self._api_key
        self.private_key_path = self._private_key_path
        self.cert_serial_no = self._cert_serial_no
        self.notify_url = self._notify_url
        self._private_key = self._private_key

    @classmethod
    def _ensure_initialized(cls):
        """确保类变量已初始化（延迟加载，只初始化一次）"""
        if cls._initialized:
            return
        
        if not config.wechat_pay:
            raise ValueError("微信支付配置未设置，请在config.yaml中配置wechat_pay")
        
        cls.appid = config.wechat_pay.appid
        cls._mchid = config.wechat_pay.mchid
        cls._api_key = config.wechat_pay.api_key
        cls._private_key_path = config.wechat_pay.private_key_path
        cls._cert_serial_no = config.wechat_pay.cert_serial_no
        cls._notify_url = config.wechat_pay.notify_url
        
        # 设置平台证书目录（商户私钥所在目录，用于查找微信支付公钥）
        cls._platform_cert_dir = os.path.dirname(cls._private_key_path)

        # 加载商户私钥并缓存到类变量
        cls._private_key = cls._load_private_key()
        
        # 加载微信支付公钥（用于回调验签）
        cls._wechatpay_public_key = cls._load_wechatpay_public_key()
        
        cls._initialized = True
    
    @classmethod
    def _load_private_key(cls) -> rsa.RSAPrivateKey:
        """
        加载商户私钥（只加载一次，缓存到类变量）
        :return: RSA私钥对象
        """
        # 如果已经加载过，直接返回缓存的私钥
        if cls._private_key is not None:
            return cls._private_key

        try:
            with open(cls._private_key_path, 'r', encoding='utf-8') as f:
                private_key_data = f.read()
            
            # 支持PEM格式的私钥
            private_key = serialization.load_pem_private_key(
                private_key_data.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            logger.info("商户私钥加载成功并缓存到内存")
            return private_key
        except Exception as e:
            logger.error(f"加载商户私钥失败: {e}")
            raise ValueError(f"加载商户私钥失败: {e}")
    
    @classmethod
    def _load_wechatpay_public_key(cls) -> Optional[rsa.RSAPublicKey]:
        """
        加载微信支付公钥（用于回调验签）
        
        根据微信支付文档：https://pay.weixin.qq.com/doc/v3/merchant/4013053249
        微信支付公钥可以从商户平台下载，通常命名为 pub_key.pem 或 wechatpay_public_key.pem
        
        :return: RSA公钥对象，如果加载失败返回None
        """
        if not cls._platform_cert_dir or not os.path.exists(cls._platform_cert_dir):
            logger.warning(f"证书目录不存在: {cls._platform_cert_dir}")
            return None
        
        # 尝试查找微信支付公钥文件
        possible_names = [
            "pub_key.pem",
            "wechatpay_public_key.pem",
            "wechatpay_pub_key.pem",
            f"{cls._mchid}_wxp_pub.pem"  # 微信支付公钥的标准命名格式
        ]
        
        for filename in possible_names:
            pub_key_path = os.path.join(cls._platform_cert_dir, filename)
            if os.path.exists(pub_key_path):
                try:
                    with open(pub_key_path, 'r', encoding='utf-8') as f:
                        pub_key_data = f.read()
                    
                    # 尝试解析为PEM格式的公钥
                    try:
                        public_key = serialization.load_pem_public_key(
                            pub_key_data.encode('utf-8'),
                            backend=default_backend()
                        )
                        logger.info(f"成功加载微信支付公钥 - 文件: {filename}")
                        return public_key
                    except Exception as e:
                        logger.warning(f"解析微信支付公钥失败 {filename}: {e}")
                        continue
                except Exception as e:
                    logger.warning(f"读取微信支付公钥文件失败 {filename}: {e}")
                    continue
        
        logger.warning(f"未找到微信支付公钥文件，尝试从证书目录查找")
        # 如果找不到，尝试从目录中查找所有可能的公钥文件
        try:
            for pattern in ["*.pem", "*.pub"]:
                for cert_file in glob.glob(os.path.join(cls._platform_cert_dir, pattern)):
                    if "key" in os.path.basename(cert_file).lower() and "pub" in os.path.basename(cert_file).lower():
                        try:
                            with open(cert_file, 'r', encoding='utf-8') as f:
                                pub_key_data = f.read()
                            
                            if "BEGIN PUBLIC KEY" in pub_key_data:
                                public_key = serialization.load_pem_public_key(
                                    pub_key_data.encode('utf-8'),
                                    backend=default_backend()
                                )
                                logger.info(f"成功加载微信支付公钥 - 文件: {os.path.basename(cert_file)}")
                                return public_key
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"查找微信支付公钥文件失败: {e}")
        
        logger.error(f"未找到微信支付公钥文件，请从商户平台下载并放置在证书目录: {cls._platform_cert_dir}")
        return None
    

    @classmethod
    def generate_nonce_str(cls, length: int = 32) -> str:
        """
        生成随机字符串
        :param length: 字符串长度
        :return: 随机字符串
        """
        import random
        import string
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    @classmethod
    def generate_out_trade_no(cls, prefix: str = "", length: int = 32) -> str:
        """
        生成商户订单号
        要求：6-32个字符内，只能是数字、大小写字母_-|*且在同一个商户号下唯一
        
        :param prefix: 订单号前缀，可选（如：ORDER、PAY等）
        :param length: 订单号总长度（包含前缀），默认32，范围6-32
        :return: 商户订单号
        """
        if length < 6 or length > 32:
            raise ValueError("订单号长度必须在6-32个字符之间")

        # 处理前缀
        if prefix:
            # 确保前缀只包含允许的字符
            prefix = ''.join(c for c in prefix if c.isalnum() or c in '_-|*')
            # 计算剩余长度
            remaining_length = length - len(prefix)
            if remaining_length < 6:
                raise ValueError(f"前缀过长，订单号总长度至少需要6个字符")
        else:
            remaining_length = length

        # 生成时间戳部分（精确到毫秒，13位）
        timestamp = str(int(time.time() * 1000))
        
        # 计算需要的随机字符串长度
        # 时间戳13位，所以随机字符串长度 = remaining_length - 13
        random_length = max(6, remaining_length - len(timestamp))
        if random_length < 0:
            # 如果时间戳已经超过剩余长度，只使用时间戳的一部分
            timestamp = timestamp[:remaining_length]
            random_length = 0

        # 生成随机字符串部分
        random_part = cls.generate_nonce_str(length=random_length) if random_length > 0 else ""

        # 组合：时间戳 + 随机字符串
        combined = timestamp + random_part

        # 确保组合长度符合要求
        if len(combined) > remaining_length:
            combined = combined[:remaining_length]
        elif len(combined) < remaining_length:
            # 如果太短，补充随机字符
            combined += cls.generate_nonce_str(length=remaining_length - len(combined))

        # 添加前缀
        out_trade_no = prefix + combined if prefix else combined

        # 最终验证长度（应该总是符合要求）
        if len(out_trade_no) < 6:
            out_trade_no += cls.generate_nonce_str(length=6 - len(out_trade_no))
        elif len(out_trade_no) > 32:
            out_trade_no = out_trade_no[:32]
        
        return out_trade_no
    
    @classmethod
    def _build_sign_string(cls, method: str, url: str, timestamp: str, nonce_str: str, body: str = "") -> str:
        """
        构建签名字符串
        :param method: HTTP方法（GET/POST等）
        :param url: 请求URL（包含路径和查询参数）
        :param timestamp: 时间戳
        :param nonce_str: 随机字符串
        :param body: 请求体（POST请求需要）
        :return: 签名字符串
        """
        # 解析URL，只取路径和查询参数
        parsed_url = urlparse(url)
        url_path = parsed_url.path
        if parsed_url.query:
            url_path += f"?{parsed_url.query}"
        
        # 构建签名字符串
        sign_str = f"{method}\n{url_path}\n{timestamp}\n{nonce_str}\n{body}\n"
        return sign_str
    
    @classmethod
    def _sign(cls, sign_str: str) -> str:
        """
        使用RSA-SHA256算法签名
        :param sign_str: 待签名字符串
        :return: Base64编码的签名字符串
        """
        cls._ensure_initialized()
        signature = cls._private_key.sign(
            sign_str.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')
    
    @classmethod
    def generate_miniprogram_pay_sign(
        cls,
        appid: str,
        time_stamp: str,
        nonce_str: str,
        package: str
    ) -> str:
        """
        生成小程序调起支付的签名（paySign）
        
        根据微信支付文档：https://pay.weixin.qq.com/doc/v3/merchant/4012365341
        签名串格式：appId + "\n" + timeStamp + "\n" + nonceStr + "\n" + package + "\n"
        
        :param appid: 小程序appid（必须与下单时使用的appid一致）
        :param time_stamp: 时间戳（秒级，10位数字）
        :param nonce_str: 随机字符串（不超过32位）
        :param package: 预支付交易会话标识，格式：prepay_id=xxx
        :return: Base64编码的签名值（paySign）
        """
        cls._ensure_initialized()
        
        # 构造签名串：appId + "\n" + timeStamp + "\n" + nonceStr + "\n" + package + "\n"
        sign_str = f"{appid}\n{time_stamp}\n{nonce_str}\n{package}\n"
        
        # 使用RSA-SHA256签名
        signature = cls._private_key.sign(
            sign_str.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        # Base64编码
        pay_sign = base64.b64encode(signature).decode('utf-8')
        
        return pay_sign

    @classmethod
    def _generate_authorization(cls, method: str, url: str, body: str = "") -> str:
        """
        生成Authorization请求头
        :param method: HTTP方法
        :param url: 请求URL
        :param body: 请求体
        :return: Authorization字符串
        """
        cls._ensure_initialized()
        timestamp = str(int(time.time()))
        nonce_str = cls.generate_nonce_str()
        
        # 构建签名字符串
        sign_str = cls._build_sign_string(method, url, timestamp, nonce_str, body)
        
        # 签名
        signature = cls._sign(sign_str)
        
        # 构建Authorization
        # 格式: WECHATPAY2-SHA256-RSA2048 mchid="商户号",nonce_str="随机字符串",signature="签名",timestamp="时间戳",serial_no="证书序列号"
        auth = (
            f'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{cls._mchid}",'
            f'nonce_str="{nonce_str}",'
            f'signature="{signature}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{cls._cert_serial_no}"'
        )
        return auth
    
    @classmethod
    async def _make_request(cls, method: str, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发送HTTP请求到微信支付API（异步）
        :param method: HTTP方法
        :param path: API路径
        :param data: 请求数据
        :return: 响应数据
        """
        cls._ensure_initialized()
        url = f"{cls.API_DOMAIN}{path}"
        # 确保body是字符串，即使为空也要是空字符串
        body = json.dumps(data, ensure_ascii=False, separators=(',', ':')) if data else ""
        
        # 生成Authorization（签名时使用body）
        authorization = cls._generate_authorization(method, url, body)
        
        # 构建请求头
        headers = {
            "Authorization": authorization,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "WechatPay-APIv3-Python"
        }
        
        try:
            # 调试日志：输出请求信息
            logger.debug(f"微信支付API请求: {method} {url}")
            logger.debug(f"请求头: {headers}")
            logger.debug(f"请求体: {body}")
            
            # 发送异步请求
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                method=method,
                url=url,
                headers=headers,
                    content=body.encode('utf-8') if body else None,
            )
            
            # 解析响应
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"微信支付API请求成功: {method} {path}, 响应: {result}")
            return result
            
        except httpx.HTTPStatusError as e:
            # HTTP错误，尝试解析微信返回的错误信息
            error_msg = f"微信支付API请求失败: {method} {path}"
            if e.response is not None:
                try:
                    error_info = e.response.json()
                    error_code = error_info.get('code', 'UNKNOWN')
                    error_message = error_info.get('message', str(e))
                    error_detail = error_info.get('detail', {})
                    
                    logger.error(f"{error_msg}")
                    logger.error(f"错误码: {error_code}")
                    logger.error(f"错误信息: {error_message}")
                    if error_detail:
                        logger.error(f"错误详情: {error_detail}")
                    logger.error(f"完整错误响应: {error_info}")
                    
                    # 抛出包含详细错误信息的异常
                    raise Exception(
                        f"微信支付API请求失败 [{error_code}]: {error_message}\n"
                        f"详情: {error_detail if error_detail else '无'}\n"
                        f"完整响应: {json.dumps(error_info, ensure_ascii=False, indent=2)}"
                    )
                except (ValueError, json.JSONDecodeError):
                    # 响应不是JSON格式
                    response_text = e.response.text
                    logger.error(f"{error_msg}")
                    logger.error(f"响应内容: {response_text}")
                    logger.error(f"响应状态码: {e.response.status_code}")
                    logger.error(f"响应头: {dict(e.response.headers)}")
                    raise Exception(
                        f"微信支付API请求失败: HTTP {e.response.status_code}\n"
                        f"响应内容: {response_text}"
                    )
            else:
                raise Exception(f"{error_msg}: {str(e)}")
                
        except httpx.RequestError as e:
            logger.error(f"微信支付API请求失败: {method} {path}, 错误: {e}")
            raise Exception(f"微信支付API请求失败: {str(e)}")
    
    @classmethod
    async def create_jsapi_order(
            cls,
        description: str,
        out_trade_no: str,
        total: int,
        openid: str,
        time_expire: Optional[str] = None,
        attach: Optional[str] = None,
        goods_tag: Optional[str] = None,
        support_fapiao: bool = False,
        currency: str = "CNY",
        detail: Optional[Dict] = None,
        scene_info: Optional[Dict] = None,
        settle_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        创建JSAPI/小程序支付订单（异步）
        
        :param description: 商品描述，不能超过127个字符
        :param out_trade_no: 商户订单号，要求6-32个字符内，只能是数字、大小写字母_-|*且在同一个商户号下唯一
        :param total: 订单总金额，单位为分，必须大于0
        :param openid: 用户在商户appid下的唯一标识
        :param time_expire: 支付结束时间，格式：yyyy-MM-DDTHH:mm:ss+TIMEZONE，如：2015-05-20T13:29:35+08:00
        :param attach: 商户数据包，自定义数据，在查询API和支付通知中原样返回，可作为自定义参数使用
        :param goods_tag: 订单优惠标记，代金券或立减优惠功能的参数
        :param support_fapiao: 电子发票入口开放标识，传入true时，支付成功消息和支付详情页将出现开票入口
        :param currency: 货币类型，符合ISO 4217标准的三位字母代码，默认CNY
        :param detail: 商品详情，商品详情描述
        :param scene_info: 场景信息，支付场景描述
        :param settle_info: 结算信息，是否指定分账
        :return: 包含prepay_id的响应数据
        """
        cls._ensure_initialized()
        # 构建请求数据
        request_data = {
            "appid": cls.appid,
            "mchid": cls._mchid,
            "description": description,
            "out_trade_no": out_trade_no,
            "notify_url": cls._notify_url,
            "amount": {
                "total": total,
                "currency": currency
            },
            "payer": {
                "openid": openid
            }
        }
        
        # 可选参数
        if time_expire:
            request_data["time_expire"] = time_expire
        if attach:
            request_data["attach"] = attach
        if goods_tag:
            request_data["goods_tag"] = goods_tag
        if support_fapiao:
            request_data["support_fapiao"] = support_fapiao
        if detail:
            request_data["detail"] = detail
        if scene_info:
            request_data["scene_info"] = scene_info
        if settle_info:
            request_data["settle_info"] = settle_info
        
        # 发送请求
        result = await cls._make_request("POST", cls.JSAPI_ORDER_PATH, request_data)
        
        return result
    
    @classmethod
    async def create_jsapi_order_with_expire(
        cls,
        description: str,
        out_trade_no: str,
        total: int,
        openid: str,
            expire_minutes: int = 30,
        attach: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建JSAPI/小程序支付订单（带自动过期时间，异步）
        
        :param description: 商品描述
        :param out_trade_no: 商户订单号
        :param total: 订单总金额（分）
        :param openid: 用户openid
        :param expire_minutes: 订单过期时间（分钟），默认30分钟
        :param kwargs: 其他参数，同create_jsapi_order
        :return: 包含prepay_id的响应数据
        """
        # 计算过期时间（北京时间）
        expire_time = datetime.now() + timedelta(minutes=expire_minutes)
        time_expire = expire_time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        
        return await cls.create_jsapi_order(
            description=description,
            out_trade_no=out_trade_no,
            total=total,
            openid=openid,
            time_expire=time_expire,
            attach = attach,
            **kwargs
        )
    
    @classmethod
    def verify_callback_signature(
        cls,
        timestamp: str,
        nonce: str,
        body: str,
        signature: str,
        serial_no: str
    ) -> bool:
        """
        验证微信支付回调签名
        
        根据微信支付文档：https://pay.weixin.qq.com/doc/v3/merchant/4013053249
        验签串格式：timestamp\nnonce\nbody\n
        使用微信支付公钥（RSA）验证签名
        
        :param timestamp: 时间戳（Wechatpay-Timestamp）
        :param nonce: 随机字符串（Wechatpay-Nonce）
        :param body: 请求体（原始字符串，JSON格式）
        :param signature: 签名（Wechatpay-Signature，Base64编码）
        :param serial_no: 证书序列号（Wechatpay-Serial，用于日志记录）
        :return: 验证是否通过
        """
        cls._ensure_initialized()
        
        try:
            # 构建验签串：timestamp\nnonce\nbody\n
            sign_str = f"{timestamp}\n{nonce}\n{body}\n"
            
            # 使用微信支付公钥进行验签
            if not cls._wechatpay_public_key:
                logger.error(f"微信支付公钥未加载，无法进行验签 - 序列号: {serial_no}")
                # 尝试重新加载
                cls._wechatpay_public_key = cls._load_wechatpay_public_key()
                if not cls._wechatpay_public_key:
                    logger.error(f"无法加载微信支付公钥，请从商户平台下载并放置在证书目录: {cls._platform_cert_dir}")
                    return False
            
            # Base64解码签名
            signature_bytes = base64.b64decode(signature)
            
            # 使用微信支付公钥验证签名（RSA-SHA256）
            try:
                cls._wechatpay_public_key.verify(
                    signature_bytes,
                    sign_str.encode('utf-8'),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                logger.info(f"微信支付回调签名验证成功 - 序列号: {serial_no}")
                return True
            except Exception as e:
                logger.error(f"微信支付回调签名验证失败 - 序列号: {serial_no}, 错误: {e}")
                logger.debug(f"验签串: {repr(sign_str)}")
                return False
                
        except Exception as e:
            logger.exception(f"验证回调签名时发生异常: {e}")
            return False

    @classmethod
    def decrypt_callback_resource(cls, ciphertext: str, nonce: str, associated_data: str) -> Dict[str, Any]:
        """
        解密微信支付回调通知中的resource数据（AES-256-GCM算法）
        
        根据微信支付文档：https://pay.weixin.qq.com/doc/v3/merchant/4012071382
        使用API密钥（32字节）进行AES-256-GCM解密
        
        :param ciphertext: 加密数据（resource.ciphertext，Base64编码）
        :param nonce: 随机数（resource.nonce，Base64编码）
        :param associated_data: 附加数据（resource.associated_data，通常为"transaction"）
        :return: 解密后的数据字典
        """
        cls._ensure_initialized()
        try:
            # 微信支付V3的API密钥处理
            # 根据微信支付文档，API密钥是商户在微信支付商户平台设置的32位字符串
            # 需要直接使用字符串的UTF-8编码作为密钥（32字节）
            api_key_str = cls._api_key
            api_key_bytes = api_key_str.encode('utf-8')
            
            # 验证API密钥长度
            if len(api_key_bytes) != 32:
                raise ValueError(f"API密钥长度必须为32字节，当前长度: {len(api_key_bytes)}")
            
            # Base64解码
            # 注意：根据微信支付官方文档，ciphertext是Base64编码的，需要解码
            # 但是nonce是原始字符串（12字节），不是Base64编码的，直接转为UTF-8字节即可
            ciphertext_bytes = base64.b64decode(ciphertext)
            nonce_bytes = nonce.encode('utf-8')  # nonce是原始字符串，直接编码为字节
            
            # 记录详细的调试信息
            logger.info(f"解密参数详情:")
            logger.info(f"  - associated_data: '{associated_data}' (长度: {len(associated_data.encode('utf-8'))})")
            logger.info(f"  - nonce (原始字符串): '{nonce}' (长度: {len(nonce)})")
            logger.info(f"  - nonce (UTF-8字节长度): {len(nonce_bytes)}")
            logger.info(f"  - ciphertext (原始Base64长度): {len(ciphertext)}")
            logger.info(f"  - ciphertext (Base64解码后长度): {len(ciphertext_bytes)}")
            logger.info(f"  - API密钥长度: {len(api_key_bytes)}")
            logger.info(f"  - API密钥前8字节(hex): {api_key_bytes[:8].hex()}")
            logger.info(f"  - API密钥前8字符: '{api_key_str[:8]}'")
            logger.info(f"  - nonce字节(hex): {nonce_bytes.hex()}")
            logger.info(f"⚠️ 注意：nonce应为原始字符串（12字节），不是Base64编码")
            
            # associated_data 处理：如果为空字符串，转换为空字节；否则编码为字节
            # 注意：即使 associated_data 为空字符串，也需要正确处理
            if associated_data:
                associated_data_bytes = associated_data.encode('utf-8')
            else:
                associated_data_bytes = b''
            
            # 使用AES-256-GCM解密
            # 注意：GCM模式的认证标签（tag）在密文的最后16字节
            # 微信支付V3的ciphertext格式：加密数据 + 16字节tag
            if len(ciphertext_bytes) < 16:
                raise ValueError("密文长度不足，无法提取认证标签")
            
            tag = ciphertext_bytes[-16:]
            encrypted_data = ciphertext_bytes[:-16]
            
            # 创建AES-GCM解密器
            # 注意：nonce长度可以是12字节（推荐）或其他长度，但必须与加密时一致
            cipher = AES.new(api_key_bytes, AES.MODE_GCM, nonce=nonce_bytes)
            
            # 设置关联数据（必须在解密前设置）
            # 即使 associated_data 为空字节，也需要调用 update（传入空字节）
            cipher.update(associated_data_bytes)

            # 解密并验证认证标签
            try:
                decrypted_data = cipher.decrypt_and_verify(encrypted_data, tag)
            except ValueError as e:
                # MAC验证失败，记录详细信息用于调试
                logger.error(f"MAC验证失败 - associated_data: '{associated_data}' (长度: {len(associated_data_bytes)}), "
                           f"nonce长度: {len(nonce_bytes)}, ciphertext长度: {len(ciphertext_bytes)}, "
                           f"encrypted_data长度: {len(encrypted_data)}, tag长度: {len(tag)}, "
                           f"API密钥长度: {len(api_key_bytes)}")
                logger.error(f"API密钥前8字节: {api_key_bytes[:8].hex()}")
                raise ValueError(f"解密失败：MAC验证失败，可能是密钥、associated_data或nonce错误: {str(e)}")
            
            # 解析JSON
            result = json.loads(decrypted_data.decode('utf-8'))
            logger.info(f"微信支付回调数据解密成功")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析解密后的JSON数据失败: {e}")
            raise ValueError(f"解密回调数据失败：JSON解析错误: {str(e)}")
        except Exception as e:
            logger.error(f"微信支付回调数据解密失败: {e}")
            raise ValueError(f"解密回调数据失败: {str(e)}")


# 创建全局实例（延迟初始化）
_wechat_pay_utils: Optional[WechatPayUtils] = None


def get_wechat_pay_utils() -> WechatPayUtils:
    """
    获取微信支付工具类实例（单例模式）
    :return: WechatPayUtils实例
    """
    global _wechat_pay_utils
    if _wechat_pay_utils is None:
        _wechat_pay_utils = WechatPayUtils()
    return _wechat_pay_utils


__all__ = [
    "WechatPayUtils",
    "get_wechat_pay_utils",
]
