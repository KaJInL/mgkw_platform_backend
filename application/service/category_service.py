from typing import Optional, List, Dict, Any
from application.common.base import BaseService
from application.common.models import Category
from application.core.redis_client import redis_client, TimeUnit
from application.core.logger_util import logger


class CategoryService(BaseService[Category]):
    """
    分类服务
    支持树形结构查询和 Redis 缓存优化
    """

    # Redis 缓存键前缀
    CACHE_PREFIX = "category"
    CACHE_TREE_KEY = f"{CACHE_PREFIX}:tree"
    CACHE_ALL_KEY = f"{CACHE_PREFIX}:all"
    CACHE_ITEM_KEY = f"{CACHE_PREFIX}:item"

    # 缓存过期时间（默认1小时）
    CACHE_EXPIRE = 1
    CACHE_UNIT = TimeUnit.HOURS

    async def get_all_with_cache(self) -> List[Dict[str, Any]]:
        """
        获取所有分类（带缓存）
        
        :return: 分类列表
        """
        # 尝试从缓存获取
        cached_data = await redis_client.get(self.CACHE_ALL_KEY)
        if cached_data:
            logger.debug(f"✅ 从缓存获取所有分类数据")
            return cached_data

        # 从数据库查询
        categories = await self.list(order_by=["id"])
        
        # 转换为字典并保存到缓存
        if categories:
            categories_dict = [c.to_dict() for c in categories]
            await redis_client.set(
                self.CACHE_ALL_KEY,
                categories_dict,
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )
            logger.debug(f"💾 已缓存所有分类数据")
            return categories_dict
        
        return []

    async def get_by_id_with_cache(self, category_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取分类（带缓存）
        
        :param category_id: 分类ID
        :return: 分类信息
        """
        cache_key = f"{self.CACHE_ITEM_KEY}:{category_id}"

        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取分类 {category_id}")
            return cached_data

        # 从数据库查询
        category = await self.get_by_id(category_id)
        if not category:
            return None

        category_dict = category.to_dict() if hasattr(category, 'to_dict') else category

        # 保存到缓存
        await redis_client.set(
            cache_key,
            category_dict,
            time=self.CACHE_EXPIRE,
            unit=self.CACHE_UNIT
        )
        logger.debug(f"💾 已缓存分类 {category_id}")

        return category_dict

    async def build_tree(
            self,
            parent_id: Optional[int] = None,
            max_depth: Optional[int] = None,
            current_depth: int = 0
    ) -> List[Dict[str, Any]]:
        """
        构建分类树形结构
        
        :param parent_id: 父级ID，None表示顶级分类
        :param max_depth: 最大深度限制，None表示不限制
        :param current_depth: 当前深度（内部使用）
        :return: 树形结构的分类列表
        """
        # 如果是顶级查询，尝试获取完整树缓存
        if parent_id is None:
            cached_tree = await redis_client.get(self.CACHE_TREE_KEY)
            if cached_tree:
                logger.debug("✅ 从缓存获取完整分类树")
                return cached_tree

        # 检查深度限制
        if max_depth is not None and current_depth >= max_depth:
            return []

        # 获取所有分类数据
        all_categories = await self.get_all_with_cache()

        # 构建树形结构
        tree = self._build_tree_recursive(
            all_categories,
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
            logger.debug("💾 已缓存完整分类树")

        return tree

    def _build_tree_recursive(
            self,
            all_categories: List[Dict[str, Any]],
            parent_id: Optional[int],
            max_depth: Optional[int] = None,
            current_depth: int = 0
    ) -> List[Dict[str, Any]]:
        """
        递归构建树形结构（内部方法）
        
        :param all_categories: 所有分类数据
        :param parent_id: 父级ID
        :param max_depth: 最大深度限制
        :param current_depth: 当前深度
        :return: 树形结构
        """
        tree = []

        # 检查深度限制
        if max_depth is not None and current_depth >= max_depth:
            return tree

        for category in all_categories:
            # 匹配父级ID
            if category.get('parent_id') == parent_id:
                category_node = category.copy()

                # 递归获取子分类
                children = self._build_tree_recursive(
                    all_categories,
                    category.get('id'),
                    max_depth,
                    current_depth + 1
                )

                if children:
                    category_node['children'] = children
                else:
                    category_node['children'] = []

                tree.append(category_node)

        return tree

    async def get_children(
            self,
            parent_id: int,
            recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取指定分类的子分类
        
        :param parent_id: 父级分类ID
        :param recursive: 是否递归获取所有后代
        :return: 子分类列表
        """
        cache_key = f"{self.CACHE_PREFIX}:children:{parent_id}:recursive_{recursive}"

        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取分类 {parent_id} 的子分类")
            return cached_data

        # 获取所有分类数据
        all_categories = await self.get_all_with_cache()

        # 根据递归参数获取子分类
        result = (
            self._get_descendants(all_categories, parent_id) if recursive
            else [cat for cat in all_categories if cat.get('parent_id') == parent_id]
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
            all_categories: List[Dict[str, Any]],
            parent_id: int
    ) -> List[Dict[str, Any]]:
        """
        递归获取所有后代分类（内部方法）
        
        :param all_categories: 所有分类数据
        :param parent_id: 父级ID
        :return: 后代分类列表
        """
        descendants = []

        for category in all_categories:
            if category.get('parent_id') == parent_id:
                descendants.append(category)
                # 递归获取子孙分类
                descendants.extend(
                    self._get_descendants(all_categories, category.get('id'))
                )

        return descendants

    async def get_path_to_root(
            self,
            category_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取从指定分类到根节点的路径
        
        :param category_id: 分类ID
        :return: 路径列表（从根到当前节点）
        """
        cache_key = f"{self.CACHE_PREFIX}:path:{category_id}"

        # 尝试从缓存获取
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.debug(f"✅ 从缓存获取分类 {category_id} 的路径")
            return cached_data

        # 获取所有分类数据
        all_categories = await self.get_all_with_cache()

        # 构建ID到分类的映射
        category_map = {cat['id']: cat for cat in all_categories}

        # 向上追溯到根节点
        path = []
        current_id = category_id
        while current_id:
            category = category_map.get(current_id)
            if not category:
                break
            path.insert(0, category)  # 插入到列表开头
            current_id = category.get('parent_id')

        # 保存到缓存
        if path:
            await redis_client.set(
                cache_key,
                path,
                time=self.CACHE_EXPIRE,
                unit=self.CACHE_UNIT
            )

        return path

    async def create_category(
            self,
            name: str,
            parent_id: Optional[int] = None
    ) -> Category:
        """
        创建分类（自动计算 top_parent_id）
        
        :param name: 分类名称
        :param parent_id: 父级分类ID
        :return: 创建的分类对象
        """
        # 计算顶级父分类ID
        top_parent_id = None
        if parent_id:
            parent = await self.get_by_id(parent_id)
            if parent:
                top_parent_id = parent.top_parent_id or parent.id

        # 创建分类
        category = await Category.create(
            name=name,
            parent_id=parent_id,
            top_parent_id=top_parent_id
        )

        # 清除缓存
        await self.clear_cache()

        logger.info(f"✅ 创建分类: {name} (ID: {category.id})")
        return category

    async def update_category(
            self,
            category_id: int,
            data: Dict[str, Any]
    ) -> int:
        """
        更新分类
        
        :param category_id: 分类ID
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

        # 更新分类
        result = await self.update_by_id(category_id, data)

        # 清除缓存
        await self.clear_cache()

        logger.info(f"✅ 更新分类 {category_id}")
        return result

    async def delete_category(
            self,
            category_id: int,
            recursive: bool = False
    ) -> int:
        """
        删除分类
        
        :param category_id: 分类ID
        :param recursive: 是否递归删除子分类
        :return: 删除的记录数
        """
        # 非递归删除：直接删除当前分类
        if not recursive:
            result = await self.delete_by_id(category_id)
            await self.clear_cache()
            logger.info(f"✅ 删除分类 {category_id}")
            return result

        # 递归删除：获取所有子孙分类并一起删除
        all_categories = await self.list(order_by=["id"])  # 跳过缓存，确保数据最新
        descendants = self._get_descendants(all_categories, category_id)
        descendant_ids = [cat['id'] for cat in descendants]

        # 删除所有子孙分类和自己
        all_ids = [category_id] + descendant_ids
        result = await self.delete_by_ids(all_ids)

        # 清除缓存
        await self.clear_cache()

        logger.info(f"✅ 删除分类 {category_id} 及其 {len(descendant_ids)} 个子孙分类")
        return result

    async def clear_cache(self):
        """清除所有分类相关缓存"""
        try:
            # 获取所有分类相关的缓存键
            cache_keys = await redis_client.keys(f"{self.CACHE_PREFIX}:*")
            if not cache_keys:
                return

            # 批量删除
            for key in cache_keys:
                await redis_client.delete(key)
            logger.info(f"🗑️  已清除 {len(cache_keys)} 个分类缓存")
        except Exception as e:
            logger.error(f"❌ 清除分类缓存失败: {e}")


category_service = CategoryService()
