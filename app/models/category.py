from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class Category(Base):
    __tablename__ = "categories"
    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, comment="分类 ID"
    )
    name = Column(String(50), nullable=False, unique=True, comment="分类名称")
    color = Column(String(20), nullable=False, default="#1890ff", comment="分类颜色")
    description = Column(Text, nullable=True, comment="分类描述")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    tasks = relationship("Task", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', color='{self.color}')>"
