"""
配置与安全层：密码加密与 JWT 认证工具 (core/security.py)

【为什么需要这个文件？】
标准企业级项目会将安全认证相关的通用逻辑（密码 Hash、JWT Token 生成与解析）
封装在 core 层中，以便所有接口（如用户登录、鉴权中间件）统一调用。
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

import bcrypt
import jwt

from app.core.config import settings

# JWT 签名算法，HS256 为标准对称加密算法
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    校验明文密码是否与数据库中存储的哈希密码一致

    :param plain_password: 用户输入的明文密码
    :param hashed_password: 数据库中经过 bcrypt 加密后的哈希字符串
    :return: True 验证通过，False 密码错误
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """
    使用 bcrypt 算法对用户明文密码进行安全加盐哈希

    :param password: 明文密码
    :return: 加密后的哈希字符串（存储入库）
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    生成 JWT 访问令牌（Access Token）

    :param subject: 令牌主题（通常为用户的 ID 或用户名）
    :param expires_delta: 自定义过期时长（可选）
    :return: 编码后的 JWT 字符串
    """
    # 计算过期时间
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # 组装载荷（Payload）
    to_encode = {"exp": expire, "sub": str(subject)}
    # 使用密钥与算法进行签名生成 Token
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    解析并校验 JWT 访问令牌

    :param token: 客户端传过来的 JWT 字符串
    :return: 解析成功返回 Payload 字典，过期或伪造则返回 None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
