from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="登录名")
    password: str = Field(..., min_length=1, max_length=64, description="密码")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
