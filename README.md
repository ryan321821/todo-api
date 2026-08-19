# FastAPI + Docker + MySQL 全栈实战项目

## 📋 项目概述

本项目通过**迷你任务备忘录（Task Memo）**场景，串联 Docker、FastAPI、Pydantic、SQLAlchemy、MySQL 等核心技术栈，帮助初学者建立"端到端数据流转与架构协同"的全局观。

---

## 1. 场景描述与架构协同图

### 业务场景

实现一个轻量级任务备忘录系统，支持：
- 创建任务（标题、描述、优先级）
- 查询任务列表（支持按状态筛选）
- 查询单个任务详情
- 更新任务状态（完成/未完成）
- 删除任务

### 数据流向与端口映射

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              客户端                                          │
│                    (浏览器 / Postman / curl)                                  │
│                              │                                               │
│                              │ HTTP 请求                                      │
│                              │ (访问 localhost:8000)                           │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                    Docker Host (宿主机)                                  │  │
│  │                                                                         │  │
│  │    ┌──────────────────────────────────────────────────────────────┐     │  │
│  │    │                  Docker Network (bridge)                      │     │  │
│  │    │                                                               │     │  │
│  │    │   ┌─────────────────────┐     ┌─────────────────────┐        │     │  │
│  │    │   │   web 容器          │     │   db 容器            │        │     │  │
│  │    │   │   (FastAPI App)     │     │   (MySQL 8.0)        │        │     │  │
│  │    │   │                     │     │                      │        │     │  │
│  │    │   │  端口: 8000:8000    │     │  端口: 3306:3306     │        │     │  │
│  │    │   │                     │     │                      │        │     │  │
│  │    │   │  ┌───────────────┐  │     │  ┌───────────────┐   │        │     │  │
│  │    │   │  │  FastAPI       │  │     │  │  MySQL        │   │        │     │  │
│  │    │   │  │  应用服务器    │──┼─────┼──▶│  数据库服务    │   │        │     │  │
│  │    │   │  │  :8000         │  │ TCP │  │  :3306        │   │        │     │  │
│  │    │   │  └───────────────┘  │     │  └───────────────┘   │        │     │  │
│  │    │   │                     │     │                      │        │     │  │
│  │    │   │  镜像: python:3.11  │     │  镜像: mysql:8.0     │        │     │  │
│  │    │   └─────────────────────┘     └─────────────────────┘        │     │  │
│  │    │                                                               │     │  │
│  │    │   通过服务名 "db" 通信 (DNS 解析)                               │     │  │
│  │    └──────────────────────────────────────────────────────────────┘     │  │
│  │                                                                         │  │
│  │    数据卷映射:                                                           │  │
│  │    - ./app → /app/app (代码热更新)                                       │  │
│  │    - mysql_data → /var/lib/mysql (数据持久化)                             │  │
│  │                                                                         │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**关键点说明：**
- **端口映射**：宿主机 `8000` → 容器 `8000`（FastAPI），宿主机 `3306` → 容器 `3306`（MySQL）
- **容器间通信**：FastAPI 容器通过服务名 `db`（Docker DNS）连接 MySQL，无需使用宿主机 IP
- **数据持久化**：MySQL 数据存储在 Docker Volume `mysql_data` 中，容器重启后数据不丢失

---

## 2. 完整项目工程目录

```
python web fastAPI Project/
├── app/
│   ├── __init__.py          # 空文件，标识为 Python 包
│   ├── main.py              # FastAPI 应用入口
│   ├── database.py          # 数据库连接配置
│   ├── models.py            # SQLAlchemy ORM 模型
│   └── schemas.py           # Pydantic 数据验证模型
├── requirements.txt         # Python 依赖
├── Dockerfile               # Docker 镜像构建文件
├── docker-compose.yml       # Docker Compose 编排文件
└── README.md                # 项目说明文档（本文件）
```

---

## 3. 核心代码清单

### 3.1 requirements.txt

```txt
fastapi==0.109.2
uvicorn[standard]==0.27.1
sqlalchemy==2.0.27
pymysql==1.1.0
pydantic==2.6.1
python-dotenv==1.0.1
```

---

### 3.2 app/__init__.py

```python
# 空文件，标识 app 目录为 Python 包
```

---

### 3.3 app/database.py

