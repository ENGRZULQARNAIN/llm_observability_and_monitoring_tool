from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # SQLite Database Configuration
    DATABASE_URL: str = 'sqlite:///./app_database.db'
    DATABASE_ECHO: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

