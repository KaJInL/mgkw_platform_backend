from abc import ABC
from typing import TypeVar, Dict, Any, Optional, List, Generic, Type, Union

from tortoise.queryset import QuerySet
from .base_model import DefaultModel
from ..schema import PaginationResult

T = TypeVar("T", bound=DefaultModel)


class CoreService:
    """
    通用服务基类，封装了所有与数据库模型交互的通用逻辑（分页、查询、更新、删除等）
    """

    # ---------------- 分页 ----------------
    async def paginate_dic(
        self,
        query: QuerySet,
        page_no: int = 1,
        page_size: int = 10,
        select_fields: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        返回分页字典数据（适用于不需要泛型模型的场景）
        """
        if page_no < 1:
            page_no = 1
        offset = (page_no - 1) * page_size
        total = await query.count()
        has_next = offset + page_size < total

        if order_by:
            query = query.order_by(*order_by)

        query = query.offset(offset).limit(page_size)
        if select_fields:
            items = await query.values(*select_fields)
            list_dicts = items
        else:
            items = await query.all()
            list_dicts = [item.to_dict() for item in items]

        return {"list": list_dicts, "total": total, "hasNext": has_next}

    async def paginate_with_model_class(
        self,
        query: QuerySet,
        model_class: Type[T],
        page_no: int = 1,
        page_size: int = 10,
        order_by: Optional[List[str]] = None
    ) -> PaginationResult[T]:
        """
        分页查询（返回 PaginationResult 泛型对象）
        """
        if page_no < 1:
            page_no = 1
        offset = (page_no - 1) * page_size
        total = await query.count()
        has_next = offset + page_size < total

        if order_by:
            query = query.order_by(*order_by)

        query = query.offset(offset).limit(page_size)
        items = await query.all()

        return PaginationResult(items, total, has_next)

    # ---------------- 查询 ----------------
    async def get_by_id_with_model_class(
        self,
        model_class: Type[DefaultModel],
        id: int,
        select_fields: Optional[List[str]] = None
    ) -> Optional[Union[DefaultModel, Dict[str, Any]]]:
        """
        根据 ID 查询单个对象
        """
        query = model_class.filter(id=id)
        if select_fields:
            return await query.first().values(*select_fields)
        return await query.first()

    async def get_one_with_model_class(
        self,
        model_class: Type[DefaultModel],
        **filters
    ) -> Optional[DefaultModel]:
        """
        根据过滤条件查询单个对象
        """
        return await model_class.filter(**filters).first()

    async def get_by_ids_with_model_class(
        self,
        model_class: Type[DefaultModel],
        ids: List[int],
        order_by: Optional[List[str]] = None
    ) -> List[Union[DefaultModel, Dict[str, Any]]]:
        """
        根据多个 ID 批量获取对象列表
        """
        query = model_class.filter(id__in=ids)
        if order_by:
            query = query.order_by(*order_by)
        items = await query.all()
        return [item.to_dict() for item in items]

    async def list_with_model_class(
        self,
        model_class: Type[DefaultModel],
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[str]] = None,
        select_fields: Optional[List[str]] = None
    ) -> List[Union[DefaultModel, Dict[str, Any]]]:
        """
        查询对象列表（可带过滤条件、排序、字段筛选）
        """
        query = model_class.all()
        if filters:
            query = query.filter(**filters)
        if order_by:
            query = query.order_by(*order_by)
        if select_fields:
            return await query.values(*select_fields)
        return await query.all()

    # ---------------- 保存 / 更新 ----------------
    async def save_or_update_with_model_class(
        self,
        model_class: Type[DefaultModel],
        defaults: Dict[str, Any],
        **kwargs
    ) -> tuple[DefaultModel, bool]:
        """
        根据条件存在则更新，否则创建（等价于 upsert）
        """
        if kwargs:
            instance, created = await model_class.update_or_create(defaults=defaults, **kwargs)
        else:
            instance = await model_class.create(**defaults)
            created = True
        return instance, created

    async def update_by_id_with_model_class(
        self,
        model_class: Type[DefaultModel],
        id: int,
        data: Dict[str, Any]
    ) -> int:
        """
        根据 ID 更新对象
        """
        data.pop('id',None)
        return await model_class.filter(id=id).update(**data)

    async def update_with_model_class(
        self,
        model_class: Type[DefaultModel],
        filters: Dict[str, Any],
        data: Dict[str, Any]
    ) -> int:
        """
        根据条件更新对象
        """
        return await model_class.filter(**filters).update(**data)

    async def bulk_update_with_model_class(
        self,
        model_class: Type[DefaultModel],
        objs: List[T],
        fields: List[str]
    ) -> int:
        """
        批量更新多个对象的指定字段
        """
        update_count = 0
        for obj in objs:
            if not isinstance(obj, model_class):
                raise ValueError(f"Object must be an instance of {model_class.__name__}")
            update_data = {field: getattr(obj, field) for field in fields if hasattr(obj, field)}
            updated = await model_class.filter(id=obj.id).update(**update_data)
            update_count += updated
        return update_count

    async def bulk_create_with_model_class(
        self,
        model_class: Type[DefaultModel],
        objs: List[DefaultModel]
    ):
        """
        批量创建多个对象
        """
        await model_class.bulk_create(objs)

    # ---------------- 删除 ----------------
    async def delete_by_id_with_model_class(
        self,
        model_class: Type[DefaultModel],
        id: int
    ) -> int:
        """
        根据 ID 删除对象
        """
        return await model_class.filter(id=id).delete()

    async def delete_with_model_class(
        self,
        model_class: Type[DefaultModel],
        **filters
    ) -> int:
        """
        根据条件删除对象
        """
        return await model_class.filter(**filters).delete()

    async def delete_by_ids_with_model_class(
        self,
        model_class: Type[DefaultModel],
        ids: List[int]
    ) -> int:
        """
        根据多个 ID 批量删除对象
        """
        return await model_class.filter(id__in=ids).delete()


class BaseService(ABC, CoreService, Generic[T]):
    """
    通用业务服务基类，继承自 CoreService。
    每个业务 Service 只需继承 BaseService[ModelClass] 即可自动获得 CRUD 能力。
    """
    model_class: type[T]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # 获取泛型类型（例如 BaseService[User] -> User）
        model = None
        for base in getattr(cls, "__orig_bases__", []):
            args = getattr(base, "__args__", None)
            if args:
                model = args[0]
                break

        if model is None:
            raise TypeError("无法获取泛型类型，子类必须继承 BaseService[Model]")
        if not issubclass(model, DefaultModel):
            raise TypeError("泛型类型必须是 BaseModel 子类")

        cls.model_class = model

    # ---------------- 分页 ----------------
    async def paginate(
        self,
        query: QuerySet,
        page_no: int = 1,
        page_size: int = 10,
        order_by: Optional[List[str]] = None
    ) -> "PaginationResult[T]":
        """
        分页查询（返回 PaginationResult 泛型对象）
        """
        return await super().paginate_with_model_class(query, self.model_class, page_no, page_size, order_by)

    # ---------------- 查询 ----------------
    async def get_by_id(
        self,
        id: int,
        select_fields: Optional[List[str]] = None
    ) -> Optional[Union[T, Dict[str, Any]]]:
        """
        根据 ID 查询单个对象
        """
        return await super().get_by_id_with_model_class(self.model_class, id, select_fields)

    async def get_one(self, **filters) -> Optional[T]:
        """
        根据条件查询单个对象
        """
        return await super().get_one_with_model_class(self.model_class, **filters)

    async def get_by_ids(
        self,
        ids: List[int],
        select_fields: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None
    ) -> List[Union[T, Dict[str, Any]]]:
        """
        根据多个 ID 批量获取对象列表
        """
        return await super().get_by_ids_with_model_class(self.model_class, ids, order_by)

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[str]] = None,
        select_fields: Optional[List[str]] = None
    ) -> List[Union[T, Dict[str, Any]]]:
        """
        查询对象列表（支持过滤、排序、字段选择）
        """
        return await super().list_with_model_class(self.model_class, filters, order_by, select_fields)

    # ---------------- 保存 / 更新 ----------------
    async def save_or_update(self, defaults: Dict[str, Any], **kwargs) -> tuple[T, bool]:
        """
        根据条件存在则更新，否则创建（等价于 upsert）
        """
        return await super().save_or_update_with_model_class(self.model_class, defaults, **kwargs)

    async def update_by_id(self, id: int, data: Dict[str, Any]) -> int:
        """
        根据 ID 更新对象
        """
        return await super().update_by_id_with_model_class(self.model_class, id, data)

    async def update(self, filters: Dict[str, Any], data: Dict[str, Any]) -> int:
        """
        根据条件更新对象
        """
        return await super().update_with_model_class(self.model_class, filters, data)

    async def bulk_create(self, objs: List[DefaultModel]):
        """
        批量创建多个对象
        """
        await super().bulk_create_with_model_class(self.model_class, objs)

    async def bulk_update(self, objs: List[T], fields: List[str]) -> int:
        """
        批量更新多个对象的指定字段
        """
        return await super().bulk_update_with_model_class(self.model_class, objs, fields)

    # ---------------- 删除 ----------------
    async def delete_by_id(self, id: int) -> int:
        """
        根据 ID 删除对象
        """
        return await super().delete_by_id_with_model_class(self.model_class, id)

    async def delete(self, **filters) -> int:
        """
        根据条件删除对象
        """
        return await super().delete_with_model_class(self.model_class, **filters)

    async def delete_by_ids(self, ids: List[int]) -> int:
        """
        根据多个 ID 批量删除对象
        """
        return await super().delete_by_ids_with_model_class(self.model_class, ids)

    # ---------------- 缓存辅助方法 ----------------
    def dict_to_model(self, data: Dict[str, Any]) -> T:
        """
        将字典转换为模型对象（不保存到数据库）
        主要用于从缓存恢复对象
        
        :param data: 字典数据
        :return: 模型对象
        """
        instance = self.model_class(**data)
        # 标记为已从数据库加载，避免重复保存
        instance._saved_in_db = True
        return instance
