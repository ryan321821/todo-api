from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

"""
核心层：RBAC 初始化种子数据 (core/seed.py)

企业里通常有一个"系统引导/初始化"步骤：
应用第一次启动时，自动创建初始角色、权限和超级管理员。
这样开发、测试、生产环境的行为完全一致。
"""


def init_seed_data(db: Session):
    """
    创建初始权限、角色与超级管理员。
    幂等设计：通过查询判断数据是否已存在，确保重复执行不会产生重复数据。

    注意：当前逻辑在最后统一 commit，如果在中间步骤发生异常，整个操作会回滚，
    但由于缺少显式的异常捕获，建议在调用此函数的外层配合 try-except 或依赖 FastAPI 的中间件进行事务管理。
    """

    # ==================== 步骤1：初始化权限 ====================
    # 定义系统所需的基础权限集合，键为权限代码，值为权限中文名
    permission_defs = {  # definitions，权限定义
        "task:read": "查看任务",
        "task:write": "创建与编辑任务",
        "task:delete": "删除任务",
        "category:read": "查看分类",
        "category:write": "创建与编辑分类",
        "user:read": "查看用户",
        "user:write": "管理用户",
        "role:read": "查看角色",
        "role:write": "管理角色",
    }

    # 存储权限对象，供后续建立角色与权限的多对多关系使用
    perm_objs: dict[str, Permission] = {}
    for code, name in permission_defs.items():
        # 查询数据库中是否已存在该权限，保证幂等性
        perm = db.query(Permission).filter(Permission.code == code).first()
        if not perm:
            perm = Permission(code=code, name=name)
            db.add(perm)
            db.flush()  # 提前刷入数据库，获取权限的自增ID，以便后续建立关联关系
        perm_objs[code] = perm

    # ==================== 步骤2：初始化角色并分配权限 ====================
    # 初始化超级管理员角色
    admin_role = db.query(Role).filter(Role.code == "admin").first()
    if not admin_role:
        admin_role = Role(code="admin", name="超级管理员", description="拥有全部权限")
        # 超级管理员默认拥有系统内的所有权限
        admin_role.permissions = list(perm_objs.values())
        db.add(admin_role)
        db.flush()

    # 初始化普通用户角色
    user_role = db.query(Role).filter(Role.code == "user").first()
    if not user_role:
        user_role = Role(code="user", name="普通用户", description="管理自己的任务")
        # 普通用户仅分配任务相关和查看分类的权限
        user_role.permissions = [
            perm_objs["task:read"],
            perm_objs["task:write"],
            perm_objs["task:delete"],
            perm_objs["category:read"],
        ]
        db.add(user_role)
        db.flush()

    # ==================== 步骤3：初始化超级管理员账号 ====================
    admin = db.query(User).filter(User.username == settings.FIRST_SUPERUSER).first()
    if not admin:
        admin = User(
            username=settings.FIRST_SUPERUSER,
            email=f"{settings.FIRST_SUPERUSER}@example.com",
            hashed_password=get_password_hash(
                settings.FIRST_SUPERUSER_PASSWORD
            ),  # 存储哈希密码而非明文，保障安全
            is_active=True,
            is_superuser=True,  # 标记为系统最高权限用户
        )

        # 将超级管理员与 admin 角色进行绑定
        admin.roles = [admin_role]
        db.add(admin)

    # 统一提交所有数据库变更，确保数据一致性
    db.commit()
