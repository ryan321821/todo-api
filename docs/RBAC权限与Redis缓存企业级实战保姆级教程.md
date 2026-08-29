# RBAC 权限与 Redis 缓存企业级实战保姆级教程

> **核心提问**：我已经写完了"任务（Task）与分类（Category）的一对多联动"，现在要做用户登录、角色权限、高并发缓存，**架构需要怎么升级？**  
> **答案**：必须从 **数据库设计 → ORM 模型 → Pydantic 校验 → CRUD 持久层 → 依赖注入 → 路由控制器** 进行一条完整链路升级，而不是在 `main.py` 里堆代码。  
> **本教程主线**：模块一 `RBAC + JWT 鉴权`、模块二 `Redis 缓存层`；模块三 `Excel 导入导出 + 定时统计` 作为扩展演练。

---

## 目录

1. 阅读前提与文件总览
2. 模块一：RBAC + JWT 鉴权
   - 第 0 步：需求与目标
   - 第 1 步：数据库设计与迁移（SQL / Alembic）
   - 第 2 步：ORM 数据模型（多对多关系）
   - 第 3 步：Pydantic 数据传输模型
   - 第 4 步：核心层扩展（config / seed 种子数据）
   - 第 5 步：认证与权限依赖注入（api/deps.py）
   - 第 6 步：CRUD 持久层（事务与避免 N+1）
   - 第 7 步：路由控制器（登录 / 用户 / 角色 / 任务鉴权）
   - 第 8 步：路由总线与主入口
   - 模块一关键设计决策
3. 模块二：Redis 缓存层
   - 第 1 步：环境与配置改造
   - 第 2 步：缓存封装（core/cache.py）
   - 第 3 步：改造任务列表接口（Cache-Aside）
   - 第 4 步：写操作缓存失效
   - 模块二关键设计决策
4. 模块三（扩展）：Excel 批量导入导出 + 定时统计
5. 环境与基础设施同步汇总
6. 验证与全流程测试
7. 避坑指南与最佳实践（FAQ）
8. 总结清单（Checklist）

---

## 1. 阅读前提与文件总览

本教程建立在两份已完成文档的基础之上：

- 《企业级目录结构重构详解》：理解 `core / db / models / schemas / crud / api` 分层。
- 《任务与分类前后端联动改造实战教程》：理解"自底向上"改造一对多关系的 4 步法。

本次新增或修改的文件总览：

```text
app/
├── core/
│   ├── config.py                 # 【修改】增加 REDIS_URL / CACHE_TTL / 初始管理员
│   ├── security.py               #  复用（密码哈希、JWT 生成与解析）
│   ├── seed.py                   # 【新增】初始化角色、权限、超级管理员
│   └── cache.py                  # 【新增】Redis 缓存封装（模块二）
├── db/
│   └── base.py                   # 【修改】注册 User / Role / Permission 等模型
├── models/
│   ├── associations.py           # 【新增】两张多对多关联表
│   ├── user.py                   # 【新增】用户模型
│   ├── role.py                   # 【新增】角色模型
│   ├── permission.py             # 【新增】权限模型
│   ├── task.py                   # 【修改】增加 owner_id 归属
│   └── __init__.py               # 【修改】导出新模型
├── schemas/
│   ├── token.py                  # 【新增】登录请求 / Token 响应
│   ├── user.py                   # 【新增】用户 DTO / VO
│   ├── role.py                   # 【新增】角色 DTO / VO
│   ├── permission.py             # 【新增】权限 DTO / VO
│   └── task.py                   # 【修改】响应增加 owner_id
├── crud/
│   ├── crud_user.py              # 【新增】用户持久层
│   ├── crud_role.py              # 【新增】角色持久层
│   ├── crud_permission.py        # 【新增】权限持久层
│   ├── crud_task.py              # 【修改】按归属查询、创建时写入 owner_id
│   └── __init__.py               # 【修改】导出新单例
├── api/
│   ├── deps.py                   # 【新增】认证与权限依赖注入
│   └── v1/
│       ├── api.py                # 【修改】注册 auth / users / roles 路由
│       └── endpoints/
│           ├── auth.py           # 【新增】登录 / 注册
│           ├── users.py          # 【新增】用户管理
│           ├── roles.py          # 【新增】角色管理
│           └── tasks.py          # 【修改】加鉴权、归属校验、Redis 缓存
└── main.py                       # 【修改】启动种子数据、全局异常、定时任务
```

---

## 2. 模块一：RBAC + JWT 鉴权

### 第 0 步：需求与目标

要落地的能力：

1. 用户可以用 `username + password` 登录，拿到 JWT。
2. 后续请求携带 `Authorization: Bearer <token>`，后端统一解析出当前用户。
3. 角色与权限是多对多关系，路由用"权限点"做拦截。
4. 任务有归属，普通用户只能操作自己的任务，超级管理员可以看全部。

### 第 1 步：数据库设计与迁移（SQL / Alembic）

#### 1.1 目标表结构

新增 5 张表：`users`、`roles`、`permissions`、`user_roles`、`role_permissions`。

```text
users(id PK, username UQ, email UQ, hashed_password, is_active, is_superuser, created_at, updated_at)
roles(id PK, code UQ, name, description)
permissions(id PK, code UQ, name, description)
user_roles(user_id FK, role_id FK, 复合主键)
role_permissions(role_id FK, permission_id FK, 复合主键)
```

#### 1.2 保留旧数据地更新 MySQL：执行 SQL

在 `docker-compose.yml` 的 `db` 服务已就绪后，先登录 MySQL：

```bash
docker compose exec db mysql -u root -p123456
```

然后执行下面的 SQL（注意顺序：先建父表 `users`、`roles`、`permissions`，再建关联表和给 `tasks` 加列）：

```sql
USE todo;

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email (email),
    KEY ix_users_id (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 角色表
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(200) NULL,
    UNIQUE KEY uq_roles_code (code),
    KEY ix_roles_id (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 权限表
CREATE TABLE IF NOT EXISTS permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(200) NULL,
    UNIQUE KEY uq_permissions_code (code),
    KEY ix_permissions_id (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 用户-角色关联表（复合主键，天然去重）
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INT NOT NULL,
    role_id INT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 角色-权限关联表
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT fk_role_permissions_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    CONSTRAINT fk_role_permissions_permission FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 已有表 tasks 增加归属列（保留旧数据的关键：用 ALTER 而不是 DROP 重建）
ALTER TABLE tasks
    ADD COLUMN owner_id INT NULL,
    ADD KEY ix_tasks_owner_id (owner_id),
    ADD CONSTRAINT fk_tasks_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL;
```

历史任务回填（可选，建议在种子数据创建出 `admin` 用户之后执行）：

```sql
-- 把之前没有归属的历史任务统一归属给 admin，避免它们对普通用户"隐身"
UPDATE tasks t
JOIN users u ON u.username = 'admin'
SET t.owner_id = u.id
WHERE t.owner_id IS NULL;
```

> ⚠️ **为什么不能只依赖 `Base.metadata.create_all()`？**  
> 它会创建**不存在的表**，但不会自动 `ALTER TABLE` 修改已有 `tasks` 表。所以已有表必须手动执行迁移。

#### 1.3 生产环境正规做法：Alembic 迁移思路

在项目根目录引入 Alembic：

```bash
pip install alembic
alembic init alembic
```

在 `alembic/env.py` 中把我们的 `Base.metadata` 挂进去：

