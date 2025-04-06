from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta
from modules.project_connections.models import Projects
from modules.monitor.models import TestInfo
from core.logger import logger
from core.database import get_db, SessionLocal
from modules.benchmark.utils import TestRunner

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
                    # Create and run test runner
                    test_runner = TestRunner(project.project_id)
                    try:
                        await test_runner.run()
                        logger.info(f"Tests completed for project {project.project_name}")
                    except Exception as e:
                        logger.error(f"Error running tests for project {project.project_name}: {str(e)}")
        
        return projects
    except Exception as e:
        # Log the error appropriately
        logger.error(f"Error in project_monitoror: {str(e)}")
        raise
    finally:
        if db:
            db.close()