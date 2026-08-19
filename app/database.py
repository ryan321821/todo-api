"""
数据库连接配置模块

作用：
- 创建数据库引擎（engine）：负责真正连接 MySQL
- 创建会话工厂（SessionLocal）：每次请求生成一个数据库会话
- 提供依赖注入函数（get_db）：让接口函数自动获取/关闭会话
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 连接串：优先读取环境变量 DATABASE_URL（docker-compose.yml 里已经设置好了）
# 如果环境变量不存在，就用下面这个默认值
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://todo:todo@db:3306/todo?charset=utf8mb4",
)

# 创建数据库引擎
# pool_pre_ping=True  每次使用连接前先检查连接是否有效，避免用到失效连接
# pool_recycle=3600   连接超过 1 小时回收重建，防止被 MySQL 超时断开
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# 创建会话工厂：SessionLocal() 一次就产生一个新的数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 模型的基类：所有数据表模型（第 3 步的 Task）都要继承它
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入函数：请求开始给一个会话，请求结束自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()