from enum import Enum


class RoleEnum(str, Enum):
    """
    系统角色枚举
    """
    SUPER_ADMIN = "super_admin"  # 超级管理员
    ADMIN = "admin"  # 管理员
    USER = "user"  # 普通用户
    DESIGNER = "designer"  # 设计师
    COMPANY_DESIGNER = "company_designer"  # 设计师


class RoleNameEnum(str, Enum):
    """
    系统角色名称枚举（中文描述）
    """
    SUPER_ADMIN = "超级管理员"
    ADMIN = "管理员"
    USER = "普通用户"
    DESIGNER = "设计师"
    COMPANY_DESIGNER = "公司设计师"
