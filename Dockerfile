# =========================
# 基础镜像
# =========================
FROM python:3.12-slim

# =========================
# 工作目录
# =========================
WORKDIR /app

# =========================
# 环境变量
# =========================
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=prod

# =========================
# 安装系统依赖和 uv
# =========================
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y \
       build-essential \
       default-libmysqlclient-dev \
       pkg-config \
       curl \
    && rm -rf /var/lib/apt/lists/*

# =========================
# 安装 uv 并复制依赖文件
# =========================
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./

# =========================  
# 安装依赖（uv sync 会自动创建虚拟环境）
# =========================
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --no-dev

# 将 uv 和虚拟环境添加到 PATH
ENV PATH="/root/.local/bin:/app/.venv/bin:$PATH"

# =========================
# 复制项目代码
# =========================
COPY . .

# =========================
# 创建必要目录
# =========================
RUN mkdir -p logs uploads certs

# 微信支付证书目录（运行时挂载 volume）
VOLUME ["/app/certs"]

# =========================
# 暴露端口
# =========================
EXPOSE 5001

# =========================
# 复制启动脚本并设置权限
# =========================
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# =========================
# 使用 ENTRYPOINT 灵活启动服务
# =========================
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["fastapi"]
