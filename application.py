import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.logger import logger


# Get the absolute path to your app directory
BASE_DIR = Path(__file__).resolve().parent

# Add the app directory to Python path
sys.path.append(str(BASE_DIR))
from core.database import create_tables
from modules.Auth import auth_routers
from modules.project_connections import project_routers
from modules import services
print("Python path:", sys.path)
print("Current working directory:", os.getcwd())
print("Base directory:", BASE_DIR)


async def startup_event():
    """
    Runs when the application starts.
    Add initialization tasks here.
    """
    try:
        # Initialize your startup tasks here
        logger.info("Starting OBAM AI application...")
        # create_tables()
    except Exception as e:
        logger.error(f"Startup error: {e}")

# Initialize FastAPI application and register the startup event
application = FastAPI(
    title="OBAM AI FYP",
    on_startup=[startup_event] 
)


application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@application.get("/")
async def read_items():
    return {"message":"OBAM AI: v0.1.8"}


application.include_router(auth_routers.router)

application.include_router(services.router)
application.include_router(project_routers.router)