```python
"""
数据库连接配置模块

核心知识点：
- SQLAlchemy 引擎创建
- SessionLocal 会话工厂
- 依赖注入 get_db 实现数据库会话的自动管理
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 数据库连接 URL
# 格式: mysql+pymysql://用户名:密码@主机:端口/数据库名
# 注意：容器内使用服务名 "db" 作为主机，而非 localhost
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:123456@db:3306/task_memo"

# 创建数据库引擎
# - pool_pre_ping=True: 每次使用前检测连接是否有效，避免使用断开的连接
# - pool_recycle=3600: 连接回收时间（秒），防止 MySQL 超时断开
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

# 创建会话工厂
# 每次调用 SessionLocal() 会生成一个新的数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建 ORM 模型的基类
# 所有数据库模型都继承自 Base
Base = declarative_base()


def get_db():
    """
    依赖注入函数：获取数据库会话

    使用 yield 实现会话的自动关闭：
    - yield 之前：创建会话并提供给路由函数
    - yield 之后：请求结束后自动关闭会话（即使发生异常）

    用法（在路由中）：
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### 3.4 app/models.py

```python
"""
SQLAlchemy ORM 数据模型

核心知识点：
- 声明式模型定义
- 字段类型与约束
- 表结构与 Python 类的映射
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func

from .database import Base


class Task(Base):
    """任务表 ORM 模型"""

    __tablename__ = "tasks"

    # 主键，自增
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 任务标题，必填，最大长度 100
    title = Column(String(100), nullable=False, comment="任务标题")

    # 任务描述，可选，文本类型
    description = Column(Text, nullable=True, comment="任务描述")

    # 优先级：low/medium/high，默认 medium
    priority = Column(
        String(20),
        nullable=False,
        default="medium",
        comment="优先级: low/medium/high"
    )

    # 完成状态：默认未完成
    is_completed = Column(Boolean, default=False, comment="是否完成")

    # 创建时间：自动记录
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间"
    )

    # 更新时间：自动更新
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', priority='{self.priority}')>"
```

---

### 3.5 app/schemas.py

```python
"""
Pydantic 数据验证模型

核心知识点：
- 请求体验证（Create/Update）
- 响应体序列化（Response）
- 模型继承与字段复用
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class TaskCreate(BaseModel):
    """创建任务的请求体"""

    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="任务标题",
        examples=["完成项目文档"]
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="任务描述",
        examples=["需要完成 README.md 的编写"]
    )
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high)$",
        description="优先级: low/medium/high",
        examples=["high"]
    )


class TaskUpdate(BaseModel):
    """更新任务的请求体"""

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="任务标题"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="任务描述"
    )
    priority: Optional[str] = Field(
        None,
        pattern="^(low|medium|high)$",
        description="优先级: low/medium/high"
    )
    is_completed: Optional[bool] = Field(
        None,
        description="是否完成"
    )


# ==================== 响应模型 ====================

class TaskResponse(BaseModel):
    """单个任务的响应体"""

    id: int = Field(..., description="任务 ID")
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    priority: str = Field(..., description="优先级")
    is_completed: bool = Field(..., description="是否完成")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    # Pydantic V2 配置：允许从 ORM 对象直接转换
    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """任务列表响应体"""

    total: int = Field(..., description="总任务数")
    tasks: list[TaskResponse] = Field(..., description="任务列表")


class MessageResponse(BaseModel):
    """通用消息响应体"""

    message: str = Field(..., description="操作结果消息")
    id: Optional[int] = Field(None, description="相关任务 ID")
```

---

### 3.6 app/main.py

```python
"""
FastAPI 应用入口

核心知识点：
- 应用初始化与配置
- 路由定义与 CRUD 实现
- 依赖注入数据库会话
- 异步处理与 Swagger 文档
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from .database import engine, Base, get_db
from .models import Task
from .schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    MessageResponse
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    在应用启动时创建数据库表（如果不存在）
    """
    # 启动时：创建所有表
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表已创建/验证")
    yield
    # 关闭时：可以添加清理逻辑
    print("🛑 应用关闭")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="迷你任务备忘录 API",
    description="一个基于 FastAPI + Docker + MySQL 的实战示例项目",
    version="1.0.0",
    lifespan=lifespan
)


# ==================== 健康检查 ====================

@app.get("/", tags=["系统"])
def root():
    """健康检查接口"""
    return {"message": "🚀 迷你任务备忘录 API 正在运行", "docs": "/docs"}


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
    """
    创建新任务

    - **title**: 任务标题（必填）
    - **description**: 任务描述（可选）
    - **priority**: 优先级 low/medium/high（默认 medium）
    """
    db_task = Task(
        title=task.title,
        description=task.description,
        priority=task.priority
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)  # 刷新以获取数据库生成的 id 和时间戳
    return db_task


