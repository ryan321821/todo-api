"""
数据库层：数据库引擎与会话管理 (db/session.py)

【为什么需要这个文件？】
封装数据库底层的连接池管理以及会话生命周期。
通过 FastAPI 的 Depends(get_db) 依赖注入机制，实现"每个请求获取一个会话，请求结束自动释放"。
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# ==================== 创建数据库引擎 (Engine) ====================
# - pool_pre_ping=True: 每次从连接池借出连接前执行一次心跳探测，避免使用已经断开的失效连接
# - pool_recycle=3600: 连接存活超过 1 小时自动回收重建，防止被 MySQL 8.0 默认超时断开
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# ==================== 创建会话工厂 (SessionLocal) ====================
# 每次调用 SessionLocal() 会生成一个独立的数据库会话 Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ==================== 依赖注入函数 (get_db) ====================
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 路由依赖注入函数
    
    【执行流程】：
    1. 当客户端请求进来时，进入此函数，通过 SessionLocal() 创建会话并 yield 提供给路由函数使用；
    2. 路由函数处理业务、读写数据库；
    3. 响应返回后（即使发生异常），自动进入 finally 代码块执行 db.close()，防止连接泄露。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
