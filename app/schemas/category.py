"""
数据传输层：Category相关的 Pydantic 校验与响应模型（schemas/category.py）
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

# ======================= 客户端请求模型（Request DTO） =======================
# Data Transfer Object（请求数据传输对象）


class CategoryCreate(BaseModel):
    """创建分类时的请求体（POST/categories/）"""

    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="分类名称，长度 1-50 个字符",
        example="工作",
    )
    color: str = Field(
        default="#1890ff", description="分类颜色，默认为蓝色", example="#1890ff"
    )
    description: Optional[str] = Field(
        None,
        max_length=200,
        description="分类描述",
        examples=["工作相关的任务", "生活琐事", "学习计划"],
    )


class CategoryUpdate(BaseModel):
    """更新分类时的请求体（PUT/categories/{category_id}）"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=50, description="分类名称"
    )
    color: Optional[str] = Field(None, max_length=20, description="分类颜色")
    description: Optional[str] = Field(None, max_length=200, description="分类描述")


# ======================= 接口响应模型 (Response VO) =======================
# View Object（响应视图对象）


class CategoryResponse(BaseModel):
    """单个分类详情的响应模型"""

    id: int = Field(..., description="分类 ID")
    name: str = Field(..., description="分类名称")
    color: str = Field(..., description="分类颜色")
    description: Optional[str] = Field(None, description="分类描述")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class CategoryListResponse(BaseModel):
    """分类列表接口的响应模型（GET/categories/）"""

    total: int = Field(..., description="分类总数")
    categories: list[CategoryResponse] = Field(..., description="分类列表")
