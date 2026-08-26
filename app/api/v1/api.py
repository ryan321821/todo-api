"""
路由层：API v1 路由总线聚合模块 (api/v1/api.py)

【为什么需要这个文件？】
作为 v1 版本所有业务路由的汇聚入口（Router Aggregator）。
各个具体业务模块（如 health、tasks，以及未来的 users 等）的子路由在这里统一 include 组装，
然后由 main.py 一次性挂载到 FastAPI 应用实例上。
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, tasks, categories

# 实例化 v1 统一路由器
api_router = APIRouter()

# 挂载系统监控与健康检查子路由（不加前缀，直接挂在根下）
api_router.include_router(health.router, tags=["系统"])

# 挂载任务模块子路由，统一前缀为 /tasks
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务"])

# 2. 挂载分类模块（统一加前缀 /categories，打上标签）
api_router.include_router(categories.router, prefix="/categories", tags=["分类"])
