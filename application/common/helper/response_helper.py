from datetime import datetime
from decimal import Decimal
from typing import Any
from enum import Enum

import pydantic
from starlette.responses import JSONResponse

from application.common.exception.http_error_code_enum import HttpErrorCodeEnum
from application.common.schema import PaginationResult


class ResDateTimeFormat(Enum):
    NONE = None
    YMDHMS = "%Y-%m-%d %H:%M:%S"
    YMD = "%Y-%m-%d"
    TIMESTAMP = "timestamp"
    TIMESTAMP_MS = "timestamp_ms"


def snake_to_camel(snake_str: str) -> str:
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def convert_keys_to_camel(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {snake_to_camel(k): convert_keys_to_camel(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_keys_to_camel(item) for item in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


def format_special_types(data: Any, datetime_format: ResDateTimeFormat = ResDateTimeFormat.YMDHMS) -> Any:
    if isinstance(data, datetime):
        if datetime_format == ResDateTimeFormat.NONE:
            return data
        elif datetime_format == ResDateTimeFormat.TIMESTAMP:
            return int(data.timestamp())
        elif datetime_format == ResDateTimeFormat.TIMESTAMP_MS:
            return int(data.timestamp() * 1000)
        else:
            return data.strftime(datetime_format.value)
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, dict):
        return {k: format_special_types(v, datetime_format) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [format_special_types(item, datetime_format) for item in data]
    else:
        return data


def base_model_to_dict(data: Any, datetime_format: ResDateTimeFormat) -> Any:
    from application.common.base.base_model import DefaultModel
    if isinstance(data, DefaultModel) or isinstance(data, PaginationResult):
        return format_special_types(data.to_dict(), datetime_format)
    elif isinstance(data, pydantic.BaseModel):
        return format_special_types(data.model_dump(), datetime_format)
    elif isinstance(data, (list, tuple)) and all(isinstance(item, DefaultModel) for item in data):
        return {"list": [format_special_types(item.to_dict(), datetime_format) for item in data]}
    elif isinstance(data, (list, tuple)) and all(isinstance(item, pydantic.BaseModel) for item in data):
        return {"list": [format_special_types(item.model_dump(), datetime_format) for item in data]}
    elif isinstance(data, (list, tuple)):
        return {"list": [format_special_types(item, datetime_format) for item in data]}
    else:
        return format_special_types(data, datetime_format)


class ResponseHelper:
    @staticmethod
    def success(
            data: Any = None,
            message: str = "成功",
            code: str = "0",
            datetime_format: ResDateTimeFormat = ResDateTimeFormat.YMDHMS
    ) -> JSONResponse:
        response = {
            "code": code,
            "isSuccess": True,
            "message": message,
        }
        if data is not None:
            response["data"] = base_model_to_dict(data, datetime_format)
            if isinstance(data, bool):
                response["isSuccess"] = data
                if data:
                    response["code"] = HttpErrorCodeEnum.SUCCESS.code
                    response["message"] = HttpErrorCodeEnum.SUCCESS.message
                else:
                    response["code"] = HttpErrorCodeEnum.ERROR.code
                    response["message"] = HttpErrorCodeEnum.ERROR.message

        return JSONResponse(
            content=convert_keys_to_camel(response),
            status_code=200,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )

    @staticmethod
    def result(state: bool) -> JSONResponse:
        return ResponseHelper.success() if state else ResponseHelper.error(message="失败")

    @staticmethod
    def error(
            code: str = HttpErrorCodeEnum.ERROR.code,
            message: str = HttpErrorCodeEnum.ERROR.message
    ) -> JSONResponse:
        response = {
            "code": code,
            "isSuccess": False,
            "message": message,
        }
        return JSONResponse(
            content=convert_keys_to_camel(response),
            status_code=200,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )

    @staticmethod
    def error_with_error_code(error_code: HttpErrorCodeEnum) -> JSONResponse:
        return ResponseHelper.error(code=error_code.code, message=error_code.message)
