from fastapi import FastAPI

from application.apis import register_routes
from application.common.config import config
from application.common.tasks.celery_task.celery_app import celery_manager
from application.core.lifespan import lifespan
from application.common.middleware import register_middleware


class _Application:
    """
    项目统一容器，负责创建 FastAPI/Celery 等实例
    """

    def __init__(self):
        self.fastapi_app: FastAPI | None = None
        self.celery_app = celery_manager.app
        self.fast_app = self._init_app()


    def _init_app(self) -> FastAPI:
        """
        创建并初始化 FastAPI 实例
        """

        app = FastAPI(
            lifespan=lifespan,
            title=config.project_name,
            docs_url=f"{config.prefix}{config.doc.docs_url}" if config.doc.enable_docs else None,
            redoc_url=f"{config.prefix}{config.doc.redoc_url}" if config.doc.enable_redoc else None,
        )
        # 注册所有模块路由
        register_routes(app)

        # 注册中间键
        register_middleware(app)
        self.fastapi_app = app
        return app


application = _Application()
app = application.fastapi_app
celery_app = application.celery_app
