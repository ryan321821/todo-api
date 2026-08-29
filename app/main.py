"""
FastAPI 应用全局入口 (main.py)

【为什么需要这个文件？】
作为整个 Web 服务的最高调度中心，负责：
1. 管理应用的整个生命周期（Lifespan：启动时自动建表、关闭时释放资源）；
2. 实例化 FastAPI 核心对象；
3. 注册全局中间件（如 CORS 跨域支持）；
4. 托管静态文件服务（使前端页面 http://localhost:8000/static/index.html 可直接访问）；
5. 注册并挂载所有 API 路由。
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.seed import init_seed_data
from app.db.base import Base
from app.db.session import SessionLocal, engine


# ==================== 应用生命周期管理 (Lifespan) ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 推荐的生命周期上下文管理器
    - yield 之前：在应用启动 (Startup) 时执行；
    - yield 之后：在应用关闭 (Shutdown) 时执行。
    """
    # 1. 启动时：根据 Base.metadata 自动创建所有尚未在 MySQL 中存在的数据表
    Base.metadata.create_all(bind=engine)

    # 2. 初始化 RBAC 种子数据（角色、权限、超级管理员）
    with SessionLocal() as db:
        init_seed_data(db)

    print("✅ [Lifespan] 数据库表已验证/创建完成")
    yield
    # 关闭时：释放连接池或清理资源
    print("🛑 [Lifespan] 应用已正常关闭")


# ==================== 创建 FastAPI 核心实例 ====================
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",  # Swagger UI 交互式文档路径
    redoc_url="/redoc",  # ReDoc 文档路径
)


# ==================== 注册全局中间件 ====================
# 配置 CORS (跨源资源共享)，允许前端应用跨域发送请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（生产环境可限定特定域名）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法 (GET, POST, PUT, DELETE 等)
    allow_headers=["*"],  # 允许所有请求头
)


# ==================== 全局异常统管 ====================
# 数据库唯一键冲突（如用户名/邮箱重复）统一转成 409，避免把堆栈抛给前端
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "数据冲突：用户名、邮箱或编码可能已存在"},
    )


# ==================== 挂载静态文件目录 ====================
# 将本地 static 文件夹映射到 HTTP 路径 /static
# 浏览器访问 http://localhost:8000/static/index.html 即可查看前端管理页面
if os.path.exists(settings.STATIC_DIR):
    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")


# ==================== 注册业务路由 ====================
# 1. 挂载到根路径（支持 /、/healthz、/health、/tasks、/categories 直接访问）
app.include_router(api_router)

# 2. 同时挂载到标准 API 版本路径 /api/v1（例如：/api/v1/tasks、/api/v1/categories）
app.include_router(api_router, prefix=settings.API_V1_STR)
