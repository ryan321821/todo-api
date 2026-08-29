from typing import Optional

from app.models.permission import Permission
from app.schemas.permission import PermissionCreate
from app.crud.base import CRUDBase
from sqlalchemy.orm import Session


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionCreate]):
    def get_by_code(self, db: Session, *, code: str) -> Optional[Permission]:
        return db.query(Permission).filter(Permission.code == code).first()

    def get_multi_with_count(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> tuple[int, list[Permission]]:
        """
        分页查询返回总数和列表。重点来了：即使数据库一张表里完全没有数据，query.all()
        也会返回 空列表 []，而永远不会返回 None。既然返回值是确定的 list 对象（只是空），
        就不需要 Optional。
        """

        query = db.query(Permission).oder_by(Permission.id)
        total = query.count()
        permissions = query.offset(skip).limit(limit).all()
        return total, permissions


permission = CRUDPermission(Permission)
