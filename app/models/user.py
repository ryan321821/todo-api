from sqlalchemy import Column, Integer, String, func, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    hashed_password = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_superuser = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 这个 secondary 参数必须接收一个 Table 对象，即associations.py中的 user_roles 对象
    roles = relationship(
        "Role", secondary="user_roles", back_populates="users", lazy="selectin"
    )
    tasks = relationship("Task", back_populates="owner", lazy="selectin")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
