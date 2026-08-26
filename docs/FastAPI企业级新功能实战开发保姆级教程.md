# FastAPI + MySQL 企业级新功能实战开发保姆级教程

> **适用对象**：准备在现有 FastAPI 企业级架构上**从零独立开发新功能**的开发者。  
> **运行环境**：Docker / Docker Compose（所有代码修改会通过 Volume 挂载自动热重载生效，无需本地配置环境）。  
> **核心目标**：掌握一套标准、规范、可复制的**企业级功能开发 6 步法（SOP）**，以后面对任何新业务需求，都能行云流水般写出高质量代码。

---

## 目录

1. [💡 企业级功能开发核心思维模型（6 步开发流）](#1-企业级功能开发核心思维模型6-步开发流)
2. [🎯 实战场景设想与需求规划](#2-实战场景设想与需求规划)
   - [场景一：任务分类管理（Category）—— 基础单表拓展【本次教学主线】](#场景一任务分类管理category-基础单表拓展本次教学主线)
   - [场景二：任务步骤清单（Subtask）—— 进阶一对多外键关联](#场景二任务步骤清单subtask-进阶一对多外键关联)
   - [场景三：任务仪表盘统计（Analytics）—— 高级数据聚合分析](#场景三任务仪表盘统计analytics-高级数据聚合分析)
3. [🚀 手把手实战开发：任务分类（Category）模块](#3-手把手实战开发任务分类category模块)
   - [第 1 步：创建 ORM 数据模型（`app/models/category.py`）](#第-1-步创建-orm-数据模型appmodelscategorypy)
   - [第 2 步：在元数据中心注册模型（`app/db/base.py`）](#第-2-步在元数据中心注册模型appdbbasepy)
   - [第 3 步：编写 Pydantic 数据传输模型（`app/schemas/category.py`）](#第-3-步编写-pydantic-数据传输模型appschemascategorypy)
   - [第 4 步：编写 CRUD 数据持久层（`app/crud/crud_category.py`）](#第-4-步编写-crud-数据持久层appcrudcrud_categorypy)
   - [第 5 步：编写业务路由控制器（`app/api/v1/endpoints/categories.py`）](#第-5-步编写业务路由控制器appapiv1endpointscategoriespy)
   - [第 6 步：在路由总线中挂载子路由（`app/api/v1/api.py`）](#第-6-步在路由总线中挂载子路由appapiv1apipy)
4. [🐳 Docker 环境下的验证与联调测试](#4-docker-环境下的验证与联调测试)
5. [🧗 进阶挑战实战：外键关联表开发（SubTask 示例）](#5-进阶挑战实战外键关联表开发subtask-示例)
6. [⚠️ 避坑指南与最佳实践（FAQ）](#6-避坑指南与最佳实践faq)

---

## 1. 💡 企业级功能开发核心思维模型（6 步开发流）

在企业级分层架构中，开发一个新功能绝不是直接在 `main.py` 乱写代码，而是严格遵循**自底向上、关注点分离**的开发闭环：

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       【企业级功能标准开发 6 步法】                            │
└─────────────────────────────────────────────────────────────────────────────┘

  第 1 步：ORM 模型定义 (models/)     ──> 定义 MySQL 表名、列、数据类型、索引
            │
  第 2 步：元数据汇聚 (db/base.py)    ──> 导入新模型，确保 Docker 启动时自动在 MySQL 建表
            │
  第 3 步：Schema 校验 (schemas/)     ──> 定义客户端传什么 (DTO)、接口返回什么 (VO)
            │
  第 4 步：CRUD 数据层 (crud/)        ──> 继承通用 CRUDBase，写数据库具体增删改查逻辑
            │
  第 5 步：路由控制器 (endpoints/)    ──> 编写 HTTP 接口，接收请求 -> 调 CRUD -> 返回响应
            │
  第 6 步：路由总线注册 (api/v1/api.py)──> include_router 挂载子路由
            │
            ▼
       Docker 热重载生效 ──> 打开 /docs 交互式测试验证 🎉
```

### 为什么必须按这个顺序写？
1. **数据模型先行**：一切业务都围绕"数据结构"展开，先确定数据库存什么。
2. **Schema 紧随其后**：明确接口的入参和出参规则。
3. **CRUD 隔离 SQL**：避免在路由里写乱七八糟的数据库查询，保持代码极度整洁与可复用。
4. **路由组装一切**：控制器只做"调度员"，不做繁重计算。

---

## 2. 🎯 实战场景设想与需求规划

基于现有的 `Task`（任务备忘录）系统，我们可以设想以下 3 个真实的业务场景：

### 场景一：任务分类管理（Category）—— 基础单表拓展【本次教学主线】
- **业务背景**：用户任务太多，需要按分类整理（如"工作"、"生活"、"学习"、"健身"），并支持给分类自定义颜色标识和图标。
- **涉及技术**：独立单表的完整 CRUD、唯一性约束排重（`unique=True`）、分类列表查询、分类更新与删除。

### 场景二：任务步骤清单（Subtask）—— 进阶一对多外键关联
- **业务背景**：一个大任务包含多个具体执行子步骤（如"上线新功能"包含"编写代码"、"单元测试"、"部署"）。
- **涉及技术**：SQLAlchemy `ForeignKey` 外键关联、级联删除（主任务删除时自动删除所有子步骤）、按父任务 ID 查询子任务。

### 场景三：任务仪表盘统计（Analytics）—— 高级数据聚合分析
- **业务背景**：统计报表页面，显示"待办任务总数"、"已完成任务占比"、"各优先级任务分布"、"今日新建任务数"。
- **涉及技术**：SQLAlchemy 聚合函数（`func.count`, `func.group_by`）、自定义聚合响应 Schema。

---

## 3. 🚀 手把手实战开发：任务分类（Category）模块

下面我们将以 **「场景一：任务分类管理（Category）」** 为例，完整演示从 0 到 1 开发新功能的 6 个步骤。

### 业务接口设计清单

| 方法 | 接口路径 | 说明 | 状态码 | 请求体 / 参数 |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/categories` | 新建分类（名称不能重复） | 201 | `{ "name": "工作", "color": "#1890ff", "description": "工作相关" }` |
| `GET` | `/api/v1/categories` | 获取分类列表（按创建时间倒序） | 200 | `?skip=0&limit=100` |
| `GET` | `/api/v1/categories/{id}` | 获取单个分类详情 | 200 | 路径参数 `id` |
| `PUT` | `/api/v1/categories/{id}` | 更新分类信息 | 200 | 可选修改 `name`, `color`, `description` |
| `DELETE` | `/api/v1/categories/{id}` | 删除分类 | 200 | 路径参数 `id` |

---

### 第 1 步：创建 ORM 数据模型（`app/models/category.py`）

**目标**：告诉 SQLAlchemy 在 MySQL 中创建一张名为 `categories` 的数据表。

#### 1. 新建文件 `app/models/category.py`，写入以下代码：

```python
"""
ORM 模型层：Category（分类）数据表映射模型 (models/category.py)
"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base_class import Base


class Category(Base):
    """
    分类表 ORM 模型
    对应 MySQL 中的 `categories` 表
    """

    __tablename__ = "categories"  # 表名

    # 主键 ID：自增，建立索引
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 分类名称：必填，建立唯一约束（unique=True，分类名不能重复）
    name = Column(String(50), nullable=False, unique=True, index=True, comment="分类名称")

    # 分类颜色标签：如 "#1890ff" 或 "blue"，默认 "#1890ff"
    color = Column(String(20), nullable=False, default="#1890ff", comment="颜色HEX或名称")

    # 分类详细描述：选填
    description = Column(Text, nullable=True, comment="分类说明")

    # 创建时间：数据库自动生成当前时间戳
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间",
    )

    # 更新时间：数据库在更新时自动刷新时间戳
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', color='{self.color}')>"
```

#### 2. 更新 `app/models/__init__.py`，导出新模型：

```python
from .category import Category
from .task import Task

__all__ = ["Task", "Category"]
```

> 💡 **重点解析**：
> - `unique=True`：在 MySQL 中会为此字段添加唯一索引（UNIQUE INDEX），从数据库层面防止同名分类插入。
> - `__repr__`：方便在调试打印时看清对象内容，非必需但属于工程好习惯。

---

### 第 2 步：在元数据中心注册模型（`app/db/base.py`）

**目标**：让 `lifespan` 自动建表逻辑能够"发现"新创建的 `Category` 模型。

#### 修改 `app/db/base.py`：

```python
"""
数据库层：ORM 模型统一发现与元数据注册中心 (db/base.py)
"""

from app.db.base_class import Base  # noqa: F401
from app.models.category import Category  # noqa: F401  <-- 新增这一行！
from app.models.task import Task  # noqa: F401
```

> ⚠️ **新手最容易踩的坑**：
> 如果你写了 `app/models/category.py`，但**忘记**在 `app/db/base.py` 里导入它，
> 启动 Docker 时，`Base.metadata.create_all()` 就**不会**在 MySQL 里创建 `categories` 表，后续调用接口会报 `Table 'todo.categories' doesn't exist` 错误！

---

### 第 3 步：编写 Pydantic 数据传输模型（`app/schemas/category.py`）

**目标**：定义接口的入参（客户端传进来的 JSON 格式）和出参（接口返回给客户端的 JSON 格式）。

#### 1. 新建文件 `app/schemas/category.py`，写入以下代码：

```python
"""
数据传输层：Category 相关的 Pydantic 校验与响应模型 (schemas/category.py)
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 客户端请求模型 (Request DTO) ====================


class CategoryCreate(BaseModel):
    """创建分类时的请求体 (POST /categories)"""

    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="分类名称（必填，1-50字符）",
        examples=["工作"],
    )
    color: str = Field(
        default="#1890ff",
        max_length=20,
        description="分类颜色标识",
        examples=["#1890ff"],
    )
    description: Optional[str] = Field(
        None,
        max_length=200,
        description="分类描述",
        examples=["所有与工作相关的任务"],
    )


class CategoryUpdate(BaseModel):
    """更新分类时的请求体 (PUT /categories/{id})"""

    name: Optional[str] = Field(None, min_length=1, max_length=50, description="分类名称")
    color: Optional[str] = Field(None, max_length=20, description="分类颜色标识")
    description: Optional[str] = Field(None, max_length=200, description="分类描述")


# ==================== 接口响应模型 (Response VO) ====================


class CategoryResponse(BaseModel):
    """单个分类详情的响应模型"""

    id: int = Field(..., description="分类 ID")
    name: str = Field(..., description="分类名称")
    color: str = Field(..., description="颜色")
    description: Optional[str] = Field(None, description="分类描述")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")

    # 关键：允许 Pydantic 直接从 SQLAlchemy ORM 对象读取属性
    model_config = {"from_attributes": True}


class CategoryListResponse(BaseModel):
    """分类列表接口的响应模型 (GET /categories)"""

    total: int = Field(..., description="分类总数")
    categories: list[CategoryResponse] = Field(..., description="分类列表")
```

#### 2. 更新 `app/schemas/__init__.py`，导出新模型：

```python
from .category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)
from .msg import MessageResponse
from .task import TaskCreate, TaskListResponse, TaskResponse, TaskUpdate

__all__ = [
    "MessageResponse",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskListResponse",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "CategoryListResponse",
]
```

> 💡 **重点解析**：
> - `Field(..., min_length=1)`：`...` 代表该字段为必填项；Pydantic 会自动拦截空字符串并返回 422 错误。
> - `model_config = {"from_attributes": True}`：在 FastAPI 中返回 SQLAlchemy ORM 对象时，此配置会让 Pydantic 自动把 ORM 实例转化为 JSON 字典。

---

### 第 4 步：编写 CRUD 数据持久层（`app/crud/crud_category.py`）

**目标**：封装数据库层对 `categories` 表的操作，路由层只负责调用方法。

#### 1. 新建文件 `app/crud/crud_category.py`，写入以下代码：

```python
"""
数据持久层：Category 专属 CRUD 数据访问对象 (crud/crud_category.py)
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CRUDCategory(CRUDBase[Category, CategoryCreate, CategoryUpdate]):
    """
    分类专属数据持久层
    自动继承了 CRUDBase 提供的 get, get_multi, create, update, remove 基础方法
    """

    def get_by_name(self, db: Session, *, name: str) -> Optional[Category]:
        """
        根据分类名称精确查询（用于新建或修改时的重名校验）
        对应 SQL: SELECT * FROM categories WHERE name = :name LIMIT 1;
        """
        return db.query(self.model).filter(self.model.name == name).first()

    def get_multi_with_count(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> tuple[int, list[Category]]:
        """
        分页查询分类列表并返回总数
        """
        query = db.query(self.model).order_by(self.model.created_at.desc())
        total = query.count()
        categories = query.offset(skip).limit(limit).all()
        return total, categories


# 实例化单例对象
category = CRUDCategory(Category)
```

#### 2. 更新 `app/crud/__init__.py`，导出单例对象：

```python
from .crud_category import category
from .crud_task import task

__all__ = ["task", "category"]
```

> 💡 **重点解析**：
> - 为什么不用重复写 `create` / `get` / `remove`？因为继承了 `CRUDBase`，通用增删改查基类已经帮你写好了！
> - 这里只需要补充当前业务特有的方法（如 `get_by_name` 做排重检查）。

---

### 第 5 步：编写业务路由控制器（`app/api/v1/endpoints/categories.py`）

**目标**：编写暴露给前端或客户端调用的 HTTP 接口。

#### 新建文件 `app/api/v1/endpoints/categories.py`，写入以下代码：

```python
"""
路由控制器层：Category 分类业务端点 (api/v1/endpoints/categories.py)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_db
from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)
from app.schemas.msg import MessageResponse

router = APIRouter()


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建新分类",
)
def create_category(category_in: CategoryCreate, db: Session = Depends(get_db)):
    """
    创建新分类：
    - **name**: 分类名称（必填，不可重复）
    - **color**: 颜色代码（选填，默认 #1890ff）
    - **description**: 描述（选填）
    """
    # 业务校验：检查同名分类是否已存在
    existing = crud.category.get_by_name(db=db, name=category_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"分类名称 '{category_in.name}' 已存在，请勿重复创建",
        )
    return crud.category.create(db=db, obj_in=category_in)


@router.get("", response_model=CategoryListResponse, summary="获取分类列表")
def read_categories(
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(100, ge=1, le=100, description="返回条数"),
    db: Session = Depends(get_db),
):
    """
    获取所有分类列表（按创建时间倒序）
    """
    total, categories = crud.category.get_multi_with_count(db=db, skip=skip, limit=limit)
    return CategoryListResponse(total=total, categories=categories)


@router.get("/{category_id}", response_model=CategoryResponse, summary="获取单个分类详情")
def read_category(category_id: int, db: Session = Depends(get_db)):
    """根据分类 ID 查询详情"""
    db_category = crud.category.get(db=db, id=category_id)
    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分类 ID {category_id} 不存在",
        )
    return db_category


@router.put("/{category_id}", response_model=CategoryResponse, summary="更新分类信息")
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db),
):
    """
    更新分类信息：
    - 仅更新传入的字段
    - 若修改了名称，会检查新名称是否与其他分类重名
    """
    db_category = crud.category.get(db=db, id=category_id)
    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分类 ID {category_id} 不存在",
        )

    # 若用户尝试修改名称，校验新名字是否被其他人占用
    if category_update.name and category_update.name != db_category.name:
        existing = crud.category.get_by_name(db=db, name=category_update.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"分类名称 '{category_update.name}' 已被使用",
            )

    return crud.category.update(db=db, db_obj=db_category, obj_in=category_update)


@router.delete(
    "/{category_id}",
    response_model=MessageResponse,
    summary="删除分类",
)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """根据分类 ID 删除分类"""
    db_category = crud.category.get(db=db, id=category_id)
    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分类 ID {category_id} 不存在",
        )
    crud.category.remove(db=db, id=category_id)
    return MessageResponse(message=f"分类 ID {category_id} 已删除", id=category_id)
```

> 💡 **重点解析**：
> - `Depends(get_db)`：自动借出连接并在函数执行结束后自动归还连接池。
> - `raise HTTPException(status_code=400, detail=...)`：业务异常时规范返回 HTTP 错误状态码和中文提示。

---

### 第 6 步：在路由总线中挂载子路由（`app/api/v1/api.py`）

**目标**：将写好的分类路由挂载到 FastAPI 应用的路由树上。

#### 修改 `app/api/v1/api.py`：

```python
"""
路由层：API v1 路由总线聚合模块 (api/v1/api.py)
"""

from fastapi import APIRouter

# 1. 导入新的分类端点模块
from app.api.v1.endpoints import categories, health, tasks

api_router = APIRouter()

# 挂载健康检查
api_router.include_router(health.router, tags=["系统"])

# 挂载任务模块
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务"])

# 2. 挂载分类模块（统一加前缀 /categories，打上标签）
api_router.include_router(categories.router, prefix="/categories", tags=["分类"])
```

**大功告成！** 你已经完成了全部代码开发！整个过程完全没有碰 `app/main.py`，这就是模块化架构的优雅之处！

---

## 4. 🐳 Docker 环境下的验证与联调测试

因为 `docker-compose.yml` 已经把本地 `./app` 目录挂载到容器中，并且启用了 `--reload`：

```yaml
volumes:
  - ./app:/app/app
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

当你保存上述文件时，容器内会自动检测到代码变更并重新加载！

### 1. 验证数据库自动建表
如果你的服务已经在运行，重启一次容器以触发 `lifespan` 自动建表：
```bash
docker compose restart api
```
查看容器启动日志：
```bash
docker compose logs -f api
```
看到：
```text
✅ [Lifespan] 数据库表已验证/创建完成
INFO:     Application startup complete.
```
说明 MySQL 中的 `categories` 表已自动建好！

---

### 2. 在 Swagger UI 交互式测试
打开浏览器访问：**`http://localhost:8000/docs`**

你会看到新增的 **`[分类]`** 标签组，包含 5 个新接口：

1. **测试新建分类 (`POST /categories`)**：
   - 请求体传入：
     ```json
     {
       "name": "学习提升",
       "color": "#52c41a",
       "description": "编程、阅读等学习事项"
     }
     ```
   - 点击 **Execute**，返回 `201 Created` 及生成的 `id: 1`。
2. **测试重名校验**：再次点击发送完全相同的数据，系统会准确拦截并返回 `400 Bad Request: 分类名称 '学习提升' 已存在`。
3. **测试列表查询 (`GET /categories`)**：返回包含刚才创建数据的分类列表。
4. **测试更新 (`PUT /categories/1`)**：修改颜色为 `#ff4d4f`，返回更新后的数据。
5. **测试删除 (`DELETE /categories/1`)**：返回 `{"message": "分类 ID 1 已删除", "id": 1}`。

---

## 5. 🧗 进阶挑战实战：外键关联表开发（SubTask 示例）

当你熟悉了单表开发后，下一步最常遇到的就是**多表关联（一对多）**。
例如：一个 `Task`（主任务）拥有多个 `Subtask`（子任务/检查项）。

这里给出关键代码范例供你练习参考：

### 1. 模型定义（`app/models/subtask.py`）

```python
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class Subtask(Base):
    __tablename__ = "subtasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False, comment="子任务标题")
    is_completed = Column(Boolean, default=False, comment="是否完成")

    # 外键：关联 tasks 表的主键 id
    # ondelete="CASCADE": 主任务被删除时，关联的子任务自动随之删除
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 2. 在主模型建立双向关联（`app/models/task.py`）

```python
# 在 Task 类中追加 relationship:
subtasks = relationship("Subtask", backref="task", cascade="all, delete-orphan")
```

按照 6 步法：
1. `models/subtask.py` -> 2. `db/base.py` -> 3. `schemas/subtask.py` -> 4. `crud/crud_subtask.py` -> 5. `endpoints/subtasks.py` -> 6. `api.py`。
你就可以实现如 `GET /tasks/{task_id}/subtasks` 和 `POST /tasks/{task_id}/subtasks` 这样的关联业务！

---

## 6. ⚠️ 避坑指南与最佳实践（FAQ）

### Q1: 我修改了 Model 里的字段（例如新增了一列），为什么 MySQL 里没有生效？
> 💡 **原理**：`Base.metadata.create_all()` 只负责**创建不存在的表**。如果表已经存在，SQLAlchemy **不会**自动去执行 `ALTER TABLE` 修改已有表的列结构。  
> **解决方案**：
> - **开发阶段最快方式**：进入 MySQL 删除这张旧表（`DROP TABLE categories;`），重启容器让其重新建表；
> - **生产环境正规方式**：使用数据库迁移工具 **Alembic** 生成迁移版本脚本（后续进阶掌握）。

### Q2: 为什么 Pydantic 响应模型里一定要写 `model_config = {"from_attributes": True}`？
> 💡 **原理**：SQLAlchemy 从数据库查出来的是 Python 对象（通过 `task.title` 取值），而常规 Python 字典是通过 `task["title"]` 取值。`from_attributes = True` 告诉 Pydantic 允许用 `getattr()` 去读取对象属性，否则 FastAPI 在返回数据时会报错。

### Q3: 为什么不要在 Endpoint 路由函数里写 `db.query(...)`？
> 💡 **原理**：保持路由函数（Controller）的轻量。路由只负责：
> 1. 参数校验；
> 2. 调用 CRUD；
> 3. 错误时抛出 `HTTPException`。
> 数据查询逻辑放在 CRUD 层，不仅代码清晰，而且在写单元测试或在其他函数里复用查询时会极其方便。

---

## 7. 总结清单（Checklist）

每次开发新功能时，在心中默念这张清单：

- [ ] **1. `models/`**：定义 ORM 类，并在 `models/__init__.py` 导出。
- [ ] **2. `db/base.py`**：导入新模型（确保建表能够被扫描到）。
- [ ] **3. `schemas/`**：定义 Create / Update / Response Schema，配置 `from_attributes = True`。
- [ ] **4. `crud/`**：继承 `CRUDBase`，按需编写定制查询方法，并在 `crud/__init__.py` 导出单例。
- [ ] **5. `endpoints/`**：编写路由函数，使用 `Depends(get_db)` 并调用 `crud`。
- [ ] **6. `api/v1/api.py`**：将新路由通过 `include_router` 挂载到总线。
- [ ] **7. 验证**：打开 `http://localhost:8000/docs` 逐项测试。