```python
from app.db.base import Base
from app.core.config import settings

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

生成迁移：

```bash
alembic revision --autogenerate -m "add rbac and task owner"
```

迁移文件里的人工补全示例（保留旧数据）：

```python
def upgrade():
    op.create_table("users", ...)
    op.create_table("roles", ...)
    op.create_table("permissions", ...)
    op.create_table("user_roles", ...)
    op.create_table("role_permissions", ...)

    # 先加列、允许 NULL，避免对已有大表造成锁表/失败
    op.add_column("tasks", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_index("ix_tasks_owner_id", "tasks", ["owner_id"])
    op.create_foreign_key(
        "fk_tasks_owner",
        "tasks",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_tasks_owner", "tasks", type_="foreignkey")
    op.drop_index("ix_tasks_owner_id", table_name="tasks")
    op.drop_column("tasks", "owner_id")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
```

然后执行：

```bash
alembic upgrade head
```

### 第 2 步：ORM 数据模型（多对多关系）

#### 2.1 新建 `app/models/associations.py`

SQLAlchemy 的多对多关系通常用**关联表**表达，关联表本身没有业务主键，直接用复合主键：

```python
"""
ORM 模型层：多对多关联表定义 (models/associations.py)

为什么单独放在这里？
user.py 需要 user_roles，role.py 需要 user_roles 和 role_permissions，
permission.py 需要 role_permissions。集中定义可以避免模型之间的循环导入。
"""

from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.base_class import Base


# 用户-角色关联表（多对多）
user_roles = Table(
    "user_roles",
    Base.metadata,
    # 复合主键：同一对 (user_id, role_id) 只会存在一条，天然防重复
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


# 角色-权限关联表（多对多）
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        Integer,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
```

> 💡 **关键设计决策：关联表为什么要用 `ondelete="CASCADE"`？**
> 关联表只是"关系凭证"，不是业务主体。删除用户或角色时，凭证必须跟着消失，否则会留下指向不存在记录的脏关联。

#### 2.2 新建 `app/models/user.py`

```python
"""
ORM 模型层：User（用户）数据表映射模型 (models/user.py)
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base
from app.models.associations import user_roles


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True, comment="登录名")
    email = Column(String(255), nullable=False, unique=True, index=True, comment="邮箱")

    # 只存 bcrypt 哈希，绝不存明文密码
    hashed_password = Column(String(255), nullable=False, comment="bcrypt 密码哈希")

    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    is_superuser = Column(Boolean, default=False, nullable=False, comment="是否超级管理员")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    # 多对多：用户拥有多个角色
    # lazy="selectin"：访问 user.roles 时一次性批量查询，避免 N+1
    roles = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
```

#### 2.3 新建 `app/models/role.py`

```python
"""
ORM 模型层：Role（角色）数据表映射模型 (models/role.py)
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.associations import role_permissions, user_roles


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True, index=True, comment="角色编码，如 admin")
    name = Column(String(50), nullable=False, comment="角色名称")
    description = Column(String(200), nullable=True, comment="角色说明")

    # 反向关联：哪些用户拥有此角色
    users = relationship("User", secondary=user_roles, back_populates="roles")

    # 多对多：角色拥有的权限
    # lazy="selectin"：访问 role.permissions 时一次性批量加载
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, code='{self.code}')>"
```

#### 2.4 新建 `app/models/permission.py`

```python
"""
ORM 模型层：Permission（权限）数据表映射模型 (models/permission.py)
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.associations import role_permissions


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(100), nullable=False, unique=True, index=True, comment="权限编码，如 task:write")
    name = Column(String(100), nullable=False, comment="权限名称")
    description = Column(String(200), nullable=True, comment="权限说明")

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, code='{self.code}')>"
```

#### 2.5 修改 `app/models/task.py`

在 `Task` 类中增加 `owner_id` 与 `owner`：

```python
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False, comment="任务标题")
    description = Column(Text, nullable=True, comment="任务描述")
    priority = Column(
        String(20),
        nullable=False,
        default="medium",
        comment="优先级: low/medium/high",
    )
    is_completed = Column(Boolean, default=False, comment="是否完成")

    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属分类ID",
    )
    category = relationship("Category", backref="tasks", lazy="joined")

    # ==================== 【新增】任务归属用户 ====================
    # 多对一：一个用户拥有多个任务
    # ondelete="SET NULL"：删除用户时保留任务，只解除归属
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属用户ID",
    )
    owner = relationship("User", backref="tasks", lazy="selectin")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return (
            f"<Task(id={self.id}, title='{self.title}', "
            f"owner_id={self.owner_id}, is_completed={self.is_completed})>"
        )
```

> 💡 **关键设计决策：`owner` 为什么用 `lazy="selectin"` 而不是 `joined`？**
> - `owner` 是单侧父对象，任务列表响应里暂时只需要 `owner_id`，不需要完整用户对象。
> - `selectin` 只有在代码真的访问 `task.owner` 时才发起批量查询；`joined` 则会让每次 `Task` 查询都强制 JOIN `users`。
> - 这样可以避免为不使用的字段支付额外 JOIN 成本。

#### 2.6 更新 `app/models/__init__.py`

```python
from .associations import role_permissions, user_roles
from .category import Category
from .permission import Permission
from .role import Role
from .task import Task
from .user import User

__all__ = [
    "Task",
    "Category",
    "User",
    "Role",
    "Permission",
    "user_roles",
    "role_permissions",
]
```

#### 2.7 更新 `app/db/base.py`

这是最容易漏的一步：不导入模型，`Base.metadata.create_all()` 就看不到新表。

```python
"""
数据库层：ORM 模型统一发现与元数据注册中心 (db/base.py)
"""

from app.db.base_class import Base  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.permission import Permission  # noqa: F401
from app.models.role import Role  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.user import User  # noqa: F401
```

### 第 3 步：Pydantic 数据传输模型

#### 3.1 新建 `app/schemas/token.py`

```python
"""
数据传输层：登录与 Token 相关的 Pydantic 模型 (schemas/token.py)
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求体"""

    username: str = Field(..., min_length=1, max_length=50, description="登录名")
    password: str = Field(..., min_length=1, max_length=64, description="密码")


class TokenResponse(BaseModel):
    """登录成功后返回的令牌"""

    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
```

#### 3.2 新建 `app/schemas/permission.py`

```python
"""
数据传输层：Permission 相关的 Pydantic 模型 (schemas/permission.py)
"""

from typing import Optional

from pydantic import BaseModel, Field


class PermissionCreate(BaseModel):
    """创建权限时的请求体"""

    code: str = Field(..., min_length=2, max_length=100, description="权限编码")
    name: str = Field(..., min_length=1, max_length=100, description="权限名称")
    description: Optional[str] = Field(None, max_length=200, description="权限说明")


class PermissionResponse(BaseModel):
    """权限响应模型"""

    id: int = Field(..., description="权限 ID")
    code: str = Field(..., description="权限编码")
    name: str = Field(..., description="权限名称")
    description: Optional[str] = Field(None, description="权限说明")

    model_config = {"from_attributes": True}


class PermissionListResponse(BaseModel):
    total: int = Field(..., description="权限总数")
    permissions: list[PermissionResponse] = Field(..., description="权限列表")
```

#### 3.3 新建 `app/schemas/role.py`

```python
"""
数据传输层：Role 相关的 Pydantic 模型 (schemas/role.py)
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.permission import PermissionResponse


class RoleCreate(BaseModel):
    """创建角色时的请求体"""

    code: str = Field(..., min_length=2, max_length=50, description="角色编码")
    name: str = Field(..., min_length=1, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, max_length=200, description="角色说明")
    permission_codes: list[str] = Field(default_factory=list, description="角色初始权限编码列表")


class RoleUpdate(BaseModel):
    """更新角色时的请求体"""

    name: Optional[str] = Field(None, min_length=1, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, max_length=200, description="角色说明")
    permission_codes: Optional[list[str]] = Field(None, description="角色权限编码列表")


class RoleResponse(BaseModel):
    """角色响应模型"""

    id: int = Field(..., description="角色 ID")
    code: str = Field(..., description="角色编码")
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(None, description="角色说明")
    permissions: list[PermissionResponse] = Field(default_factory=list, description="角色权限列表")

    model_config = {"from_attributes": True}


class RoleListResponse(BaseModel):
    total: int = Field(..., description="角色总数")
    roles: list[RoleResponse] = Field(..., description="角色列表")
```

#### 3.4 新建 `app/schemas/user.py`

```python
"""
数据传输层：User 相关的 Pydantic 模型 (schemas/user.py)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.role import RoleResponse


class UserCreate(BaseModel):
    """创建用户时的请求体"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="登录名（3-50 位字母/数字/下划线）",
    )
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=8, max_length=64, description="密码（至少 8 位）")
    role_codes: list[str] = Field(default_factory=list, description="初始角色编码列表")