@app.get("/tasks", response_model=TaskListResponse, tags=["任务"])
def read_tasks(
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(10, ge=1, le=100, description="返回条数"),
    is_completed: bool | None = Query(None, description="按完成状态筛选"),
    priority: str | None = Query(None, description="按优先级筛选"),
    db: Session = Depends(get_db)
):
    """
    获取任务列表

    支持分页和筛选：
    - **skip**: 跳过前 N 条
    - **limit**: 最多返回 N 条
    - **is_completed**: 筛选完成/未完成
    - **priority**: 筛选优先级
    """
    query = db.query(Task)

    # 动态筛选
    if is_completed is not None:
        query = query.filter(Task.is_completed == is_completed)
    if priority is not None:
        query = query.filter(Task.priority == priority)

    # 按创建时间倒序
    query = query.order_by(Task.created_at.desc())

    # 获取总数
    total = query.count()

    # 分页查询
    tasks = query.offset(skip).limit(limit).all()

    return TaskListResponse(total=total, tasks=tasks)


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["任务"])
def read_task(task_id: int, db: Session = Depends(get_db)):
    """
    获取单个任务详情

    - **task_id**: 任务 ID
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 ID {task_id} 不存在")
    return task


@app.put("/tasks/{task_id}", response_model=TaskResponse, tags=["任务"])
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    """
    更新任务信息

    - **task_id**: 任务 ID
    - 请求体中只需传入要更新的字段
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 ID {task_id} 不存在")

    # 只更新传入的字段（排除 None 值）
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", response_model=MessageResponse, tags=["任务"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    删除任务

    - **task_id**: 任务 ID
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 ID {task_id} 不存在")

    db.delete(task)
    db.commit()

    return MessageResponse(message=f"任务 ID {task_id} 已删除")
```

---

## 4. Docker 容器化配置文件

### 4.1 Dockerfile

```dockerfile
# ==================== 基础镜像 ====================
# 使用 Python 3.11 slim 版本（体积小，功能完整）
FROM python:3.11-slim

# ==================== 设置工作目录 ====================
WORKDIR /app

