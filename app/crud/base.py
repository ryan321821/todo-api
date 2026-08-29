"""
数据持久层：通用 CRUD 泛型基类 (crud/base.py)

【为什么需要这个文件？】
在真实项目中，每张表的"按 ID 查、分页查、增、改、删"逻辑几乎 90% 是重复的。
通过定义泛型基类 CRUDBase：
1. 一次性实现标准的增删改查方法，子类直接继承即可使用；
2. 彻底将 SQL/ORM 操作与 FastAPI 路由层解耦，提高代码复用率。
"""

from typing import Any, Generic, Optional, Type, TypeVar, Union
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base_class import Base

# 定义泛型类型变量：
# - ModelType: 继承自 Base 的 ORM 模型类（如 Task）
# - CreateSchemaType: 继承自 BaseModel 的创建数据模型（如 TaskCreate）
# - UpdateSchemaType: 继承自 BaseModel 的更新数据模型（如 TaskUpdate）
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    通用增删改查基类
    """

    def __init__(self, model: Type[ModelType]):
        """
        初始化 CRUD 对象
        :param model: 绑定的 SQLAlchemy ORM 模型类
        """
        self.model = model

    def get(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """
        根据主键 ID 查询单条记录
        对应 SQL: SELECT * FROM 表名 WHERE id = :id LIMIT 1;
        """
        return db.query(self.model).filter(self.model.id == id).first()

    # *：表示强制要求 * 后面的所有参数必须使用“关键字参数（Keyword Arguments）”的形式进行传递

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        """
        分页查询多条记录
        对应 SQL: SELECT * FROM 表名 LIMIT :limit OFFSET :skip;
        """
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        创建新记录
        对应 SQL: INSERT INTO 表名 (...) VALUES (...);
        """
        # model_dump()方法将 Pydantic 请求模型转为 Python 字典
        obj_in_data = obj_in.model_dump()
        # 解包字典创建 ORM 模型实例
        db_obj = self.model(**obj_in_data)  # **：作用是字典解包，展开为关键字参数
        db.add(db_obj)
        db.commit()  # 提交事务写入 MySQL
        db.refresh(db_obj)  # 刷新对象以获取数据库生成的自增 ID 和默认时间戳
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, dict[str, Any]],
    ) -> ModelType:
        """
        更新已有记录（只修改传入的有效字段）
        对应 SQL: UPDATE 表名 SET 字段=值 WHERE id = :id;
        """
        # 如果传入的是 Pydantic 模型，只获取用户显式设置了值的字段（exclude_unset=True）
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # 动态更新属性
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.commit()  # 提交事务
        db.refresh(db_obj)  # 刷新获取最新的 updated_at 时间戳
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[ModelType]:
        """
        根据主键 ID 物理删除记录
        对应 SQL: DELETE FROM 表名 WHERE id = :id;
        """
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
