"""
ORM 模型层：Task（任务）数据表映射模型 (models/task.py)

【为什么需要这个文件？】
使用 SQLAlchemy ORM 将 Python 类映射为 MySQL 数据库表。
一个类 = 一张数据表，类的一个属性 = 表里的一个列/字段。
【本次升级】：增加 category_id 外键与 relationship 关联，将任务与分类绑定。
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Task(Base):
    """
    任务表 ORM 数据模型
    对应 MySQL 中的 `tasks` 表
    """

    __tablename__ = "tasks"  # 指定 MySQL 中实际创建的表名

    # 主键 ID：自增整数，建立索引以加快按 ID 查询速度
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 任务标题：必填字段（nullable=False），最长 100 字符
    title = Column(String(100), nullable=False, comment="任务标题")

    # 任务详细描述：选填字段（nullable=True），使用 Text 类型可存储长文本
    description = Column(Text, nullable=True, comment="任务描述")

    # 任务优先级：字符串类型，限定为 low / medium / high，默认值为 medium
    priority = Column(
        String(20),
        nullable=False,
        default="medium",
        comment="优先级: low/medium/high",
    )

    # 任务是否完成：布尔值，默认 False（未完成）
    is_completed = Column(Boolean, default=False, comment="是否完成")

    # ==================== 所属分类外键关联 ====================
    # 外键：关联 categories 表的主键 id
    # ondelete="SET NULL": 当分类被删除时，关联的任务不被删除，而是将分类置空 (NULL)
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属分类ID",
    )
    # ORM 关系映射：允许通过 task.category 直接获取 Category 对象
    category = relationship("Category", back_populates="tasks", lazy="joined")

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="所属用户ID",
    )

    owner = relationship("User", back_populates="tasks", lazy="selectin")

    # 记录创建时间：由数据库端自动填入当前时间戳
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间",
    )

    def __repr__(self) -> str:
        """调试或打印对象时的友好字符串表达"""
        return (
            f"<Task(id={self.id}, title='{self.title}', "
            f"priority='{self.priority}', category_id={self.category_id}, is_completed={self.is_completed})>"
        )