class UserUpdate(BaseModel):
    """更新用户时的请求体（全部可选）"""

    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="登录名",
    )
    email: Optional[EmailStr] = Field(None, description="邮箱")
    password: Optional[str] = Field(None, min_length=8, max_length=64, description="密码")
    is_active: Optional[bool] = Field(None, description="是否启用")
    is_superuser: Optional[bool] = Field(None, description="是否超级管理员")
    role_codes: Optional[list[str]] = Field(None, description="角色编码列表")


class UserResponse(BaseModel):
    """用户响应模型（绝不返回 hashed_password）"""

    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="登录名")
    email: EmailStr = Field(..., description="邮箱")
    is_active: bool = Field(..., description="是否启用")
    is_superuser: bool = Field(..., description="是否超级管理员")
    roles: list[RoleResponse] = Field(default_factory=list, description="用户角色列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int = Field(..., description="用户总数")
    users: list[UserResponse] = Field(..., description="用户列表")
```

> 💡 **关键设计决策：为什么 `UserResponse` 不包含 `hashed_password`？**
> Pydantic 响应模型天然做了一层"白名单过滤"。即使 ORM 对象里有 `hashed_password` 字段，只要响应模型没声明它，就不会泄漏到接口返回中。

#### 3.5 修改 `app/schemas/task.py`

在 `TaskResponse` 中增加 `owner_id`（`TaskCreate` / `TaskUpdate` 不需要，归属由后端从当前用户取得）：

```python
class TaskResponse(BaseModel):
    id: int = Field(..., description="任务主键 ID")
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    priority: str = Field(..., description="任务优先级")
    is_completed: bool = Field(..., description="是否已完成")
    category_id: Optional[int] = Field(None, description="所属分类ID")
    category: Optional[CategoryResponse] = Field(None, description="所属分类对象信息")
    owner_id: Optional[int] = Field(None, description="所属用户ID")  # 【新增】
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")

    model_config = {"from_attributes": True}
```

#### 3.6 更新 `app/schemas/__init__.py`

```python
from .category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)
from .msg import MessageResponse
from .permission import PermissionCreate, PermissionListResponse, PermissionResponse
from .role import RoleCreate, RoleListResponse, RoleResponse, RoleUpdate
from .task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate
from .token import LoginRequest, TokenResponse
from .user import UserCreate, UserListResponse, UserResponse, UserUpdate

__all__ = [
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "CategoryListResponse",
    "MessageResponse",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskListResponse",
    "LoginRequest",
    "TokenResponse",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "RoleListResponse",
    "PermissionCreate",
    "PermissionResponse",
    "PermissionListResponse",
]
```

### 第 4 步：核心层扩展（config / seed 种子数据）

#### 4.1 修改 `app/core/config.py`

增加 Redis 配置和初始管理员配置：

```python
class Settings(BaseSettings):
    # ... 保留原有 PROJECT_NAME / VERSION / DESCRIPTION / API_V1_STR / DATABASE_URL 等 ...

    # ==================== Redis 缓存配置（模块二使用） ====================
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    CACHE_TTL_SECONDS: int = int(os.environ.get("CACHE_TTL_SECONDS", "300"))

    # ==================== 初始超级管理员配置（种子数据） ====================
    FIRST_SUPERUSER: str = os.environ.get("FIRST_SUPERUSER", "admin")
    FIRST_SUPERUSER_PASSWORD: str = os.environ.get(
        "FIRST_SUPERUSER_PASSWORD", "Admin123456"
    )
```

#### 4.2 新建 `app/core/seed.py`

`seed.py` 的作用：应用启动时，如果数据库里没有角色、权限、管理员，就自动"播种"一份，避免手工执行 SQL。

```python
"""
核心层：RBAC 初始化种子数据 (core/seed.py)

企业里通常有一个"系统引导/初始化"步骤：
应用第一次启动时，自动创建初始角色、权限和超级管理员。
这样开发、测试、生产环境的行为完全一致。
"""

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


