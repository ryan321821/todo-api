from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)  # 用户或者管理员："admin"
    name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=False)

    users = relationship("User", secondary="user_roles", back_populates="roles")
    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )

    def __rper__(self):
        return (
            f"<Role(id = {self.id}, code = {self.code}, "
            f"name = {self.name}, description = {self.description})>"
        )
