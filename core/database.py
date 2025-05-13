from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import Settings, get_settings
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Annotated
from fastapi import Depends
from core.logger import logger

Base = declarative_base()
settings = Settings()
SQL_ALCHEMMY_URL= settings.DATABASE_URL
engine = create_engine(SQL_ALCHEMMY_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)
# Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
async def get_mongodb(settings=None):
    """Get MongoDB connection asynchronously"""
    if settings is None:
        from core.config import get_settings
        settings = get_settings()
    print(f"MongoDB URL: {settings.MONGODB_URL}")
    print(f"MongoDB DB: {settings.MONGODB_DB}")
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client[settings.MONGODB_DB]
    return db
    # return AsyncIOMotorClient(settings.MONGODB_URL)[settings.MONGODB_DB]