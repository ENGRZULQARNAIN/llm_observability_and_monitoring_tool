import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.background import BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
# Get the absolute path to your app directory
BASE_DIR = Path(__file__).resolve().parent

# Add the app directory to Python path
sys.path.append(str(BASE_DIR))
from core.database import create_tables
from modules.Auth import auth_routers
from core.logger import logger
from modules.project_connections import project_routers
from modules.benchmark import routes as benchmark_routes
from modules.monitor import project_monitoror
from modules import services
import asyncio

async def scheduled_project_monitoror():
    """
    Runs the project_monitoror function periodically.
    """
    while True:
        try:
            await project_monitoror.project_monitoror()
            logger.info("Project monitoror executed successfully")
        except Exception as e:
            logger.error(f"Error in scheduled project monitoror: {e}")
        
        # Wait for some time before running again (e.g., every hour)
        await asyncio.sleep(3600//2)  # Sleep for 0.5 hour

async def startup_event():
    """
    Runs when the application starts.
    Add initialization tasks here.
    """
    try:
        # Initialize your startup tasks here
        logger.info("Starting OBAM AI application...")
        # create_tables()
        logger.info("Starting project monitoror as a background task...")
        # Create the background task properly
        asyncio.create_task(scheduled_project_monitoror())
        logger.info("OBAM AI application started successfully")
    except Exception as e:
        logger.error(f"Startup error: {e}")

async def run_project_monitoror():
    """
    Wrapper function to call the project_monitoror function.
    """
    await project_monitoror.project_monitoror()

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
    return {"message":"OBAM AI: v0.2.2"}


application.include_router(auth_routers.router, prefix="/api/v1")
application.include_router(services.router, prefix="/api/v1")
application.include_router(project_routers.router, prefix="/api/v1")
application.include_router(benchmark_routes.router, prefix="/api/v1")


