"""
验证工具类
提供常用的数据格式验证方法
"""
import re


class ValidationUtils:
    """验证工具类"""

    # 中国大陆手机号正则表达式
    # 1开头 + 第二位为3-9 + 后面9位数字
    PHONE_PATTERN = r'^1[3-9]\d{9}$'

    # 邮箱正则表达式（基础版）
    EMAIL_PATTERN = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

    # 身份证号正则表达式（18位）
    ID_CARD_PATTERN = r'^\d{17}[\dXx]$'

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """
        验证是否为有效的中国大陆手机号
        
        支持的号段：
        - 移动：134-139, 147, 148, 150-152, 157, 158, 159, 172, 178, 182-184, 187, 188, 195, 197, 198
        - 联通：130, 131, 132, 145, 146, 155, 156, 166, 171, 175, 176, 185, 186, 196
        - 电信：133, 149, 153, 173, 174, 177, 180, 181, 189, 191, 193, 199
        - 虚拟运营商：170
        
        :param phone: 手机号字符串
        :return: 是否有效
        """
        if not phone or not isinstance(phone, str):
            return False

        phone = phone.strip()

        # 检查长度
        if len(phone) != 11:
            return False

        # 检查是否为纯数字
        if not phone.isdigit():
            return False

        # 使用正则表达式验证格式
        return bool(re.match(ValidationUtils.PHONE_PATTERN, phone))

    @staticmethod
    def validate_phone(phone: str) -> str:
        """
        验证手机号并返回处理后的手机号
        如果验证失败则抛出 ValueError
        
        :param phone: 手机号字符串
        :return: 处理后的手机号
        :raises ValueError: 手机号格式不正确
        """
        if not phone:
            raise ValueError('手机号不能为空')

        phone = phone.strip()

        if not phone.isdigit():
            raise ValueError('手机号必须为纯数字')

        if len(phone) != 11:
            raise ValueError('手机号必须为11位')

        if not ValidationUtils.is_valid_phone(phone):
            raise ValueError('手机号格式不正确，请输入有效的中国大陆手机号')

        return phone

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        验证是否为有效的邮箱地址
        
        :param email: 邮箱字符串
        :return: 是否有效
        """
        if not email or not isinstance(email, str):
            return False

        email = email.strip()
        return bool(re.match(ValidationUtils.EMAIL_PATTERN, email))

    @staticmethod
    def validate_email(email: str) -> str:
        """
        验证邮箱并返回处理后的邮箱
        如果验证失败则抛出 ValueError
        
        :param email: 邮箱字符串
        :return: 处理后的邮箱
        :raises ValueError: 邮箱格式不正确
        """
        if not email:
            raise ValueError('邮箱不能为空')

        email = email.strip().lower()

        if not ValidationUtils.is_valid_email(email):
            raise ValueError('邮箱格式不正确')

        return email

    @staticmethod
    def is_valid_id_card(id_card: str) -> bool:
        """
        验证是否为有效的身份证号（18位）
        
        :param id_card: 身份证号字符串
        :return: 是否有效
        """
        if not id_card or not isinstance(id_card, str):
            return False

        id_card = id_card.strip().upper()

        # 检查长度
        if len(id_card) != 18:
            return False

        # 检查格式
        if not re.match(ValidationUtils.ID_CARD_PATTERN, id_card):
            return False

        # 校验校验码
        return ValidationUtils._validate_id_card_checksum(id_card)

    @staticmethod
    def _validate_id_card_checksum(id_card: str) -> bool:
        """
        验证身份证号校验码
        
        :param id_card: 18位身份证号
        :return: 校验码是否正确
        """
        # 加权因子
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        # 校验码对照表
        check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']

        try:
            # 计算校验和
            total = sum(int(id_card[i]) * weights[i] for i in range(17))
            # 计算校验码
            check_code = check_codes[total % 11]
            # 比较校验码
            return id_card[17] == check_code
        except (ValueError, IndexError):
            return False

    @staticmethod
    def validate_password_strength(password: str, 
                                   min_length: int = 6, 
                                   max_length: int = 32,
                                   require_letter: bool = True,
                                   require_digit: bool = True,
                                   require_special: bool = False) -> str:
        """
        验证密码强度
        
        :param password: 密码字符串
        :param min_length: 最小长度
        :param max_length: 最大长度
        :param require_letter: 是否要求包含字母
        :param require_digit: 是否要求包含数字
        :param require_special: 是否要求包含特殊字符
        :return: 密码字符串
        :raises ValueError: 密码不符合要求
        """
        if not password:
            raise ValueError('密码不能为空')

        if len(password) < min_length:
            raise ValueError(f'密码长度不能少于{min_length}位')

        if len(password) > max_length:
            raise ValueError(f'密码长度不能超过{max_length}位')

        if require_letter and not any(c.isalpha() for c in password):
            raise ValueError('密码必须包含字母')

        if require_digit and not any(c.isdigit() for c in password):
            raise ValueError('密码必须包含数字')

        if require_special:
            special_chars = r'!@#$%^&*()_+-=[]{}|;:,.<>?'
            if not any(c in special_chars for c in password):
                raise ValueError('密码必须包含特殊字符')

        if require_letter and require_digit and not (
            any(c.isalpha() for c in password) and any(c.isdigit() for c in password)
        ):
            raise ValueError('密码必须同时包含字母和数字')

        return password

