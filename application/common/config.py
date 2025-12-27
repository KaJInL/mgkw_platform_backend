import os
import re
import yaml
from typing import Optional
from pydantic import BaseModel, field_validator

# ============================
# 🔥 自动替换 ${ENV_VAR} 的函数
# ============================

env_pattern = re.compile(r"\$\{([^}]+)\}")

def replace_env_variables(obj):
    """
    递归替换 YAML 中的 ${VAR} 或 ${VAR:default}
    """
    if isinstance(obj, dict):
        return {k: replace_env_variables(v) for k, v in obj.items()}

    elif isinstance(obj, list):
        return [replace_env_variables(item) for item in obj]

    elif isinstance(obj, str):
        matches = env_pattern.findall(obj)
        if not matches:
            return obj

        new_value = obj
        for match in matches:
            if ":" in match:
                env_name, default = match.split(":", 1)
                env_value = os.getenv(env_name, default)
            else:
                env_value = os.getenv(match, "")

            new_value = new_value.replace("${" + match + "}", env_value)

        return new_value

    return obj


# ============================
#        配置模型
# ============================

class DatabaseConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    name: str
    charset: str
    echo: bool


class LogConfig(BaseModel):
    level: str
    file: str


class Redis(BaseModel):
    host: str
    port: int
    password: str = ""
    db: int
    max_connections: int


class Upload(BaseModel):
    dir: str


class CeleryConfig(BaseModel):
    broker_url: str
    result_backend: str
    task_serializer: str
    result_serializer: str
    accept_content: list
    result_expires: int
    timezone: str


class DOC(BaseModel):
    docs_url: str
    enable_docs: bool
    redoc_url: str
    enable_redoc: bool


class AuthConfig(BaseModel):
    token_expire_days: int = 7
    max_tokens_per_user: int = 0


class OrderConfig(BaseModel):
    expire_minutes: int = 30  # 待支付订单过期时间（分钟）


class MiniProgram(BaseModel):
    wechat_app_id: str
    wechat_app_secret: str


class WechatPay(BaseModel):
    """微信支付配置"""
    appid: str  # 公众账号ID
    mchid: str  # 商户号
    api_key: str  # API密钥（用于签名）
    private_key_path: str  # 商户私钥文件路径（用于V3签名）
    cert_serial_no: str  # 商户证书序列号
    notify_url: str  # 支付回调通知地址

    @field_validator("mchid", mode="before")
    @classmethod
    def mchid_to_str(cls, v):
        return str(v)

class Setting(BaseModel):
    debug_mode: bool = False
    base_url: str
    secret_key: str
    database: DatabaseConfig
    miniprogram : MiniProgram
    wechat_pay: Optional[WechatPay] = None  # 微信支付配置，可选
    log: LogConfig
    redis: Redis
    upload: Upload
    celery: CeleryConfig
    doc: DOC
    auth: AuthConfig
    order: OrderConfig = OrderConfig()  # 订单配置，默认值
    project_name: str
    prefix: str

    @classmethod
    def from_yaml(cls, path: str) -> "Setting":
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        # 🔥 自动替换环境变量
        data = replace_env_variables(data)

        return cls(**data)


# ============================
#        加载配置文件
# ============================

def _load_config() -> Setting:
    env = os.getenv("ENV")  # dev, prod, etc
    base_filename = "config.yaml"
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    filename = f"config-{env}.yaml" if env else base_filename

    print(f"load config from {filename}")

    if not os.path.isabs(filename):
        filename = os.path.join(root_dir, filename)

    if not os.path.exists(filename):
        if env:
            fallback_path = os.path.join(root_dir, base_filename)
            if os.path.exists(fallback_path):
                filename = fallback_path
            else:
                raise FileNotFoundError(f"配置文件 {filename} 和默认文件 {fallback_path} 都未找到，请检查路径。")
        else:
            raise FileNotFoundError(f"配置文件 {filename} 未找到，请检查路径。")

    return Setting.from_yaml(filename)


# ============================
#        全局 config 实例
# ============================

config: Setting = _load_config()

__all__ = ["config"]
