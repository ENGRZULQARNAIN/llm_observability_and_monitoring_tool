from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # SQLite Database Configuration
    DATABASE_URL: str = 'sqlite:///./app_database.db'
    DATABASE_ECHO: bool = False
    BASE_URL : str = 'http://fypobservabillity-env.eba-una3djfn.us-east-1.elasticbeanstalk.com/'

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

