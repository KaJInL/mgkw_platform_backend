from application.common.exception.http_error_code_enum import HttpErrorCodeEnum


class HttpBusinessException(Exception):
    """基础业务异常类"""
    message: str
    code: str

    def __init__(self, error_code=HttpErrorCodeEnum.ERROR, message=""):
        self.message = message if message else error_code.message
        self.code = error_code.code
        super().__init__(error_code.message)


class BaseHttpException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
