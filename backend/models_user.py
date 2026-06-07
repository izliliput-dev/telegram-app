from sqlalchemy import Column, String, Integer, DateTime, LargeBinary, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), onupdate=func.now())
    
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String, nullable=False)
    
    mafile_encrypted = Column(LargeBinary, nullable=False)
    
    steam_login_encrypted = Column(LargeBinary, nullable=True)
    steam_password_encrypted = Column(LargeBinary, nullable=True)
    
    steam_id = Column(String, nullable=True)
    shared_secret_encrypted = Column(LargeBinary, nullable=True)
    identity_secret_encrypted = Column(LargeBinary, nullable=True)
    device_id = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="accounts")
