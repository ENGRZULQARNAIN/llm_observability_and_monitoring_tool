import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.background import BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import multiprocessing
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

# Global variable to track monitor processes
monitor_process = None

def run_monitor_in_process():
    """Run a single monitoring job in a separate process to avoid blocking the main application"""
    # This runs in a separate process
    import asyncio
    from modules.monitor import project_monitoror
    from core.logger import logger
    
    async def run_once():
        try:
            await project_monitoror.project_monitoror()
            logger.info("Project monitoror executed successfully in separate process")
        except Exception as e:
            logger.error(f"Error in separate process monitor: {e}")
    
    # Run the event loop in the separate process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_once())

def run_periodic_monitor_in_process():
    """Run the periodic monitoring in a separate process to avoid blocking the main application"""
    # This runs in a separate process
    import asyncio
    import time
    from modules.monitor import project_monitoror
    from core.logger import logger
    
    async def run_periodically():
        while True:
            try:
                await project_monitoror.project_monitoror()
                logger.info("Periodic project monitoror executed successfully")
            except Exception as e:
                logger.error(f"Error in periodic monitor: {e}")
            
            # Sleep between monitoring runs
            await asyncio.sleep(3600//4)  # Sleep for 0.25 hour
    
    # Run the event loop in the separate process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_periodically())

async def startup_event():
    """
    Runs when the application starts.
    Add initialization tasks here.
    """
    try:
        # Initialize your startup tasks here
        logger.info("Starting OBAM AI application...")
        create_tables()
        logger.info("Starting project monitoror as a background task...")
        
        # Start automatic monitoring in a separate process instead of using asyncio
        global monitor_process
        
        # Create and start a new process for periodic monitoring
        monitor_process = multiprocessing.Process(target=run_periodic_monitor_in_process)
        monitor_process.daemon = True  # This makes the process exit when the main process exits
        monitor_process.start()
        
        logger.info("OBAM AI application started successfully - monitoring running in separate process")
    except Exception as e:
        logger.error(f"Startup error: {e}")

async def run_project_monitoror(background_tasks: BackgroundTasks):
    """
    Wrapper function to call the project_monitoror function as a background task.
    This ensures requests never wait for monitoring to complete.
    """
    # Use a separate process to avoid blocking the main event loop completely
    global monitor_process
    
    # Check if a monitor process is already running
    if monitor_process is not None and monitor_process.is_alive():
        return {"message": "Monitoring is already running in background"}
    
    # Create and start a new process for monitoring
    monitor_process = multiprocessing.Process(target=run_monitor_in_process)
    monitor_process.daemon = True  # This makes the process exit when the main process exits
    monitor_process.start()
    
    return {"message": "Project monitoring started in a separate process"}

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
    return {"message":"OBAM AI: v0.2.4"}

@application.post("/api/v1/trigger-monitor")
async def trigger_monitor(background_tasks: BackgroundTasks):
    """
    Trigger the project monitor manually.
    This implementation runs monitoring in a separate process to guarantee no blocking.
    """
    return await run_project_monitoror(background_tasks)

application.include_router(auth_routers.router, prefix="/api/v1")
application.include_router(services.router, prefix="/api/v1")
application.include_router(project_routers.router, prefix="/api/v1")
application.include_router(benchmark_routes.router, prefix="/api/v1")