def init_seed_data(db: Session) -> None:
    """创建初始权限、角色与超级管理员。幂等：重复执行不会产生重复数据。"""

    # 1. 权限定义
    permission_defs = {
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

    perm_objs: dict[str, Permission] = {}
    for code, name in permission_defs.items():
        perm = db.query(Permission).filter(Permission.code == code).first()
        if not perm:
            perm = Permission(code=code, name=name)
            db.add(perm)
            db.flush()  # 先拿到权限 ID，供下面建立多对多关系
        perm_objs[code] = perm

    # 2. 角色定义
    admin_role = db.query(Role).filter(Role.code == "admin").first()
    if not admin_role:
        admin_role = Role(code="admin", name="超级管理员", description="拥有全部权限")
        admin_role.permissions = list(perm_objs.values())
        db.add(admin_role)
        db.flush()

    user_role = db.query(Role).filter(Role.code == "user").first()
    if not user_role:
        user_role = Role(code="user", name="普通用户", description="管理自己的任务")
        user_role.permissions = [
            perm_objs["task:read"],
            perm_objs["task:write"],
            perm_objs["task:delete"],
            perm_objs["category:read"],
        ]
        db.add(user_role)
        db.flush()

    # 3. 超级管理员（这个是可以登录的账号）
    admin = db.query(User).filter(User.username == settings.FIRST_SUPERUSER).first()
    if not admin:
        admin = User(
            username=settings.FIRST_SUPERUSER,
            email=f"{settings.FIRST_SUPERUSER}@example.com",
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            is_active=True,
            is_superuser=True,
        )
        admin.roles = [admin_role]
        db.add(admin)

    db.commit()
```

> 💡 **关键设计决策：为什么种子数据要"幂等"？**
> 应用可能被重启无数次，`lifespan` 每次都会执行。先查询再创建，保证不会因为重复启动而产生重复角色/权限/管理员，也不会覆盖用户已经改过的角色。

### 第 5 步：认证与权限依赖注入（`app/api/deps.py`）

这是 RBAC 的"路由器开关"：把"解析 Token、加载用户、校验权限"抽成可复用的 `Depends`。

```python
"""
API 层：认证与权限依赖注入 (api/deps.py)

为什么单独放在 api 层而不是 core 层？
get_current_user 依赖 FastAPI 的 HTTPBearer / Depends / HTTPException，
这是"接口层"的职责；core/security.py 只负责纯算法（哈希、JWT 编解码）。
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import crud
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

# auto_error=False：没有带 Token 时，由我们自己统一返回友好的 401 中文提示
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> User:
    """
    从请求头 Authorization: Bearer <token> 解析当前用户。
    成功返回带角色和权限的用户对象，失败抛 401/403。
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证凭证无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证凭证格式错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 一次性加载用户 + 角色 + 权限，避免后续权限校验触发 N+1
    user = crud.user.get_with_roles(db=db, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """需要"已登录"但不需要具体权限时使用"""
    return current_user


def require_permissions(*required_permissions: str):
    """
    权限校验工厂函数。
    用法：Depends(require_permissions("task:read", "task:write"))
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user

        # 把所有角色的权限编码拍平成集合
        user_perms = {
            permission.code
            for role in current_user.roles
            for permission in role.permissions
        }
        missing = set(required_permissions) - user_perms
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {', '.join(sorted(missing))}",
            )
        return current_user

    return checker


def require_roles(*required_roles: str):
    """
    角色校验工厂函数。
    用法：Depends(require_roles("admin"))
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user

        user_role_codes = {role.code for role in current_user.roles}
        missing = set(required_roles) - user_role_codes
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少角色: {', '.join(sorted(missing))}",
            )
        return current_user

    return checker
```

> 💡 **关键设计决策：为什么用"工厂函数"而不是写死 8 个依赖？**
> `require_permissions("task:read")` 每次调用返回一个**新的闭包**，不同路由可以声明不同权限组合，代码复用度最高，也最接近企业里 FastAPI 的常见写法。

### 第 6 步：CRUD 持久层（事务与避免 N+1）

#### 6.1 新建 `app/crud/crud_user.py`

```python
"""
数据持久层：User 专属 CRUD (crud/crud_user.py)
"""

from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    # *：表示强制要求 * 后面的所有参数必须使用“关键字参数（Keyword Arguments）”的形式进行传递
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_with_roles(self, db: Session, *, user_id: int) -> Optional[User]:
        """
        一次性把用户、角色、权限都加载出来。
        selectinload 会发 3 条 SQL（用户 -> 角色 -> 权限），而不是 N+1。
        """
        return (
            db.query(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .filter(User.id == user_id)
            .first()
        )

    def authenticate(
        self, db: Session, *, username: str, password: str
    ) -> Optional[User]:
        """登录认证：先查用户，再校验 bcrypt 密码"""
        user = self.get_by_username(db, username=username)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    def create_with_roles(
        self, db: Session, *, obj_in: UserCreate, role_codes: list[str] | None = None
    ) -> User:
        """创建用户并同时分配角色（同一事务）"""
        try:
            db_obj = User(
                username=obj_in.username,
                email=obj_in.email,
                hashed_password=get_password_hash(obj_in.password),
                is_active=True,
                is_superuser=False,
            )
            if role_codes:
                db_obj.roles = (
                    db.query(Role).filter(Role.code.in_(role_codes)).all()
                )
            db.add(db_obj)
            db.commit()
            return self.get_with_roles(db, user_id=db_obj.id)
        except Exception:
            # 事务回滚：用户和角色要么都成功，要么都不落库
            db.rollback()
            raise

    def update_with_roles(
        self, db: Session, *, db_obj: User, obj_in: UserUpdate
    ) -> User:
        """更新用户资料，若传入 role_codes 则同时重建角色关联"""
        update_data = obj_in.model_dump(
            exclude_unset=True, exclude={"password", "role_codes"}
        )

        # 密码需要单独哈希，不能直接把明文写进 hashed_password
        if obj_in.password is not None:
            db_obj.hashed_password = get_password_hash(obj_in.password)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        if obj_in.role_codes is not None:
            db_obj.roles = db.query(Role).filter(Role.code.in_(obj_in.role_codes)).all()

        db.commit()
        return self.get_with_roles(db, user_id=db_obj.id)

    def get_multi_with_roles(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> tuple[int, list[User]]:
        query = (
            db.query(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .order_by(User.id)
        )
        total = query.count()
        users = query.offset(skip).limit(limit).all()
        return total, users


user = CRUDUser(User)
```

#### 6.2 新建 `app/crud/crud_role.py`

```python
"""
数据持久层：Role 专属 CRUD (crud/crud_role.py)
"""

from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models.permission import Permission
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate


class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    def get_by_code(self, db: Session, *, code: str) -> Optional[Role]:
        return db.query(Role).filter(Role.code == code).first()

    def _get_with_permissions(self, db: Session, *, role_id: int) -> Optional[Role]:
        """重新加载角色及其权限，保证返回前关系已加载"""
        return (
            db.query(Role)
            .options(selectinload(Role.permissions))
            .filter(Role.id == role_id)
            .first()
        )

    def get_multi_with_permissions(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> tuple[int, list[Role]]:
        query = (
            db.query(Role)
            .options(selectinload(Role.permissions))
            .order_by(Role.id)
        )
        total = query.count()
        roles = query.offset(skip).limit(limit).all()
        return total, roles

    def create_with_permissions(
        self, db: Session, *, obj_in: RoleCreate
    ) -> Role:
        db_obj = Role(code=obj_in.code, name=obj_in.name, description=obj_in.description)
        if obj_in.permission_codes:
            db_obj.permissions = (
                db.query(Permission)
                .filter(Permission.code.in_(obj_in.permission_codes))
                .all()
            )
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
            db_obj.permissions = (
                db.query(Permission)
                .filter(Permission.code.in_(obj_in.permission_codes))
                .all()
            )
        db.commit()
        return self._get_with_permissions(db, role_id=db_obj.id)


role = CRUDRole(Role)
```

#### 6.3 新建 `app/crud/crud_permission.py`

```python
"""
数据持久层：Permission 专属 CRUD (crud/crud_permission.py)
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.permission import Permission
from app.schemas.permission import PermissionCreate


class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionCreate]):
    def get_by_code(self, db: Session, *, code: str) -> Optional[Permission]:
        return db.query(Permission).filter(Permission.code == code).first()

    def get_multi_with_count(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> tuple[int, list[Permission]]:
        query = db.query(Permission).order_by(Permission.id)
        total = query.count()
        permissions = query.offset(skip).limit(limit).all()
        return total, permissions


permission = CRUDPermission(Permission)
```

#### 6.4 修改 `app/crud/crud_task.py`

增加两个能力：按归属查询、创建时写入归属。

```python
class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):
    def get_multi_with_filter(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 20,
        is_completed: Optional[bool] = None,
        priority: Optional[str] = None,
        category_id: Optional[int] = None,
        owner_id: Optional[int] = None,  # 【新增】按归属用户筛选
    ) -> tuple[int, list[Task]]:
        query = db.query(self.model)

        if is_completed is not None:
            query = query.filter(self.model.is_completed == is_completed)
        if priority is not None:
            query = query.filter(self.model.priority == priority)
        if category_id is not None:
            query = query.filter(self.model.category_id == category_id)
        if owner_id is not None:
            query = query.filter(self.model.owner_id == owner_id)

        query = query.order_by(self.model.created_at.desc())
        total = query.count()
        tasks = query.offset(skip).limit(limit).all()
        return total, tasks

    def create_with_owner(
        self, db: Session, *, obj_in: TaskCreate, owner_id: int
    ) -> Task:
        """创建任务时，把归属用户由后端写入，避免前端伪造 owner_id"""
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data, owner_id=owner_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


task = CRUDTask(Task)
```

#### 6.5 更新 `app/crud/__init__.py`

```python
from .crud_category import category
from .crud_permission import permission
from .crud_role import role
from .crud_task import task
from .crud_user import user

__all__ = ["task", "category", "user", "role", "permission"]
```

> 💡 **关键设计决策：什么时候用 `selectinload`，什么时候用 `joined`？**
> - 一对多/多对多集合（`User.roles`、`Role.permissions`）用 `selectinload`：避免 JOIN 导致结果集膨胀和分页失真。
> - 只在"每次都一定要用到的单侧父对象"（如任务详情里的 `category`）才考虑 `joined`。

### 第 7 步：路由控制器

#### 7.1 新建 `app/api/v1/endpoints/auth.py`

```python
"""
路由控制器层：认证端点 (api/v1/endpoints/auth.py)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.token import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="用户登录")
def login(login_in: LoginRequest, db: Session = Depends(get_db)):
    """用户名密码登录，成功返回 JWT"""
    user = crud.user.authenticate(
        db, username=login_in.username, password=login_in.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    access_token = create_access_token(subject=user.id)
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """注册用户，默认分配 user 角色"""
    if crud.user.get_by_username(db, username=user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )
    if crud.user.get_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册",
        )

    role_codes = user_in.role_codes or ["user"]
    return crud.user.create_with_roles(db, obj_in=user_in, role_codes=role_codes)
```

#### 7.2 新建 `app/api/v1/endpoints/users.py`

> 注意：`/me` 这类固定路径必须写在 `/{user_id}` 之前，否则 FastAPI 会把 `me` 当成 `user_id` 去匹配。

```python
"""
路由控制器层：用户管理端点 (api/v1/endpoints/users.py)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_current_user, require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.msg import MessageResponse
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse, summary="更新当前用户信息")
def update_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """普通用户只能改自己的 username / email / password"""
    if user_in.username and user_in.username != current_user.username:
        if crud.user.get_by_username(db, username=user_in.username):
            raise HTTPException(status_code=400, detail="用户名已存在")

    # 越权保护：不允许普通用户自行提权或改角色
    if (
        user_in.role_codes is not None
        or user_in.is_superuser is not None
        or user_in.is_active is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="普通用户无权修改角色、启用状态或超级管理员标志",
        )

    return crud.user.update_with_roles(db, db_obj=current_user, obj_in=user_in)


@router.get("", response_model=UserListResponse, summary="获取用户列表")
def read_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("user:read")),
):
    total, users = crud.user.get_multi_with_roles(db, skip=skip, limit=limit)
    return UserListResponse(total=total, users=users)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户（管理员）",
)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("user:write")),
):
    if crud.user.get_by_username(db, username=user_in.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    if crud.user.get_by_email(db, email=user_in.email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    return crud.user.create_with_roles(
        db, obj_in=user_in, role_codes=user_in.role_codes
    )


@router.get("/{user_id}", response_model=UserResponse, summary="获取单个用户")
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("user:read")),
):
    db_user = crud.user.get_with_roles(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail=f"用户 ID {user_id} 不存在")
    return db_user


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户（管理员）")
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("user:write")),
):
    db_user = crud.user.get_with_roles(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail=f"用户 ID {user_id} 不存在")
    return crud.user.update_with_roles(db, db_obj=db_user, obj_in=user_in)


@router.delete("/{user_id}", response_model=MessageResponse, summary="删除用户（管理员）")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("user:write")),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    db_user = crud.user.get(db=db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail=f"用户 ID {user_id} 不存在")
    crud.user.remove(db=db, id=user_id)
    return MessageResponse(message=f"用户 ID {user_id} 已删除", id=user_id)
```

#### 7.3 新建 `app/api/v1/endpoints/roles.py`

```python
"""
路由控制器层：角色管理端点 (api/v1/endpoints/roles.py)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.msg import MessageResponse
from app.schemas.role import RoleCreate, RoleListResponse, RoleResponse, RoleUpdate

router = APIRouter()


@router.get("", response_model=RoleListResponse, summary="获取角色列表")
def read_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("role:read")),
):
    total, roles = crud.role.get_multi_with_permissions(db, skip=skip, limit=limit)
    return RoleListResponse(total=total, roles=roles)


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建角色",
)
def create_role(
    role_in: RoleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("role:write")),
):
    if crud.role.get_by_code(db, code=role_in.code):
        raise HTTPException(status_code=400, detail=f"角色编码 '{role_in.code}' 已存在")
    return crud.role.create_with_permissions(db, obj_in=role_in)


