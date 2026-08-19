"""
Pydantic 数据验证模型

作用：
- 请求体模型：定义客户端传过来的数据格式（自动校验，错了直接返回 422）
- 响应体模型：定义接口返回给客户端的数据格式（自动过滤多余字段）
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==================== 请求模型 ====================


class TaskCreate(BaseModel):
    """创建任务时的请求体"""

    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="任务标题",
        examples=["完成项目文档"],
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="任务描述",
        examples=["需要完成 README.md 的编写"],
    )
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high)$",
        description="优先级: low/medium/high",
        examples=["high"],
    )


class TaskUpdate(BaseModel):
    """更新任务时的请求体（所有字段都可选，只更新传入的字段）"""

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="任务标题",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="任务描述",
    )
    priority: Optional[str] = Field(
        None,
        pattern="^(low|medium|high)$",
        description="优先级: low/medium/high",
    )
    is_completed: Optional[bool] = Field(
        None,
        description="是否完成",
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

    # Pydantic V2 配置：允许直接从 ORM 对象（Task）转换成这个响应模型
    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """任务列表的响应体"""

    total: int = Field(..., description="总任务数")
    tasks: list[TaskResponse] = Field(..., description="任务列表")


class MessageResponse(BaseModel):
    """通用消息响应体（比如删除成功）"""

    message: str = Field(..., description="操作结果消息")
    id: Optional[int] = Field(None, description="相关任务 ID")