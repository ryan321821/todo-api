"""
数据传输层：Task 相关的 Pydantic 校验与响应模型 (schemas/task.py)

【为什么需要这个文件？】
FastAPI 使用 Pydantic 模型来实现：
1. 请求体验证（Request DTO）：自动校验客户端传来的 JSON 数据类型与格式，错误时自动返回 422 错误；
2. 响应体序列化（Response VO）：自动过滤多余字段，只向客户端输出规定的字段，并提供 Swagger 文档规范。
【本次升级】：增加 category_id 接收与 CategoryResponse 嵌套响应。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.category import CategoryResponse

# ==================== 客户端请求模型 (Request DTO) ====================


class TaskCreate(BaseModel):
    """
    创建任务时的请求体校验模型 (POST /tasks)
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="任务标题（必填，1-100字符）",
        examples=["完成项目文档"],
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="任务详细描述（选填，最多500字符）",
        examples=["需要完成 README.md 的编写"],
    )
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high)$",  # 正则限定必须是 low / medium / high 三者之一
        description="任务优先级: low/medium/high（默认 medium）",
        examples=["high"],
    )
    category_id: Optional[int] = Field(
        None,
        description="所属分类ID（选填，关联分类表）",
        examples=[1],
    )


class TaskUpdate(BaseModel):
    """
    更新任务时的请求体校验模型 (PUT /tasks/{id})
    所有字段均为可选（Optional），客户端传了哪个字段就更新哪个字段
    """

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="任务标题",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="任务详细描述",
    )
    priority: Optional[str] = Field(
        None,
        pattern="^(low|medium|high)$",
        description="任务优先级: low/medium/high",
    )
    is_completed: Optional[bool] = Field(
        None,
        description="是否已完成",
    )
    category_id: Optional[int] = Field(
        None,
        description="所属分类ID",
    )


# ==================== 接口响应模型 (Response VO) ====================


class TaskResponse(BaseModel):
    """
    单个任务详情的返回数据模型
    """

    id: int = Field(..., description="任务主键 ID")
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    priority: str = Field(..., description="任务优先级")
    is_completed: bool = Field(..., description="是否已完成")
    category_id: Optional[int] = Field(None, description="所属分类ID")
    owner_id: int = Field(..., description="所属用户ID")
    category: Optional[CategoryResponse] = Field(None, description="所属分类对象信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")

    # Pydantic V2 配置项：
    # from_attributes = True 允许 Pydantic 直接读取 SQLAlchemy ORM 对象（Task）的属性并自动转为 JSON
    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """
    任务列表接口的返回数据模型 (GET /tasks)
    包含总条数与当前页任务列表，方便前端做分页器
    """

    total: int = Field(..., description="符合条件的总任务数")
    tasks: list[TaskResponse] = Field(..., description="当前页的任务列表")
