from enum import Enum


class BoolEnum(str, Enum):
    YES = "1"
    NO = "0"

    @classmethod
    def from_value(cls, value) -> "BoolEnum":
        """将任意输入值转换为 BoolEnum"""
        if isinstance(value, cls):
            return value
        if str(value).lower() in ["1", "true", "yes", "y"]:
            return cls.YES
        elif str(value).lower() in ["0", "false", "no", "n"]:
            return cls.NO
        raise ValueError(f"无法识别的布尔值: {value}")

    @classmethod
    def is_yes(cls, value) -> bool:
        """判断是否为 YES"""
        return cls.from_value(value) == cls.YES

    @classmethod
    def is_no(cls, value) -> bool:
        """判断是否为 NO"""
        return cls.from_value(value) == cls.NO
