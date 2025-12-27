"""
微信支付下单测试脚本
用于测试微信支付JSAPI/小程序下单功能
"""
import asyncio
import sys
from datetime import datetime

# 添加项目根目录到Python路径
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application.common.utils.WechatPayUtils import get_wechat_pay_utils, WechatPayUtils
from application.core.logger_util import logger


async def test_create_jsapi_order():
    """
    测试创建JSAPI/小程序支付订单
    """
    print("=" * 60)
    print("微信支付下单测试")
    print("=" * 60)
    
    try:
        # 获取微信支付工具类实例
        wechat_pay = get_wechat_pay_utils()
        print(f"✓ 微信支付工具类初始化成功")
        print(f"  - AppID: {wechat_pay.appid}")
        print(f"  - 商户号: {wechat_pay.mchid}")
        print(f"  - 回调地址: {wechat_pay.notify_url}")
        print()
        
        # 测试参数（请根据实际情况修改）
        test_params = {
            "description": "测试商品-微信支付下单",
            "out_trade_no": f"TEST{datetime.now().strftime('%Y%m%d%H%M%S')}",  # 使用时间戳生成唯一订单号
            "total": 1,  # 1分钱，用于测试
            "openid": "o69pE19EkoQqPFkfkkqCglbUYag4",  # 请替换为真实的openid
            "expire_minutes": 30,  # 30分钟后过期
        }
        
        print("测试参数:")
        for key, value in test_params.items():
            print(f"  - {key}: {value}")
        print()
        
        # 创建订单（异步）
        print("正在创建支付订单...")
        result = await WechatPayUtils.create_jsapi_order_with_expire(**test_params)
        
        print("=" * 60)
        print("✓ 订单创建成功！")
        print("=" * 60)
        print(f"预支付交易会话ID (prepay_id): {result.get('prepay_id')}")
        print()
        print("完整响应数据:")
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        return result
        
    except ValueError as e:
        print("=" * 60)
        print("✗ 配置错误")
        print("=" * 60)
        print(f"错误信息: {e}")
        print()
        print("请检查以下配置:")
        print("1. 在 config.yaml 中配置 wechat_pay 部分")
        print("2. 确保所有必需的环境变量都已设置")
        print("3. 确保商户私钥文件路径正确")
        return None
        
    except Exception as e:
        print("=" * 60)
        print("✗ 订单创建失败")
        print("=" * 60)
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print()
        
        # 如果错误信息包含多行，逐行显示
        error_lines = str(e).split('\n')
        if len(error_lines) > 1:
            print("详细错误信息:")
            for line in error_lines:
                print(f"  {line}")
        print()
        
        logger.exception("微信支付下单测试失败")
        return None


async def test_create_jsapi_order_with_custom_params():
    """
    测试创建订单（使用自定义参数）
    """
    print("=" * 60)
    print("微信支付下单测试（自定义参数）")
    print("=" * 60)
    
    try:
        wechat_pay = get_wechat_pay_utils()
        
        # 自定义过期时间（RFC3339格式）
        from datetime import datetime, timedelta
        expire_time = datetime.now() + timedelta(minutes=30)
        time_expire = expire_time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        
        # 测试参数
        test_params = {
            "description": "测试商品-自定义参数",
            "out_trade_no": f"TEST{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "total": 100,  # 1元
            "openid": "test_openid_123456789",  # 请替换为真实的openid
            "time_expire": time_expire,
            "attach": "测试附加数据",
            "goods_tag": "WXG1",  # 订单优惠标记（如果有）
        }
        
        print("测试参数:")
        for key, value in test_params.items():
            print(f"  - {key}: {value}")
        print()
        
        # 创建订单（异步）
        print("正在创建支付订单...")
        result = await WechatPayUtils.create_jsapi_order(**test_params)
        
        print("=" * 60)
        print("✓ 订单创建成功！")
        print("=" * 60)
        print(f"预支付交易会话ID (prepay_id): {result.get('prepay_id')}")
        print()
        
        return result
        
    except Exception as e:
        print("=" * 60)
        print("✗ 订单创建失败")
        print("=" * 60)
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print()
        
        # 如果错误信息包含多行，逐行显示
        error_lines = str(e).split('\n')
        if len(error_lines) > 1:
            print("详细错误信息:")
            for line in error_lines:
                print(f"  {line}")
        print()
        
        logger.exception("微信支付下单测试失败")
        return None


async def main():
    """
    主函数
    """
    print()
    print("请选择测试模式:")
    print("1. 基础测试（使用默认参数）")
    print("2. 自定义参数测试")
    print()
    
    choice = input("请输入选项 (1/2，直接回车默认选择1): ").strip()
    
    if choice == "2":
        await test_create_jsapi_order_with_custom_params()
    else:
        await test_create_jsapi_order()
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    print()
    print("注意事项:")
    print("1. 请确保在 config.yaml 中正确配置了微信支付参数")
    print("2. 请将测试脚本中的 openid 替换为真实的用户openid")
    print("3. 测试环境建议使用1分钱进行测试")
    print("4. 订单号需要保证唯一性，建议使用时间戳或UUID")
    print()


if __name__ == "__main__":
    asyncio.run(main())

