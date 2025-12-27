# logger_util.py
import logging
import sys
from logging import Logger
from colorama import Fore, Style, init as colorama_init
import os

colorama_init(autoreset=True)

class ColorFormatter(logging.Formatter):
    """
    彩色日志格式化器，双行显示：
    第一行：完整文件路径
    第二行：时间 - [级别缩写] - 模块名:行号 : 日志内容
    """
    COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA,
    }

    LEVEL_ABBR = {
        logging.DEBUG: "D",
        logging.INFO: "I",
        logging.WARNING: "W",
        logging.ERROR: "E",
        logging.CRITICAL: "C",
    }

    SEPARATOR = "-" * 80

    def __init__(self, fmt=None, datefmt=None):
        # 第二行的格式
        fmt = fmt or "%(asctime)s - [%(level_abbr)s] - %(module)s:%(lineno)d : %(message)s"
        datefmt = datefmt or "%Y-%m-%d %H:%M:%S"
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        record.level_abbr = self.LEVEL_ABBR.get(record.levelno, "I")

        # 模块名
        record.module = os.path.splitext(os.path.basename(record.pathname))[0]

        # 第一行完整路径
        full_path = f"{Fore.CYAN}{record.pathname}{Style.RESET_ALL}"

        # 第二行正常格式
        second_line = super().format(record)
        second_line = f"{color}{second_line}{Style.RESET_ALL}"

        # 仅 INFO 及以上显示分割线
        if record.levelno >= logging.INFO:
            return f"{self.SEPARATOR}\n{full_path}\n{second_line}\n{self.SEPARATOR}"
        else:
            return f"{full_path}\n{second_line}"


def str_to_log_level(level_str: str) -> int:
    return {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }.get(level_str.upper(), logging.INFO)


class Log:
    logger: Logger = None

    @classmethod
    def init_logger(cls, level_str: str = "INFO") -> Logger:
        if cls.logger:
            return cls.logger

        level = str_to_log_level(level_str)
        cls.logger = logging.getLogger("custom_logger")
        cls.logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColorFormatter())
        cls.logger.addHandler(handler)

        cls.logger.propagate = False
        return cls.logger


# 单例
logger = Log.init_logger()
