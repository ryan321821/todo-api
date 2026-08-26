"""
路由控制器层：Task 任务业务端点 (api/v1/endpoints/tasks.py)

【为什么需要这个文件？】
专注于处理任务模块的 HTTP 请求与响应：
1. 接收客户端输入并由 Pydantic 进行入参类型与格式校验；
2. 通过 Depends(get_db) 注入数据库会话；
3. 调用 crud.task 层的持久化方法执行具体数据操作；
4. 进行统一的异常处理（如 404 Not Found）并返回标准响应模型。
【本次升级】：支持通过 category_id 进行多维筛选。
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_db
from app.schemas.msg import MessageResponse
from app.schemas.task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate

# 实例化当前模块的子路由器
router = APIRouter()


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建新任务",
)
def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    """
    创建新任务：
    - **title**: 任务标题（必填）
    - **description**: 任务详细描述（选填）
    - **priority**: 优先级（low/medium/high，默认 medium）
    - **category_id**: 所属分类ID（选填）
    """
    # 如果指定了分类，检查分类是否存在
    if task_in.category_id is not None:
        db_category = crud.category.get(db=db, id=task_in.category_id)
        if not db_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"指定的分类 ID {task_in.category_id} 不存在",
            )
    return crud.task.create(db=db, obj_in=task_in)


@router.get("", response_model=TaskListResponse, summary="获取任务列表")
def read_tasks(
    skip: int = Query(0, ge=0, description="分页跳过的前 N 条数"),
    limit: int = Query(20, ge=1, le=100, description="每页返回的最大条数"),
    is_completed: Optional[bool] = Query(None, description="按完成状态筛选 (true/false)"),
    priority: Optional[str] = Query(None, description="按优先级筛选 (low/medium/high)"),
    category_id: Optional[int] = Query(None, description="按分类ID筛选"),
    db: Session = Depends(get_db),
):
    """
    获取任务列表：
    - 支持分页（skip, limit）
    - 支持动态筛选（is_completed, priority, category_id）
    - 默认按创建时间倒序排列
    """
    total, tasks = crud.task.get_multi_with_filter(
        db=db,
        skip=skip,
        limit=limit,
        is_completed=is_completed,
        priority=priority,
        category_id=category_id,
    )
    return TaskListResponse(total=total, tasks=tasks)


@router.get("/{task_id}", response_model=TaskResponse, summary="获取单个任务详情")
def read_task(task_id: int, db: Session = Depends(get_db)):
    """
    根据任务 ID 查询单个任务详情：
    - 若不存在则返回 404 错误
    """
    db_task = crud.task.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 ID {task_id} 不存在",
        )
    return db_task


@router.put("/{task_id}", response_model=TaskResponse, summary="更新任务信息")
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
):
    """
    根据任务 ID 更新任务：
    - 仅更新请求体中显式传入的字段（支持局部更新）
    - 若任务不存在则返回 404 错误
    """
    db_task = crud.task.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 ID {task_id} 不存在",
        )
    if task_update.category_id is not None:
        db_category = crud.category.get(db=db, id=task_update.category_id)
        if not db_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"指定的分类 ID {task_update.category_id} 不存在",
            )
    return crud.task.update(db=db, db_obj=db_task, obj_in=task_update)


@router.delete(
    "/{task_id}",
    response_model=MessageResponse,
    summary="删除任务",
)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    根据任务 ID 物理删除任务：
    - 若任务不存在则返回 404 错误
    - 删除成功后返回通用提示消息
    """
    db_task = crud.task.get(db=db, id=task_id)
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 ID {task_id} 不存在",
        )
    crud.task.remove(db=db, id=task_id)
    return MessageResponse(message=f"任务 ID {task_id} 已删除", id=task_id)
