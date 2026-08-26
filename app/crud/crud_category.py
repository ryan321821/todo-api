"""
数据持久层：Category 专属 CRUD 数据访问对象 (crud/crud_category.py)
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate

class CRUDCategory(CRUDBase[Category, CategoryCreate, CategoryUpdate]):
    """
    Category 专属数据操作类
    """

    def get_by_name(self, db: Session, *, name: str) -> Optional[Category]:
        """
        根据分类名称查询单条记录
        对应 SQL: SELECT * FROM category WHERE name = :name LIMIT 1;
        """
        return db.query(self.model).filter(self.model.name == name).first()

    def get_multi_with_count(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> tuple[int, list[Category]]:
        query = db.query(self.model).order_by(self.model.created_at.desc())
        total = query.count()
        categories = query.offset(skip).limit(limit).all()
        return total, categories


category = CRUDCategory(Category)
