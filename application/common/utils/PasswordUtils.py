import hashlib
import secrets
from typing import Tuple

"""
密码加密工具类
使用 PBKDF2-SHA256 算法进行密码加密
"""


def generate_salt(length: int = 32) -> str:
    """
    生成随机盐值
    :param length: 盐值长度（字节数），默认32字节
    :return: 十六进制字符串形式的盐值
    """
    return secrets.token_hex(length)


def hash_password(password: str, salt: str = None, iterations: int = 100000) -> Tuple[str, str]:
    """
    对密码进行加密
    :param password: 明文密码
    :param salt: 盐值，如果为None则自动生成
    :param iterations: PBKDF2迭代次数，默认100000次
    :return: (password_hash, salt) 元组
    """
    if not salt:
        salt = generate_salt()

    # 使用 PBKDF2-HMAC-SHA256 算法
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations
    )

    # 将hash结果转换为十六进制字符串
    return password_hash.hex(), salt


def verify_password(password: str, password_hash: str, salt: str, iterations: int = 100000) -> bool:
    """
    验证密码是否正确
    :param password: 待验证的明文密码
    :param password_hash: 存储的密码哈希值
    :param salt: 存储的盐值
    :param iterations: PBKDF2迭代次数，必须与加密时一致
    :return: 密码是否匹配
    """
    # 使用相同的盐值和迭代次数重新计算哈希
    new_hash, _ = hash_password(password, salt, iterations)
    return new_hash == password_hash
