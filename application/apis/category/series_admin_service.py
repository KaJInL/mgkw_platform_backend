from typing import List
from tortoise.expressions import Q

from application.apis.category.schema.request import (
    CreateSeriesReq, UpdateSeriesReq, DeleteSeriesReq, QuerySeriesListReq,
    GetSeriesDetailReq, GetSeriesTreeReq, GetSeriesChildrenReq, GetSeriesPathReq
)
from application.apis.category.schema.response import SeriesInfoRes, SeriesTreeNodeRes
from application.common.base.base_service import CoreService
from application.common.exception.exception import HttpBusinessException
from application.common.models import Series
from application.service.series_service import series_service


class SeriesAdminService(CoreService):
    """
    系列管理后台 service
    """

    async def query_series_list(self, req: QuerySeriesListReq):
        """
        查询系列列表
        :param req: 查询请求
        :return: PaginationResult[Series] - 会被自动转换为字典格式
        """
        # 构建查询条件
        query = Series.all()
        
        # 关键词搜索：系列名称
        if req.keyword:
            keyword = req.keyword.strip()
            query = query.filter(Q(name__icontains=keyword))
        
        # 父级系列筛选
        if req.parent_id is not None:
            query = query.filter(parent_id=req.parent_id)
        
        # 使用 series_service 的分页方法
        return await series_service.paginate(
            query=query,
            page_no=req.page,
            page_size=req.page_size,
            order_by=['id']
        )

    async def create_series(self, req: CreateSeriesReq) -> SeriesInfoRes:
        """
        新增系列
        :param req: 创建系列请求
        :return: 系列信息
        """
        # 检查父级系列是否存在
        if req.parent_id:
            parent = await series_service.get_by_id(req.parent_id)
            if not parent:
                raise HttpBusinessException("父级系列不存在")
        
        # 检查同级系列名称是否重复
        existing = await Series.filter(
            name=req.name,
            parent_id=req.parent_id
        ).first()
        if existing:
            raise HttpBusinessException("同级系列名称已存在")
        
        # 使用 series_service 创建系列
        series = await series_service.create_series(
            name=req.name,
            parent_id=req.parent_id
        )

        return SeriesInfoRes(
            id=series.id,
            name=series.name,
            parent_id=series.parent_id,
            top_parent_id=series.top_parent_id,
            created_at=series.created_at,
            updated_at=series.updated_at
        )

    async def update_series(self, req: UpdateSeriesReq) -> SeriesInfoRes:
        """
        修改系列信息
        :param req: 更新系列请求
        :return: 系列信息
        """
        # 检查系列是否存在
        series = await series_service.get_by_id(req.series_id)
        if not series:
            raise HttpBusinessException("系列不存在")

        # 检查父级系列是否存在
        if req.parent_id is not None:
            # 不能将自己设为父级
            if req.parent_id == req.series_id:
                raise HttpBusinessException("不能将自己设为父级系列")
            
            # 检查父级系列是否存在
            if req.parent_id:
                parent = await series_service.get_by_id(req.parent_id)
                if not parent:
                    raise HttpBusinessException("父级系列不存在")
                
                # 检查是否会形成循环引用（父级系列不能是当前系列的子孙）
                descendants = await series_service.get_children(
                    parent_id=req.series_id,
                    recursive=True
                )
                descendant_ids = [d['id'] for d in descendants]
                if req.parent_id in descendant_ids:
                    raise HttpBusinessException("不能将子孙系列设为父级系列")

        # 检查同级系列名称是否重复
        if req.name:
            parent_id = req.parent_id if req.parent_id is not None else series.parent_id
            existing = await Series.filter(
                name=req.name,
                parent_id=parent_id
            ).exclude(id=req.series_id).first()
            if existing:
                raise HttpBusinessException("同级系列名称已存在")

        # 更新系列信息
        update_data = {}
        if req.name is not None:
            update_data['name'] = req.name
        if req.parent_id is not None:
            update_data['parent_id'] = req.parent_id

        if update_data:
            await series_service.update_series(req.series_id, update_data)
            # 重新查询系列
            series = await series_service.get_by_id(req.series_id)

        return SeriesInfoRes(
            id=series.id,
            name=series.name,
            parent_id=series.parent_id,
            top_parent_id=series.top_parent_id,
            created_at=series.created_at,
            updated_at=series.updated_at
        )

    async def delete_series(self, req: DeleteSeriesReq) -> bool:
        """
        删除系列
        :param req: 删除系列请求
        :return: 是否成功
        """
        # 检查系列是否存在
        series = await series_service.get_by_id(req.series_id)
        if not series:
            raise HttpBusinessException("系列不存在")

        # 如果不是递归删除，检查是否有子系列
        if not req.recursive:
            children = await series_service.get_children(
                parent_id=req.series_id,
                recursive=False
            )
            if children:
                raise HttpBusinessException("该系列下存在子系列，请先删除子系列或使用递归删除")

        # 删除系列
        await series_service.delete_series(
            series_id=req.series_id,
            recursive=req.recursive
        )

        return True

    async def get_series_detail(self, req: GetSeriesDetailReq) -> SeriesInfoRes:
        """
        获取系列详情
        :param req: 获取系列详情请求
        :return: 系列信息
        """
        # 从缓存获取系列
        series = await series_service.get_by_id(req.series_id)
        if not series:
            raise HttpBusinessException("系列不存在")

        return SeriesInfoRes(**series)

    async def get_series_tree(self, req: GetSeriesTreeReq) -> List[SeriesTreeNodeRes]:
        """
        获取系列树
        :param req: 获取系列树请求
        :return: 系列树列表
        """
        tree = await series_service.build_tree(
            parent_id=req.parent_id,
            max_depth=req.max_depth
        )
        
        return [SeriesTreeNodeRes(**node) for node in tree]

    async def get_series_children(self, req: GetSeriesChildrenReq) -> List[SeriesInfoRes]:
        """
        获取子系列
        :param req: 获取子系列请求
        :return: 子系列列表
        """
        # 检查父级系列是否存在
        parent = await series_service.get_by_id(req.parent_id)
        if not parent:
            raise HttpBusinessException("父级系列不存在")
        
        children = await series_service.get_children(
            parent_id=req.parent_id,
            recursive=req.recursive
        )
        
        return [SeriesInfoRes(**child) for child in children]

    async def get_series_path(self, req: GetSeriesPathReq) -> List[SeriesInfoRes]:
        """
        获取系列路径（从根到当前节点）
        :param req: 获取系列路径请求
        :return: 系列路径列表
        """
        # 检查系列是否存在
        series = await series_service.get_by_id(req.series_id)
        if not series:
            raise HttpBusinessException("系列不存在")
        
        path = await series_service.get_path_to_root(req.series_id)
        
        return [SeriesInfoRes(**node) for node in path]


series_admin_service = SeriesAdminService()

