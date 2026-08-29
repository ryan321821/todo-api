"""
数据持久层：Task 专属 CRUD 数据访问对象 (crud/crud_task.py)

【为什么需要这个文件？】
继承通用 CRUDBase 获取标准增删改查能力，并专门为 Task 业务
拓展定制化的查询方法（如多条件组合筛选、倒序排列与总数统计）。
【本次升级】：支持按 category_id 分类筛选。
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


class CRUDTask(CRUDBase[Task, TaskCreate, TaskUpdate]):
    """
    Task 专属数据操作类
    """

    """按筛选条件批量查询多条数据"""

    def get_multi_with_filter(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 20,
        is_completed: Optional[bool] = None,
        priority: Optional[str] = None,
        category_id: Optional[int] = None,
    ) -> tuple[int, list[Task]]:
        """
        获取任务列表，支持多条件筛选、时间倒序排列与总数统计

        :param db: 数据库会话
        :param skip: 分页跳过条数
        :param limit: 每页返回条数
        :param is_completed: 是否完成筛选（None 则不筛选）
        :param priority: 优先级筛选（None 则不筛选）
        :param category_id: 分类ID筛选（None 则不筛选）
        :return: (符合条件的总条数, 当前分页任务列表)
        """
        query = db.query(self.model)

        # 动态筛选：按完成状态过滤
        if is_completed is not None:
            query = query.filter(self.model.is_completed == is_completed)

        # 动态筛选：按优先级过滤
        if priority is not None:
            query = query.filter(self.model.priority == priority)

        # 动态筛选：按分类ID过滤
        if category_id is not None:
            query = query.filter(self.model.category_id == category_id)

        # 排序：按创建时间倒序（最新的排最前）
        query = query.order_by(self.model.created_at.desc())

        # 统计符合筛选条件的总记录数（用于前端展示和分页计算）
        total = query.count()

        # 取当前页数据
        tasks = query.offset(skip).limit(limit).all()

        return total, tasks

    def create_with_owner(
        self, db: Session, *, obj_in: TaskCreate, owner_id: int
    ) -> Task:
        """
        创建任务，把归属用户由后端写入，避免前端伪造 owner_id
        """
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data, owner_id=owner_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


# 实例化 Task 的 CRUD 单例对象，外部直接调用 crud.task.xxx
task = CRUDTask(Task)
