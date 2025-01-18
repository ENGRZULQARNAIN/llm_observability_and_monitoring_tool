from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, create_engine, desc)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from auth.models import Users
from core.database import Base



class Projects(Base):
    project_id = Column(String, primary_key=True ,nullable=False, unique=True)
    project_name = Column(String)
    user_id = Column(String)
    benchmark_knowledge_id = Column(String)
    test_interval_in_hrs = Column(Float)
    is_active = Column(Boolean)
    registered_at = Column(DateTime,default=datetime.utcnow)







