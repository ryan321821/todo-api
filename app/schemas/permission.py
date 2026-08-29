from pydantic import BaseModel, Field
from typing import Optional


# ==================== 客户端请求模型 (Request DTO) ====================
class PermissionCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=100, description="权限编码")
    name: str = Field(..., min_length=1, max_length=100, description="权限名称")
    description: Optional[str] = Field(None, max_length=200, description="权限说明")


# ==================== 接口响应模型 (Response VO) ====================
class PermissionResponse(BaseModel):
    id: str = Field(..., description="权限ID")
    code: str = Field(..., description="权限编码")
    name: str = Field(..., description="权限名称")
    description: Optional[str] = Field(None, description="权限说明")

    model_config = {"from_attributes": True}


class PermissionListResponse(BaseModel):
    total: int = Field(..., description="权限总数")
    permissions: list[PermissionResponse] = Field(..., description="权限列表")
