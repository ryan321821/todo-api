from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import crud
from app.api.deps import get_current_user, require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.msg import MessageResponse
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate
from sqlalchemy.orm import Session

router = APIRouter()

"""
类 / 数据模型（Class / Schema） 属于 名词概念：采用 大驼峰命名（PascalCase），把主体对象放在最前面。
接口动作（Function / Endpoint） 属于 动作执行：采用 小写下划线命名（snake_case），把动作动词放在最前面。
"""


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse, summary="更新当前用户信息")
def update_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """普通用户只能改自己的信息"""
    if user_in.username and user_in.username != current_user.username:
        if crud.user.get_by_username(db, username=user_in.username):
            # 　if 全部为True才执行raise
            raise HTTPException(status_code=400, detail="用户名已存在")

    # 任意一个都要为None，越权保护：防止普通用户自行提权或修改角色
    if (
        user_in.role_codes is not None
        or user_in.issuperuser is not None
        or user_in.is_active is not None
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="越权操作")
    return crud.user.update_with_roles(db, db_obj=current_user, obj_in=user_in)


@router.get("", response_model=UserListResponse, summary="获取用户列表")
def read_users(
    skip: int = Query(0, ge=0, description="分页跳过的前 N 条数"),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("user:read")),
    # 【_】 ：表示一个“我不打算在后续代码中使用的占位变量，纯粹是为了触发依赖校验
):
    total, users = crud.user.get_multi_with_roles(db, skip=skip, limit=limit)
    return UserListResponse(total=total, users=users)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户(管理员)",
)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("user:write")),
):
    if crud.user.get_by_username(db, username=user_in.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    if crud.user.get_by_email(db, email=user_in.email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    return crud.user.create_with_roles(
        db, obj_in=user_in, role_codes=user_in.role_codes
    )


@router.get("/{user_id}", response_model=UserResponse, summary="获取单个用户信息")
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("user:read")),
):
    db_user = crud.user.get_with_roles(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail=f"用户ID{user_id}不存在")
    return db_user


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户信息(管理员)")
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("user:write")),
):
    db_user = crud.user.get_with_roles(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail=f"用户ID{user_id}不存在")
    return crud.user.update_with_roles(db, db_obj=db_user, obj_in=user_in)


@router.delete("/{user_id}", response_model=MessageResponse, summary="删除用户(管理员)")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("user:write")),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录用户")
    db_user = crud.user.get(db=db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail=f"用户{user_id} 不存在")
    crud.user.remove(db=db, id=user_id)
    return MessageResponse(message=f"用户{user_id} 已删除", id=user_id)