@router.put("/{role_id}", response_model=RoleResponse, summary="更新角色及权限")
def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("role:write")),
):
    db_role = crud.role.get(db=db, id=role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail=f"角色 ID {role_id} 不存在")
    return crud.role.update_with_permissions(db, db_obj=db_role, obj_in=role_in)


@router.delete("/{role_id}", response_model=MessageResponse, summary="删除角色")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("role:write")),
):
    db_role = crud.role.get(db=db, id=role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail=f"角色 ID {role_id} 不存在")
    crud.role.remove(db=db, id=role_id)
    return MessageResponse(message=f"角色 ID {role_id} 已删除", id=role_id)
```

#### 7.4 修改 `app/api/v1/endpoints/tasks.py`

加入三层企业级逻辑：**登录鉴权 + 权限拦截 + 资源归属校验**。

```python
"""
路由控制器层：Task 任务业务端点 (api/v1/endpoints/tasks.py)

本次升级：
1. 所有接口要求登录并携带指定权限；
2. 普通用户只能操作自己 owner_id 的任务，超级管理员不受限制。
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.msg import MessageResponse
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate

router = APIRouter()


def _can_access_task(db_task, current_user: User) -> bool:
    """资源归属判断：超级管理员可访问一切，普通用户只能访问自己的任务"""
    if current_user.is_superuser:
        return True
    return db_task is not None and db_task.owner_id == current_user.id


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建新任务",
)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("task:write")),
):
    """创建任务：归属由后端设置为当前用户"""
    if task_in.category_id is not None:
        db_category = crud.category.get(db=db, id=task_in.category_id)
        if not db_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"指定的分类 ID {task_in.category_id} 不存在",
            )
    return crud.task.create_with_owner(db=db, obj_in=task_in, owner_id=current_user.id)


@router.get("", response_model=TaskListResponse, summary="获取任务列表")
def read_tasks(
    skip: int = Query(0, ge=0, description="分页跳过的前 N 条数"),
    limit: int = Query(20, ge=1, le=100, description="每页返回的最大条数"),
    is_completed: Optional[bool] = Query(None, description="按完成状态筛选"),
    priority: Optional[str] = Query(None, description="按优先级筛选"),
    category_id: Optional[int] = Query(None, description="按分类ID筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("task:read")),
):
    """获取任务列表。普通用户只能看到自己的任务，管理员看到全部。"""
    owner_id = None if current_user.is_superuser else current_user.id
    total, tasks = crud.task.get_multi_with_filter(
        db=db,
        skip=skip,
        limit=limit,
        is_completed=is_completed,
        priority=priority,
        category_id=category_id,
        owner_id=owner_id,
    )
    return TaskListResponse(total=total, tasks=tasks)


@router.get("/{task_id}", response_model=TaskResponse, summary="获取单个任务详情")
def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("task:read")),
):
    db_task = crud.task.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail=f"任务 ID {task_id} 不存在")
    if not _can_access_task(db_task, current_user):
        raise HTTPException(status_code=403, detail="无权访问该任务")
    return db_task


@router.put("/{task_id}", response_model=TaskResponse, summary="更新任务信息")
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("task:write")),
):
    db_task = crud.task.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail=f"任务 ID {task_id} 不存在")
    if not _can_access_task(db_task, current_user):
        raise HTTPException(status_code=403, detail="无权操作该任务")
    if task_update.category_id is not None:
        db_category = crud.category.get(db=db, id=task_update.category_id)
        if not db_category:
            raise HTTPException(
                status_code=400, detail=f"指定的分类 ID {task_update.category_id} 不存在"
            )
    return crud.task.update(db=db, db_obj=db_task, obj_in=task_update)


@router.delete("/{task_id}", response_model=MessageResponse, summary="删除任务")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("task:delete")),
):
    db_task = crud.task.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail=f"任务 ID {task_id} 不存在")
    if not _can_access_task(db_task, current_user):
        raise HTTPException(status_code=403, detail="无权操作该任务")
    crud.task.remove(db=db, id=task_id)
    return MessageResponse(message=f"任务 ID {task_id} 已删除", id=task_id)
```

#### 7.5 分类模块的同类改造（`app/api/v1/endpoints/categories.py`）

分类模块不需要归属校验，只需在创建/更新/删除时加入权限依赖：

```python
from app.api.deps import require_permissions
from app.models.user import User

@router.post("", ..., summary="创建新分类")
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("category:write")),
):
    ...

@router.get("", ..., summary="获取分类列表")
def read_categories(
    ...,
    _: User = Depends(require_permissions("category:read")),
):
    ...
```

### 第 8 步：路由总线与主入口

#### 8.1 修改 `app/api/v1/api.py`

```python
from fastapi import APIRouter

from app.api.v1.endpoints import auth, categories, health, roles, tasks, users

api_router = APIRouter()

api_router.include_router(health.router, tags=["系统"])
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(roles.router, prefix="/roles", tags=["角色"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务"])
api_router.include_router(categories.router, prefix="/categories", tags=["分类"])
```

#### 8.2 修改 `app/main.py`

加入三件事：启动时播种 RBAC 数据、全局异常统管、为后续定时任务预留生命周期钩子。

```python
"""
FastAPI 应用全局入口 (main.py)
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.seed import init_seed_data
from app.db.base import Base
from app.db.session import SessionLocal, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 自动创建尚不存在的表
    Base.metadata.create_all(bind=engine)

    # 2. 初始化 RBAC 种子数据（角色、权限、超级管理员）
    with SessionLocal() as db:
        init_seed_data(db)

    print("✅ [Lifespan] 数据库表与 RBAC 种子数据已就绪")
    yield
    print("🛑 [Lifespan] 应用已正常关闭")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 全局异常统管 ====================
# 数据库唯一键冲突（如用户名/邮箱重复）统一转成 409，避免把堆栈抛给前端
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "数据冲突：用户名、邮箱或编码可能已存在"},
    )


if os.path.exists(settings.STATIC_DIR):
    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")


