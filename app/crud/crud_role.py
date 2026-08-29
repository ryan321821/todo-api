from typing import Optional

from app.crud.base import CRUDBase
from app.models.permission import Permission
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate

from sqlalchemy.orm import Session, selectinload


class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    """
    数据持久层：Role 专属 CRUD 数据访问对象 (crud/crud_role.py)
    """

    def get_by_code(self, db: Session, *, code: str) -> Optional[Role]:
        return db.query(Role).filter(Role.code == code).first()

    """
    单下划线开头	_get_with_permissions	提示为内部/私有方法。外部强行调用虽然也能跑，但不合规范，IDE 不会自动推荐。
    双下划线开头	__get_with_permissions	开启名称修饰（Name Mangling），使子类无法轻易重写，封装级别更高。
    单下划线做变量名	_: User = Depends(...)	占位符，表示“这个变量的值我不需要用”。
    """

    def _get_with_permissions(self, db: Session, *, role_id: int) -> Optional[Role]:
        # options是 SQLAlchemy Query 对象自带的一个成员方法,给当前的 SQL 查询附加特殊的加载策略选项
        return db.query(Role).options(
            selectinload(Role.permissions).filter(Role.id == role_id).first()
        )

    def get_multi_with_permissions(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> tuple[int, list[Role]]:
        query = db.query(Role).options(selectinload(Role.permissions)).order_by(Role.id)
        total = query.count()
        roles = query.offset(skip).limit(limit).all()
        return total, roles

    def create_with_permissions(self, db: Session, *, obj_in: RoleCreate) -> Role:
        db_obj = Role(
            code=obj_in.code, name=obj_in.name, description=obj_in.description
        )
        if obj_in.permission_codes:
            db_obj.permissions = (
                db.query(Permission).filter(
                    Permission.code.in_(obj_in.permission_codes)
                )
            ).all()
        db.add(db_obj)
        db.commit()
        return self._get_with_permissions(db, role_id=db_obj.id)

    def update_with_permissions(
        self, db: Session, *, db_obj: Role, obj_in: RoleUpdate
    ) -> Role:
        update_data = obj_in.model_dump(
            exclude_unset=True, exclude={"permission_codes"}
        )
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        if obj_in.permission_codes is not None:
            db_obj.permissions = db.query(Permission).filter(
                Permission.code.in_(obj_in.permission_codes)
            )
        db.commit()
        return self._get_with_permissions(db, role_id=db_obj.id)


role = CRUDRole(Role)
