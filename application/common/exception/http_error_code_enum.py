from enum import Enum


class HttpErrorCodeEnum(Enum):
    """
    http错误代码枚举
    """
    SUCCESS = ("0", "成功")
    ERROR = ("40000", "失败")
    PARAM_EMPTY = ("40001", "参数校验错误")
    SHOW_MESSAGE = ("40002", "展示消息")
    DATA_DUPLICATE = ("40003", "数据重复")
    METHOD_NOT_ALLOWED = ("40005", "请求method不支持")
    FILE_TYPE_NOT_SUPPORTED = ("40006", "文件类型不支持")
    UNAUTHORIZED = ("40100", "用户未登录")
    TOKEN_EXPIRED = ("40101", "登录已过期")
    TOKEN_INVALID = ("40102", "无效的登录凭证")
    LOGIN_FAILED = ("40103", "登录失败")
    FORBIDDEN = ("40300", "没有权限操作")


    def __init__(self, code, message):
        self.code = code
        self.message = message
