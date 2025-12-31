from typing import List
import json

from application.service.sys_conf_service import sys_conf_service
from application.apis.recommend.schema.response import RecommendItem
from application.core.logger_util import logger


class RecommendService:
    """推荐通用服务"""
    
    # 系统配置 key
    RECOMMEND_CONFIG_KEY = "recommend_list"
    
    async def get_recommend_list(self) -> List[RecommendItem]:
        """
        获取推荐列表（通用方法）
        :return: 推荐列表
        """
        try:
            # 从系统配置获取推荐数据
            value = await sys_conf_service.get_value_by_key(self.RECOMMEND_CONFIG_KEY)
            
            if not value:
                # 如果没有配置，返回空列表
                return []
            
            # 解析 JSON 字符串
            items_data = json.loads(value)
            
            # 转换为通用模型
            return [RecommendItem(**item) for item in items_data]
            
        except json.JSONDecodeError as e:
            logger.error(f"解析推荐列表 JSON 失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取推荐列表失败: {e}")
            return []


# 创建全局实例
recommend_service = RecommendService()

