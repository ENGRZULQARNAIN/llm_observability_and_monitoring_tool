from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, create_engine, desc)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


# unique value inserted for user id
class Users(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    isVerified = Column(Boolean, default=False)
    verification_token = Column(String, unique=True, nullable=True)
    registered_at = Column(DateTime, default=datetime.utcnow)  # Add this line