# ==================== 安装系统依赖 ====================
# 减少镜像层数，合并安装命令
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev pkg-config && \
    rm -rf /var/lib/apt/lists/*

# ==================== 配置 pip 国内镜像加速 ====================
# 使用清华镜像源，加快下载速度
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# ==================== 安装 Python 依赖 ====================
# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==================== 复制应用代码 ====================
COPY ./app ./app

# ==================== 暴露端口 ====================
EXPOSE 8000

# ==================== 启动命令 ====================
# 使用 uvicorn 启动 FastAPI 应用
# --host 0.0.0.0: 允许容器外访问
# --port 8000: 监听端口
# --reload: 开发模式下自动重载（生产环境可移除）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

---

### 4.2 docker-compose.yml

```yaml
# Docker Compose 编排文件
# 定义并管理多个容器服务

version: "3.8"

services:
  # ==================== Web 服务（FastAPI） ====================
  web:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fastapi-web
    ports:
      - "8000:8000"  # 宿主机:容器
    volumes:
      # 挂载代码目录，实现热更新（修改代码后自动重载）
      - ./app:/app/app
    environment:
      # 环境变量（可在代码中通过 os.environ 获取）
      - APP_ENV=development
      - DATABASE_URL=mysql+pymysql://root:123456@db:3306/task_memo
    depends_on:
      db:
        condition: service_healthy  # 等待数据库健康后再启动
    networks:
      - app-network
    restart: unless-stopped

  # ==================== 数据库服务（MySQL） ====================
  db:
    image: mysql:8.0
    container_name: fastapi-db
    ports:
      - "3306:3306"
    environment:
      # MySQL root 密码
      MYSQL_ROOT_PASSWORD: "123456"
      # 自动创建数据库
      MYSQL_DATABASE: task_memo
      # 字符集配置（支持中文）
      MYSQL_CHARACTER_SET_SERVER: utf8mb4
      MYSQL_COLLATION_SERVER: utf8mb4_unicode_ci
    volumes:
      # 命名卷：数据持久化，容器重启后数据不丢失
      - mysql_data:/var/lib/mysql
    networks:
      - app-network
    # 健康检查配置
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p123456"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    restart: unless-stopped

# ==================== 数据卷 ====================
volumes:
  mysql_data:
    driver: local

# ==================== 网络 ====================
networks:
  app-network:
    driver: bridge
```

---

## 5. 实战步骤与验证指南

### 步骤 1：创建项目文件

在 `D:\Projects\Myself\python web fastAPI Project` 目录下创建以下结构：

```
python web fastAPI Project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   └── schemas.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### 步骤 2：一键构建并启动

在项目根目录打开终端，执行：

```bash
docker compose up --build
```

**预期输出：**
```
fastapi-db-1  | ... MySQL ready for connections
fastapi-web-1 | ✅ 数据库表已创建/验证
fastapi-web-1 | INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 步骤 3：访问 Swagger UI 交互式文档

打开浏览器访问：**http://localhost:8000/docs**

即可看到自动生成的 API 文档，可直接在页面上测试所有接口。

### 步骤 4：接口测试示例

#### 4.1 创建任务

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "完成项目文档",
    "description": "编写 README.md 说明文档",
    "priority": "high"
  }'
```

**响应示例：**
```json
{
  "id": 1,
  "title": "完成项目文档",
  "description": "编写 README.md 说明文档",
  "priority": "high",
  "is_completed": false,
  "created_at": "2026-08-19T10:30:00Z",
  "updated_at": "2026-08-19T10:30:00Z"
}
```

#### 4.2 查询任务列表

```bash
curl http://localhost:8000/tasks
```

**响应示例：**
```json
{
  "total": 1,
  "tasks": [
    {
      "id": 1,
      "title": "完成项目文档",
      "description": "编写 README.md 说明文档",
      "priority": "high",
      "is_completed": false,
      "created_at": "2026-08-19T10:30:00Z",
      "updated_at": "2026-08-19T10:30:00Z"
    }
  ]
}
```

#### 4.3 更新任务状态

```bash
curl -X PUT http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"is_completed": true}'
```

**响应示例：**
```json
{
  "id": 1,
  "title": "完成项目文档",
  "description": "编写 README.md 说明文档",
  "priority": "high",
  "is_completed": true,
  "created_at": "2026-08-19T10:30:00Z",
  "updated_at": "2026-08-19T10:35:00Z"
}
```

#### 4.4 删除任务

```bash
curl -X DELETE http://localhost:8000/tasks/1
```

**响应示例：**
```json
{
  "message": "任务 ID 1 已删除"
}
```

### 步骤 5：验证数据持久化

1. 创建几条任务数据
2. 停止并移除容器：
   ```bash
   docker compose down
   ```
3. 重新启动服务：
   ```bash
   docker compose up
   ```
4. 再次查询任务列表，数据依然存在 ✅

**原理**：MySQL 数据存储在 Docker 命名卷 `mysql_data` 中，该卷独立于容器生命周期，容器删除后数据仍保留。

---

## 6. 核心概念串联小结

| 技术 | 角色定位 | 在本项目中的作用 |
|------|----------|------------------|
| **Docker** | 环境标准化与隔离 | 将 FastAPI 应用和 MySQL 打包成独立容器，保证"一次构建，处处运行" |
| **Docker Compose** | 多容器编排 | 定义 web/db 服务关系、网络、卷，一键启动完整环境 |
| **FastAPI** | Web 应用框架 | 提供路由、请求处理、Swagger 文档，构建 RESTful API |
| **Pydantic** | 数据验证层 | 定义请求/响应模型，自动校验输入、序列化输出 |
| **SQLAlchemy** | ORM 映射层 | 将 Python 类映射为数据库表，用面向对象方式操作数据库 |
| **MySQL** | 数据持久化 | 存储任务数据，支持事务和复杂查询 |

**一句话总结**：Docker 负责"打包环境"，Docker Compose 负责"编排服务"，FastAPI 负责"处理请求"，Pydantic 负责"验证数据"，SQLAlchemy 负责"操作数据库"，MySQL 负责"存储数据"——它们共同构成了一个现代 Python Web 应用的完整技术栈。

---

## 附录：常用命令速查

```bash
# 启动服务（后台运行）
docker compose up -d

# 查看运行状态
docker compose ps

# 查看日志
docker compose logs -f web

# 进入 MySQL 容器
docker compose exec db mysql -u root -p123456

# 进入 Web 容器
docker compose exec web bash

# 停止并移除容器
docker compose down

# 停止并移除容器及数据卷（⚠️ 会删除数据）
docker compose down -v
```
