import re
from typing import  Dict, Any


def snake_to_camel(snake_str: str) -> str:
    """
    蛇形命名转小驼峰
    example: category_id -> categoryId
    """
    components = snake_str.split('_')
    # 第一个单词小写，后面每个单词首字母大写
    return components[0] + ''.join(x.title() for x in components[1:])


def camel_to_snake(camel_str: str) -> str:
    """
    小驼峰转蛇形命名
    example: categoryId -> category_id
    """
    # 在小写字母和大写字母之间插入下划线，并转小写
    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()
    return snake

def dict_keys_snake_to_camel(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归转换 dict 的所有 key，从 snake_case 转成 camelCase
    """
    new_dict = {}
    for k, v in d.items():
        new_key = snake_to_camel(k)
        if isinstance(v, dict):
            new_dict[new_key] = dict_keys_snake_to_camel(v)
        elif isinstance(v, list):
            new_dict[new_key] = [dict_keys_snake_to_camel(i) if isinstance(i, dict) else i for i in v]
        else:
            new_dict[new_key] = v
    return new_dict

def dict_keys_camel_to_snake(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归转换 dict 的所有 key，从 camelCase 转成 snake_case
    """
    new_dict = {}
    for k, v in d.items():
        new_key = camel_to_snake(k)
        if isinstance(v, dict):
            new_dict[new_key] = dict_keys_camel_to_snake(v)
        elif isinstance(v, list):
            new_dict[new_key] = [dict_keys_camel_to_snake(i) if isinstance(i, dict) else i for i in v]
        else:
            new_dict[new_key] = v
    return new_dict