app.include_router(api_router)
app.include_router(api_router, prefix=settings.API_V1_STR)
```

> 💡 **关键设计决策：为什么要在 `main.py` 做全局异常统管？**
> 业务层无法预判所有数据库异常（例如并发注册时撞了唯一索引）。全局异常处理器保证任何未捕获的 `IntegrityError` 都返回统一的、可读的 409 响应，而不是 500 堆栈。

### 模块一关键设计决策

1. **密码只存哈希、不存明文**：`User` 模型用 `hashed_password`，`UserResponse` 永不暴露该字段。
2. **多对多用关联表 + 复合主键**：`user_roles`、`role_permissions` 用 `(a_id, b_id)` 复合主键，天然防重复。
3. **关联表级联删除**：删除用户/角色时，关联凭证用 `ON DELETE CASCADE` 清理，避免脏数据。
4. **`selectinload` 避免 N+1**：用户 -> 角色 -> 权限三层关系，用 3 条批量 SQL 完成，而不是每加载一个对象都发一条查询。
5. **认证与权限分层**：`get_current_user` 负责"是谁"，`require_permissions` 负责"能不能做"，资源归属校验负责"是不是你的"。
6. **归属由后端写入**：`owner_id` 不放进 `TaskCreate`，避免前端伪造参数访问他人数据。
7. **固定路由优先**：`/users/me` 必须写在 `/users/{user_id}` 前面，避免被路径参数吞掉。
8. **全局异常统管**：数据库唯一冲突等未预期异常统一转成可读的 409。

---

## 3. 模块二：Redis 缓存层

### 第 1 步：环境与配置改造

#### 1.1 修改 `docker-compose.yml`

新增 `redis` 服务，并给 `api` 注入 Redis 配置：

```yaml
services:
  api:
    build: .
    container_name: todo-api
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app
      - ./static:/app/static
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      DATABASE_URL: mysql+pymysql://todo:todo@db:3306/todo?charset=utf8mb4
      SECRET_KEY: change-me-in-production
      REDIS_URL: redis://redis:6379/0          # 【新增】
      CACHE_TTL_SECONDS: 300                   # 【新增】
      FIRST_SUPERUSER: admin                   # 【新增】
      FIRST_SUPERUSER_PASSWORD: Admin123456    # 【新增】
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy             # 【新增】

  db:
    # ... 保持不变 ...

  redis:                                       # 【新增】
    image: redis:7-alpine
    container_name: todo-redis
    ports:
      - "6379:6379"
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  mysql_data:
  redis_data:                                  # 【新增】
```

#### 1.2 修改 `requirements.txt`

```text
fastapi
uvicorn[standard]
sqlalchemy
pydantic
pydantic-settings
PyJWT
bcrypt
python-multipart
email-validator
PyMySQL
pytest
httpx
redis>=5.0.0          # 【新增】Redis 客户端
openpyxl>=3.1.2       # 【新增】Excel 读写（模块三）
APScheduler>=3.10.4   # 【新增】定时任务（模块三）
```

#### 1.3 修改 `app/core/config.py`

在第 4 步已经加入了 `REDIS_URL` 与 `CACHE_TTL_SECONDS`，这里只需确认存在即可。

### 第 2 步：缓存封装（`app/core/cache.py`）

```python
"""
核心层：Redis 缓存封装 (core/cache.py)

职责：
1. 维护全局 Redis 连接（连接池复用）；
2. 提供 get / set / 前缀失效的通用方法；
3. 让调用方（路由层）不需要关心 redis-py 的细节。
"""

import json
from typing import Any, Optional

import redis

from app.core.config import settings

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """返回全局单例 Redis 客户端，连接池内部复用"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_client


def cache_get(client: redis.Redis, key: str) -> Optional[Any]:
    """读取缓存，命中则反序列化，未命中返回 None"""
    raw = client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def cache_set(client: redis.Redis, key: str, value: Any, ttl: int | None = None) -> None:
    """写入缓存并设置 TTL"""
    ttl = ttl or settings.CACHE_TTL_SECONDS
    client.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))


def invalidate_by_prefix(client: redis.Redis, prefix: str) -> int:
    """按前缀批量删除缓存，返回删除的 key 数量"""
    keys = list(client.scan_iter(match=f"{prefix}*", count=1000))
    if keys:
        return client.delete(*keys)
    return 0


def get_redis():
    """FastAPI 依赖注入函数：把 Redis 客户端交给路由"""
    yield get_redis_client()
```

> 💡 **关键设计决策：为什么要加 `decode_responses=True` 和超时？**
> - `decode_responses=True`：返回字符串而不是字节，减少手动 `decode`。
> - `socket_connect_timeout / socket_timeout`：Redis 抖动时快速失败，避免请求被拖死；配合路由层的 `try/except` 降级回 MySQL。

### 第 3 步：改造任务列表接口（Cache-Aside 读路径）

在 `app/api/v1/endpoints/tasks.py` 顶部新增导入，并改造 `read_tasks`：

```python
import json

from app.core.cache import cache_get, cache_set, get_redis_client
from app.core.config import settings


@router.get("", response_model=TaskListResponse, summary="获取任务列表")
def read_tasks(
    skip: int = Query(0, ge=0, description="分页跳过的前 N 条数"),
    limit: int = Query(20, ge=1, le=100, description="每页返回的最大条数"),
    is_completed: Optional[bool] = Query(None, description="按完成状态筛选"),
    priority: Optional[str] = Query(None, description="按优先级筛选"),
    category_id: Optional[int] = Query(None, description="按分类ID筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("task:read")),
):
    """带 Redis 缓存的任务列表查询（Cache-Aside）"""
    owner_id = None if current_user.is_superuser else current_user.id

    # 缓存键必须包含用户与全部筛选条件，防止串数据
    cache_key = (
        f"tasks:list:v1:{current_user.id}:{skip}:{limit}:"
        f"{is_completed}:{priority}:{category_id}:{owner_id}"
    )
    redis_client = get_redis_client()

    # 读路径：先查缓存
    try:
        cached = cache_get(redis_client, cache_key)
        if cached is not None:
            return cached
    except Exception:
        # 缓存故障降级：继续走数据库，不影响主业务
        pass

    # 回源数据库
    total, tasks = crud.task.get_multi_with_filter(
        db=db,
        skip=skip,
        limit=limit,
        is_completed=is_completed,
        priority=priority,
        category_id=category_id,
        owner_id=owner_id,
    )
    response = TaskListResponse(total=total, tasks=tasks).model_dump(mode="json")

    # 写路径：回写缓存，带 TTL
    try:
        cache_set(redis_client, cache_key, response, ttl=settings.CACHE_TTL_SECONDS)
    except Exception:
        pass

    return response
```

> 💡 **关键设计决策：为什么缓存值要 `model_dump(mode="json")`？**
> Pydantic 的 `mode="json"` 会把 `datetime` 转成字符串，把 ORM 对象转成可 JSON 序列化的字典。直接 `json.dumps` 一个 ORM 对象会报错。

### 第 4 步：写操作缓存失效

在 `tasks.py` 中新增一个失效辅助函数，并在创建/更新/删除后调用：

```python
from app.core.cache import get_redis_client, invalidate_by_prefix


def _invalidate_task_list_cache() -> None:
    """任何写操作后，清空任务列表缓存"""
    try:
        invalidate_by_prefix(get_redis_client(), "tasks:list:")
    except Exception:
        # Redis 失效失败也不阻塞写库结果
        pass
```

然后修改写接口：

```python
@router.post("", response_model=TaskResponse, status_code=201, summary="创建新任务")
def create_task(...):
    # ... 校验分类 ...
    result = crud.task.create_with_owner(db=db, obj_in=task_in, owner_id=current_user.id)
    _invalidate_task_list_cache()  # 【新增】
    return result


@router.put("/{task_id}", response_model=TaskResponse, summary="更新任务信息")
def update_task(...):
    # ... 404 / 403 / 分类校验 ...
    result = crud.task.update(db=db, db_obj=db_task, obj_in=task_update)
    _invalidate_task_list_cache()  # 【新增】
    return result


@router.delete("/{task_id}", response_model=MessageResponse, summary="删除任务")
def delete_task(...):
    # ... 404 / 403 校验 ...
    crud.task.remove(db=db, id=task_id)
    _invalidate_task_list_cache()  # 【新增】
    return MessageResponse(message=f"任务 ID {task_id} 已删除", id=task_id)
```

### 模块二关键设计决策

1. **Cache-Aside（旁路缓存）**：缓存由应用自己管理，Redis 只做加速，MySQL 仍是唯一事实源。
2. **写后失效顺序**：**先更新数据库，后删除缓存**。这样即使并发，也不会出现"数据库已是新值、缓存还是旧值且长期不失效"的最坏情况。
3. **缓存键包含租户与筛选条件**：防止 A 用户的列表被 B 用户命中。
4. **故障降级**：所有 Redis 操作都包 `try/except`，Redis 挂了服务仍可用，只是慢一点。
5. **TTL 兜底**：即使有遗漏的失效，缓存也会在 300 秒后自动过期。
6. **序列化边界清晰**：入库前用 `model_dump(mode="json")` 转成 JSON 友好的字典，读取时直接返回字典，交给 `response_model` 校验。

> 进阶：生产环境可用"版本号/命名空间"代替 `scan_iter` 全量删除，进一步降低大 key 场景下的失效成本；本教程先用 `scan_iter` 便于理解。

---

## 4. 模块三（扩展）：Excel 批量导入导出 + 定时统计

> 该模块覆盖"复杂业务与数据处理"方向，重点体会**事务控制、批量插入、文件解析、自动化调度**。代码给出完整可运行骨架，注释说明关键点。

### 4.1 需求与接口

| 方法 | 接口路径 | 说明 |
| :--- | :--- | :--- |
| `GET` | `/api/v1/tasks/export` | 导出当前用户可见任务为 Excel |
| `POST` | `/api/v1/tasks/import` | 上传 Excel，批量导入任务（整批事务） |
| `GET` | `/api/v1/stats/task-daily` | 查询每日任务统计 |

### 4.2 新增模型：`app/models/task_statistic.py`

```python
"""
ORM 模型层：TaskDailyStatistic 每日任务统计表 (models/task_statistic.py)
"""

from sqlalchemy import Column, Date, DateTime, Integer
from sqlalchemy.sql import func

from app.db.base_class import Base


class TaskDailyStatistic(Base):
    __tablename__ = "task_daily_statistics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    stat_date = Column(Date, nullable=False, unique=True, index=True, comment="统计日期")
    total_tasks = Column(Integer, default=0, nullable=False, comment="截止当日任务总数")
    completed_tasks = Column(Integer, default=0, nullable=False, comment="已完成任务总数")
    created_today = Column(Integer, default=0, nullable=False, comment="当日新增任务数")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="生成时间")
```

在 `app/models/__init__.py` 和 `app/db/base.py` 中分别导入该模型（否则不会建表）。

### 4.3 Excel 服务：`app/services/task_excel.py`

```python
"""
服务层：任务 Excel 导入导出 (services/task_excel.py)

