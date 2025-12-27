from enum import Enum
from decimal import Decimal

from tortoise import models, fields
from pydantic import BaseModel


class DefaultModel(models.Model):
    id = fields.IntField(pk=True, description="id")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True  # 作为抽象基类，不会映射成数据库表

    def to_dict(self, exclude_fields=None):
        """
        手动序列化模型为 dict
        :param exclude_fields: 可选，排除的字段列表或集合
        :return: dict
        """
        exclude_fields = exclude_fields or set()
        data = {}

        for field_name, field_obj in self._meta.fields_map.items():
            if field_name in exclude_fields:
                continue

            value = getattr(self, field_name)

            # 枚举类型，转成枚举的值（字符串）
            if isinstance(value, Enum):
                data[field_name] = value.value
            # datetime 类型，转字符串
            elif hasattr(value, "isoformat"):
                data[field_name] = value.isoformat()
            # Decimal 类型，转成固定两位小数字符串
            elif isinstance(value, Decimal):
                # 去掉科学计数法
                data[field_name] = format(value, 'f')  # 这里固定两位小数
            else:
                data[field_name] = value

        return data

    def __str__(self):
        """
        统一调试输出格式，方便打印查看
        """
        return f"<{self.__class__.__name__} {self.to_dict()}>"
