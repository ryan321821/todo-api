from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional

from app.schemas.role import RoleResponse


# ==================== 客户端请求模型 (Request DTO) ====================
class UserCreate(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="用户名",
    )
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(
        ..., min_length=8, max_length=64, description="密码（至少8位）"
    )
    role_codes: list[str] = Field(default_factory=list, description="初始角色编码列表")


class UserUpdate(BaseModel):
    username: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="登录名",
    )
    email: Optional[EmailStr] = Field(None, description="邮箱")
    password: Optional[str] = Field(
        None, min_length=8, max_length=64, description="密码（至少8位）"
    )
    is_active: Optional[bool] = Field(None, description="是否启用")
    is_superuser: Optional[bool] = Field(None, description="是否为超级管理员")
    role_codes: Optional[list[str]] = Field(None, description="角色编码列表")


# ==================== 接口响应模型 (Response VO) ====================
class UserResponse(BaseModel):
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    is_active: bool = Field(..., description="是否启用")
    is_superuser: bool = Field(..., description="是否为超级管理员")
    roles: list[RoleResponse] = Field(default_factory=list, description="用户角色列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    # 告诉 Pydantic，允许从“具有属性的对象”中读取数据，而不仅仅是从字典（dict）中读取。
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    total: int = Field(..., description="用户总数")
    users: list[UserResponse] = Field(..., description="用户列表")
