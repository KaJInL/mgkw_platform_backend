from typing import Optional, List, Dict, Any
from application.common.base import BaseService
from application.common.models import Series
from application.core.redis_client import redis_client, TimeUnit
from application.core.logger_util import logger


class SeriesService(BaseService[Series]):
    """
    系列服务
    支持树形结构查询和 Redis 缓存优化
    """
    
    # Redis 缓存键前缀
    CACHE_PREFIX = "series"
    CACHE_TREE_KEY = f"{CACHE_PREFIX}:tree"
    CACHE_ALL_KEY = f"{CACHE_PREFIX}:all"
    CACHE_ITEM_KEY = f"{CACHE_PREFIX}:item"
    
    # 缓存过期时间（默认1小时）
    CACHE_EXPIRE = 1
    CACHE_UNIT = TimeUnit.HOURS
    
    async def get_all_with_cache(self) -> List[Dict[str, Any]]:
        """
        获取所有系列（带缓存）
        
        :return: 系列列表
        """
        # 尝试从缓存获取
        cached_data = await redis_client.get(self.CACHE_ALL_KEY)
        if cached_data:
            logger.debug(f"✅ 从缓存获取所有系列数据")
            return cached_data
        
        # 从数据库查询
        series_list = await self.list(order_by=["id"])
        
        # 转换为字典并保存到缓存
        if series_list:
            series_dict = [s.to_dict() for s in series_list]
            await redis_client.set(
                self.CACHE_ALL_KEY,
                series_dict,
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
            logger.debug(f"💾 已缓存所有系列数据")
            return series_dict
        
        return []
    
    async def get_by_id_with_cache(self, series_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取系列（带缓存）
        
        :param series_id: 系列ID
        :return: 系列信息
        """
        cache_key = f"{self.CACHE_ITEM_KEY}:{series_id}"
        
        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取系列 {series_id}")
            return cached_data
        
        # 从数据库查询
        series = await self.get_by_id(series_id)
        if not series:
            return None
        
        series_dict = series.to_dict() if hasattr(series, 'to_dict') else series
        
        # 保存到缓存
        await redis_client.set(
            cache_key,
            series_dict,
            time=self.CACHE_EXPIRE,
            unit=self.CACHE_UNIT
        )
        logger.debug(f"💾 已缓存系列 {series_id}")
        
        return series_dict
    
    async def build_tree(
        self,
        parent_id: Optional[int] = None,
        max_depth: Optional[int] = None,
        current_depth: int = 0
    ) -> List[Dict[str, Any]]:
        """
        构建系列树形结构
        
        :param parent_id: 父级ID，None表示顶级系列
        :param max_depth: 最大深度限制，None表示不限制
        :param current_depth: 当前深度（内部使用）
        :return: 树形结构的系列列表
        """
        # 如果是顶级查询，尝试获取完整树缓存
        if parent_id is None:
            cached_tree = await redis_client.get(self.CACHE_TREE_KEY)
            if cached_tree:
                logger.debug("✅ 从缓存获取完整系列树")
                return cached_tree
        
        # 检查深度限制
        if max_depth is not None and current_depth >= max_depth:
            return []
        
        # 获取所有系列数据
        all_series = await self.get_all_with_cache()
        
        # 构建树形结构
        tree = self._build_tree_recursive(
            all_series,
            parent_id,
            max_depth,
            current_depth
        )
        
        # 如果是顶级查询且有数据，保存完整树到缓存
        if parent_id is None and tree:
            await redis_client.set(
                self.CACHE_TREE_KEY,
                tree,
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
            logger.debug("💾 已缓存完整系列树")

        
        return tree
    
    def _build_tree_recursive(
        self,
        all_series: List[Dict[str, Any]],
        parent_id: Optional[int],
        max_depth: Optional[int] = None,
        current_depth: int = 0
    ) -> List[Dict[str, Any]]:
        """
        递归构建树形结构（内部方法）
        
        :param all_series: 所有系列数据
        :param parent_id: 父级ID
        :param max_depth: 最大深度限制
        :param current_depth: 当前深度
        :return: 树形结构
        """
        tree = []
        
        # 检查深度限制
        if max_depth is not None and current_depth >= max_depth:
            return tree
        
        for series in all_series:
            # 匹配父级ID
            if series.get('parent_id') == parent_id:
                series_node = series.copy()
                
                # 递归获取子系列
                children = self._build_tree_recursive(
                    all_series,
                    series.get('id'),
                    max_depth,
                    current_depth + 1
                )
                
                if children:
                    series_node['children'] = children
                else:
                    series_node['children'] = []
                
                tree.append(series_node)
        
        return tree
    
    async def get_children(
        self,
        parent_id: int,
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取指定系列的子系列
        
        :param parent_id: 父级系列ID
        :param recursive: 是否递归获取所有后代
        :return: 子系列列表
        """
        cache_key = f"{self.CACHE_PREFIX}:children:{parent_id}:recursive_{recursive}"
        
        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取系列 {parent_id} 的子系列")
            return cached_data
        
        # 获取所有系列数据
        all_series = await self.get_all_with_cache()
        
        # 根据递归参数获取子系列
        result = (
            self._get_descendants(all_series, parent_id) if recursive
            else [s for s in all_series if s.get('parent_id') == parent_id]
        )
        
        # 保存到缓存
        if result:
            await redis_client.set(
                cache_key,
                result,
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
        
        return result
    
    def _get_descendants(
        self,
        all_series: List[Dict[str, Any]],
        parent_id: int
    ) -> List[Dict[str, Any]]:
        """
        递归获取所有后代系列（内部方法）
        
        :param all_series: 所有系列数据
        :param parent_id: 父级ID
        :return: 后代系列列表
        """
        descendants = []
        
        for series in all_series:
            if series.get('parent_id') == parent_id:
                descendants.append(series)
                # 递归获取子孙系列
                descendants.extend(
                    self._get_descendants(all_series, series.get('id'))
                )
        
        return descendants
    
    async def get_path_to_root(
        self,
        series_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取从指定系列到根节点的路径
        
        :param series_id: 系列ID
        :return: 路径列表（从根到当前节点）
        """
        cache_key = f"{self.CACHE_PREFIX}:path:{series_id}"
        
        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取系列 {series_id} 的路径")
            return cached_data
        
        # 获取所有系列数据
        all_series = await self.get_all_with_cache()
        
        # 构建ID到系列的映射
        series_map = {s['id']: s for s in all_series}
        
        # 向上追溯到根节点
        path = []
        current_id = series_id
        while current_id:
            series = series_map.get(current_id)
            if not series:
                break
            path.insert(0, series)  # 插入到列表开头
            current_id = series.get('parent_id')
        
        # 保存到缓存
        if path:
            await redis_client.set(
                cache_key,
                path,
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
        
        return path
    
    async def create_series(
        self,
        name: str,
        parent_id: Optional[int] = None
    ) -> Series:
        """
        创建系列（自动计算 top_parent_id）
        
        :param name: 系列名称
        :param parent_id: 父级系列ID
        :return: 创建的系列对象
        """
        # 计算顶级父系列ID
        top_parent_id = None
        if parent_id:
            parent = await self.get_by_id(parent_id)
            if parent:
                top_parent_id = parent.top_parent_id or parent.id
        
        # 创建系列
        series = await Series.create(
            name=name,
            parent_id=parent_id,
            top_parent_id=top_parent_id
        )
        
        # 清除缓存
        await self.clear_cache()
        
        logger.info(f"✅ 创建系列: {name} (ID: {series.id})")
        return series
    
    async def update_series(
        self,
        series_id: int,
        data: Dict[str, Any]
    ) -> int:
        """
        更新系列
        
        :param series_id: 系列ID
        :param data: 更新数据
        :return: 更新的记录数
        """
        # 如果更新了父级ID，需要重新计算 top_parent_id
        if 'parent_id' in data:
            parent_id = data['parent_id']
            # 卫语句：没有父级ID则清空 top_parent_id
            if not parent_id:
                data['top_parent_id'] = None
            else:
                # 有父级ID则根据父级计算 top_parent_id
                parent = await self.get_by_id(parent_id)
                if parent:
                    data['top_parent_id'] = parent.top_parent_id or parent.id
        
        # 更新系列
        result = await self.update_by_id(series_id, data)
        
        # 清除缓存
        await self.clear_cache()
        
        logger.info(f"✅ 更新系列 {series_id}")
        return result
    
    async def delete_series(
        self,
        series_id: int,
        recursive: bool = False
    ) -> int:
        """
        删除系列
        
        :param series_id: 系列ID
        :param recursive: 是否递归删除子系列
        :return: 删除的记录数
        """
        # 非递归删除：直接删除当前系列
        if not recursive:
            result = await self.delete_by_id(series_id)
            await self.clear_cache()
            logger.info(f"✅ 删除系列 {series_id}")
            return result
        
        # 递归删除：获取所有子孙系列并一起删除
        all_series = await self.list(order_by=["id"])  # 跳过缓存，确保数据最新
        descendants = self._get_descendants(all_series, series_id)
        descendant_ids = [s['id'] for s in descendants]
        
        # 删除所有子孙系列和自己
        all_ids = [series_id] + descendant_ids
        result = await self.delete_by_ids(all_ids)
        
        # 清除缓存
        await self.clear_cache()
        
        logger.info(f"✅ 删除系列 {series_id} 及其 {len(descendant_ids)} 个子孙系列")
        return result
    
    async def clear_cache(self):
        """清除所有系列相关缓存"""
        try:
            # 获取所有系列相关的缓存键
            cache_keys = await redis_client.keys(f"{self.CACHE_PREFIX}:*")
            if not cache_keys:
                return
            
            # 批量删除
            for key in cache_keys:
                await redis_client.delete(key)
            logger.info(f"🗑️  已清除 {len(cache_keys)} 个系列缓存")
        except Exception as e:
            logger.error(f"❌ 清除系列缓存失败: {e}")


series_service = SeriesService()
