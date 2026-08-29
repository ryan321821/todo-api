from fastapi import APIRouter, Depends, Query, status, HTTPException

from app import crud
from app.api.deps import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.msg import MessageResponse
from app.schemas.role import RoleCreate, RoleListResponse, RoleResponse, RoleUpdate
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=RoleListResponse, summary="获取角色列表")
def read_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    _User=Depends(require_permissions("role:read")),
):
    total, roles = crud.role.get_multi_with_permissions(db, skip=skip, limit=limit)
    return RoleListResponse(total=total, roles=roles)


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建角色",
)
def create_role(
    role_in: RoleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("role:write")),
):
    if crud.role.get_by_code(db, code=role_in.code):
        raise HTTPException(status_code=400, detail=f"角色{role_in.code}已存在")
    return crud.role.create_with_permissions(db, obj_in=role_in)


@router.put("/{role_id}", response_model=RoleResponse, summary="更新角色权限")
def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("role:write")),
):
    db_role = crud.role.get(db=db, id=role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail=f"角色 ID {role_id} 不存在")
    return crud.role.update_with_permissions(db=db, db_obj=db_role, obj_in=role_in)


@router.delete("/{role_id}", response_model=MessageResponse, summary="删除角色")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("role:write")),
):
    db_role = crud.role.get(db=db, role_id=role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail=f"角色ID{role_id}不存在")
    crud.role.remove(db=db, db_obj=db_role)
    return MessageResponse(message=f"删除角色{db_role.name}成功", id=role_id)
