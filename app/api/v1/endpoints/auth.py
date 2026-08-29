from fastapi import APIRouter, Depends, HTTPException, status

from app import crud
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.token import LoginRequest, TokenResponse

from app.schemas.user import UserCreate, UserResponse
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="用户登录")
def login(login_in: LoginRequest, db: Session = Depends(get_db)):
    """
    db: Session = Depends(get_db)：
        仅在 FastAPI 的 API 路由函数（@router.get / @router.post 等）的入参中使用。
        路由需要直接面对客户端请求，必须依赖 FastAPI 的机制来自动创建和回收数据库连接。
    """

    """ 用户名密码登录，成功返回 JWT 访问令牌 """
    user = crud.user.authenticate(db, login_in.username, login_in.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用"
        )
    # HTTP 协议是无状态（Stateless）的——服务器记不住“谁刚才登录过”。如果登录完不给前端发 Token，
    # 用户接下来点击“查看个人中心”、“下单”、“修改头像”时，难道每次发请求都要让用户重新输入一次账号密码吗？
    access_token = create_access_token(
        subject=user.id
    )  # subject：JWT 的标准字段，用来存放用户的身份信息，比如用户 ID
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if crud.user.get_by_username(db, username=user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detal="用户名已存在"
        )
    if crud.user.get_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册"
        )
    role_codes = user_in.role_codes or ["user"]
    return crud.user.create_with_roles(db, obj_in=user_in, role_codes=role_codes)
