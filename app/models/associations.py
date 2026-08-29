from sqlalchemy import Column, Integer, Table, ForeignKey

from app.db.base_class import Base

# 执行Base.metadata.create_all(engine) 时，创建这张表。
user_roles = Table(  # 实例化 Table 类（创建对象），用于定义关联表
    "user_roles",
    Base.metadata,
    # 复合主键：同一对 (user_id, role_id) 只会存在一条，天然防重复
    Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
    comment="用户角色关联表",
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "permission_id",
        Integer,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
