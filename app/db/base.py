"""
数据库层：ORM 模型统一发现与元数据注册中心 (db/base.py)

【为什么需要这个文件？】
SQLAlchemy 的 Base.metadata.create_all() 和 Alembic 数据库迁移工具
在自动建表或生成迁移脚本时，必须先在内存中"看到"所有的 ORM 模型类。
通过在这个文件里把所有的 models 集中导入一次，就能确保所有数据表被自动识别并创建。
"""

# 导入公共 Base 基类
from app.db.base_class import Base  # noqa: F401

"""
noqa: F401 是给代码检查工具（如 Flake8、VS Code、PyCharm）看的注释指令
意思是：“忽略『导入了但未使用』的警告”。
"""

# 集中导入所有 ORM 模型类（未来新增其他模型如 User、Note 都在这里加一行即可）
from app.models.category import Category  # noqa: F401
from app.models.permission import Permission  # noqa: F401
from app.models.role import Role  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.user import User  # noqa: F401
