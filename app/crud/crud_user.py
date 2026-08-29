from typing import Optional

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from sqlalchemy.orm import Session, selectinload


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):  # 方括号 [...] 是 Python 泛型
    """
    后端开发中，CRUD 命名通常遵循一套标准的语义公式：
        by = WHERE 过滤条件（如 get_by_username --> WHERE username = ?）
        with = Eager Loading 关联加载 / 联动操作（如 get_with_roles --> 级联加载/绑定 roles）
        multi = 批量/列表查询（通常带有 skip 和 limit 分页参数）
    """

    # 根据用户名查询用户
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    # 根据邮箱查询用户
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    # 预加载角色的用户查询
    def get_with_roles(self, db: Session, *, user_id: int) -> Optional[User]:
        return (
            db.query(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .filter(User.id == user_id)
            .first()
        )

    # 用户身份认证 / 登录校验
    def authenticate(self, db: Session, username: str, password: str) -> Optional[User]:
        user = self.get_by_username(db, username=username)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    # 创建用户并绑定角色
    def create_with_roles(
        self, db: Session, *, obj_in: UserCreate, role_codes: list[str] | None = None
    ) -> User:
        try:
            db_obj = User(
                username=obj_in.username,
                email=obj_in.email,
                hashed_password=get_password_hash(obj_in.password),
                is_active=True,
                is_superuser=False,
            )
            if obj_in.role_codes:
                db_obj.roles = (
                    db.query(Role).filter(Role.code.in_(obj_in.role_codes)).all()
                )
            db.add(db_obj)
            db.commit()
            return self.get_with_roles(db, user_id=db_obj.id)
        except Exception as e:
            db.rollback()
            raise e

    # 更新用户及角色关系
    def update_with_roles(self, db: Session, db_obj: User, obj_in: UserUpdate) -> User:
        update_data = obj_in.model_dump(  # model_dump() 是 Pydantic 的方法，作用是把对象转换成字典。
            # exclude_unset:只导出前端实际传过来的字段，忽略那些没传的None字段
            exclude_unset=True,
            exclude={"password", "role_codes"},
        )

        if obj_in.password is not None:
            db_obj.hashed_password = get_password_hash(obj_in.password)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        # SQLAlchemy 对“普通列（Column）”和“关系（Relationship）”的处理机制完全不同！
        # 对于普通列，直接使用 setattr() 方法即可。
        # 对于关系列，必须使用 add() 和 remove() 方法，而不能直接赋值,ORM 要的是对象列表！
        if obj_in.role_codes is not None:
            db_obj.roles = db.query(Role).filter(Role.code.in_(obj_in.role_codes)).all()

        db.commit()
        return self.get_with_roles(db, user_id=db_obj.id)

    # 分页获取用户列表（含角色）
    def get_multi_with_roles(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> tuple[int, list[User]]:
        query = (
            db.query(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .order_by(User.id)
        )
        total = query.count()
        users = (
            query.offset(skip).limit(limit).all()
        )  # offset(skip) 跳过skip条数据，limit(limit) 每页最大limit条数据
        return total, users


user = CRUDUser(User)
