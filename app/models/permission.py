from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(String(200), nullable=True)

    roles = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin",
    )

    def __repr__(self):
        return (
            f"<Permission(id={self.id}, code={self.code}, "
            f"name={self.name}, description={self.description})>"
        )
