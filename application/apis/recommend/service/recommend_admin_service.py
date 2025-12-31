from typing import List
import json

from application.service.sys_conf_service import sys_conf_service
from application.service.recommend_service import recommend_service
from application.apis.recommend.schema.response import RecommendItem
from application.core.logger_util import logger


class RecommendAdminService:
    """推荐管理服务"""
    
    async def get_recommend_list(self) -> List[RecommendItem]:
        """
        获取推荐列表（调用通用服务）
        :return: 推荐列表
        """
        return await recommend_service.get_recommend_list()
    
    async def update_recommend_list(self, items: List[RecommendItem]) -> bool:
        """
        更新推荐列表
        :param items: 推荐项列表
        :return: 是否更新成功
        """
        try:
            # 将请求模型转换为字典
            items_dict = [item.model_dump() for item in items]
            
            # 转换为 JSON 字符串
            json_str = json.dumps(items_dict, ensure_ascii=False)
            
            # 保存到系统配置
            await sys_conf_service.set_config(
                sys_key=recommend_service.RECOMMEND_CONFIG_KEY,
                sys_value=json_str,
                description="推荐列表配置"
            )
            
            logger.info(f"更新推荐列表成功，共 {len(items)} 条")
            return True
            
        except Exception as e:
            logger.error(f"更新推荐列表失败: {e}")
            return False


recommend_admin_service = RecommendAdminService()
