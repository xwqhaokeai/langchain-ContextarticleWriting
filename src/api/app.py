from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings
from .middleware import ExceptionHandlingMiddleware
from ..infrastructure.tracking import RequestTrackingMiddleware
from ..infrastructure.tracing import setup_tracing
from ..infrastructure.logging import get_logger
from .routers import writing

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Context Article Writing API",
        description="API for generating articles with context from various sources.",
        version="1.0.0",
        docs_url=None,  # 禁用默认路径，以便自定义
        redoc_url="/redoc",
    )

    # 1. 链路追踪 (必须在所有中间件之前)
    # setup_tracing(app) # Tracing is now configured in main.py

    # 2. 异常处理
    app.add_middleware(ExceptionHandlingMiddleware)

    # 3. 请求追踪
    app.add_middleware(RequestTrackingMiddleware)

    # 4. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # MVP阶段允许所有源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(writing.router, prefix="/api/v1", tags=["writing"])

    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Context Article Writing API"}

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """
        使用国内CDN加载Swagger UI，以获得更好的访问速度。
        """
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=app.title + " - Swagger UI",
            swagger_js_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.17.14/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.17.14/swagger-ui.css",
        )

    return app

app = create_app()
