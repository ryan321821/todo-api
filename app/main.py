"""
FastAPI 应用入口

包含：
- 应用生命周期管理（启动时自动创建数据表）
- 健康检查接口
- 任务（Task）的增删改查接口
"""
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Task
from .schemas import (
    MessageResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时自动创建数据库表（如果还不存在）"""
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表已创建/验证")
    yield
    print("🛑 应用关闭")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="迷你任务备忘录 API",
    description="一个基于 FastAPI + Docker + MySQL 的实战示例项目",
    version="1.0.0",
    lifespan=lifespan,
)

# 挂载静态文件目录：把项目根目录的 static 文件夹暴露到 /static 路径
# 之后浏览器访问 http://localhost:8000/static/index.html 就能打开前端页面
app.mount("/static", StaticFiles(directory="static"), name="static")


# ==================== 健康检查 ====================


@app.get("/", tags=["系统"])
def root():
    """根路径：返回欢迎信息"""
    return {"message": "🚀 迷你任务备忘录 API 正在运行", "docs": "/docs"}


@app.get("/healthz", tags=["系统"])
def healthz():
    """进程级健康检查（原接口，保留）"""
    return {"status": "ok"}


@app.get("/health", tags=["系统"])
def health_check(db: Session = Depends(get_db)):
    """数据库连接健康检查"""
    try:
        db.execute(func.now())
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"数据库连接异常: {str(e)}")


# ==================== 任务 CRUD 接口 ====================


@app.post("/tasks", response_model=TaskResponse, status_code=201, tags=["任务"])
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """创建新任务"""
    db_task = Task(
        title=task.title,
        description=task.description,
        priority=task.priority,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)  # 刷新，拿到数据库生成的主键 id 和时间戳
    return db_task


@app.get("/tasks", response_model=TaskListResponse, tags=["任务"])
def read_tasks(
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(10, ge=1, le=100, description="返回条数"),
    is_completed: bool | None = Query(None, description="按完成状态筛选"),
    priority: str | None = Query(None, description="按优先级筛选"),
    db: Session = Depends(get_db),
):
    """获取任务列表，支持分页和筛选"""
    query = db.query(Task)

    # 按完成状态筛选（可选）
    if is_completed is not None:
        query = query.filter(Task.is_completed == is_completed)
    # 按优先级筛选（可选）
    if priority is not None:
        query = query.filter(Task.priority == priority)

    # 按创建时间倒序（最新的排最前）
    query = query.order_by(Task.created_at.desc())

    total = query.count()          # 符合条件的总数
    tasks = query.offset(skip).limit(limit).all()  # 分页取数据

    return TaskListResponse(total=total, tasks=tasks)


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["任务"])
def read_task(task_id: int, db: Session = Depends(get_db)):
    """获取单个任务详情"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 ID {task_id} 不存在")
    return task


@app.put("/tasks/{task_id}", response_model=TaskResponse, tags=["任务"])
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    """更新任务（只更新传入的字段）"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 ID {task_id} 不存在")

    # 只取请求里"确实传了"的字段，None 的忽略
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", response_model=MessageResponse, tags=["任务"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 ID {task_id} 不存在")

    db.delete(task)
    db.commit()
    return MessageResponse(message=f"任务 ID {task_id} 已删除")