企业里通常把"文件解析 + 业务校验 + 批量落库"放在 service 层，
让 endpoint 保持薄薄一层，只负责接收上传文件。
"""

import io

from fastapi import HTTPException
from openpyxl import Workbook, load_workbook
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.task import Task

EXPORT_COLUMNS = ["标题", "描述", "优先级", "是否完成", "分类ID"]


def export_tasks_to_xlsx(tasks: list[Task]) -> bytes:
    """把任务列表写入内存中的 xlsx 并返回二进制内容"""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "任务"
    worksheet.append(EXPORT_COLUMNS)

    for task in tasks:
        worksheet.append(
            [
                task.title,
                task.description,
                task.priority,
                task.is_completed,
                task.category_id,
            ]
        )

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def import_tasks_from_xlsx(db: Session, content: bytes, owner_id: int) -> dict:
    """解析 Excel 并批量导入。整批成功才提交，任何异常回滚。"""
    workbook = load_workbook(filename=io.BytesIO(content), read_only=True)
    worksheet = workbook.active
    rows = list(worksheet.iter_rows(min_row=2, values_only=True))

    # 预加载分类，避免在循环里反复查库（避免 N+1）
    categories = {c.id: c for c in db.query(Category).all()}

    batch: list[Task] = []
    errors: list[str] = []

    for index, row in enumerate(rows, start=2):
        if row is None or all(cell is None for cell in row):
            continue

        title = (row[0] or "").strip() if len(row) > 0 else ""
        description = (row[1] or "").strip() if len(row) > 1 else ""
        priority = (row[2] or "medium").strip().lower() if len(row) > 2 else "medium"
        is_completed = bool(row[3]) if len(row) > 3 else False
        category_id = row[4] if len(row) > 4 else None

        # 行级校验：把能提前发现的错误收集起来，最后一次性返回
        if not title:
            errors.append(f"第 {index} 行：标题不能为空")
            continue
        if priority not in {"low", "medium", "high"}:
            errors.append(f"第 {index} 行：优先级必须为 low/medium/high")
            continue

        parsed_category_id = None
        if category_id is not None and str(category_id).strip() != "":
            try:
                parsed_category_id = int(category_id)
            except (TypeError, ValueError):
                errors.append(f"第 {index} 行：分类ID 不是有效整数")
                continue
            if parsed_category_id not in categories:
                errors.append(f"第 {index} 行：分类ID {parsed_category_id} 不存在")
                continue

        batch.append(
            Task(
                title=title,
                description=description or None,
                priority=priority,
                is_completed=is_completed,
                category_id=parsed_category_id,
                owner_id=owner_id,
            )
        )

    imported = 0
    if batch:
        try:
            db.add_all(batch)   # 批量插入
            db.commit()          # 整批事务提交
            imported = len(batch)
        except Exception:
            db.rollback()        # 失败回滚，避免半批导入
            raise HTTPException(status_code=500, detail="导入失败，事务已回滚")

    return {
        "total_rows": len(rows),
        "imported": imported,
        "skipped": len(errors),
        "errors": errors[:100],
    }
```

> 💡 **关键设计决策：批量导入为什么"整批提交、失败回滚"？**
> 企业里导入数据最怕"导一半成功一半失败"，产生不可追踪的脏数据。要么全部成功，要么全部回滚，边界清晰。

### 4.4 在 `tasks.py` 中新增导入导出接口

> 注意：`/export` 和 `/import` 必须写在 `/{task_id}` 之前，否则路径参数会先匹配。

```python
import io

from fastapi import File, UploadFile
from fastapi.responses import StreamingResponse

from app.services.task_excel import export_tasks_to_xlsx, import_tasks_from_xlsx


@router.get("/export", summary="导出任务 Excel")
def export_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("task:read")),
):
    owner_id = None if current_user.is_superuser else current_user.id
    _, tasks = crud.task.get_multi_with_filter(
        db=db, skip=0, limit=10000, owner_id=owner_id
    )
    content = export_tasks_to_xlsx(tasks)
    headers = {"Content-Disposition": "attachment; filename=tasks.xlsx"}
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/import", summary="批量导入任务 Excel")
def import_tasks(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("task:write")),
):
    content = file.file.read()
    result = import_tasks_from_xlsx(db, content, owner_id=current_user.id)
    _invalidate_task_list_cache()
    return result
```

### 4.5 定时统计服务：`app/services/statistics.py`

```python
"""
服务层：每日任务统计（模拟 RPA 自动化场景） (services/statistics.py)
"""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.task_statistic import TaskDailyStatistic


def run_daily_statistics(db: Session, stat_date: date) -> TaskDailyStatistic:
    """聚合某一天的统计数据并 upsert 到统计表"""
    created_today = (
        db.query(func.count(Task.id))
        .filter(func.date(Task.created_at) == stat_date)
        .scalar()
        or 0
    )
    total_tasks = db.query(func.count(Task.id)).scalar() or 0
    completed_tasks = (
        db.query(func.count(Task.id)).filter(Task.is_completed.is_(True)).scalar() or 0
    )

    stat = (
        db.query(TaskDailyStatistic)
        .filter(TaskDailyStatistic.stat_date == stat_date)
        .first()
    )
    if not stat:
        stat = TaskDailyStatistic(stat_date=stat_date)
        db.add(stat)

    stat.total_tasks = total_tasks
    stat.completed_tasks = completed_tasks
    stat.created_today = created_today
    db.commit()
    db.refresh(stat)
    return stat
```

### 4.6 在 `main.py` 中启动定时任务

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.statistics import run_daily_statistics


scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def _run_daily_statistics_job() -> None:
    db = SessionLocal()
    try:
        run_daily_statistics(
            db, stat_date=datetime.now(ZoneInfo("Asia/Shanghai")).date()
        )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        init_seed_data(db)

    # 每天 00:05 执行一次统计任务
    scheduler.add_job(
        _run_daily_statistics_job,
        CronTrigger(hour=0, minute=5),
        id="daily_task_statistics",
        replace_existing=True,
    )
    scheduler.start()

    print("✅ [Lifespan] 数据库、RBAC 种子数据与定时任务已就绪")
    yield

    scheduler.shutdown(wait=False)
    print("🛑 [Lifespan] 应用已正常关闭")
```

### 4.7 统计查询接口（可选）

新增 `app/api/v1/endpoints/stats.py`：

```python
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import require_permissions
from app.db.session import get_db
from app.models.task_statistic import TaskDailyStatistic
from app.models.user import User

router = APIRouter()


@router.get("/task-daily", summary="查询每日任务统计")
def read_daily_stats(
    stat_date: date,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("task:read")),
):
    stat = (
        db.query(TaskDailyStatistic)
        .filter(TaskDailyStatistic.stat_date == stat_date)
        .first()
    )
    if stat is None:
        raise HTTPException(status_code=404, detail=f"{stat_date} 暂无统计数据")
    return {
        "stat_date": stat.stat_date.isoformat(),
        "total_tasks": stat.total_tasks,
        "completed_tasks": stat.completed_tasks,
        "created_today": stat.created_today,
    }
```

并在 `api.py` 中挂载：

```python
api_router.include_router(stats.router, prefix="/stats", tags=["统计"])
```

### 模块三关键设计决策

1. **服务层隔离文件解析**：Excel 读写、统计聚合不放路由层，保持控制器轻量。
2. **整批事务导入**：批量 `add_all` + 单次 `commit`，失败 `rollback`。
3. **行级校验先行**：能提前发现的错误先收集，一次返回给用户，避免反复上传。
4. **预加载分类字典**：导入循环里不查库，避免 N+1。
5. **定时任务用 `BackgroundScheduler`**：随 FastAPI 生命周期启停，避免独立进程带来的部署复杂度。

---

## 5. 环境与基础设施同步汇总

### 5.1 完整 `docker-compose.yml`（改造后）

```yaml
services:
  api:
    build: .
    container_name: todo-api
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app
      - ./static:/app/static
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      DATABASE_URL: mysql+pymysql://todo:todo@db:3306/todo?charset=utf8mb4
      SECRET_KEY: change-me-in-production
      REDIS_URL: redis://redis:6379/0
      CACHE_TTL_SECONDS: 300
      FIRST_SUPERUSER: admin
      FIRST_SUPERUSER_PASSWORD: Admin123456
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  db:
    image: mysql:8.0
    container_name: todo-db
    command: --default-authentication-plugin=mysql_native_password
    environment:
      MYSQL_DATABASE: todo
      MYSQL_USER: todo
      MYSQL_PASSWORD: todo
      MYSQL_ROOT_PASSWORD: 123456
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 -u root -p$$MYSQL_ROOT_PASSWORD --silent"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: todo-redis
    ports:
      - "6379:6379"
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  mysql_data:
  redis_data:
```

### 5.2 完整 `requirements.txt`（改造后）

```text
fastapi
uvicorn[standard]
sqlalchemy
pydantic
pydantic-settings
PyJWT
bcrypt
python-multipart
email-validator
PyMySQL
pytest
httpx
redis>=5.0.0
openpyxl>=3.1.2
APScheduler>=3.10.4
```

### 5.3 数据库迁移速查

如果还没有 `users` 等新表，最省事的方式是让 `lifespan` 自动建表：

```bash
docker compose up --build
```

已有 `tasks` 表需要保留数据时，不要 `docker compose down -v`，而是执行模块一第 1 步的 `ALTER TABLE` SQL（或 Alembic 迁移）后重启。

---

## 6. 验证与全流程测试

### 6.1 启动与初始化

```bash
docker compose up --build -d
docker compose logs -f api
```

看到类似日志即表示种子数据初始化成功：

```text
✅ [Lifespan] 数据库、RBAC 种子数据与定时任务已就绪
```

### 6.2 登录拿 Token

初始超级管理员：`admin / Admin123456`。

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123456"}'
```

响应：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### 6.3 验证路由拦截

不带 Token 访问任务列表，应返回 401：

```bash
curl -i http://localhost:8000/api/v1/tasks
```

带 Token 访问，应返回 200：

```bash
curl http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer <你的access_token>"
```

### 6.4 验证缓存

连续请求两次任务列表，第二次会命中 Redis：

```bash
docker compose exec redis redis-cli
> keys tasks:list:*
```

创建或更新任务后，再执行 `keys tasks:list:*`，应看到缓存已被失效。

### 6.5 验证 Excel 导入导出

```bash
# 导出
curl http://localhost:8000/api/v1/tasks/export \
  -H "Authorization: Bearer <token>" -o tasks.xlsx

# 导入（使用一个标准 xlsx 文件）
curl -X POST http://localhost:8000/api/v1/tasks/import \
  -H "Authorization: Bearer <token>" \
  -F "file=@tasks.xlsx"
```

### 6.6 验证定时统计

可以临时把 Cron 时间改到当前分钟附近触发，或手动执行一次统计函数，再查询：

```bash
curl "http://localhost:8000/api/v1/stats/task-daily?stat_date=2026-08-26" \
  -H "Authorization: Bearer <token>"
```

> ⚠️ 前端部分本教程未写。前端要接入时，登录后把 `access_token` 存起来，每个请求加 `Authorization: Bearer <token>` 头即可。

---

## 7. 避坑指南与最佳实践（FAQ）

### Q1：为什么我新增了 User 模型，MySQL 里却没有 `users` 表？
> 💡 大概率是忘了在 `app/db/base.py` 里 `from app.models.user import User`。`Base.metadata` 只认识被导入过的模型。

### Q2：为什么 `tasks` 加了 `owner_id` 后，旧接口查询不到历史任务？
> 💡 历史任务的 `owner_id` 是 `NULL`。普通用户查询条件 `owner_id = 当前用户ID` 不会命中它们。按模块一第 1 步执行回填 SQL，把历史任务归属到 `admin` 即可。

### Q3：`scan_iter` 按前缀删缓存会不会误删？
> 💡 只要前缀设计清晰（如 `tasks:list:` 只用于任务列表缓存），就不会误删其他业务的 key。生产环境数据量大时，可升级为"缓存版本号"方案。

### Q4：Redis 连不上，服务会挂吗？
> 💡 不会。所有 Redis 调用都包了 `try/except`，读路径自动回源 MySQL，写路径忽略失效失败。这是企业里"缓存可降级"的基本要求。

### Q5：为什么 `/users/me` 返回 404 或匹配到了数字参数？
> 💡 检查路由定义顺序。固定路径 `/me` 必须在 `/{user_id}` 之前声明，否则 FastAPI 会把 `me` 当作 `user_id`。

### Q6：Alembic 和 `create_all()` 可以同时用吗？
> 💡 生产环境推荐只保留 Alembic，`create_all()` 只在开发环境兜底。两者同时用于同一库会互相干扰版本管理。本教程为了最小成本保留了 `create_all()`，实际入职后应切换到 Alembic。

---

## 8. 总结清单（Checklist）

开发企业级"身份 + 权限 + 缓存"功能时，按下面清单自查：

- [ ] **1. 数据库设计**：新增表结构清晰；已有表用 `ALTER TABLE` / Alembic 保留旧数据。
- [ ] **2. `models/`**：多对多用关联表 + 复合主键，集合关系用 `selectinload`，并更新 `models/__init__.py`。
- [ ] **3. `db/base.py`**：导入所有新模型，确保建表可被扫描到。
- [ ] **4. `schemas/`**：请求 DTO 与响应 VO 分离；响应模型绝不暴露密码哈希。
- [ ] **5. `core/`**：配置集中管理；种子数据幂等。
- [ ] **6. `crud/`**：事务控制、批量查询、避免 N+1；更新 `crud/__init__.py`。
- [ ] **7. `api/deps.py`**：`get_current_user` + `require_permissions` + `require_roles`。
- [ ] **8. `endpoints/`**：登录、用户、角色、任务鉴权与归属校验；固定路径写在动态路径前。
- [ ] **9. `api.py` / `main.py`**：注册路由、启动种子、全局异常、缓存与定时任务。
- [ ] **10. `docker-compose.yml` / `requirements.txt`**：Redis 服务与新增依赖齐全。
- [ ] **11. 验证**：登录、鉴权、缓存命中/失效、Excel 导入导出、定时统计。
