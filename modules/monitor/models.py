from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, create_engine, desc)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


# unique value inserted for user id
class TestInfo(Base):
    __tablename__ = "test_info"
    test_id = Column(String, primary_key=True)
    user_id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.project_id"))
    test_status = Column(String, nullable=False)
    hallucination_score = Column(Float, nullable=True)
    helpfullness_score = Column(Float, nullable=True)
    last_test_conducted = Column(DateTime, default=datetime.utcnow)
    question = Column(String, nullable=False)
    student_answer = Column(String, nullable=False)
    factual_answer = Column(String, nullable=False)
    difficulty_level = Column(String, nullable=False)
