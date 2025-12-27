from typing import List

from application.apis.category.schema.request import (
    QueryCategoryListReq, GetCategoryTreeReq, QuerySeriesListReq, GetSeriesTreeReq
)
from application.apis.category.schema.response import (
    CategoryInfoRes, CategoryTreeNodeRes, SeriesInfoRes, SeriesTreeNodeRes
)
from application.common.base.base_service import CoreService
from application.service.category_service import category_service
from application.service.series_service import series_service


class CategoryService(CoreService):
    """
    分类和系列公开接口 service
    """

    async def get_category_list(self, req: QueryCategoryListReq) -> List[CategoryInfoRes]:
        """
        获取分类列表（公开接口）
        :param req: 查询请求
        :return: 分类列表
        """
        # 构建查询条件
        query = category_service.model_class.all()
        
        # 关键词搜索：分类名称
        if req.keyword:
            keyword = req.keyword.strip()
            query = query.filter(name__icontains=keyword)
        
        # 父级分类筛选
        if req.parent_id is not None:
            query = query.filter(parent_id=req.parent_id)
        
        # 排序并获取所有数据
        query = query.order_by('id')
        categories = await query
        
        return [CategoryInfoRes(**category.to_dict()) for category in categories]

    async def get_category_tree(self, req: GetCategoryTreeReq) -> List[CategoryTreeNodeRes]:
        """
        获取分类树（公开接口）
        :param req: 获取分类树请求
        :return: 分类树列表
        """
        tree = await category_service.build_tree(
            parent_id=req.parent_id,
            max_depth=req.max_depth
        )
        
        return [CategoryTreeNodeRes(**node) for node in tree]

    async def get_series_list(self, req: QuerySeriesListReq) -> List[SeriesInfoRes]:
        """
        获取系列列表（公开接口）
        :param req: 查询请求
        :return: 系列列表
        """
        # 构建查询条件
        query = series_service.model_class.all()
        
        # 关键词搜索：系列名称
        if req.keyword:
            keyword = req.keyword.strip()
            query = query.filter(name__icontains=keyword)
        
        # 父级系列筛选
        if req.parent_id is not None:
            query = query.filter(parent_id=req.parent_id)
        
        # 排序并获取所有数据
        query = query.order_by('id')
        series_list = await query
        
        return [SeriesInfoRes(**series.to_dict()) for series in series_list]

    async def get_series_tree(self, req: GetSeriesTreeReq) -> List[SeriesTreeNodeRes]:
        """
        获取系列树（公开接口）
        :param req: 获取系列树请求
        :return: 系列树列表
        """
        tree = await series_service.build_tree(
            parent_id=req.parent_id,
            max_depth=req.max_depth
        )
        
        return [SeriesTreeNodeRes(**node) for node in tree]


category_public_service = CategoryService()

