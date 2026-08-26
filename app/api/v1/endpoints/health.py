"""
路由控制器层：系统健康检查与欢迎端点 (api/v1/endpoints/health.py)

【为什么需要这个文件？】
将系统级的监控、健康检查与欢迎页面接口从主入口 main.py 中剥离出来，
便于运维探针（如 Kubernetes liveness/readiness probe）和 Docker 容器健康检查调用。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/", summary="欢迎信息")
def root():
    """
    根路径接口：返回欢迎信息与交互式文档地址
    """
    return {"message": "🚀 迷你任务备忘录 API 正在运行", "docs": "/docs"}


@router.get("/healthz", summary="进程存活健康检查")
def healthz():
    """
    进程级存活性检查接口（Liveness Probe）
    只要 Web 服务进程正常响应就返回 200 OK，不涉及外部依赖
    """
    return {"status": "ok"}


@router.get("/health", summary="数据库连接健康检查")
def health_check(db: Session = Depends(get_db)):
    """
    数据库就绪性检查接口（Readiness Probe）
    向 MySQL 执行简单的 SELECT NOW() 探针查询：
    - 正常返回 200 {"status": "healthy", "database": "connected"}
    - 异常返回 503 Service Unavailable
    """
    try:
        db.execute(func.now())
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库连接异常: {str(e)}")
