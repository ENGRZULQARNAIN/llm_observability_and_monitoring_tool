from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta
from modules.project_connections.models import Projects
from modules.monitor.models import TestInfo
from core.logger import logger
from core.database import get_db, SessionLocal
from modules.benchmark.utils import TestRunner
import asyncio

async def project_monitoror():
    """
    Monitor projects based on their testing intervals and last registered time.
    
    Returns:
        List[Project]: List of projects that need testing based on their interval
    """
    db = None
    try:
        logger.info("Running project monitoror...")
        # Get current time
        current_time = datetime.utcnow()
        db = SessionLocal()
        projects = db.query(Projects).all()
        
        # Create a list to store all test runner tasks
        test_tasks = []
        
        for project in projects:
            if project.is_active:
                project_test_info = db.execute(select(TestInfo).filter(TestInfo.project_id == project.project_id)).first()
                
                # Check if project needs testing
                should_test = False
                if project_test_info is None:
                    logger.info(f"Project {project.project_name} has no test info. Running initial tests...")
                    should_test = True
                else:
                    project_test_info = project_test_info[0]  # Extract from result proxy
                    # Calculate the time difference between the last test and now
                    time_diff = current_time - project_test_info.last_test_conducted
                    if time_diff >= timedelta(hours=project.test_interval_in_hrs):
                        logger.info(f"Project {project.project_name} needs testing. Running tests...")
                        should_test = True
                
                if should_test:
                    # Create test runner and add to tasks list
                    test_runner = TestRunner(project.project_id)
                    # Add task to our list
                    test_tasks.append(
                        run_test_with_timeout(test_runner, project.project_name)
                    )
        
        # Run all test tasks concurrently if there are any
        if test_tasks:
            logger.info(f"Running {len(test_tasks)} test tasks concurrently")
            # Wait for all tasks to complete, with a maximum timeout
            await asyncio.gather(*test_tasks, return_exceptions=True)
            logger.info("All test tasks completed")
        else:
            logger.info("No projects require testing at this time")
        
        return projects
    except Exception as e:
        # Log the error appropriately
        logger.error(f"Error in project_monitoror: {str(e)}")
        raise
    finally:
        if db:
            db.close()

async def run_test_with_timeout(test_runner, project_name, timeout_seconds=300):
    """
    Run a test with a timeout to prevent it from blocking indefinitely.
    
    Args:
        test_runner: The TestRunner instance
        project_name: Name of the project for logging
        timeout_seconds: Maximum time to allow for the test to run
        
    Returns:
        Result of the test or None if timed out
    """
    try:
        # Run the test with a timeout
        result = await asyncio.wait_for(test_runner.run(), timeout=timeout_seconds)
        logger.info(f"Tests completed for project {project_name}")
        return result
    except asyncio.TimeoutError:
        logger.warning(f"Test for project {project_name} timed out after {timeout_seconds} seconds")
        return None
    except Exception as e:
        logger.error(f"Error running tests for project {project_name}: {str(e)}")
        return None