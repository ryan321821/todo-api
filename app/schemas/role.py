from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

from app.schemas.permission import PermissionResponse


# ==================== 客户端请求模型 (Request DTO) ====================
class RoleCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="角色编码")
    name: str = Field(..., min_length=1, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, max_length=200, description="角色说明")
    permission_codes: list[str] = Field(
        default_factory=list, description="角色初识权限编码列表"
    )


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(
        None, min_length=1, max_length=50, description="角色名称"
    )
    description: Optional[str] = Field(None, max_length=200, description="角色说明")
    permission_codes: Optional[list[str]] = Field(None, description="角色权限编码列表")


# ==================== 接口响应模型 (Response VO) ====================
class RoleResponse(BaseModel):
    id: int = Field(..., description="角色ID")
    code: str = Field(..., description="角色编码")
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(None, description="角色说明")
    permissions: list[PermissionResponse] = Field(
        default_factory=list, description="角色权限列表"
    )

    model_config = ConfigDict(from_attributes=True)


class RoleListResponse(BaseModel):
    total: int = Field(..., description="角色总数")
    roles: list[RoleResponse] = Field(..., description="角色列表")
