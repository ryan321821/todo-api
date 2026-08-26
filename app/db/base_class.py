"""
数据库层：SQLAlchemy ORM 声明基类定义 (db/base_class.py)

【为什么需要这个文件？】
在 SQLAlchemy 中，所有数据表模型（如 Task、User 等）都需要继承同一个 Base 基类。
将其独立放置在 base_class.py 中，可以避免 models 层与 db 层的循环导入问题。
"""

from sqlalchemy.orm import declarative_base

# 创建 ORM 模型的公共基类
# 所有的数据表类（如 models/task.py 中的 Task）都必须继承此 Base
Base = declarative_base()
