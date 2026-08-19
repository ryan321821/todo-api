"""
SQLAlchemy ORM 数据模型

作用：用 Python 类描述数据库表结构。
一个类 = 一张表，一个属性 = 一个字段。
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from .database import Base


class Task(Base):
    """任务表 ORM 模型"""

    __tablename__ = "tasks"  # 指定数据库里的表名

    # 主键，自增
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 任务标题：必填，最长 100 个字符
    title = Column(String(100), nullable=False, comment="任务标题")

    # 任务描述：可选（可空），用 Text 类型可以存较长内容
    description = Column(Text, nullable=True, comment="任务描述")

    # 优先级：low / medium / high，默认 medium
    priority = Column(
        String(20),
        nullable=False,
        default="medium",
        comment="优先级: low/medium/high",
    )

    # 是否完成：默认 False（未完成）
    is_completed = Column(Boolean, default=False, comment="是否完成")

    # 创建时间：由数据库自动生成当前时间
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间",
    )

    # 更新时间：每次修改自动更新
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    def __repr__(self):
        """打印这个对象时显示的内容，方便调试"""
        return (
            f"<Task(id={self.id}, title='{self.title}', "
            f"priority='{self.priority}')>"
        )