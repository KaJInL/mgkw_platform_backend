"""
通用 Schema 模块

自动导出所有 schema 模块中的公开类，方便其他模块导入使用
"""

# 自动导入所有模块中的公开类
from .response_schema import *
from .login_schema import *
from .product_schema import *
from .request_schema import *
