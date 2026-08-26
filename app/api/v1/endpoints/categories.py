"""
路由控制器层：Category 分类业务端点（api/v1/endpoints/categories.py）
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.schemas.msg import MessageResponse
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_db
from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建新分类",
)
def create_category(category_in: CategoryCreate, db: Session = Depends(get_db)):
    existing = crud.category.get_by_name(db=db, name=category_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"分类名称'{category_in.name}' 已存在,请勿重复创建",
        )
    return crud.category.create(db=db, obj_in=category_in)


@router.get("", response_model=CategoryListResponse, summary="获取分类列表")
def read_categories(
    skip: int = Query(0, ge=0, description="分页跳过的前 N 条数"),
    limit: int = Query(100, ge=1, ls=100, description="每页返回的最大条数"),
    db: Session = Depends(get_db),
):
    """
    获取所有分类列表（按创建时间倒序）
    """
    total, categories = crud.category.get_multi_with_count(
        db=db, skip=skip, limit=limit
    )
    return CategoryListResponse(total=total, categories=categories)


@router.get(
    "/{category_id}", response_model=CategoryResponse, summary="获取单个分类详情"
)
def read_category(category_id: int, db: Session = Depends(get_db)):
    """根据分类ID查询单个分类详情"""
    db_category = crud.category.get(db=db, id=category_id)
    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分类ID '{category_id}' 不存在",
        )
    return db_category


@router.put("/{category_id}", response_model=CategoryResponse, summary="更新分类信息")
def update_category(
    category_id: int, category_update: CategoryUpdate, db: Session = Depends(get_db)
):
    """更新分类信息，若修改了名称，会检查是否与其他分类名称冲突"""
    db_category = crud.category.get(db=db, id=category_id)
    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分类ID '{category_id}' 不存在",
        )
    # 若用户尝试修改分类名称，检查是否与其他分类名称冲突
    if category_update.name and category_update.name != db_category.name:
        existing = crud.category.get_by_name(db=db, name=category_update.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"分类名称 '{category_update.name}' 已存在,请勿重复创建",
            )

    return crud.category.update(db=db, db_obj=db_category, obj_in=category_update)


@router.delete("{category_id}", response_model=MessageResponse, summary="删除分类")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    db_category = crud.category.get(db=db, id=category_id)
    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"分类ID{category_id}不存在"
        )
    crud.category.remove(db=db, id=category_id)
    return MessageResponse(message=f"分类 ID {category_id} 已删除", id=category_id)
