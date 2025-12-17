# models.py
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    trial_used = Column(Boolean, default=False)

    accounts = relationship("VPNAccount", back_populates="owner")
    trials = relationship("Trial", back_populates="user")


class VPNAccount(Base):
    __tablename__ = "vpn_accounts"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    expires_at = Column(String, nullable=False)
    plan = Column(String, nullable=False)
    ehi_file = Column(String, nullable=False)
    notified_expire = Column(Integer, default=0)  # 0 = não notificado, 1 = notificado


    owner = relationship("User", back_populates="accounts")
    


class Trial(Base):
    __tablename__ = "trials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ssh_user = Column(String, nullable=False)
    ssh_pass = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    expires_at = Column(String, nullable=False)
    active = Column(Boolean, default=True)

    user = relationship("User", back_populates="trials")
    
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    plan_days = Column(Integer)
    mp_payment_id = Column(String)
    status = Column(String)
    created_at = Column(String)
    
    
    
class LoginLog(Base):
    __tablename__ = "login_logs"

    id = Column(Integer, primary_key=True)
    email = Column(String)
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
