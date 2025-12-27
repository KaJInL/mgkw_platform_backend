from typing import List, Dict, Any
from tortoise.expressions import Q

from application.apis.category.schema.request import (
    CreateCategoryReq, UpdateCategoryReq, DeleteCategoryReq, QueryCategoryListReq,
    GetCategoryDetailReq, GetCategoryTreeReq, GetCategoryChildrenReq, GetCategoryPathReq
)
from application.apis.category.schema.response import CategoryInfoRes, CategoryTreeNodeRes
from application.common.base.base_service import CoreService
from application.common.exception.exception import HttpBusinessException
from application.common.models import Category
from application.service.category_service import category_service


class CategoryAdminService(CoreService):
    """
    分类管理后台 service
    """

    async def query_category_list(self, req: QueryCategoryListReq):
        """
        查询分类列表
        :param req: 查询请求
        :return: PaginationResult[Category] - 会被自动转换为字典格式
        """
        # 构建查询条件
        query = Category.all()
        
        # 关键词搜索：分类名称
        if req.keyword:
            keyword = req.keyword.strip()
            query = query.filter(Q(name__icontains=keyword))
        
        # 父级分类筛选
        if req.parent_id is not None:
            query = query.filter(parent_id=req.parent_id)
        
        # 使用 category_service 的分页方法
        return await category_service.paginate(
            query=query,
            page_no=req.page,
            page_size=req.page_size,
            order_by=['id']
        )

    async def create_category(self, req: CreateCategoryReq) -> CategoryInfoRes:
        """
        新增分类
        :param req: 创建分类请求
        :return: 分类信息
        """
        # 检查父级分类是否存在
        if req.parent_id:
            parent = await category_service.get_by_id(req.parent_id)
            if not parent:
                raise HttpBusinessException("父级分类不存在")
        
        # 检查同级分类名称是否重复
        existing = await Category.filter(
            name=req.name,
            parent_id=req.parent_id
        ).first()
        if existing:
            raise HttpBusinessException("同级分类名称已存在")
        
        # 使用 category_service 创建分类
        category = await category_service.create_category(
            name=req.name,
            parent_id=req.parent_id
        )

        return CategoryInfoRes(
            id=category.id,
            name=category.name,
            parent_id=category.parent_id,
            top_parent_id=category.top_parent_id,
            created_at=category.created_at,
            updated_at=category.updated_at
        )

    async def update_category(self, req: UpdateCategoryReq) -> CategoryInfoRes:
        """
        修改分类信息
        :param req: 更新分类请求
        :return: 分类信息
        """
        # 检查分类是否存在
        category = await category_service.get_by_id(req.category_id)
        if not category:
            raise HttpBusinessException("分类不存在")

        # 检查父级分类是否存在
        if req.parent_id is not None:
            # 不能将自己设为父级
            if req.parent_id == req.category_id:
                raise HttpBusinessException("不能将自己设为父级分类")
            
            # 检查父级分类是否存在
            if req.parent_id:
                parent = await category_service.get_by_id(req.parent_id)
                if not parent:
                    raise HttpBusinessException("父级分类不存在")
                
                # 检查是否会形成循环引用（父级分类不能是当前分类的子孙）
                descendants = await category_service.get_children(
                    parent_id=req.category_id,
                    recursive=True
                )
                descendant_ids = [d['id'] for d in descendants]
                if req.parent_id in descendant_ids:
                    raise HttpBusinessException("不能将子孙分类设为父级分类")

        # 检查同级分类名称是否重复
        if req.name:
            parent_id = req.parent_id if req.parent_id is not None else category.parent_id
            existing = await Category.filter(
                name=req.name,
                parent_id=parent_id
            ).exclude(id=req.category_id).first()
            if existing:
                raise HttpBusinessException("同级分类名称已存在")

        # 更新分类信息
        update_data = {}
        if req.name is not None:
            update_data['name'] = req.name
        if req.parent_id is not None:
            update_data['parent_id'] = req.parent_id

        if update_data:
            await category_service.update_category(req.category_id, update_data)
            # 重新查询分类
            category = await category_service.get_by_id(req.category_id)

        return CategoryInfoRes(
            id=category.id,
            name=category.name,
            parent_id=category.parent_id,
            top_parent_id=category.top_parent_id,
            created_at=category.created_at,
            updated_at=category.updated_at
        )

    async def delete_category(self, req: DeleteCategoryReq) -> bool:
        """
        删除分类
        :param req: 删除分类请求
        :return: 是否成功
        """
        # 检查分类是否存在
        category = await category_service.get_by_id(req.category_id)
        if not category:
            raise HttpBusinessException("分类不存在")

        # 如果不是递归删除，检查是否有子分类
        if not req.recursive:
            children = await category_service.get_children(
                parent_id=req.category_id,
                recursive=False
            )
            if children:
                raise HttpBusinessException("该分类下存在子分类，请先删除子分类或使用递归删除")

        # 删除分类
        await category_service.delete_category(
            category_id=req.category_id,
            recursive=req.recursive
        )

        return True

    async def get_category_detail(self, req: GetCategoryDetailReq) -> CategoryInfoRes:
        """
        获取分类详情
        :param req: 获取分类详情请求
        :return: 分类信息
        """
        # 从缓存获取分类
        category = await category_service.get_by_id(req.category_id)
        if not category:
            raise HttpBusinessException("分类不存在")

        return CategoryInfoRes(**category)

    async def get_category_tree(self, req: GetCategoryTreeReq) -> List[CategoryTreeNodeRes]:
        """
        获取分类树
        :param req: 获取分类树请求
        :return: 分类树列表
        """
        tree = await category_service.build_tree(
            parent_id=req.parent_id,
            max_depth=req.max_depth
        )
        
        return [CategoryTreeNodeRes(**node) for node in tree]

    async def get_category_children(self, req: GetCategoryChildrenReq) -> List[CategoryInfoRes]:
        """
        获取子分类
        :param req: 获取子分类请求
        :return: 子分类列表
        """
        # 检查父级分类是否存在
        parent = await category_service.get_by_id(req.parent_id)
        if not parent:
            raise HttpBusinessException("父级分类不存在")
        
        children = await category_service.get_children(
            parent_id=req.parent_id,
            recursive=req.recursive
        )
        
        return [CategoryInfoRes(**child) for child in children]

    async def get_category_path(self, req: GetCategoryPathReq) -> List[CategoryInfoRes]:
        """
        获取分类路径（从根到当前节点）
        :param req: 获取分类路径请求
        :return: 分类路径列表
        """
        # 检查分类是否存在
        category = await category_service.get_by_id(req.category_id)
        if not category:
            raise HttpBusinessException("分类不存在")
        
        path = await category_service.get_path_to_root(req.category_id)
        
        return [CategoryInfoRes(**node) for node in path]


category_admin_service = CategoryAdminService()

