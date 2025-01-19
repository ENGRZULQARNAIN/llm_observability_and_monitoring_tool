from datetime import datetime, UTC

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, create_engine, desc)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base

class Projects(Base):
    __tablename__ = 'projects'
    project_id = Column(String, primary_key=True ,nullable=False, unique=True)
    user_id = Column(String)
    project_name = Column(String)
    payload_type = Column(String) # possible values (GraphQL, Binary, Raw, Form Data) DropDown
    pyload_base_url = Column(String) # must be valid 
    payload_method = Column(String) # DropDown
    payload_route = Column(String) # must be valid
    payload_headers = Column(String) 
    payload_body = Column(String)
    is_active = Column(Boolean)
    test_interval_in_hrs = Column(Float)
    benchmark_knowledge_id = Column(String)
    registered_at = Column(DateTime, default=lambda: datetime.now(UTC))
