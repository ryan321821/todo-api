"""
deps.py 是 dependencies.py 的常见缩写，意思是 “依赖项”（Dependencies）。
API 层：认证与权限依赖注入 (api/deps.py)

为什么单独放在 api 层而不是 core 层？
get_current_user 依赖 FastAPI 的 HTTPBearer / Depends / HTTPException，
这是"接口层"的职责；core/security.py 只负责纯算法（哈希、JWT 编解码）。
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app import crud
from app.core.security import decode_access_token
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User

# HTTPBearer：是 FastAPI 提供的一个类，专门用来处理 Authorization 请求头。
bearer_scheme = HTTPBearer(auto_error=False)
"""
    auto_error=False：这是一个开关。
    默认是 True（不写时的默认值）：如果请求头里没有 Bearer Token，它会自动抛出 401 错误，连函数体都进不去。
    False：表示“不要自动报错”。如果请求头里没 Token，不会抛异常，而是返回 None，由自定义代码（如 if credentials is None）决定如何处理。
"""


# bearer_scheme：持有者令牌方案。特指 HTTP 认证头中的 Bearer 认证方式（即 Authorization: Bearer <token>）。
#               一般直接保留英文叫 “Bearer 认证方案”。
# credentials:身份凭据。特指客户端在请求头里携带的那个 Token（令牌字符串）。


# HTTP请求到达 -> [1.deps.py(拦截/检查)] -> [2.router(路由调度)] -> [3.crud_user.py(查库)] -> 返回响应


def get_current_user(
    db: Session = Depends(get_db),  # 数据库会话依赖，用于数据库操作
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        bearer_scheme
    ),  # Bearer令牌认证依赖
) -> User:  # 返回用户对象
    """get_current_userz中的参数credentials是一个对象类型，而不是数据类型
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",                        # 方案类型
        credentials="eyJhbGci...abc123"         # 真正的令牌码
    )
    """

    """
    从请求头 Authorization: Bearer <token> 解析当前用户。
    成功返回带角色和权限的用户对象，失败抛 401/403。
    """
    if credentials is None:  # 检查是否提供了认证凭证
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供访问令牌",
            headers={"WWW-Authenticate": "Bearer"},  # 提示客户端使用Bearer认证
        )

    """
    sub 的来源与常见标准字段
        JWT 规范定义的常见 3 字母缩写字段如下：
        sub（Subject，主体）：必填/最核心字段。代表这个 Token 是发给谁的（通常存放用户的唯一标识，如用户 ID 100 或账号名）。
        exp（Expiration Time，过期时间）：Unix 时间戳，表示 Token 啥时候失效。
        iat（Issued At，签发时间）：Unix 时间戳，表示 Token 是啥时候生成的。
        iss（Issuer，签发者）：谁签发的 Token（比如 "my-fastapi-app"）。
        nbf（Not Before，生效时间）：在此时间之前 Token 不可用。
    """
    payload = decode_access_token(credentials.credentials)  # 解码JWT令牌获取payload
    if payload is None or "sub" not in payload:  # 检查payload是否有效且包含用户ID
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证凭证无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload["sub"])  # 从payload中提取用户ID并转换为整数
    except (TypeError, ValueError):  # 处理ID转换可能的异常
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证凭证格式错误",
            headers={"WWW-authenticate": "Bearer"},
        )

    # 一次性加载用户 + 角色 + 权限，避免后续权限校验触发 N+1 查询问题
    user = crud.user.get_with_roles(
        db=db, user_id=user_id
    )  # 从数据库获取用户及其角色权限信息
    if user is None:  # 检查用户是否存在
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在"
        )
    if not user.is_active:  # 检查用户账号是否被禁用
        raise HTTPException(
            status_cocde=status.HTTP_403_FORBIDDEN, detail="账号已被禁用"
        )
    return user  # 返回已验证的用户对象


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    # 需要 '已登陆' 但不需要具体权限时是使用
    return current_user


def require_permissions(*required_permissions: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_supueruser:
            return current_user

        user_perms = {
            permission.code
            for role in current_user.roles
            for permission in role.permissions
        }
        missing = set(required_permissions) - user_perms
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"用户没有权限: {','.join(missing)}",
            )
        return current_user

    return checker

    """
        * 的作用（可变参数 *args）
        *required_permissions 意思是 “接收任意数量的参数，并自动打包成一个元组（Tuple）”。
    """


def require_role(*required_roles: str):
    # 1. 这是一个工厂函数，接收你要求的角色列表，例如 require_role("admin", "editor")

    def checker(current_user: User = Depends(get_current_user)) -> User:
        # 2. 先解析请求头，获取当前登录用户对象

        # 3. 【超级管理员特权】如果用户是超级管理员，直接放行，不检查具体角色
        if current_user.is_superuser:
            return current_user

        # 4. 提取当前用户已有的所有角色代码（如 ["admin", "user"]）
        user_role_codes = [role.code for role in current_user.roles]

        # 5. 关键逻辑：计算差集（需要的角色 - 已有的角色）
        missing = set(required_roles) - user_role_codes

        # 6. 如果差集不为空，说明用户缺少某些必要角色
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"用户没有角色: {' '.join(missing)}",
            )

        # 7. 检查通过，返回用户对象
        return current_user

    return checker
